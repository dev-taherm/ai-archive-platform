import { z } from "zod";

export const ProviderTypeSchema = z.enum([
  "openai",
  "anthropic",
  "google",
  "azure",
  "ollama",
  "custom",
]);
export type ProviderType = z.infer<typeof ProviderTypeSchema>;

export const ProviderConfigSchema = z.object({
  id: z.string().uuid().optional(),
  provider_type: ProviderTypeSchema,
  label: z.string().optional(),
  api_key: z.string().optional(),
  base_url: z.string().optional(),
  default_model: z.string().optional(),
  is_active: z.boolean().default(true),
  priority: z.number().default(0),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});
export type ProviderConfig = z.infer<typeof ProviderConfigSchema>;
