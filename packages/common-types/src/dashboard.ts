import { z } from "zod";

export const DashboardStatsSchema = z.object({
  total_files: z.number().default(0),
  total_documents: z.number().default(0),
  total_chunks: z.number().default(0),
  total_agents: z.number().default(0),
  documents_by_type: z.record(z.number()).default({}),
  documents_last_7_days: z.number().default(0),
  storage_used_bytes: z.number().default(0),
  agents_online: z.number().default(0),
  recent_errors: z.number().default(0),
});
export type DashboardStats = z.infer<typeof DashboardStatsSchema>;
