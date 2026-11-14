import { Wordmark } from "../../components/brand";
import { Button } from "../../components/ui";

/**
 * Before the first answer of /api/auth/me (docs/auth.md §7.1): the ground colour and the wordmark,
 * no blinking spinner. When the server cannot be reached, one plain line and "Thử lại".
 */
export function AuthSplash({ error, onRetry, retrying }: { error?: string | null; onRetry?: () => void; retrying?: boolean }) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 bg-bg px-5" aria-busy={!error}>
      <h1 className="sr-only">Lyris</h1>
      <Wordmark size={40} animated={false} />
      {error ? (
        <div role="alert" className="flex max-w-[360px] flex-col items-center gap-4 text-center">
          <p className="text-[15px] leading-snug text-muted">{error}</p>
          {onRetry && (
            <Button size="sm" onClick={onRetry} loading={retrying}>
              Thử lại
            </Button>
          )}
        </div>
      ) : (
        <span className="sr-only">Đang mở Lyris…</span>
      )}
    </div>
  );
}
