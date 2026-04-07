import fitz
import io
from PIL import Image

def render_pdf_page_with_highlight(pdf_path: str, page_num: int, search_text: str):
    try:
        if not search_text or len(search_text.strip()) < 3:
            with fitz.open(pdf_path) as doc:
                page = doc.load_page(page_num - 1)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                return pix.tobytes("png")

        with fitz.open(pdf_path) as doc:
            page = doc.load_page(page_num - 1)
            
            lines = [line.strip() for line in search_text.split('\n') if len(line.strip()) > 5]
            
            if not lines:
                lines = [s.strip() for s in search_text.split('.') if len(s.strip()) > 5]

            highlight_count = 0
            for line in lines:
                text_instances = page.search_for(line)
                for inst in text_instances:
                    page.add_highlight_annot(inst)
                    highlight_count += 1
            
            if highlight_count == 0:
                text_instances = page.search_for(search_text[:100])
                for inst in text_instances:
                    page.add_highlight_annot(inst)

            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            return pix.tobytes("png")
            
    except Exception as e:
        print(f"[ERROR] PDF Rendering failed: {e}")
        return None
