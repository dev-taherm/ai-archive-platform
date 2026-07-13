"use client";

import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FileText, Eye, Download } from "lucide-react";
import type { Document } from "@/types/api";
import type { TranslationFunction } from "./types";

interface FilePreviewSectionProps {
  document: Document;
  onPreview: (url: string) => void;
  t: TranslationFunction;
}

export default function FilePreviewSection({
  document: doc,
  onPreview,
  t,
}: FilePreviewSectionProps) {
  if (!doc.file_name) return null;

  const handlePreview = async () => {
    const res = await api.get(`/files/${doc.file_id}/download`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    onPreview(url);
  };

  const handleDownload = async () => {
    const res = await api.get(`/files/${doc.file_id}/download`, { responseType: "blob" });
    const blob = new Blob([res.data]);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = doc.file_name;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="h-5 w-5 text-brand-teal" />
            <div>
              <p className="text-sm font-medium">{doc.file_name}</p>
              <p className="text-xs text-muted-foreground">{doc.file_mime_type || t("unknownType")}</p>
            </div>
          </div>
          <div className="flex gap-2">
            {(doc.file_mime_type?.startsWith("image/") || doc.file_mime_type === "application/pdf") && (
              <Button variant="outline" size="sm" onClick={handlePreview}>
                <Eye className="mr-1 h-3 w-3" />
                {t("preview")}
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={handleDownload}>
              <Download className="mr-1 h-3 w-3" />
              {t("download")}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
