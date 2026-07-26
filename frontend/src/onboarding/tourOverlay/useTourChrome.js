import { useEffect } from 'react';

export function useTourChrome({ isOpen, stepIndex, skip, dialogRef }) {
  useEffect(() => {
    if (!isOpen) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialogRef.current?.focus();
    return () => { document.body.style.overflow = prev; };
  }, [isOpen, stepIndex, dialogRef]);

  useEffect(() => {
    if (!isOpen) return undefined;
    function onKey(e) {
      if (e.key === 'Escape') {
        e.preventDefault();
        skip();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, skip]);
}
