import { useTranslation } from "react-i18next";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import type { FileRecord } from "../lib/agent-api";

interface FileTableProps {
  files: FileRecord[];
}

function formatSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatDate(iso: string): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

const statusVariant: Record<string, "success" | "destructive" | "default" | "secondary"> = {
  completed: "success",
  processed: "success",
  failed: "destructive",
  processing: "default",
  pending: "secondary",
};

export function FileTable({ files }: FileTableProps) {
  const { t } = useTranslation();

  if (files.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          {t("files.empty")}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("files.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2 font-medium">{t("files.name")}</th>
                <th className="pb-2 font-medium">{t("files.size")}</th>
                <th className="pb-2 font-medium">{t("files.status")}</th>
                <th className="pb-2 font-medium">{t("files.synced")}</th>
                <th className="pb-2 font-medium">{t("files.added")}</th>
              </tr>
            </thead>
            <tbody>
              {files.map((file) => (
                <tr key={file.id} className="border-b last:border-0">
                  <td className="py-2 max-w-[200px] truncate" title={file.local_path}>
                    {file.filename}
                  </td>
                  <td className="py-2 text-muted-foreground">
                    {formatSize(file.size_bytes)}
                  </td>
                  <td className="py-2">
                    <Badge variant={statusVariant[file.processing_status] || "default"}>
                      {file.processing_status}
                    </Badge>
                  </td>
                  <td className="py-2">
                    {file.synced ? (
                      <Badge variant="success">{t("files.yes")}</Badge>
                    ) : (
                      <Badge variant="secondary">{t("files.no")}</Badge>
                    )}
                  </td>
                  <td className="py-2 text-muted-foreground">
                    {formatDate(file.first_seen_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
