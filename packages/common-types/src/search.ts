import { z } from "zod";

export const SearchRequestSchema = z.object({
  query: z.string(),
  doc_types: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  limit: z.number().default(20),
  offset: z.number().default(0),
  min_confidence: z.number().min(0).max(1).optional(),
  date_from: z.string().optional(),
  date_to: z.string().optional(),
});
export type SearchRequest = z.infer<typeof SearchRequestSchema>;

export const SearchResultSchema = z.object({
  document_id: z.string().uuid(),
  file_id: z.string().uuid(),
  title: z.string(),
  snippet: z.string(),
  score: z.number(),
  doc_type: z.string(),
  page_count: z.number().default(0),
  chunk_count: z.number().default(0),
  created_at: z.string(),
});
export type SearchResult = z.infer<typeof SearchResultSchema>;

export const SearchResponseSchema = z.object({
  results: z.array(SearchResultSchema),
  total: z.number(),
  query: z.string(),
  took_ms: z.number(),
});
export type SearchResponse = z.infer<typeof SearchResponseSchema>;
