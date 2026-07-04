"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ArrowLeft,
  FileText,
  Calendar,
  Globe,
  Hash,
  Layers,
  AlertCircle,
} from "lucide-react";
import { formatDateTime } from "@/lib/utils";
import type { Document } from "@/types/api";

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "success" | "warning"> = {
  queued: "warning",
  extracting: "secondary",
  classifying: "secondary",
  indexing: "secondary",
  completed: "success",
  failed: "destructive",
  retrying: "warning",
};

export default function DocumentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const { data: doc, isLoading, error } = useQuery<Document>({
    queryKey: ["document", id],
    queryFn: async () => {
      const res = await api.get<Document>(`/documents/${id}`);
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-12 text-muted-foreground">
        Loading document...
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <AlertCircle className="mb-4 h-12 w-12 opacity-50" />
        <p className="text-lg font-medium">Document not found</p>
        <Link href="/documents">
          <Button variant="link">Back to documents</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/documents">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{doc.title || doc.doc_type}</h1>
          <p className="text-muted-foreground">
            {doc.subject || doc.author || "No description"}
          </p>
        </div>
        <Badge variant={statusVariant[doc.processing_status] || "secondary"}>
          {doc.processing_status}
        </Badge>
      </div>

      {/* Metadata Grid */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileText className="h-4 w-4" />
              Type
            </div>
            <p className="mt-1 text-lg font-semibold">{doc.doc_type}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Globe className="h-4 w-4" />
              Language
            </div>
            <p className="mt-1 text-lg font-semibold">{doc.language || "Unknown"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Hash className="h-4 w-4" />
              Words
            </div>
            <p className="mt-1 text-lg font-semibold">{doc.word_count.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Layers className="h-4 w-4" />
              Chunks
            </div>
            <p className="mt-1 text-lg font-semibold">{doc.chunk_count}</p>
          </CardContent>
        </Card>
      </div>

      {/* Details */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Classification */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Classification</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Type</span>
              <span className="font-medium">{doc.doc_type}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Confidence</span>
              <span className="font-medium">
                {doc.classification_confidence != null
                  ? `${(doc.classification_confidence * 100).toFixed(1)}%`
                  : "—"}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Pages</span>
              <span className="font-medium">{doc.page_count || "—"}</span>
            </div>
          </CardContent>
        </Card>

        {/* Timestamps */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Timeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Created:</span>
              <span>{formatDateTime(doc.created_at)}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Updated:</span>
              <span>{formatDateTime(doc.updated_at)}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tags */}
      {doc.tags.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Tags</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {doc.tags.map((tag) => (
                <Badge key={tag} variant="outline">
                  {tag}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Extracted Text Preview */}
      {doc.extracted_text_preview && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Extracted Text Preview</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-64 overflow-auto rounded-md bg-muted p-4 text-sm whitespace-pre-wrap">
              {doc.extracted_text_preview}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Error */}
      {doc.error_message && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-base text-destructive">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-destructive">{doc.error_message}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
