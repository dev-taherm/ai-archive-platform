#!/usr/bin/env python3
"""Standalone OCR worker that runs in a subprocess.

Isolates PaddleOCR model loading (which can OOM) from the Django process.
Called by ocr_engine.py via subprocess with a timeout.

Usage:
    python ocr_worker.py <temp_file_path> <lang>

Output (JSON to stdout):
    {"text": "...", "error": null} or {"text": "", "error": "..."}
"""
from __future__ import annotations

import json
import sys
import os


def run_ocr(temp_path: str, lang: str = "en") -> dict[str, str | None]:
    """Run PaddleOCR on a temp file, fall back to Tesseract on failure."""
    try:
        from paddleocr import PaddleOCR
        engine = PaddleOCR(lang=lang)
        result = engine.ocr(temp_path, cls=True)
        if result and result[0]:
            lines = []
            for line in result[0]:
                if line and len(line) >= 2:
                    text = line[1][0]
                    if text and text.strip():
                        lines.append(text.strip())
            return {"text": "\n".join(lines), "error": None}
        return {"text": "", "error": None}
    except Exception:
        pass

    # Fallback to Tesseract
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(temp_path)
        tesseract_lang = "eng+ara" if lang in ("en", "eng", "ar", "ara") else lang
        text = pytesseract.image_to_string(img, lang=tesseract_lang)
        return {"text": text.strip() if text else "", "error": None}
    except Exception as e:
        return {"text": "", "error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"text": "", "error": "Usage: ocr_worker.py <file_path> [lang]"}))
        sys.exit(1)

    temp_path = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "en"

    result = run_ocr(temp_path, lang)
    print(json.dumps(result))

    # Cleanup temp file
    try:
        os.unlink(temp_path)
    except OSError:
        pass
