"use client";

import { create } from "zustand";

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: "default" | "destructive";
}

interface ToastStore {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (toast) =>
    set((state) => ({
      toasts: [
        ...state.toasts,
        { ...toast, id: Math.random().toString(36).slice(2) },
      ],
    })),
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}));

export function useToast() {
  const { addToast, removeToast } = useToastStore();

  const toast = (props: Omit<Toast, "id">) => {
    addToast(props);
    setTimeout(() => {
      const { toasts } = useToastStore.getState();
      if (toasts.length > 0) {
        removeToast(toasts[toasts.length - 1].id);
      }
    }, 4000);
  };

  return { toast, removeToast };
}
