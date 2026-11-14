/**
 * A screen-reader-only status line that stays mounted: the owner sets `text` when something starts
 * (typing, loading) and clears it when it ends, so the change is announced. Mount it once per view,
 * never together with its first text.
 */
export function LiveStatus({ text }: { text: string }) {
  return (
    <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
      {text}
    </p>
  );
}
