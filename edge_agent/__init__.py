"""Edge Agent — Stateless document parse server for the AI Archive Platform.

Runs as a sidecar process to:
- Parse documents (MinerU / fallback)
- OCR scanned documents (PaddleOCR / Tesseract)

All persistence, file discovery, and sync lives in the desktop Rust app.
"""

__version__ = "0.1.0"
