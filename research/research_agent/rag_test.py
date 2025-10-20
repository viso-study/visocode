from local_pdf_rag_tool import LocalPDFRAGTool

rag = LocalPDFRAGTool()  # <-- correct
chunks = rag.forward(
    question="What are the normal equations that distributing A⊤ yields:?",
    pdf_paths=["./docs/main.pdf"],
    top_n=3
)

for i, c in enumerate(chunks, 1):
    print(f"\n--- Chunk {i} ---\n{c[:600]}")
