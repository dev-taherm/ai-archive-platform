import { z } from "zod";

export const AgentStatusSchema = z.enum([
  "online",
  "offline",
  "syncing",
  "error",
]);
export type AgentStatus = z.infer<typeof AgentStatusSchema>;

export const AgentCapabilitySchema = z.enum([
  "scan",
  "ocr",
  "parse",
  "embed",
]);
export type AgentCapability = z.infer<typeof AgentCapabilitySchema>;

export const AgentFolderSchema = z.object({
  id: z.string().uuid().optional(),
  local_path: z.string(),
  label: z.string().optional(),
  is_active: z.boolean().default(true),
  last_scanned_at: z.string().optional(),
  file_count: z.number().default(0),
});
export type AgentFolder = z.infer<typeof AgentFolderSchema>;

export const AgentSchema = z.object({
  id: z.string().uuid().optional(),
  agent_id: z.string(),
  name: z.string(),
  status: AgentStatusSchema.default("online"),
  sync_interval_minutes: z.number().default(30),
  max_file_size_mb: z.number().default(100),
  push_original_files: z.boolean().default(false),
  platform: z.string().optional(),
  hostname: z.string().optional(),
  ip_address: z.string().optional(),
  agent_version: z.string().optional(),
  capabilities: z.array(AgentCapabilitySchema).default(["scan", "ocr", "parse"]),
  last_seen: z.string().optional(),
  last_sync_at: z.string().optional(),
  files_count: z.number().default(0),
  total_size_bytes: z.number().default(0),
  folders: z.array(AgentFolderSchema).default([]),
  pending_commands_count: z.number().default(0),
  api_key: z.string().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});
export type Agent = z.infer<typeof AgentSchema>;

export const AgentHeartbeatSchema = z.object({
  agent_id: z.string(),
  status: AgentStatusSchema,
  platform: z.string().optional(),
  hostname: z.string().optional(),
  ip_address: z.string().optional(),
  agent_version: z.string().optional(),
  files_count: z.number().default(0),
  total_size_bytes: z.number().default(0),
  uptime_seconds: z.number().default(0),
  folders_monitored: z.array(z.string()).default([]),
});
export type AgentHeartbeat = z.infer<typeof AgentHeartbeatSchema>;

export const AgentCommandSchema = z.object({
  id: z.string().uuid().optional(),
  command_type: z.enum(["sync", "scan", "process", "config_update", "shutdown"]),
  payload: z.record(z.unknown()).default({}),
  status: z.enum(["pending", "delivered", "completed", "failed"]).default("pending"),
  result: z.record(z.unknown()).optional(),
  created_at: z.string().optional(),
  executed_at: z.string().optional(),
});
export type AgentCommand = z.infer<typeof AgentCommandSchema>;

export const AgentRegistrationSchema = z.object({
  agent_id: z.string(),
  name: z.string(),
  platform: z.string().optional(),
  hostname: z.string().optional(),
  agent_version: z.string().optional(),
  capabilities: z.array(AgentCapabilitySchema).default(["scan", "ocr", "parse"]),
  sync_interval_minutes: z.number().default(30),
  push_original_files: z.boolean().default(false),
});
export type AgentRegistration = z.infer<typeof AgentRegistrationSchema>;
