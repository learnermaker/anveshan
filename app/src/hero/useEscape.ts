import { useEffect } from 'react';

/** Close a dialog with the Escape key while it is open; on close, focus returns to what opened it. */
export function useEscape(open: boolean, onClose: () => void): void {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);
  // separate effect keyed on `open` only: onClose is often a new function each render
  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    return () => opener?.focus?.();
  }, [open]);
}
