"use client";

import { Button } from "@/components/ui/button";
import { X } from "lucide-react";
import type { Document } from "@/types/api";
import type { TranslationFunction } from "./types";

interface FilePreviewModalProps {
  previewUrl: string;
  onClose: () => void;
  document: Document;
  t: TranslationFunction;
}

export default function FilePreviewModal({
  previewUrl,
  onClose,
  document: doc,
  t,
}: FilePreviewModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-background rounded-lg max-w-4xl max-h-[90vh] overflow-auto p-6 w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-medium">{doc.file_name}</h3>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        {doc.file_mime_type?.startsWith("image/") ? (
          <img src={previewUrl} alt={doc.file_name} className="max-w-full max-h-[70vh] object-contain mx-auto" />
        ) : doc.file_mime_type === "application/pdf" ? (
          <iframe src={previewUrl} className="w-full h-[70vh] border rounded" title={doc.file_name} />
        ) : (
          <pre className="text-sm whitespace-pre-wrap bg-muted p-4 rounded max-h-[70vh] overflow-auto">
            {t("previewNotAvailable")}
          </pre>
        )}
      </div>
    </div>
  );
}
