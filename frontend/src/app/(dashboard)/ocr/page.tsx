"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ScanEye,
  Play,
  Trash2,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Filter,
} from "lucide-react";
import api from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface OcrJob {
  id: string;
  file_id: string;
  file_name: string;
  status: "queued" | "processing" | "completed" | "failed";
  language: string;
  confidence: number | null;
  text_length: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

const statusConfig: Record<
  string,
  { variant: "default" | "secondary" | "destructive" | "success" | "warning"; icon: typeof Clock }
> = {
  queued: { variant: "warning", icon: Clock },
  processing: { variant: "secondary", icon: Loader2 },
  completed: { variant: "success", icon: CheckCircle },
  failed: { variant: "destructive", icon: XCircle },
};

export default function OcrPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { data: jobs = [], isLoading } = useQuery<OcrJob[]>({
    queryKey: ["ocr-jobs"],
    queryFn: async () => {
      const res = await api.get("/ocr/jobs");
      return Array.isArray(res.data) ? res.data : res.data.results || [];
    },
  });

  const rerunMutation = useMutation({
    mutationFn: async (jobId: string) => {
      await api.post(`/ocr/jobs/${jobId}/rerun`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ocr-jobs"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (jobId: string) => {
      await api.delete(`/ocr/jobs/${jobId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ocr-jobs"] });
    },
  });

  const filtered = jobs.filter((job) => {
    const matchesSearch = job.file_name.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || job.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const stats = {
    total: jobs.length,
    completed: jobs.filter((j) => j.status === "completed").length,
    failed: jobs.filter((j) => j.status === "failed").length,
    processing: jobs.filter((j) => j.status === "processing" || j.status === "queued").length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">OCR Jobs</h1>
          <p className="text-muted-foreground">
            Track and manage optical character recognition tasks
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => queryClient.invalidateQueries({ queryKey: ["ocr-jobs"] })}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Jobs</CardDescription>
            <CardTitle className="text-2xl">{stats.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Completed</CardDescription>
            <CardTitle className="text-2xl text-emerald-600">{stats.completed}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Failed</CardDescription>
            <CardTitle className="text-2xl text-red-600">{stats.failed}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>In Progress</CardDescription>
            <CardTitle className="text-2xl text-amber-600">{stats.processing}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Input
              placeholder="Search by file name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-sm"
            />
            <div className="flex items-center gap-1">
              <Filter className="h-4 w-4 text-muted-foreground" />
              {["all", "queued", "processing", "completed", "failed"].map((s) => (
                <Badge
                  key={s}
                  variant={statusFilter === s ? "default" : "outline"}
                  className="cursor-pointer capitalize"
                  onClick={() => setStatusFilter(s)}
                >
                  {s}
                </Badge>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8 text-muted-foreground">
              Loading OCR jobs...
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <ScanEye className="mb-4 h-12 w-12 opacity-50" />
              <p className="text-lg font-medium">No OCR jobs found</p>
              <p className="text-sm">
                {search || statusFilter !== "all"
                  ? "Try adjusting your filters"
                  : "OCR jobs will appear here when documents are processed"}
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>File</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Language</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Text Length</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead className="w-20"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((job) => {
                  const config = statusConfig[job.status] || statusConfig.queued;
                  const StatusIcon = config.icon;
                  return (
                    <TableRow key={job.id}>
                      <TableCell>
                        <p className="font-medium">{job.file_name}</p>
                        <p className="text-xs text-muted-foreground">{job.file_id}</p>
                      </TableCell>
                      <TableCell>
                        <Badge variant={config.variant} className="gap-1">
                          <StatusIcon className="h-3 w-3" />
                          {job.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">{job.language || "—"}</TableCell>
                      <TableCell className="text-sm">
                        {job.confidence != null ? `${(job.confidence * 100).toFixed(1)}%` : "—"}
                      </TableCell>
                      <TableCell className="text-sm">{job.text_length.toLocaleString()}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDateTime(job.created_at)}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {job.completed_at ? formatDateTime(job.completed_at) : "—"}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          {(job.status === "failed" || job.status === "completed") && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => rerunMutation.mutate(job.id)}
                              disabled={rerunMutation.isPending}
                              title="Re-run OCR"
                            >
                              <Play className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive"
                            onClick={() => deleteMutation.mutate(job.id)}
                            disabled={deleteMutation.isPending}
                            title="Delete job"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {filtered.length > 0 && (
        <p className="text-sm text-muted-foreground">
          {filtered.length} job(s) shown
        </p>
      )}
    </div>
  );
}
