import logging

import numpy as np
import pymupdf

logger = logging.getLogger(__name__)

_ocr_engine = None


def _load_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr import RapidOCR

        _ocr_engine = RapidOCR()
        logger.info("RapidOCR engine loaded")
    return _ocr_engine


def _ocr_pdf(pdf_data: bytes) -> str:
    """OCR an image-based (scanned) PDF using RapidOCR."""
    try:
        engine = _load_ocr_engine()
    except Exception:
        logger.warning("OCR engine unavailable; cannot extract scanned PDF text", exc_info=True)
        return ""

    doc = pymupdf.open(stream=pdf_data, filetype="pdf")
    page_texts: list[str] = []
    try:
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            if pix.n == 1:
                img = np.repeat(img, 3, axis=2)
            elif pix.n == 4:
                img = img[:, :, :3]
            result = engine(img)
            lines = result.txts if result and result.txts else []
            if lines:
                page_texts.append("\n".join(lines))
    finally:
        doc.close()

    return "\n\n".join(page_texts).strip()


def extract_text_from_file(uploaded_file) -> str:
    """Extract plain text from an uploaded PDF or TXT file.

    PDFs without a text layer (e.g. scanned documents) fall back to OCR.
    """
    name = uploaded_file.name.lower()
    data = uploaded_file.read()

    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace").strip()

    if name.endswith(".pdf"):
        doc = pymupdf.open(stream=data, filetype="pdf")
        try:
            text = "\n".join(page.get_text() for page in doc)
        finally:
            doc.close()
        text = text.strip()
        if text:
            return text
        return _ocr_pdf(data)

    return data.decode("utf-8", errors="replace").strip()
