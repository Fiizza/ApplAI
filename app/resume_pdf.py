import io
import pdfplumber


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract plain text from a resume PDF, page by page."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts).strip()