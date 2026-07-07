/** Processing version tag — bump whenever the pipeline contract changes. */
export const PROCESSING_VERSION = "edge-document-pipeline-v2";

/** Shared constants. */
export const DOCUMENT_CATEGORIES = [
  "invoice", "receipt", "contract", "report", "letter", "memo",
  "email", "resume", "academic_paper", "legal_document",
  "financial_statement", "technical_specification", "meeting_notes",
  "proposal", "presentation", "spreadsheet", "code", "data_export",
  "other",
] as const;

export const DOCUMENT_CATEGORIES_SET = new Set(DOCUMENT_CATEGORIES);

export const IMAGE_EXTENSIONS = new Set([
  ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp",
]);

export const DEFAULT_CHUNK_SIZE = 1000;
export const DEFAULT_CHUNK_OVERLAP = 200;
