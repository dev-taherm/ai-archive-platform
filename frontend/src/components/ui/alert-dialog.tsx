"use client";

import { createContext, useContext, type ReactNode } from "react";
import { Button } from "./button";

interface AlertDialogContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const AlertDialogContext = createContext<AlertDialogContextValue>({
  open: false,
  setOpen: () => {},
});

export function AlertDialog({
  children,
  open,
  onOpenChange,
}: {
  children: ReactNode;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  if (!open) return null;
  return (
    <AlertDialogContext.Provider value={{ open, setOpen: onOpenChange }}>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        onClick={() => onOpenChange(false)}
      >
        <div
          className="bg-background border rounded-lg shadow-lg max-w-md w-full mx-4 p-6"
          onClick={(e) => e.stopPropagation()}
        >
          {children}
        </div>
      </div>
    </AlertDialogContext.Provider>
  );
}

export function AlertDialogContent({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

export function AlertDialogHeader({ children }: { children: ReactNode }) {
  return <div className="space-y-2 mb-4">{children}</div>;
}

export function AlertDialogTitle({ children }: { children: ReactNode }) {
  return <h2 className="text-lg font-semibold">{children}</h2>;
}

export function AlertDialogDescription({ children }: { children: ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

export function AlertDialogFooter({ children }: { children: ReactNode }) {
  return <div className="flex justify-end gap-2 mt-4">{children}</div>;
}

export function AlertDialogCancel({
  children,
  onClick,
}: {
  children: ReactNode;
  onClick?: () => void;
}) {
  const { setOpen } = useContext(AlertDialogContext);
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => {
        onClick?.();
        setOpen(false);
      }}
    >
      {children}
    </Button>
  );
}

export function AlertDialogAction({
  children,
  onClick,
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <Button size="sm" className={className} onClick={onClick}>
      {children}
    </Button>
  );
}
