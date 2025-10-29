# utils/doc_utils.py
import re
from pathlib import Path
import docx2txt
import fitz  # pymupdf

def extract_text_from_pdf(path: str) -> str:
    """Extract text from PDF using PyMuPDF (fast, robust)."""
    try:
        doc = fitz.open(path)
        text_chunks = []
        for page in doc:
            text_chunks.append(page.get_text("text"))
        return "\n".join(text_chunks).strip()
    except Exception:
        # fallback: return empty
        return ""

def extract_text_from_docx(path: str) -> str:
    try:
        return docx2txt.process(path) or ""
    except Exception:
        return ""

def extract_text_from_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(str(p))
    elif suffix in [".docx", ".doc"]:
        return extract_text_from_docx(str(p))
    elif suffix == ".txt":
        return p.read_text(encoding="utf-8", errors="ignore")
    return ""
