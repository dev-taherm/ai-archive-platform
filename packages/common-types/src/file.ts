import { z } from "zod";

export const FileStatusSchema = z.enum([
  "pending",
  "processing",
  "indexing",
  "completed",
  "failed",
  "deleted",
  "duplicate",
]);
export type FileStatus = z.infer<typeof FileStatusSchema>;

export const FileSourceSchema = z.enum(["upload", "agent", "import"]);
export type FileSource = z.infer<typeof FileSourceSchema>;

export const SyncFilePayloadSchema = z.object({
  local_path: z.string(),
  file_hash: z.string(),
  file_size: z.number(),
  mime_type: z.string().default("application/octet-stream"),
  modified_at: z.string().optional(),
  metadata: z.record(z.unknown()).default({}),
  extracted_text: z.string().default(""),
  markdown: z.string().default(""),
  content_blocks: z.array(z.record(z.unknown())).default([]),
  tables: z.array(z.record(z.unknown())).default([]),
  images: z.array(z.record(z.unknown())).default([]),
  language: z.string().default("unknown"),
  word_count: z.number().default(0),
  char_count: z.number().default(0),
  page_count: z.number().default(0),
  ocr_used: z.boolean().default(false),
  agent_version: z.string().default(""),
  processing_version: z.string().default(""),
  parser_version: z.string().default(""),
  ocr_engine: z.string().default(""),
});
export type SyncFilePayload = z.infer<typeof SyncFilePayloadSchema>;

export const FileRecordSchema = z.object({
  id: z.string().uuid(),
  path: z.string(),
  original_name: z.string().optional(),
  mime_type: z.string(),
  size_bytes: z.number(),
  content_hash: z.string(),
  status: FileStatusSchema.default("pending"),
  source: FileSourceSchema.default("upload"),
  agent_id: z.string().uuid().optional(),
  tags: z.array(z.string()).default([]),
  metadata: z.record(z.unknown()).default({}),
  duplicate_group_id: z.string().uuid().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type FileRecord = z.infer<typeof FileRecordSchema>;
