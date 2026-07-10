import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAgentStore } from "../stores/agent-store";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Scan, Loader2 } from "lucide-react";

export function ScanButton() {
  const { t } = useTranslation();
  const { scanFolder, loading, folders } = useAgentStore();
  const [selectedFolder, setSelectedFolder] = useState(folders[0]?.path || "");
  const [result, setResult] = useState<string | null>(null);

  const handleScan = async () => {
    if (!selectedFolder) return;
    setResult(null);
    const res = await scanFolder(selectedFolder);
    if (res.processed > 0) {
      setResult(t("scan.success", { count: res.processed }));
    } else if (res.errors > 0) {
      setResult(t("scan.errors", { count: res.errors }));
    } else {
      setResult(t("scan.noFiles"));
    }
  };

  return (
    <div className="flex items-center gap-2">
      {folders.length > 1 ? (
        <select
          value={selectedFolder}
          onChange={(e) => setSelectedFolder(e.target.value)}
          className="flex h-9 rounded-md border bg-transparent px-3 py-1 text-sm"
        >
          {folders.map((f) => (
            <option key={f.path} value={f.path}>
              {f.label}
            </option>
          ))}
        </select>
      ) : (
        <Input
          value={selectedFolder}
          onChange={(e) => setSelectedFolder(e.target.value)}
          placeholder={t("scan.placeholder")}
          className="w-64"
        />
      )}
      <Button size="sm" onClick={handleScan} disabled={loading || !selectedFolder}>
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin mr-1" />
        ) : (
          <Scan className="h-4 w-4 mr-1" />
        )}
        {t("scan.button")}
      </Button>
      {result && <span className="text-xs text-muted-foreground">{result}</span>}
    </div>
  );
}
