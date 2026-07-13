"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  FileText,
  Search,
  Eye,
  Trash2,
  LayoutGrid,
  List,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import api from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
import { useToast } from "@/hooks/use-toast";
import type { Document } from "@/types/api";
import { documentStatusVariant as statusVariant } from "@/lib/constants";
import ScopeSelector from "@/components/features/shared/scope-selector";

export default function DocumentsPage() {
  const t = useTranslations("documents");
  const [search, setSearch] = useState("");
  const [viewMode, setViewMode] = useState<"table" | "grid">("table");
  const [page, setPage] = useState(1);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [scope, setScope] = useState<"personal" | "organization">("personal");
  const pageSize = 20;
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: documents = [], isLoading } = useQuery<Document[]>({
    queryKey: ["documents", search, scope],
    queryFn: async () => {
      const response = await api.get("/documents", {
        params: { q: search || undefined, scope },
      });
      return Array.isArray(response.data) ? response.data : response.data.results || [];
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/documents/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast({ title: t("deletedToast") });
      setDeleteId(null);
    },
    onError: () => {
      toast({ title: t("deleteFailedToast"), variant: "destructive" });
    },
  });

  const filtered = documents.filter(
    (d) =>
      d.title?.toLowerCase().includes(search.toLowerCase()) ||
      d.doc_type?.toLowerCase().includes(search.toLowerCase()) ||
      d.language?.toLowerCase().includes(search.toLowerCase())
  );

  const totalPages = Math.ceil(filtered.length / pageSize);
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-brand-teal to-brand-cyan bg-clip-text text-transparent">{t("title")}</h1>
          <p className="text-muted-foreground">
            {t("subtitle")}
          </p>
        </div>
      </div>

      <ScopeSelector value={scope} onChange={setScope} />

      <div className="flex items-center gap-2">
        <Search className="h-4 w-4 text-muted-foreground" />
        <Input
          placeholder={t("searchPlaceholder")}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="max-w-sm"
        />
        <div className="ml-auto flex items-center gap-1 rounded-md border p-0.5">
          <Button
            variant={viewMode === "table" ? "secondary" : "ghost"}
            size="icon"
            className="h-7 w-7"
            onClick={() => setViewMode("table")}
          >
            <List className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === "grid" ? "secondary" : "ghost"}
            size="icon"
            className="h-7 w-7"
            onClick={() => setViewMode("grid")}
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-cyan border-t-transparent" />
        </div>
      ) : viewMode === "table" ? (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("document")}</TableHead>
                <TableHead>{t("type")}</TableHead>
                <TableHead>{t("status")}</TableHead>
                <TableHead>{t("language")}</TableHead>
                <TableHead>{t("words")}</TableHead>
                <TableHead>{t("chunks")}</TableHead>
                <TableHead>{t("created")}</TableHead>
                <TableHead className="w-20" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginated.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="h-24 text-center text-muted-foreground">
                    {t("noDocuments")}
                  </TableCell>
                </TableRow>
              ) : (
                paginated.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell>
                      <Link href={`/documents/${doc.id}`} className="flex items-center gap-3 hover:underline">
                        <div className="rounded-md bg-brand-teal/10 p-2">
                          <FileText className="h-4 w-4 text-brand-teal" />
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
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" className="h-7 w-7" asChild>
                          <Link href={`/documents/${doc.id}`}>
                            <Eye className="h-3.5 w-3.5" />
                          </Link>
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-destructive"
                          onClick={() => setDeleteId(doc.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {paginated.length === 0 ? (
            <div className="col-span-full py-12 text-center text-muted-foreground">
              {t("noDocuments")}
            </div>
          ) : (
            paginated.map((doc) => (
              <Card key={doc.id} className="relative overflow-hidden transition-colors hover:bg-muted/50">
                <Link href={`/documents/${doc.id}`} className="block p-4">
                  <div className="mb-3 flex items-start justify-between">
                    <div className="rounded-md bg-brand-teal/10 p-2">
                      <FileText className="h-5 w-5 text-brand-teal" />
                    </div>
                    <Badge variant={statusVariant[doc.processing_status] || "secondary"} className="text-xs">
                      {doc.processing_status}
                    </Badge>
                  </div>
                  <p className="mb-1 line-clamp-1 font-medium">{doc.title || doc.doc_type}</p>
                  <p className="mb-3 line-clamp-2 text-xs text-muted-foreground">
                    {doc.extracted_text_preview || doc.subject || "—"}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    <Badge variant="outline" className="text-xs">{doc.doc_type}</Badge>
                    {doc.language && <Badge variant="secondary" className="text-xs">{doc.language}</Badge>}
                  </div>
                  <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
                    <span>{t("wordCount", { wordCount: doc.word_count.toLocaleString() })}</span>
                    <span>{formatDate(doc.created_at)}</span>
                  </div>
                </Link>
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-2 top-2 h-7 w-7 text-destructive"
                  onClick={(e) => {
                    e.preventDefault();
                    setDeleteId(doc.id);
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </Card>
            ))
          )}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {t("pageInfo", { page, totalPages, count: filtered.length })}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              <ChevronLeft className="h-4 w-4" />
              {t("prev")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              {t("next")}
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {filtered.length > 0 && (
        <p className="text-sm text-muted-foreground">
          {t("countInfo", { count: filtered.length })}
        </p>
      )}

      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteId && deleteMutation.mutate(deleteId)}
            >
              {t("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
