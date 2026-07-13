"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronsUpDown } from "lucide-react";
import type { Document } from "@/types/api";
import type { TranslationFunction } from "./types";

interface ExtractedTextPreviewProps {
  document: Document;
  expanded: boolean;
  onToggle: () => void;
  t: TranslationFunction;
}

function renderMarkdownLine(line: string, key: number) {
  if (line.startsWith("# ")) return <h1 key={key} className="text-lg font-bold mt-2 mb-1">{line.slice(2)}</h1>;
  if (line.startsWith("## ")) return <h2 key={key} className="text-base font-semibold mt-2 mb-1">{line.slice(3)}</h2>;
  if (line.startsWith("### ")) return <h3 key={key} className="text-sm font-semibold mt-2 mb-1">{line.slice(4)}</h3>;
  if (line.startsWith("- ")) return <li key={key} className="ml-4">{line.slice(2)}</li>;
  if (line.startsWith("* ")) return <li key={key} className="ml-4">{line.slice(2)}</li>;
  if (line.trim() === "") return <br key={key} />;
  return <p key={key} className="whitespace-pre-wrap">{line}</p>;
}

function isMarkdown(text: string) {
  return text.includes("**") || text.includes("#") || text.includes("- ");
}

export default function ExtractedTextPreview({
  document: doc,
  expanded,
  onToggle,
  t,
}: ExtractedTextPreviewProps) {
  if (!doc.extracted_text_preview) return null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">{t("extractedTextPreview")}</CardTitle>
        <Button variant="ghost" size="sm" onClick={onToggle}>
          {expanded ? t("collapse") : t("expand")}
          <ChevronsUpDown className="ml-1 h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        <div className={`${expanded ? "" : "max-h-64"} overflow-auto rounded-md bg-muted p-4 text-sm`}>
          {isMarkdown(doc.extracted_text_preview) ? (
            <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
              {doc.extracted_text_preview.split("\n").map((line, i) => renderMarkdownLine(line, i))}
            </div>
          ) : (
            <pre className="whitespace-pre-wrap">{doc.extracted_text_preview}</pre>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
