import json
import os
import time
from io import BytesIO
from typing import List

import requests
from PIL import Image, ImageOps
from smolagents import Tool


def _coerce_concepts(concepts: str) -> List[str]:
    """
    Accepts:
      - a JSON string with visual_brief: [{"concept": "...", "caption": "..."}]
      - a JSON string list of concepts
      - a comma-separated string
    Returns a flat list of concept strings.
    """
    try:
        obj = json.loads(concepts)
        if isinstance(obj, dict) and "visual_brief" in obj:
            return [
                item.get("concept", "").strip()
                for item in obj.get("visual_brief", [])
                if isinstance(item, dict) and item.get("concept")
            ]
        if isinstance(obj, list):
            return [str(x).strip() for x in obj if str(x).strip()]
    except Exception:
        pass
    # Fallback: comma-separated string
    return [c.strip() for c in concepts.split(",") if c.strip()]


def _background_to_transparent(img: Image.Image, light_threshold: int = 245) -> Image.Image:
    """
    Convert near-white background to transparent. Works best for flat, minimalist icons.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    r, g, b, a = img.split()
    gray = ImageOps.grayscale(Image.merge("RGB", (r, g, b)))
    # mask: 255 for 'non-bg' (ink), 0 for bg
    mask = Image.eval(gray, lambda px: 255 if px < light_threshold else 0)
    img.putalpha(mask)
    return img


class IconGenerationTool(Tool):
    name = "icon_generation"
    description = (
        "Generate simple, clear educational icons using Hugging Face FLUX models. "
        "Consumes visual_brief or concept list, produces PNGs with transparent backgrounds when possible."
    )
    inputs = {
        "concepts": {
            "type": "string",
            "description": "Either a JSON string with visual_brief, a JSON list of concept strings, or a comma-separated string.",
        },
        "model_id": {
            "type": "string",
            "description": "HF model id (e.g., 'black-forest-labs/FLUX.1-schnell' for speed or 'black-forest-labs/FLUX.1-dev' for quality).",
            "nullable": True,
            "default": "black-forest-labs/FLUX.1-schnell",
        },
        "style": {
            "type": "string",
            "description": "Visual style overrides; defaults to flat/minimal, transparent background, no text/math symbols.",
            "nullable": True,
            "default": None,
        },
        "context": {
            "type": "string",
            "description": "Short context to nudge icon content (e.g., 'for a 3Blue1Brown-style animation about gradients').",
            "nullable": True,
            "default": "",
        },
        "image_url": {
            "type": "string",
            "description": "Optional image URL for editing (if supported by the model).",
            "nullable": True,
            "default": None,
        },
    }
    output_type = "string"

    def __init__(self, api_key: str = None):
        super().__init__()
        # Load HF token strictly from 'hf_api_key.txt' unless explicitly passed
        if api_key is not None:
            self.hf_token = api_key.strip()
        else:
            token_path = "hf_api_key.txt"
            if not os.path.exists(token_path):
                raise RuntimeError(
                    "Hugging Face token file 'hf_api_key.txt' not found. "
                    "Create it with your HF token."
                )
            with open(token_path, "r", encoding="utf-8") as f:
                self.hf_token = f.read().strip()
            if not self.hf_token:
                raise RuntimeError("File 'hf_api_key.txt' is empty. Put your HF token inside.")

        os.makedirs("icons", exist_ok=True)
        self.base_url = "https://api-inference.huggingface.co/models"

    # ---------- HTTP helpers ----------
    def _post_image(self, model_id: str, payload: dict, retries: int = 3, backoff: float = 2.0) -> bytes:
        url = f"{self.base_url}/{model_id}"
        headers = {
            "Authorization": f"Bearer {self.hf_token}",
            "Content-Type": "application/json",
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        for attempt in range(1, retries + 1):
            resp = requests.post(url, data=data, headers=headers, timeout=90)
            # success returns image bytes directly
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                return resp.content
            # cold start or rate limit: retry
            if resp.status_code in (429, 503):
                time.sleep(backoff * attempt)
                continue
            if resp.status_code == 401:
                raise RuntimeError(
                    "HF request failed (401 Unauthorized). "
                    "Check the token in 'hf_api_key.txt'."
                )
            # other errors (JSON error payload or text)
            try:
                err = resp.json()
            except Exception:
                err = {"detail": resp.text[:200]}
            raise RuntimeError(f"HF request failed ({resp.status_code}): {err}")
        raise RuntimeError("HF request failed after retries (rate-limited or cold start).")

    # ---------- Main ----------
    def forward(
        self,
        concepts: str,
        model_id: str = None,
        style: str = None,
        context: str = "",
        image_url: str = None,
    ) -> str:
        """
        Generate PNG icons for given concepts (or a visual_brief JSON).
        Returns JSON with concept->file mappings and prompts used.
        """
        model = (model_id or "black-forest-labs/FLUX.1-schnell").strip()
        style = style or (
            "flat minimalist, clean shapes, high contrast foreground, "
            "transparent background, no text, no letters, no digits, no math symbols, "
            "educational diagram style"
        )

        concept_list = _coerce_concepts(concepts)
        if not concept_list:
            return json.dumps(
                {"generated_icons": [], "icon_paths": [], "total_generated": 0, "model_used": model},
                ensure_ascii=False
            )

        generated_icons = []
        paths = []

        for idx, concept in enumerate(concept_list, start=1):
            prompt = (
                f"{concept}. "
                f"Create a simple, clear educational icon; {style}. "
                f"Context: {context}. Focus on geometry/shape; avoid text and numbers."
            )
            payload = {
                "inputs": prompt,
                "parameters": {
                    "num_inference_steps": 24,
                    "guidance_scale": 3.0,
                }
            }
            if image_url:
                payload["image_url"] = image_url

            try:
                img_bytes = self._post_image(model, payload)
                img = Image.open(BytesIO(img_bytes)).convert("RGBA")
                img = _background_to_transparent(img, light_threshold=245)

                safe = "".join(ch for ch in concept if ch.isalnum() or ch in (" ", "-", "_")).rstrip()
                filename = f"icons/{safe.replace(' ', '_')}_icon_{idx}.png"
                img.save(filename, format="PNG")

                generated_icons.append({
                    "concept": concept,
                    "filename": filename,
                    "model": model,
                    "prompt": prompt,
                })
                paths.append(filename)
                print(f"✅ Icon for '{concept}' saved to {filename}")

            except Exception as e:
                print(f"❌ Icon generation failed for '{concept}' on {model}: {e}")

        return json.dumps({
            "generated_icons": generated_icons,
            "icon_paths": paths,
            "total_generated": len(generated_icons),
            "model_used": model,
        }, indent=2, ensure_ascii=False)
