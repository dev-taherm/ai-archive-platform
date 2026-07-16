// Badge variant type shared across feature components
export type BadgeVariant = "default" | "secondary" | "destructive" | "success" | "warning";

// Document processing status → badge variant
export const documentStatusVariant: Record<string, BadgeVariant> = {
  queued: "warning",
  extracting: "secondary",
  classifying: "secondary",
  indexing: "secondary",
  completed: "success",
  failed: "destructive",
  retrying: "warning",
};

// Agent connection status → badge variant
export const agentStatusVariant: Record<string, BadgeVariant> = {
  online: "success",
  syncing: "warning",
  offline: "secondary",
  error: "destructive",
};

// Workflow status → badge variant (superset covering both list and detail pages)
export const workflowStatusVariant: Record<string, BadgeVariant> = {
  draft: "secondary",
  active: "success",
  paused: "warning",
  completed: "success",
  failed: "destructive",
  running: "warning",
  succeeded: "success",
};

// Workflow step status → icon name (used with lucide-react)
export const stepStatusIconName: Record<string, string> = {
  pending: "Clock",
  running: "Loader2",
  completed: "CheckCircle",
  failed: "XCircle",
  skipped: "Clock",
};

// Document processing status → progress percentage
export const documentStatusProgress: Record<string, number> = {
  queued: 0,
  extracting: 25,
  classifying: 50,
  indexing: 75,
  completed: 100,
  failed: 100,
  retrying: 50,
};

// Document processing status → step label
export const documentStatusLabel: Record<string, string> = {
  queued: "Queued",
  extracting: "Extracting text...",
  classifying: "Classifying...",
  indexing: "Indexing...",
  completed: "Completed",
  failed: "Failed",
  retrying: "Retrying...",
};

// Document processing status → progress bar Tailwind indicator class
export const documentStatusColor: Record<string, string> = {
  queued: "bg-gradient-to-r from-brand-teal to-brand-cyan",
  extracting: "bg-gradient-to-r from-brand-teal to-brand-cyan",
  classifying: "bg-gradient-to-r from-brand-teal to-brand-cyan",
  indexing: "bg-gradient-to-r from-brand-teal to-brand-cyan",
  completed: "bg-emerald-500",
  failed: "bg-destructive",
  retrying: "bg-amber-500",
};

// Entity type → badge variant
export const entityTypeVariant: Record<string, "default" | "secondary" | "outline"> = {
  PERSON: "default",
  ORGANIZATION: "secondary",
  LOCATION: "outline",
  DATE: "default",
  MONEY: "secondary",
  "PRODUCT": "outline",
};

// Organization role → Tailwind color classes
export const roleColors: Record<string, string> = {
  owner: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
  admin: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  member: "bg-gray-100 text-gray-800 dark:bg-gray-800/30 dark:text-gray-300",
};
