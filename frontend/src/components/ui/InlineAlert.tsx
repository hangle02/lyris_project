import { IconX } from "../icons";
import { Button, IconButton } from "./Button";
import { ErrorDetails } from "./ErrorDetails";
import { cx } from "./logic";

export interface InlineAlertProps {
  tone: "error" | "info";
  text: string;
  /** Technical text under a small "Chi tiết" disclosure (Phase 3b). */
  technical?: string | null;
  onRetry?: (() => void) | null;
  retryDisabled?: boolean;
  /** Label of the action button (default "Thử lại"). */
  actionLabel?: string;
  onDismiss?: () => void;
  className?: string;
}

/**
 * One-line notice inside the block it concerns: an error on a pale negative tint with a dot and
 * "Thử lại", or a quiet hint on the surface tone. Text is ink (fg / muted), never coloured, so it
 * reads at 4.5:1 in both themes.
 */
export function InlineAlert({
  tone,
  text,
  technical,
  onRetry,
  retryDisabled = false,
  actionLabel = "Thử lại",
  onDismiss,
  className,
}: InlineAlertProps) {
  const error = tone === "error";
  return (
    <div
      role={error ? "alert" : "status"}
      className={cx(
        "flex gap-3 rounded-control py-2 pr-2 pl-4 text-[14px] leading-snug",
        // With "Chi tiết" the block grows downwards: the dot and buttons stay level with the first line.
        technical ? "items-start" : "items-center",
        error
          ? "bg-[color-mix(in_oklab,var(--color-danger)_14%,var(--color-bg))] text-fg"
          : "border border-edge bg-surface text-muted",
        className,
      )}
    >
      {error && <span aria-hidden="true" className={cx("h-2 w-2 shrink-0 rounded-full bg-danger", technical && "mt-[14px]")} />}
      <div className="min-w-0 flex-1 py-1.5 [overflow-wrap:anywhere]">
        <p>{text}</p>
        <ErrorDetails technical={technical} className="mt-0.5" />
      </div>
      {onRetry && (
        <Button size="sm" variant="secondary" onClick={onRetry} disabled={retryDisabled}>
          {actionLabel}
        </Button>
      )}
      {onDismiss && <IconButton size="sm" label="Đóng thông báo" icon={<IconX />} onClick={onDismiss} />}
    </div>
  );
}
