"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TranslationFunction } from "./types";

interface DocumentEditFormProps {
  editTitle: string;
  editDocType: string;
  editTags: string;
  onTitleChange: (v: string) => void;
  onDocTypeChange: (v: string) => void;
  onTagsChange: (v: string) => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
  t: TranslationFunction;
}

export default function DocumentEditForm({
  editTitle,
  editDocType,
  editTags,
  onTitleChange,
  onDocTypeChange,
  onTagsChange,
  onSave,
  onCancel,
  saving,
  t,
}: DocumentEditFormProps) {
  return (
    <Card className="border-dashed border-primary/50">
      <CardHeader>
        <CardTitle className="text-base">{t("editDocument")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("titleLabel")}</label>
            <Input
              value={editTitle}
              onChange={(e) => onTitleChange(e.target.value)}
              placeholder={t("documentTitle")}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("documentType")}</label>
            <Input
              value={editDocType}
              onChange={(e) => onDocTypeChange(e.target.value)}
              placeholder={t("documentTypePlaceholder")}
            />
          </div>
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">{t("tagsCommaSeparated")}</label>
          <Input
            value={editTags}
            onChange={(e) => onTagsChange(e.target.value)}
            placeholder={t("tagsPlaceholder")}
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onCancel}>
            {t("cancel")}
          </Button>
          <Button size="sm" onClick={onSave} disabled={saving}>
            {saving ? t("saving") : t("saveChanges")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
