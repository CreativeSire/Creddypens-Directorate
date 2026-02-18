import type { CSSProperties } from "react";
import { toast as sonnerToast } from "sonner";

const baseStyle: CSSProperties = {
  background: "#0A0F14",
  color: "#00F0FF",
  border: "1px solid #00F0FF55",
  fontSize: "14px",
  fontWeight: 500,
};

export const toast = {
  success(message: string, id?: string | number) {
    sonnerToast.success(message, { id, style: { ...baseStyle, borderColor: "#00F0FF" }, duration: 3000 });
  },
  error(message: string, id?: string | number) {
    sonnerToast.error(message, {
      id,
      style: { ...baseStyle, color: "#FF6B6B", borderColor: "#FF6B6B88" },
      duration: 4000,
    });
  },
  info(message: string) {
    sonnerToast.info(message, { style: baseStyle, duration: 3000 });
  },
  loading(message: string) {
    return sonnerToast.loading(message, { style: { ...baseStyle, color: "#FFB800", borderColor: "#FFB80088" } });
  },
  dismiss(id?: string | number) {
    sonnerToast.dismiss(id);
  },
  promise<T>(promise: Promise<T>, messages: { loading: string; success: string; error: string }) {
    return sonnerToast.promise(promise, {
      loading: messages.loading,
      success: messages.success,
      error: messages.error,
      style: baseStyle,
    });
  },
};
