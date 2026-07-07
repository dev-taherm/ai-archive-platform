import { z } from "zod";

export const PipelineStepSchema = z.enum([
  "load",
  "read",
  "ocr",
  "classify",
  "entities",
  "summary",
  "chunk",
  "embed",
  "complete",
]);
export type PipelineStep = z.infer<typeof PipelineStepSchema>;

export const PipelineResultSchema = z.object({
  document_id: z.string().uuid(),
  file_id: z.string().uuid(),
  status: z.string(),
  doc_type: z.string().optional(),
  chunk_count: z.number().default(0),
  embedding_count: z.number().default(0),
  summary: z.string().optional(),
  error: z.string().optional(),
  processing_log: z.array(z.string()).optional(),
  elapsed_ms: z.number().default(0),
});
export type PipelineResult = z.infer<typeof PipelineResultSchema>;
