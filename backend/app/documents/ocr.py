# PaddleOCR 기반 로컬 문자 인식(이미지 전처리·스캔 PDF·신뢰도 계산)을 담당하는 파일
"""Local OCR for scanned documents built on PaddleOCR.

The engine runs fully on this machine: uploaded images never leave the server
for text extraction, and downstream redaction/risk analysis reuses the existing
document pipeline. If PaddleOCR is not installed (or a file cannot even be
decoded) the recognizers return None so the legacy consent + LLM path applies.
"""
from __future__ import annotations

import io
import logging
import os
import threading
from dataclasses import dataclass

from ..core.config import settings

# Paddle's native inference runtime cannot read model files from paths with
# non-ASCII characters (e.g. a Korean Windows user name). Relocate the model
# cache to an ASCII path before paddlex is imported for the first time.
if os.name == "nt" and not os.environ.get("PADDLE_PDX_CACHE_HOME"):
    try:
        os.path.expanduser("~/.paddlex").encode("ascii")
    except UnicodeEncodeError:
        os.environ["PADDLE_PDX_CACHE_HOME"] = r"C:\Users\Public\jbig-paddlex"

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_engine = None
_engine_failed = False


@dataclass(frozen=True)
class OCRResult:
    text: str
    confidence: float
    pages: int = 1


def _get_engine():
    """Lazily build one PaddleOCR instance; korean covers Korean + Latin text.

    Vietnamese needs a separate latin-family model and stays a fallback for now."""
    global _engine, _engine_failed
    with _lock:
        if _engine is not None or _engine_failed or not settings.ocr_enabled:
            return _engine
        try:
            from paddleocr import PaddleOCR
            try:
                # enable_mkldnn=False: Paddle 3.x PIR + oneDNN is broken on Windows CPU.
                _engine = PaddleOCR(lang=settings.ocr_language, use_doc_orientation_classify=True, use_doc_unwarping=False, use_textline_orientation=True, enable_mkldnn=False)
            except TypeError:
                _engine = PaddleOCR(lang=settings.ocr_language, use_angle_cls=True, show_log=False)
        except Exception as error:
            _engine_failed = True
            logger.warning("PaddleOCR unavailable; falling back to legacy path: %s", type(error).__name__)
        return _engine


def ocr_available() -> bool:
    return _get_engine() is not None


def preprocess_image(image):
    """Minimal cleanup: EXIF rotation, grayscale, contrast, bounded resize."""
    from PIL import Image, ImageOps
    image = ImageOps.exif_transpose(image)
    image = ImageOps.autocontrast(image.convert("L"))
    longest = max(image.size)
    if longest > 2400:
        scale = 2400 / longest
        image = image.resize((int(image.width * scale), int(image.height * scale)))
    elif longest < 700:
        image = image.resize((image.width * 2, image.height * 2))
    return image.convert("RGB")


def _recognize_array(engine, array) -> tuple[list[str], list[float]]:
    """Adapter over PaddleOCR 3.x predict() and 2.x ocr() result shapes."""
    texts: list[str] = []
    scores: list[float] = []
    if hasattr(engine, "predict"):
        for page in engine.predict(array):
            texts.extend(page.get("rec_texts") or [])
            scores.extend(float(score) for score in (page.get("rec_scores") or []))
    else:
        for page in engine.ocr(array, cls=True) or []:
            for line in page or []:
                texts.append(line[1][0])
                scores.append(float(line[1][1]))
    return texts, scores


def _combine(texts: list[str], scores: list[float], pages: int) -> OCRResult:
    kept = [(text, score) for text, score in zip(texts, scores) if text.strip()]
    if not kept:
        return OCRResult(text="", confidence=0.0, pages=pages)
    total_weight = sum(len(text) for text, _ in kept)
    confidence = sum(len(text) * score for text, score in kept) / total_weight
    return OCRResult(text="\n".join(text for text, _ in kept), confidence=round(confidence, 3), pages=pages)


def recognize_image_bytes(content: bytes) -> OCRResult | None:
    """OCR one image. None = engine unavailable or bytes are not a decodable image."""
    engine = _get_engine()
    if engine is None:
        return None
    try:
        import numpy
        from PIL import Image
        image = preprocess_image(Image.open(io.BytesIO(content)))
    except Exception:
        return None
    try:
        texts, scores = _recognize_array(engine, numpy.array(image))
        return _combine(texts, scores, pages=1)
    except Exception as error:
        logger.warning("OCR failed on image: %s", type(error).__name__)
        return OCRResult(text="", confidence=0.0)


def recognize_pdf_bytes(content: bytes) -> OCRResult | None:
    """Rasterize up to OCR_MAX_PAGES pages of a scanned PDF and OCR each one."""
    engine = _get_engine()
    if engine is None:
        return None
    try:
        import fitz  # PyMuPDF
        import numpy
        from PIL import Image
        document = fitz.open(stream=content, filetype="pdf")
    except Exception:
        return None
    texts: list[str] = []
    scores: list[float] = []
    pages = min(document.page_count, settings.ocr_max_pages)
    try:
        for index in range(pages):
            pixmap = document.load_page(index).get_pixmap(dpi=200)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            page_texts, page_scores = _recognize_array(engine, numpy.array(preprocess_image(image)))
            texts.extend(page_texts)
            scores.extend(page_scores)
    except Exception as error:
        logger.warning("OCR failed on PDF page: %s", type(error).__name__)
    finally:
        document.close()
    return _combine(texts, scores, pages=pages)
