from __future__ import annotations

import io
import shutil
from typing import Optional, Tuple

from PIL import Image


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def extract_image_text(file_bytes: bytes, language: str = "fra+eng") -> Tuple[str, str]:
    """OCR d'une image. Retourne (texte, message)."""
    if not tesseract_available():
        return "", "Tesseract n'est pas installé sur le serveur."

    try:
        import pytesseract
        image = Image.open(io.BytesIO(file_bytes))
        image = image.convert("RGB")
        text = pytesseract.image_to_string(image, lang=language)
        return text.strip(), "OCR Tesseract terminé."
    except Exception as exc:
        return "", f"OCR indisponible : {exc}"


def extract_pdf_ocr(file_bytes: bytes, language: str = "fra+eng", max_pages: int = 10) -> Tuple[str, str]:
    """Rend les pages PDF en images puis applique Tesseract."""
    if not tesseract_available():
        return "", "Tesseract n'est pas installé sur le serveur."

    try:
        import fitz
        import pytesseract

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        chunks = []
        for page_no, page in enumerate(doc):
            if page_no >= max_pages:
                break
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            txt = pytesseract.image_to_string(image, lang=language)
            if txt.strip():
                chunks.append(f"--- PAGE {page_no + 1} ---\n{txt.strip()}")
        return "\n\n".join(chunks), "OCR PDF terminé."
    except Exception as exc:
        return "", f"OCR PDF indisponible : {exc}"
