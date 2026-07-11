import { useEffect, useState } from "react";
import { useAgentStore, type TrashEntry } from "../stores/agent-store";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { RotateCcw, Trash2, AlertCircle } from "lucide-react";

function formatSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatDate(iso: string): string {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
}

export default function TrashPage() {
  const { trash, fetchTrash, restoreFile, permanentlyDeleteFile, error } = useAgentStore();
  const [loadingId, setLoadingId] = useState<string | null>(null);

  useEffect(() => {
    fetchTrash();
  }, []);

  const handleRestore = async (entry: TrashEntry) => {
    setLoadingId(entry.id);
    await restoreFile(entry.id);
    setLoadingId(null);
    fetchTrash();
  };

  const handlePermanentDelete = async (entry: TrashEntry) => {
    if (!window.confirm(`Permanently delete "${entry.filename}"?`)) return;
    setLoadingId(entry.id);
    await permanentlyDeleteFile(entry.id);
    setLoadingId(null);
  };

  return (
    <div className="min-h-full bg-muted/40">
      <div className="border-b bg-background px-6 py-3">
        <h1 className="text-lg font-semibold">Trash</h1>
      </div>
      <div className="p-6">
        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive mb-4">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Trashed Files</CardTitle>
          </CardHeader>
          <CardContent>
            {trash.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">Trash is empty</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="pb-2 font-medium pr-4">File</th>
                      <th className="pb-2 font-medium pr-4">Original Path</th>
                      <th className="pb-2 font-medium pr-4">Size</th>
                      <th className="pb-2 font-medium pr-4">Deleted At</th>
                      <th className="pb-2 font-medium w-24">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trash.map((entry) => (
                      <tr key={entry.id} className="border-b last:border-0 hover:bg-muted/30">
                        <td className="py-2 pr-4 font-medium">{entry.filename}</td>
                        <td className="py-2 pr-4 text-muted-foreground max-w-[300px] truncate" title={entry.original_path}>
                          {entry.original_path}
                        </td>
                        <td className="py-2 pr-4 text-muted-foreground">{formatSize(entry.size_bytes)}</td>
                        <td className="py-2 pr-4 text-muted-foreground">{formatDate(entry.deleted_at)}</td>
                        <td className="py-2">
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRestore(entry)}
                              disabled={loadingId === entry.id}
                              title="Restore"
                            >
                              <RotateCcw className="h-4 w-4 text-green-600" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handlePermanentDelete(entry)}
                              disabled={loadingId === entry.id}
                              title="Delete permanently"
                            >
                              <Trash2 className="h-4 w-4 text-red-600" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
