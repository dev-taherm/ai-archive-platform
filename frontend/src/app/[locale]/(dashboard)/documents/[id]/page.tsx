"use client";

import { use } from "react";
import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { AlertCircle, FileText, ChevronRight } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import type { Document, DocumentMetadata, SiblingDocument } from "@/types/api";

import DocumentHeader from "./components/document-header";
import DocumentEditForm from "./components/document-edit-form";
import FilePreviewSection from "./components/file-preview-section";
import FilePreviewModal from "./components/file-preview-modal";
import DocumentStatsGrid from "./components/document-stats-grid";
import DocumentInfoCards from "./components/document-info-cards";
import EntityList from "./components/entity-list";
import MetadataKeyValues from "./components/metadata-key-values";
import ExtractedTextPreview from "./components/extracted-text-preview";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tag } from "lucide-react";

export default function DocumentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const t = useTranslations("documents");
  const { id } = use(params);
  const router = useRouter();
  const locale = useLocale();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDocType, setEditDocType] = useState("");
  const [editTags, setEditTags] = useState("");
  const [showDelete, setShowDelete] = useState(false);
  const queryClient = useQueryClient();
  const { toast } = useToast();

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

  const { data: siblings = [] } = useQuery<SiblingDocument[]>({
    queryKey: ["document-siblings", id],
    queryFn: async () => {
      const res = await api.get<Document>(`/documents/${id}`);
      return res.data.sibling_documents || [];
    },
    enabled: !!id,
  });

  const updateMutation = useMutation({
    mutationFn: async (data: { title?: string; doc_type?: string; tags?: string[] }) => {
      const res = await api.patch(`/documents/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document", id] });
      setEditing(false);
      toast({ title: t("updatedToast") });
    },
    onError: () => {
      toast({ title: t("updateFailedToast"), variant: "destructive" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      await api.delete(`/documents/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setShowDelete(false);
      toast({ title: t("deletedToast") });
      router.push("/documents");
    },
    onError: () => {
      toast({ title: t("deleteFailedToast"), variant: "destructive" });
    },
  });

  const startEditing = () => {
    setEditTitle(doc?.title || "");
    setEditDocType(doc?.doc_type || "unknown");
    setEditTags(doc?.tags?.join(", ") || "");
    setEditing(true);
  };

  const handleSave = () => {
    const tags = editTags.split(",").map((t) => t.trim()).filter(Boolean);
    updateMutation.mutate({
      title: editTitle || undefined,
      doc_type: editDocType || undefined,
      tags: tags.length > 0 ? tags : undefined,
    });
  };

  const handleClosePreview = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-12 text-muted-foreground">
        {t("loading")}
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <AlertCircle className="mb-4 h-12 w-12 text-brand-cyan opacity-50" />
        <p className="text-lg font-medium">{t("notFound")}</p>
        <Link href="/documents">
          <Button variant="link">{t("backToDocuments")}</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <DocumentHeader
        document={doc}
        editing={editing}
        onStartEdit={startEditing}
        onDelete={() => setShowDelete(true)}
        t={t}
      />

      {editing && (
        <DocumentEditForm
          editTitle={editTitle}
          editDocType={editDocType}
          editTags={editTags}
          onTitleChange={setEditTitle}
          onDocTypeChange={setEditDocType}
          onTagsChange={setEditTags}
          onSave={handleSave}
          onCancel={() => setEditing(false)}
          saving={updateMutation.isPending}
          t={t}
        />
      )}

      <AlertDialog open={showDelete} onOpenChange={setShowDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteConfirm", { title: doc.title || doc.file_name })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteMutation.mutate()}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? t("deleting") : t("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <FilePreviewSection document={doc} onPreview={setPreviewUrl} t={t} />

      {previewUrl && (
        <FilePreviewModal previewUrl={previewUrl} onClose={handleClosePreview} document={doc} t={t} />
      )}

      <DocumentStatsGrid document={doc} t={t} />

      <DocumentInfoCards document={doc} t={t} />

      <EntityList entities={doc.entities || []} t={t} />

      {metadata && metadata.keywords.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Tag className="h-4 w-4 text-brand-teal" />
              {t("keywords")}
            </CardTitle>
            <CardDescription>{t("keywordsDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {metadata.keywords.map((keyword) => (
                <Badge key={keyword} variant="secondary">{keyword}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {doc.tags.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("tags")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {doc.tags.map((tag) => (
                <Badge key={tag} variant="outline">{tag}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {metadata && <MetadataKeyValues metadata={metadata} t={t} />}

      <ExtractedTextPreview
        document={doc}
        expanded={expanded}
        onToggle={() => setExpanded(!expanded)}
        t={t}
      />

      {siblings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Related Documents</CardTitle>
            <CardDescription>
              This file contains {siblings.length + 1} documents
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {/* Current document */}
              <div className="flex items-center gap-3 rounded-lg border bg-muted/30 p-3">
                <FileText className="h-4 w-4 text-brand-teal" />
                <div className="flex-1">
                  <p className="text-sm font-medium">{doc.title}</p>
                  <p className="text-xs text-muted-foreground">
                    Document {doc.document_index + 1} of {doc.total_documents_for_file}
                    {doc.page_start && doc.page_end && ` · Pages ${doc.page_start}–${doc.page_end}`}
                  </p>
                </div>
                <Badge variant="success">Current</Badge>
              </div>
              {/* Sibling documents */}
              {siblings.map((sibling) => (
                <Link
                  key={sibling.id}
                  href={`/${locale}/documents/${sibling.id}`}
                  className="flex items-center gap-3 rounded-lg border p-3 hover:bg-muted/50 transition-colors"
                >
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{sibling.title}</p>
                    <p className="text-xs text-muted-foreground">
                      Document {sibling.document_index + 1} of {doc.total_documents_for_file}
                    </p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {doc.error_message && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-base text-destructive">{t("error")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-destructive">{doc.error_message}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
