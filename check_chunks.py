import sys
import os
sys.path.append(os.getcwd())
from rag_ingestor import FileIngestor

ingestor = FileIngestor()
pdf_path = "uploaded_docs/Resume.pdf"
if os.path.exists(pdf_path):
    chunks, filename = ingestor.process_file(pdf_path)
    print(f"File: {filename}")
    print(f"Number of chunks: {len(chunks)}")
    for i, c in enumerate(chunks[:3]):
        print(f"Chunk {i} (len={len(c['text'])}):")
        print(repr(c['text'][:200]) + "...")
        print("-" * 20)
else:
    print("PDF not found")
