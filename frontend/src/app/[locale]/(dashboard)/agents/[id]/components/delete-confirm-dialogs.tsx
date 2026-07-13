"use client";

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

interface DeleteConfirmDialogsProps {
  showDeleteDialog: boolean;
  onDeleteChange: (v: boolean) => void;
  showDestructiveConfirm: boolean;
  onDestructiveChange: (v: boolean) => void;
  showDeleteFolder: string | null;
  onDeleteFolderChange: (v: string | null) => void;
  onDeleteAgent: () => void;
  onConfirmDestructive: () => void;
  onDeleteFolderConfirm: () => void;
  commandType: string;
  t: (key: string, params?: Record<string, any>) => string;
  tCommon: (key: string) => string;
}

export function DeleteConfirmDialogs({
  showDeleteDialog,
  onDeleteChange,
  showDestructiveConfirm,
  onDestructiveChange,
  showDeleteFolder,
  onDeleteFolderChange,
  onDeleteAgent,
  onConfirmDestructive,
  onDeleteFolderConfirm,
  commandType,
  t,
  tCommon,
}: DeleteConfirmDialogsProps) {
  return (
    <>
      {/* Delete Agent Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={onDeleteChange}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('deleteDevice')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('deleteDeviceConfirm')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tCommon('cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={onDeleteAgent}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {tCommon('delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Destructive Command Confirm */}
      <AlertDialog open={showDestructiveConfirm} onOpenChange={onDestructiveChange}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('confirmCommand', { commandType })}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('confirmCommandDesc', { commandType })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tCommon('cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={onConfirmDestructive}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('sendCommand')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Folder Confirm */}
      <AlertDialog open={!!showDeleteFolder} onOpenChange={() => onDeleteFolderChange(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('removeFolder')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('removeFolderConfirm')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tCommon('cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={onDeleteFolderConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('remove')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
