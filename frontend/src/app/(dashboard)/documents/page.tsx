"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { FileText, Search, MoreVertical, Eye, Trash2 } from "lucide-react";
import api from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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

export default function DocumentsPage() {
  const [search, setSearch] = useState("");

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ["documents", search],
    queryFn: async () => {
      const response = await api.get("/documents", {
        params: { q: search || undefined },
      });
      return Array.isArray(response.data) ? response.data : response.data.results || [];
    },
  });

  const filtered = documents.filter(
    (d) =>
      d.title?.toLowerCase().includes(search.toLowerCase()) ||
      d.doc_type?.toLowerCase().includes(search.toLowerCase()) ||
      d.language?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Documents</h1>
          <p className="text-muted-foreground">
            Processed and indexed documents
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Search className="h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search documents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Document</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Language</TableHead>
              <TableHead>Words</TableHead>
              <TableHead>Chunks</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-12" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="h-24 text-center">
                  Loading...
                </TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                  No documents found
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell>
                    <Link href={`/documents/${doc.id}`} className="flex items-center gap-3 hover:underline">
                      <div className="rounded-md bg-muted p-2">
                        <FileText className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="font-medium">{doc.title || doc.doc_type}</p>
                        <p className="max-w-[250px] truncate text-xs text-muted-foreground">
                          {doc.extracted_text_preview || doc.subject || "—"}
                        </p>
                      </div>
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{doc.doc_type}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusVariant[doc.processing_status] || "secondary"}>
                      {doc.processing_status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {doc.language || "—"}
                  </TableCell>
                  <TableCell className="text-sm">{doc.word_count}</TableCell>
                  <TableCell className="text-sm">{doc.chunk_count}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(doc.created_at)}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" asChild>
                      <Link href={`/documents/${doc.id}`}>
                        <Eye className="h-4 w-4" />
                      </Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <p className="text-sm text-muted-foreground">
        {filtered.length} document(s)
      </p>
    </div>
  );
}
