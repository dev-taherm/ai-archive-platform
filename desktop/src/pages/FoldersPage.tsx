import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useAgentStore } from "../stores/agent-store";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { FolderPlus, Trash2 } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { useState } from "react";

export default function FoldersPage() {
  const { t } = useTranslation();
  const { folders, fetchFolders, addFolder, removeFolder } = useAgentStore();
  const [newFolder, setNewFolder] = useState("");

  useEffect(() => {
    fetchFolders();
  }, []);

  const handleAdd = async () => {
    const path = newFolder.trim();
    if (!path) return;
    await addFolder(path);
    setNewFolder("");
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{t("folders.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder={t("folders.placeholder")}
              value={newFolder}
              onChange={(e) => setNewFolder(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            />
            <Button onClick={handleAdd} size="sm">
              <FolderPlus className="h-4 w-4 mr-1" />
              {t("folders.add")}
            </Button>
          </div>

          <div className="space-y-2">
            {folders.map((folder) => (
              <div
                key={folder.path}
                className="flex items-center justify-between rounded-md border px-3 py-2"
              >
                <div className="flex items-center gap-3">
                  <div>
                    <p className="text-sm font-medium">{folder.label}</p>
                    <p className="text-xs text-muted-foreground font-mono">
                      {folder.path}
                    </p>
                  </div>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      folder.watching
                        ? "bg-green-100 text-green-700"
                        : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {folder.watching ? t("folders.watching") : t("folders.idle")}
                  </span>
                  {!folder.exists && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700">
                      {t("folders.notFound")}
                    </span>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeFolder(folder.path)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
            {folders.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">
                {t("folders.empty")}
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
