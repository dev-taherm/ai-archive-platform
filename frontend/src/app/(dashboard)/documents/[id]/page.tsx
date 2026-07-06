"use client";

import { use } from "react";
import { useState } from "react";
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
  Tag,
  Brain,
  Lightbulb,
  Info,
  Download,
  Eye,
  X,
  FileImage,
  ChevronsUpDown,
} from "lucide-react";
import { formatDateTime } from "@/lib/utils";
import type { Document, DocumentMetadata } from "@/types/api";

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "success" | "warning"> = {
  queued: "warning",
  extracting: "secondary",
  classifying: "secondary",
  indexing: "secondary",
  completed: "success",
  failed: "destructive",
  retrying: "warning",
};

const entityTypeVariant: Record<string, "default" | "secondary" | "outline"> = {
  PERSON: "default",
  ORGANIZATION: "secondary",
  DATE: "outline",
  LOCATION: "default",
  EVENT: "secondary",
  MONEY: "outline",
};

export default function DocumentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  const { data: doc, isLoading, error } = useQuery<Document>({
    queryKey: ["document", id],
    queryFn: async () => {
      const res = await api.get<Document>(`/documents/${id}`);
      return res.data;
    },
  });

  const { data: metadata } = useQuery<DocumentMetadata>({
    queryKey: ["document-metadata", id],
    queryFn: async () => {
      const res = await api.get<DocumentMetadata>(`/documents/${id}/metadata`);
      return res.data;
    },
    enabled: !!doc,
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

      {/* Original File Info */}
      {doc.file_name && (
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">{doc.file_name}</p>
                  <p className="text-xs text-muted-foreground">{doc.file_mime_type || "Unknown type"}</p>
                </div>
              </div>
              <div className="flex gap-2">
                {doc.file_mime_type?.startsWith("image/") && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      const res = await api.get(`/files/${doc.file_id}/download`, { responseType: "blob" });
                      const url = URL.createObjectURL(res.data);
                      setPreviewUrl(url);
                    }}
                  >
                    <Eye className="mr-1 h-3 w-3" />
                    Preview
                  </Button>
                )}
                {doc.file_mime_type === "application/pdf" && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      const res = await api.get(`/files/${doc.file_id}/download`, { responseType: "blob" });
                      const url = URL.createObjectURL(res.data);
                      setPreviewUrl(url);
                    }}
                  >
                    <Eye className="mr-1 h-3 w-3" />
                    Preview
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    const res = await api.get(`/files/${doc.file_id}/download`, { responseType: "blob" });
                    const blob = new Blob([res.data]);
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = doc.file_name;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  <Download className="mr-1 h-3 w-3" />
                  Download
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Preview Modal */}
      {previewUrl && (
        <div
          className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
          onClick={() => { URL.revokeObjectURL(previewUrl); setPreviewUrl(null); }}
        >
          <div
            className="bg-background rounded-lg max-w-4xl max-h-[90vh] overflow-auto p-6 w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-medium">{doc.file_name}</h3>
              <Button variant="ghost" size="sm" onClick={() => { URL.revokeObjectURL(previewUrl); setPreviewUrl(null); }}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            {doc.file_mime_type?.startsWith("image/") ? (
              <img src={previewUrl} alt={doc.file_name} className="max-w-full max-h-[70vh] object-contain mx-auto" />
            ) : doc.file_mime_type === "application/pdf" ? (
              <iframe src={previewUrl} className="w-full h-[70vh] border rounded" title={doc.file_name} />
            ) : (
              <pre className="text-sm whitespace-pre-wrap bg-muted p-4 rounded max-h-[70vh] overflow-auto">
                Preview not available
              </pre>
            )}
          </div>
        </div>
      )}

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

      {/* Document Summary */}
      {doc.summary && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Lightbulb className="h-4 w-4" />
              Summary
            </CardTitle>
            <CardDescription>
              AI-generated summary of this document
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {doc.summary}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Extracted Entities */}
      {doc.entities && doc.entities.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Brain className="h-4 w-4" />
              Extracted Entities
            </CardTitle>
            <CardDescription>
              Named entities identified by the AI pipeline
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {doc.entities.map((entity, index) => (
                <div
                  key={`${entity.name}-${entity.type}-${index}`}
                  className="flex items-start gap-3 rounded-md border p-3"
                >
                  <Badge
                    variant={entityTypeVariant[entity.type] || "outline"}
                    className="mt-0.5 shrink-0"
                  >
                    {entity.type}
                  </Badge>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{entity.name}</p>
                    {entity.context && (
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {entity.context}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Keywords */}
      {metadata && metadata.keywords.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Tag className="h-4 w-4" />
              Keywords
            </CardTitle>
            <CardDescription>
              Extracted keywords from document metadata
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {metadata.keywords.map((keyword) => (
                <Badge key={keyword} variant="secondary">
                  {keyword}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

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

      {/* Metadata */}
      {metadata && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Info className="h-4 w-4" />
              Document Metadata
            </CardTitle>
            <CardDescription>
              Extracted metadata from the document file
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {metadata.title && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Title</span>
                  <span className="font-medium">{metadata.title}</span>
                </div>
              )}
              {metadata.author && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Author</span>
                  <span className="font-medium">{metadata.author}</span>
                </div>
              )}
              {metadata.subject && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Subject</span>
                  <span className="font-medium">{metadata.subject}</span>
                </div>
              )}
              {metadata.creation_date && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Creation Date</span>
                  <span className="font-medium">{metadata.creation_date}</span>
                </div>
              )}
              {metadata.modification_date && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Modification Date</span>
                  <span className="font-medium">{metadata.modification_date}</span>
                </div>
              )}
              {metadata.char_count > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Characters</span>
                  <span className="font-medium">{metadata.char_count.toLocaleString()}</span>
                </div>
              )}
              {Object.keys(metadata.extra).length > 0 && (
                <>
                  <div className="my-2 border-t" />
                  <p className="text-sm font-medium text-muted-foreground">Additional Metadata</p>
                  {Object.entries(metadata.extra).map(([key, value]) => (
                    <div key={key} className="flex justify-between text-sm">
                      <span className="text-muted-foreground">{key}</span>
                      <span className="font-medium">
                        {typeof value === "object" ? JSON.stringify(value) : String(value)}
                      </span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Extracted Text Preview */}
      {doc.extracted_text_preview && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">Extracted Text Preview</CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? "Collapse" : "Expand"}
              <ChevronsUpDown className="ml-1 h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
            <pre className={`${expanded ? "" : "max-h-64"} overflow-auto rounded-md bg-muted p-4 text-sm whitespace-pre-wrap`}>
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
