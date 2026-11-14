import { useEffect, useMemo, useRef, useState } from "react";
import { api, errorMessage } from "../../api/client";
import { IconChevronRight, IconRefreshCw } from "../../components/icons";
import { Button, Meter, Skeleton, Spinner, cx } from "../../components/ui";
import { TOKEN_B_WARN } from "../../lib/cardForm";
import type { CharacterCard, PromptPreview, StorySettings } from "../../types";
import { hasWorldBlock, roleLabel, sampleTurnNote } from "./previewLogic";
import { Notice } from "./ui";

const BLOCKS: { key: string; label: string; hint: string }[] = [
  { key: "A", label: "A · Luật", hint: "Luật viết theo ngôn ngữ và chế độ (giới tính, quan hệ, ngôi kể, Thought…)" },
  { key: "B", label: "B · Nhân vật", hint: "Card + persona + xưng hô + style profile" },
  { key: "C", label: "C · Bối cảnh", hint: "Bối cảnh của story và tóm tắt cảnh" },
  { key: "D", label: "D · Thế giới", hint: "Mục thế giới được gợi nhớ ở lượt này" },
  { key: "E", label: "E · Lịch sử", hint: "Lời mở đầu và các lượt trước" },
  { key: "F", label: "F · Ghi chú cuối", hint: "Lời nhắc gắn vào lượt cuối của người chơi" },
];

const DEBOUNCE_MS = 700;

function fmt(n: number | undefined): string {
  return (n ?? 0).toLocaleString("vi-VN");
}

/**
 * "Xem trước prompt": the exact messages the model would get for the card being edited (saved or not),
 * with a sample player turn, and the token estimate per block. Refreshes on change while visible.
 */
