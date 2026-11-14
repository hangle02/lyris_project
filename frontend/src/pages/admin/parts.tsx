import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { errorMessage, errorTechnical } from "../../api/client";
import { Button, InlineAlert, Modal, Skeleton } from "../../components/ui";
import { copyText } from "../../lib/clipboard";

// Small pieces shared by the tabs of "Quản lý tài khoản" (accounts and invites, coins).

export type Failure = { text: string; technical: string | null };
export const failure = (e: unknown): Failure => ({ text: errorMessage(e), technical: errorTechnical(e) });

export type Load<T> = { kind: "loading" } | { kind: "ready"; items: T[] } | { kind: "error"; error: Failure };

/** "Sao chép" that says "Đã sao chép" for two seconds (and stays readable for screen readers). */
export function CopyButton({
  text,
  label,
  variant = "secondary",
  onFailed,
}: {
  text: string;
  label: string;
  variant?: "secondary" | "ghost";
  /** Copying failed: the text must then be on screen to select by hand. */
  onFailed?: () => void;
}) {
  const [state, setState] = useState<"idle" | "done" | "failed">("idle");
  const timer = useRef<number | null>(null);
  useEffect(() => () => {
    if (timer.current) window.clearTimeout(timer.current);
  }, []);
  const run = async () => {
    const ok = await copyText(text);
    setState(ok ? "done" : "failed");
    if (!ok) onFailed?.();
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setState("idle"), 2000);
  };
  return (
    <Button size="sm" variant={variant} onClick={() => void run()} aria-live="polite">
      {state === "done" ? "Đã sao chép" : state === "failed" ? "Hãy chọn và sao chép tay" : label}
    </Button>
  );
}

/** A secret shown once: big tabular digits, selectable. */
export function SecretText({ children }: { children: string }) {
  return (
    <p className="rounded-control border border-line bg-surface-2 px-4 py-3 text-center text-[20px] leading-tight font-semibold tracking-normal text-fg tabular-nums select-all [overflow-wrap:anywhere]">
      {children}
    </p>
  );
}

export function SectionHead({ id, title, count, action }: { id: string; title: string; count?: number; action?: ReactNode }) {
  return (
    <div className="flex min-h-11 items-center justify-between gap-3">
      <h2 id={id} className="text-[18px] leading-tight font-semibold text-fg">
        {title}
        {count !== undefined && <span className="ml-2 text-[14px] font-normal text-muted tabular-nums">{count}</span>}
      </h2>
      {action}
    </div>
  );
}

export function RowsSkeleton({ rows, height }: { rows: number; height: number }) {
  return (
    <div aria-busy="true" className="flex flex-col gap-2">
      <span className="sr-only">Đang tải…</span>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} shape="card" height={height} />
      ))}
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  text,
  confirmLabel,
  danger,
  onCancel,
  run,
}: {
  open: boolean;
  title: string;
  text: string;
  confirmLabel: string;
  danger?: boolean;
  onCancel: () => void;
  run: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Failure | null>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (open) {
      setBusy(false);
      setError(null);
    }
  }, [open]);
  const go = async () => {
    setBusy(true);
    setError(null);
    try {
      await run();
    } catch (e) {
      setError(failure(e));
      setBusy(false);
    }
  };
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      size="sm"
      dismissible={!busy}
      initialFocusRef={cancelRef}
      footer={
        <>
          <Button ref={cancelRef} size="sm" variant="ghost" onClick={onCancel} disabled={busy}>
            Giữ nguyên
          </Button>
          <Button size="sm" variant={danger ? "danger" : "primary"} onClick={() => void go()} loading={busy}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <p className="text-[15px] leading-relaxed text-prose">{text}</p>
        {error && <InlineAlert tone="error" text={error.text} technical={error.technical} />}
      </div>
    </Modal>
  );
}
