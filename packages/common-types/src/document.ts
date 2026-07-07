import { z } from "zod";

export const DocumentTypeSchema = z.enum([
  "invoice",
  "contract",
  "report",
  "letter",
  "memo",
  "receipt",
  "email",
  "resume",
  "academic_paper",
  "legal_document",
  "financial_statement",
  "technical_specification",
  "meeting_notes",
  "proposal",
  "presentation",
  "spreadsheet",
  "code",
  "data_export",
  "other",
  "unknown",
]);
export type DocumentType = z.infer<typeof DocumentTypeSchema>;

export const ProcessingStatusSchema = z.enum([
  "pending",
  "processing",
  "extracting",
  "indexing",
  "completed",
  "failed",
  "retrying",
]);
export type ProcessingStatus = z.infer<typeof ProcessingStatusSchema>;

export const DocumentMetadataSchema = z.object({
  title: z.string().default(""),
  author: z.string().default(""),
  subject: z.string().default(""),
  keywords: z.array(z.string()).default([]),
  creation_date: z.string().optional(),
  modification_date: z.string().optional(),
  page_count: z.number().default(0),
  word_count: z.number().default(0),
  char_count: z.number().default(0),
  language: z.string().default("unknown"),
});
export type DocumentMetadata = z.infer<typeof DocumentMetadataSchema>;

export const DocumentSchema = z.object({
  id: z.string().uuid(),
  file_id: z.string().uuid(),
  doc_type: DocumentTypeSchema.default("unknown"),
  processing_status: ProcessingStatusSchema.default("pending"),
  title: z.string().default(""),
  author: z.string().default(""),
  subject: z.string().default(""),
  language: z.string().default("unknown"),
  word_count: z.number().default(0),
  page_count: z.number().default(0),
  chunk_count: z.number().default(0),
  classification_confidence: z.number().nullable().optional(),
  tags: z.array(z.string()).default([]),
  extracted_text: z.string().default(""),
  error_message: z.string().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type Document = z.infer<typeof DocumentSchema>;

export const DocumentChunkSchema = z.object({
  id: z.string().uuid().optional(),
  document_id: z.string().uuid(),
  chunk_index: z.number(),
  content: z.string(),
  start_offset: z.number().default(0),
  end_offset: z.number().default(0),
  embedding_id: z.string().optional(),
  metadata: z.record(z.unknown()).default({}),
});
export type DocumentChunk = z.infer<typeof DocumentChunkSchema>;
