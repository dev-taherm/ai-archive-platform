"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FolderOpen, Plus, Loader2, Pencil, Trash2, Check, X } from "lucide-react";
import { formatDate } from "@/lib/utils";

interface Folder {
  id: string;
  local_path: string;
  label: string;
  file_count: number;
  is_active: boolean;
  last_scanned_at?: string | null;
}

interface AgentFoldersSectionProps {
  agentId: string;
  folders: Folder[];
  onAddFolder: (path: string, label: string) => void;
  onUpdateFolder: (id: string, path: string, label: string) => void;
  onDeleteFolder: (id: string) => void;
  addingFolder: boolean;
  t: (key: string, params?: Record<string, any>) => string;
  tCommon: (key: string) => string;
}

export function AgentFoldersSection({
  agentId,
  folders,
  onAddFolder,
  onUpdateFolder,
  onDeleteFolder,
  addingFolder,
  t,
  tCommon,
}: AgentFoldersSectionProps) {
  const [showAddFolder, setShowAddFolder] = useState(false);
  const [newFolderPath, setNewFolderPath] = useState("");
  const [newFolderLabel, setNewFolderLabel] = useState("");

  const [editingFolderId, setEditingFolderId] = useState<string | null>(null);
  const [editingFolderPath, setEditingFolderPath] = useState("");
  const [editingFolderLabel, setEditingFolderLabel] = useState("");

  const startEditFolder = (folder: Folder) => {
    setEditingFolderId(folder.id);
    setEditingFolderPath(folder.local_path);
    setEditingFolderLabel(folder.label);
  };

  const handleSaveFolder = (folderId: string) => {
    onUpdateFolder(folderId, editingFolderPath, editingFolderLabel);
    setEditingFolderId(null);
  };

  const handleAddFolder = () => {
    onAddFolder(newFolderPath, newFolderLabel);
    setNewFolderPath("");
    setNewFolderLabel("");
    setShowAddFolder(false);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <FolderOpen className="h-4 w-4" />
            {t('monitoredFolders', { count: folders?.length || 0 })}
          </CardTitle>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowAddFolder(!showAddFolder)}
          >
            <Plus className="h-4 w-4 mr-1" />
            {t('addFolder')}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {showAddFolder && (
          <div className="mb-4 p-4 rounded-lg border bg-muted/50 space-y-2">
            <Input
              placeholder={t('folderPathPlaceholder')}
              value={newFolderPath}
              onChange={(e) => setNewFolderPath(e.target.value)}
            />
            <Input
              placeholder={t('folderLabelPlaceholder')}
              value={newFolderLabel}
              onChange={(e) => setNewFolderLabel(e.target.value)}
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={handleAddFolder}
                disabled={!newFolderPath.trim() || addingFolder}
              >
                {addingFolder ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1 text-brand-teal" />
                ) : (
                  <Plus className="h-4 w-4 mr-1" />
                )}
                {t('addFolder')}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setShowAddFolder(false)}>
                {tCommon('cancel')}
              </Button>
            </div>
          </div>
        )}
        {!folders || folders.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            {t('noFolders')}
          </p>
        ) : (
          <div className="space-y-2">
            {folders.map((folder) => (
              <div
                key={folder.id}
                className="flex items-center justify-between p-3 rounded-lg border"
              >
                {editingFolderId === folder.id ? (
                  /* Inline edit mode */
                  <div className="flex-1 flex items-center gap-2">
                    <Input
                      value={editingFolderPath}
                      onChange={(e) => setEditingFolderPath(e.target.value)}
                      className="flex-1"
                      placeholder={t('folderPathPlaceholder')}
                    />
                    <Input
                      value={editingFolderLabel}
                      onChange={(e) => setEditingFolderLabel(e.target.value)}
                      className="w-40"
                      placeholder={t('folderLabelPlaceholder')}
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleSaveFolder(folder.id)}
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setEditingFolderId(null)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  /* Display mode */
                  <>
                    <div className="flex items-center gap-3">
                      <FolderOpen className="h-4 w-4 text-brand-teal" />
                      <div>
                        <p className="text-sm font-medium">{folder.local_path}</p>
                        {folder.label && (
                          <p className="text-xs text-muted-foreground">{folder.label}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{t('countFiles', { count: folder.file_count })}</span>
                      <Badge variant={folder.is_active ? "success" : "secondary"}>
                        {folder.is_active ? t('active') : t('inactive')}
                      </Badge>
                      {folder.last_scanned_at && (
                        <span>{t('scanned', { date: formatDate(folder.last_scanned_at) })}</span>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => startEditFolder(folder)}
                        title={tCommon('edit')}
                      >
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => onDeleteFolder(folder.id)}
                        title={t('removeFolder')}
                      >
                        <Trash2 className="h-3 w-3 text-destructive" />
                      </Button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
