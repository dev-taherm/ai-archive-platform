"""Edge Agent — local document processing for the AI Archive Platform.

Runs on user machines (laptop, desktop, NAS) to:
- Watch folders for changes
- Scan and fingerprint files
- Parse documents (MinerU / fallback)
- OCR scanned documents (PaddleOCR / Tesseract)
- Store metadata in local SQLite
- Sync results to the SaaS platform
"""

__version__ = "0.1.0"
