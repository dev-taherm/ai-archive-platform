"use client";

import { useState, useRef, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Upload, X, FileIcon, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { formatBytes } from "@/lib/utils";

interface UploadModalProps {
  onClose: () => void;
}

interface UploadFile {
  file: File;
  tags: string;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

export function UploadModal({ onClose }: UploadModalProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploads, setUploads] = useState<UploadFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);

  const addFiles = (files: FileList | File[]) => {
    const newUploads = Array.from(files).map((file) => ({
      file,
      tags: "",
      status: "pending" as const,
    }));
    setUploads((prev) => [...prev, ...newUploads]);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files.length) {
      addFiles(e.dataTransfer.files);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const updateTags = (index: number, tags: string) => {
    setUploads((prev) =>
      prev.map((u, i) => (i === index ? { ...u, tags } : u))
    );
  };

  const removeFile = (index: number) => {
    setUploads((prev) => prev.filter((_, i) => i !== index));
  };

  const uploadAll = async () => {
    for (let i = 0; i < uploads.length; i++) {
      if (uploads[i].status !== "pending") continue;

      setUploads((prev) =>
        prev.map((u, idx) => (idx === i ? { ...u, status: "uploading" } : u))
      );

      try {
        const formData = new FormData();
        formData.append("file", uploads[i].file);
        if (uploads[i].tags.trim()) {
          const tags = uploads[i].tags.split(",").map((t) => t.trim()).filter(Boolean);
          tags.forEach((tag) => formData.append("tags", tag));
        }

        await api.post("/files/upload", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        setUploads((prev) =>
          prev.map((u, idx) => (idx === i ? { ...u, status: "done" } : u))
        );
      } catch (err: any) {
        setUploads((prev) =>
          prev.map((u, idx) =>
            idx === i
              ? { ...u, status: "error", error: err.response?.data?.detail || "Upload failed" }
              : u
          )
        );
      }
    }
    queryClient.invalidateQueries({ queryKey: ["files"] });
  };

  const allDone = uploads.length > 0 && uploads.every((u) => u.status === "done" || u.status === "error");
  const hasPending = uploads.some((u) => u.status === "pending");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-lg max-h-[80vh] flex flex-col">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Upload Files
              </CardTitle>
              <CardDescription>
                Upload files to the server storage
              </CardDescription>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-auto space-y-4">
          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
              isDragOver
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/25 hover:border-primary/50"
            }`}
          >
            <Upload className="mb-2 h-8 w-8 text-muted-foreground" />
            <p className="text-sm font-medium">
              Drop files here or click to browse
            </p>
            <p className="text-xs text-muted-foreground">
              Any file type supported
            </p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => e.target.files && addFiles(e.target.files)}
          />

          {/* File list */}
          {uploads.length > 0 && (
            <div className="space-y-2">
              {uploads.map((upload, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-md border p-3"
                >
                  <FileIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-medium">
                      {upload.file.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatBytes(upload.file.size)}
                    </p>
                  </div>
                  {upload.status === "pending" && (
                    <Input
                      placeholder="tags (comma separated)"
                      value={upload.tags}
                      onChange={(e) => updateTags(i, e.target.value)}
                      className="w-32 text-xs"
                    />
                  )}
                  {upload.status === "uploading" && (
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  )}
                  {upload.status === "done" && (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  )}
                  {upload.status === "error" && (
                    <AlertCircle className="h-4 w-4 text-destructive" />
                  )}
                  {upload.status !== "uploading" && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => removeFile(i)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
        <CardFooter className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            {allDone ? "Close" : "Cancel"}
          </Button>
          {hasPending && (
            <Button onClick={uploadAll}>
              Upload {uploads.filter((u) => u.status === "pending").length} file(s)
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  );
}
