"""OCR extraction via EasyOCR.

No system `tesseract` binary is available in this environment, and pytesseract
requires one — so this uses EasyOCR, a pure-pip package that runs on the torch
install already present for sentence-transformers. Reader is loaded once and
cached, like the embedding model in `embeddings.py`.
"""

import io

import numpy as np
import streamlit as st
from PIL import Image, ImageOps

from config import OCR_LANGUAGES


class OCRExtractionError(Exception):
    """Raised when an image cannot be decoded or OCR'd."""


@st.cache_resource(show_spinner="Loading OCR model...")
def load_ocr_reader(languages: tuple[str, ...] = OCR_LANGUAGES):
    import easyocr

    return easyocr.Reader(list(languages), gpu=False)


def _preprocess_image(image: Image.Image) -> Image.Image:
    """Basic handling for noisy scans, rotated pages, and low contrast.

    Applies EXIF-based auto-rotation and contrast normalization — cheap steps
    that help EasyOCR on real-world scanned/photographed documents without
    pulling in a heavier CV dependency.
    """
    image = ImageOps.exif_transpose(image)
    image = image.convert("L")  # grayscale
    image = ImageOps.autocontrast(image, cutoff=1)
    return image.convert("RGB")


def extract_text_from_image_bytes(
    image_bytes: bytes,
    reader=None,
) -> tuple[str, float]:
    """OCR a single image's raw bytes. Returns (extracted_text, mean_confidence).

    mean_confidence is 0.0 when no text was detected at all — callers treat
    that as an empty/unreadable page rather than a hard failure.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        raise OCRExtractionError(f"Could not decode image: {exc}") from exc

    processed = _preprocess_image(image)
    reader = reader or load_ocr_reader()

    try:
        detections = reader.readtext(np.array(processed))
    except Exception as exc:
        raise OCRExtractionError(f"OCR failed: {exc}") from exc

    if not detections:
        return "", 0.0

    texts = [text for _, text, _ in detections]
    confidences = [float(conf) for _, _, conf in detections]
    mean_confidence = sum(confidences) / len(confidences)
    return " ".join(texts).strip(), mean_confidence
