import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { IconDownload } from "../../components/icons";
import { ChoiceGroup, EmptyState, InlineAlert, Meter, Skeleton } from "../../components/ui";
import {
  countText,
  csvRange,
  dayLabel,
  funnelRates,
  METRIC_DAYS,
  percentText,
  topActions,
} from "../../lib/compliance";
import type { AnalyticsSummary } from "../../types";

type Load = { kind: "loading" } | { kind: "ready"; data: AnalyticsSummary } | { kind: "error"; text: string; technical: string | null };

/** One number with its name: equal-size tiles in a 2-column grid (4 from sm). */
function Tile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="flex h-full min-h-[96px] flex-col justify-between gap-2 rounded-card border border-edge bg-surface px-4 py-3.5">
      <span className="text-[13px] leading-snug text-muted">{label}</span>
      <span className="flex flex-col gap-0.5">
        <span className="text-[24px] leading-none font-semibold text-fg tabular-nums">{value}</span>
        {note && <span className="text-[12px] leading-snug text-muted tabular-nums">{note}</span>}
      </span>
    </div>
  );
}

function Block({ id, title, hint, children }: { id: string; title: string; hint?: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h2 id={id} className="text-[18px] leading-tight font-semibold text-fg">
          {title}
        </h2>
        {hint && <p className="text-[13px] leading-snug text-muted">{hint}</p>}
      </div>
      {children}
    </section>
  );
}

/**
 * "Số liệu sử dụng" (owner, docs/tracking-plan.md §5, §8): who came, how far they got, who came back,
 * and the CSV of every recorded action for later analysis. Never anything anyone wrote.
 */
export function MetricsView() {
  const [days, setDays] = useState<(typeof METRIC_DAYS)[number]["value"]>("30");
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    setLoad((l) => (l.kind === "ready" ? l : { kind: "loading" }));
    api
      .analyticsSummary(Number(days), ctrl.signal)
      .then((data) => setLoad({ kind: "ready", data }))
      .catch((e: unknown) => {
        if (!ctrl.signal.aborted) setLoad({ kind: "error", text: errorMessage(e), technical: errorTechnical(e) });
      });
    return () => ctrl.abort();
  }, [days, nonce]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);
  const range = useMemo(() => csvRange(Number(days), new Date()), [days]);
  const csvHref = api.analyticsCsvUrl(range.since, range.until);

  let body: ReactNode;
  if (load.kind === "loading") {
    body = (
      <div aria-busy="true" className="flex flex-col gap-6">
        <span className="sr-only">Đang tải…</span>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} shape="card" height={96} />
          ))}
        </div>
        <Skeleton shape="card" height={220} />
      </div>
    );
  } else if (load.kind === "error") {
    body = <InlineAlert tone="error" text={`Chưa tải được số liệu. ${load.text}`} technical={load.technical} onRetry={retry} />;
  } else {
    const d = load.data;
    const rates = funnelRates(d.funnel);
    const actions = topActions(d.counts);
    const busiest = d.daily.reduce<{ date: string; active: number } | null>((best, x) => (!best || x.active > best.active ? x : best), null);
    body =
      d.total_events === 0 ? (
        <EmptyState text="Chưa có số liệu nào trong khoảng này. Số liệu xuất hiện khi mọi người dùng Lyris." />
      ) : (
        <div className="flex flex-col gap-8">
          <Block id="metrics-people" title="Người dùng" hint="Người dùng là một tài khoản, hoặc một thiết bị chưa đăng nhập.">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Tile label="Hôm nay" value={countText(d.dau)} />
              <Tile label="7 ngày qua" value={countText(d.wau)} />
              <Tile label="30 ngày qua" value={countText(d.mau)} />
              <Tile
                label="Ngày đông nhất"
                value={busiest && busiest.active > 0 ? countText(busiest.active) : "—"}
                note={busiest && busiest.active > 0 ? dayLabel(busiest.date) : undefined}
              />
            </div>
          </Block>

          <Block
            id="metrics-funnel"
            title="Hành trình người mới"
            hint="Trong số người xem Khám phá, bao nhiêu người đi tiếp tới từng bước."
          >
            <div className="flex flex-col gap-4 rounded-card border border-edge bg-surface px-4 py-4">
              {d.funnel.map((step, i) => (
                <Meter
                  key={step.step}
                  label={step.label}
                  value={step.converted}
                  max={Math.max(1, d.funnel[0]?.users ?? 1)}
                  valueText={`${countText(step.converted)} · ${percentText(rates[i])}`}
                  empty={rates[i] === null}
                />
              ))}
            </div>
          </Block>

          <Block id="metrics-return" title="Quay lại" hint="Người dùng lần đầu trong khoảng này, sau đó quay lại đúng 1 ngày / 7 ngày sau.">
            <div className="grid grid-cols-2 gap-3">
              <Tile
                label="Sau 1 ngày"
                value={percentText(d.retention.d1.rate)}
                note={`${countText(d.retention.d1.retained)} / ${countText(d.retention.d1.cohort)} người`}
              />
              <Tile
                label="Sau 7 ngày"
                value={percentText(d.retention.d7.rate)}
                note={`${countText(d.retention.d7.retained)} / ${countText(d.retention.d7.cohort)} người`}
              />
            </div>
          </Block>

          {actions.length > 0 && (
            <Block id="metrics-actions" title="Thao tác nhiều nhất">
              <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-card border border-edge bg-surface">
                {actions.map((a) => (
                  <li key={a.name} className="flex min-h-11 items-center justify-between gap-3 px-4 py-2 text-[14px]">
                    <span className="min-w-0 truncate text-fg">{a.label}</span>
                    <span className="shrink-0 text-muted tabular-nums">{countText(a.count)}</span>
                  </li>
                ))}
              </ul>
              <p className="text-[13px] text-muted tabular-nums">Tổng {countText(d.total_events)} thao tác được ghi.</p>
            </Block>
          )}
        </div>
      );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4">
        <ChoiceGroup label="Khoảng thời gian" options={METRIC_DAYS} value={days} onChange={setDays} />
        <p className="text-[13px] leading-snug text-muted">
          Chỉ ghi thao tác (mở trang, bắt đầu story, gửi lượt…), không bao giờ ghi chữ ai viết. Người đã tắt chia sẻ dữ liệu không được tính.
        </p>
      </div>
      {body}
      <section aria-labelledby="metrics-export" className="flex flex-col gap-2 border-t border-line pt-5">
        <h2 id="metrics-export" className="text-[16px] leading-tight font-semibold text-fg">
          Xuất dữ liệu
        </h2>
        <p className="text-[13px] leading-snug text-muted">
          Tệp CSV của mọi thao tác trong {METRIC_DAYS.find((o) => o.value === days)?.label ?? `${days} ngày`} qua, mở được bằng Excel hay Google Sheets.
        </p>
        <div>
          <a
            href={csvHref}
            download
            className="inline-flex h-11 items-center gap-2 rounded-full bg-surface-2 px-5 text-[15px] font-semibold text-fg transition-colors duration-150 hover:bg-surface-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent [&_svg]:text-[18px]"
          >
            <IconDownload aria-hidden="true" />
            Tải tệp CSV
          </a>
        </div>
      </section>
    </div>
  );
}
