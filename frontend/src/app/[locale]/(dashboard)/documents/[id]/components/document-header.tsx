"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Pencil, Trash2 } from "lucide-react";
import { documentStatusVariant as statusVariant } from "@/lib/constants";
import DocumentProgress from "@/components/document-progress";
import type { Document } from "@/types/api";
import type { TranslationFunction } from "./types";

interface DocumentHeaderProps {
  document: Document;
  editing: boolean;
  onStartEdit: () => void;
  onDelete: () => void;
  t: TranslationFunction;
}

export default function DocumentHeader({
  document: doc,
  editing,
  onStartEdit,
  onDelete,
  t,
}: DocumentHeaderProps) {
  return (
    <div className="flex items-start gap-4">
      <Link href="/documents" className="mt-1">
        <Button variant="ghost" size="icon">
          <ArrowLeft className="h-4 w-4" />
        </Button>
      </Link>
      <div className="flex-1">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">
          {doc.title || doc.doc_type}
        </h1>
        <p className="text-muted-foreground">
          {doc.subject || doc.author || t("noDescription")}
        </p>
        <div className="mt-2 max-w-xs">
          <DocumentProgress status={doc.processing_status} createdAt={doc.created_at} />
        </div>
      </div>
      <Badge variant={statusVariant[doc.processing_status] || "secondary"}>
        {doc.processing_status}
      </Badge>
      {doc.page_start && doc.page_end && (
        <Badge variant="outline" className="text-xs">
          Pages {doc.page_start}–{doc.page_end}
        </Badge>
      )}
      <Button variant="outline" size="sm" onClick={onStartEdit} disabled={editing}>
        <Pencil className="mr-1 h-3 w-3" />
        {t("editButton")}
      </Button>
      <Button variant="outline" size="sm" onClick={onDelete}>
        <Trash2 className="mr-1 h-3 w-3" />
        {t("deleteButton")}
      </Button>
    </div>
  );
}
