import sys
import os
sys.path.append(os.getcwd())
from rag_ingestor import FileIngestor

ingestor = FileIngestor()
pdf_path = "uploaded_docs/Ignisia Problem Statements.pdf"
if os.path.exists(pdf_path):
    print(f"Testing semantic chunking on {pdf_path}...")
    chunks, filename = ingestor.process_file(pdf_path)
    print(f"Number of semantic chunks: {len(chunks)}")
    for i, c in enumerate(chunks[:5]):
        print(f"Chunk {i} (Page {c['page']}, len={len(c['text'])}):")
        print(repr(c['text'][:200]) + "...")
        print("-" * 20)
else:
    print("PDF not found")
