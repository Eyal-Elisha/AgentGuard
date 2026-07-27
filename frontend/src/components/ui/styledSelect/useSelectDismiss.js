import { useEffect } from 'react';

/** Closes the select on Escape or pointerdown outside rootRef while open. */
export function useSelectDismiss(open, setOpen, rootRef) {
  useEffect(() => {
    if (!open) return undefined;

    function onKey(e) {
      if (e.key === 'Escape') {
        e.preventDefault();
        setOpen(false);
      }
    }

    function onPointerDown(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false);
      }
    }

    window.addEventListener('keydown', onKey);
    window.addEventListener('pointerdown', onPointerDown);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('pointerdown', onPointerDown);
    };
  }, [open, setOpen, rootRef]);
}
