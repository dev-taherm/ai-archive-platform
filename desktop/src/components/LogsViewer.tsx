import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

interface LogsViewerProps {
  logs: string[];
}

export function LogsViewer({ logs }: LogsViewerProps) {
  const { t } = useTranslation();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("logs.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-64 overflow-y-auto rounded-md bg-muted p-3 font-mono text-xs space-y-0.5">
          {logs.length === 0 ? (
            <p className="text-muted-foreground">{t("logs.empty")}</p>
          ) : (
            logs.map((line, i) => (
              <div key={i} className="whitespace-pre-wrap break-all">
                {line}
              </div>
            ))
          )}
          <div ref={endRef} />
        </div>
      </CardContent>
    </Card>
  );
}