export function PromptPreviewPanel({
  card,
  personaId,
  settings,
  active,
  blockers,
}: {
  card: CharacterCard;
  personaId: number | null;
  settings: StorySettings | null;
  /** Panel is showing: only then requests are sent. */
  active: boolean;
  /** Form errors that make the request pointless (shown instead). */
  blockers: string[];
}) {
  const [preview, setPreview] = useState<PromptPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const seq = useRef(0);
  /** Request key (body + refresh count) of the last request sent; never re-sent automatically. */
  const lastKey = useRef<string>("");

  const body = useMemo(
    () => (personaId !== null && settings ? { card, persona_id: personaId, settings } : null),
    [card, personaId, settings],
  );
  const bodyKey = useMemo(() => (body ? JSON.stringify(body) : ""), [body]);
  const bodyRef = useRef(body);
  bodyRef.current = body;

  useEffect(() => {
    const current = bodyRef.current;
    if (!active || !current || blockers.length > 0) return;
    const reqKey = `${bodyKey}#${refresh}`;
    if (reqKey === lastKey.current) return;
    const t = window.setTimeout(
      async () => {
        lastKey.current = reqKey;
        const my = ++seq.current;
        setLoading(true);
        try {
          const res = await api.previewPrompt(current);
          if (my !== seq.current) return;
          setPreview(res);
          setError(null);
        } catch (e) {
          if (my !== seq.current) return;
          setError(errorMessage(e));
        } finally {
          if (my === seq.current) setLoading(false);
        }
      },
      lastKey.current ? DEBOUNCE_MS : 0,
    );
    return () => window.clearTimeout(t);
  }, [active, bodyKey, blockers.length, refresh]);

  const est = preview?.token_estimate ?? {};
  const hasWorld = hasWorldBlock(est);
  const total = est.total ?? 0;
  const numCtx = preview?.num_ctx ?? 8192;
  const pct = numCtx > 0 ? (total / numCtx) * 100 : 0;
  const bHigh = (est.B ?? 0) > TOKEN_B_WARN;
  const meterColor = pct > 85 ? "var(--color-danger)" : pct > 60 ? "var(--color-warn)" : undefined;

  return (
    <div className="flex flex-col gap-4">
      {blockers.length > 0 && <Notice tone="warn" title="Sửa form trước khi xem trước:" lines={blockers} />}
      {error && (
        <Notice
          tone="error"
          lines={[`Không dựng được prompt: ${error}`]}
          action={
            <Button size="sm" onClick={() => setRefresh((n) => n + 1)} loading={loading}>
              Thử lại
            </Button>
          }
        />
      )}

      {preview && (
        <>
          <section aria-label="Ước lượng token" className="rounded-card border border-edge bg-surface p-4">
            <Meter
              label="Ước lượng token"
              value={total}
              max={numCtx}
              color={meterColor}
              valueText={`${fmt(total)} / ${fmt(numCtx)}`}
            />
            <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 min-[420px]:grid-cols-3">
              {BLOCKS.map((b) => {
                const warn = b.key === "B" && bHigh;
                return (
                  <div key={b.key} title={b.hint} className="flex items-baseline justify-between gap-2">
                    <dt className={cx("truncate text-[13px]", warn ? "text-warn" : "text-muted")}>{b.label}</dt>
                    <dd className={cx("text-[14px] tabular-nums", warn ? "font-semibold text-warn" : "text-fg")}>{fmt(est[b.key])}</dd>
                  </div>
                );
              })}
            </dl>
          </section>
          {bHigh && (
            <Notice
              tone="warn"
              lines={[
                `Khối nhân vật (B) dài ${fmt(est.B)} token, quá ${fmt(TOKEN_B_WARN)}. Card dài làm model dễ quên luật; nên rút gọn mô tả, hoàn cảnh, ví dụ thoại.`,
              ]}
            />
          )}
          <div className="flex items-center gap-3">
            <p className="min-w-0 flex-1 text-[13px] leading-snug text-muted">
              {sampleTurnNote(hasWorld)}
            </p>
            <Button
              variant="ghost"
              size="sm"
              icon={loading ? <Spinner size={16} /> : <IconRefreshCw />}
              onClick={() => setRefresh((n) => n + 1)}
              disabled={loading}
              className="-mr-2"
            >
              Làm mới
            </Button>
          </div>
          <div className="flex flex-col gap-2">
            {preview.messages.map((m, i) => (
              <details key={i} open={i === 0} className="group rounded-card border border-edge bg-surface">
                <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 rounded-card px-4 py-2 text-[14px] [&::-webkit-details-marker]:hidden">
                  <IconChevronRight
                    aria-hidden="true"
                    className="shrink-0 text-[16px] text-muted transition-transform duration-150 group-open:rotate-90"
                  />
                  <span className="min-w-0 flex-1 truncate font-medium text-fg">{roleLabel(i, preview.messages.length, m.role, hasWorld)}</span>
                  <span className="shrink-0 text-[12px] text-muted tabular-nums">{fmt(m.content.length)} ký tự</span>
                </summary>
                <pre className="scroll-thin max-h-[60vh] overflow-auto border-t border-line px-4 py-3 font-sans text-[13px] leading-relaxed whitespace-pre-wrap text-prose [overflow-wrap:anywhere]">
                  {m.content}
                </pre>
              </details>
            ))}
          </div>
        </>
      )}

      {!preview && !error && blockers.length === 0 &&
        (body ? (
          <div className="flex flex-col gap-4" aria-busy="true">
            <span className="sr-only">Đang dựng prompt…</span>
            <div className="rounded-card border border-edge bg-surface p-4">
              <div className="flex justify-between">
                <Skeleton shape="text" width={120} height={14} />
                <Skeleton shape="text" width={90} height={14} />
              </div>
              <Skeleton shape="pill" height={8} className="mt-2" />
              <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 min-[420px]:grid-cols-3">
                {BLOCKS.map((b) => (
                  <Skeleton key={b.key} shape="text" height={14} />
                ))}
              </div>
            </div>
            <Skeleton shape="card" height={44} />
            <Skeleton shape="card" height={44} />
          </div>
        ) : (
          <p className="py-8 text-[14px] text-muted">Chọn persona để xem trước prompt.</p>
        ))}
    </div>
  );
}
