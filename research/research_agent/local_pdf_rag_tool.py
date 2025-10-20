# local_pdf_rag_tool.py
# Minimal local PDF → (optional Tesseract OCR) → chunk → embed → retrieve top-N chunks
# Returns: list[str] (chunk texts)

import os, re, math, uuid, fitz, torch, faiss
from dataclasses import dataclass
from typing import List, Optional
from transformers import AutoTokenizer, AutoModel

# Optional: Tesseract OCR
try:
    import pytesseract
    from PIL import Image
    TESS_AVAILABLE = True
except Exception:
    TESS_AVAILABLE = False


@dataclass
class Chunk:
    text: str
    page_num: int


# ---------- OCR (Tesseract only) ----------
class TesseractAdapter:
    def run(self, image_path: str):
        if not TESS_AVAILABLE:
            raise RuntimeError("Tesseract not installed.")
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        # Keep a uniform structure similar to prior code path
        return {"text": text, "blocks": [{"text": text, "bbox": [0, 0, img.width, img.height]}]}


# ---------- PDF parsing ----------
class PDFProcessor:
    def __init__(self, ocr_adapter: Optional[TesseractAdapter] = None, dpi: int = 220):
        self.ocr_adapter = ocr_adapter
        self.dpi = dpi

    def pdf_to_text_blocks(self, pdf_path: str) -> List[str]:
        doc = fitz.open(pdf_path)
        blocks_all: List[str] = []
        img_dir = ".tmp_pdf_images"
        if self.ocr_adapter:
            os.makedirs(img_dir, exist_ok=True)

        for i, page in enumerate(doc):
            data = page.get_text("dict")
            blocks = []
            for b in data.get("blocks", []):
                if b.get("type") == 0:
                    txt = "".join(
                        span.get("text", "")
                        for line in b.get("lines", [])
                        for span in line.get("spans", [])
                    ).strip()
                    if txt:
                        blocks.append(txt)

            # If the page looks text-poor and OCR is available, try OCR on the page image
            if sum(len(t) for t in blocks) < 60 and self.ocr_adapter:
                img_path = os.path.join(img_dir, f"page_{i+1}.png")
                page.get_pixmap(dpi=self.dpi).save(img_path)
                ocr = self.ocr_adapter.run(img_path)
                if "blocks" in ocr:
                    blocks = [b["text"] for b in ocr["blocks"] if b.get("text")]

            blocks_all.extend(blocks)

        return blocks_all


# ---------- Simple chunker ----------
def chunk_texts(blocks: List[str], target_chars: int = 1000, overlap: int = 150) -> List[str]:
    chunks, buf = [], []
    total = 0
    for b in blocks:
        if total + len(b) > target_chars and buf:
            text = "\n".join(buf)
            chunks.append(text)
            tail = text[-overlap:] if overlap > 0 else ""
            buf = [tail] if tail else []
            total = len(tail)
        buf.append(b)
        total += len(b)
    if buf:
        chunks.append("\n".join(buf))
    return chunks


# ---------- Embeddings ----------
class HFEmbedder:
    def __init__(self, model_name: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model.eval()
        # infer dimension once
        self.dim = self.encode(["test"]).shape[1]

    @torch.no_grad()
    def encode(self, texts: List[str]):
        enc = self.tokenizer(texts, padding=True, truncation=True, max_length=1024, return_tensors="pt")
        enc = {k: v.to(self.device) for k, v in enc.items()}
        out = self.model(**enc)
        # mean-pool with mask
        last_hidden = out[0]
        mask = enc["attention_mask"].unsqueeze(-1).expand(last_hidden.size()).float()
        pooled = (last_hidden * mask).sum(1) / torch.clamp(mask.sum(1), min=1e-9)
        pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        return pooled.cpu()


# ---------- Core retriever ----------
class LocalPDFRAGTool:
    def __init__(self, embed_model: str = "Qwen/Qwen3-Embedding-0.6B", use_ocr: bool = True):
        self.embedder = HFEmbedder(embed_model)
        self.ocr = TesseractAdapter() if (use_ocr and TESS_AVAILABLE) else None
        self.pdf = PDFProcessor(ocr_adapter=self.ocr)

    def forward(self, question: str, pdf_paths: List[str], top_n: int = 5) -> List[str]:
        # 1. Extract + chunk all text
        chunks: List[str] = []
        for p in pdf_paths:
            blocks = self.pdf.pdf_to_text_blocks(p)
            chunks.extend(chunk_texts(blocks))

        if not chunks:
            return []

        # 2. Embed all chunks + question
        chunk_vecs = self.embedder.encode(chunks)
        q_vec = self.embedder.encode([question])

        # 3. Search top-N
        index = faiss.IndexFlatIP(self.embedder.dim)
        index.add(chunk_vecs.numpy())
        D, I = index.search(q_vec.numpy(), min(top_n, len(chunks)))
        top_texts = [chunks[i] for i in I[0] if i != -1]
        return top_texts
