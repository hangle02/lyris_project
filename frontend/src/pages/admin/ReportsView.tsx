import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { Badge, Button, EmptyState, InlineAlert, Modal, SegmentedControl, Skeleton } from "../../components/ui";
import {
  reasonLabel,
  REPORT_STATUS_OPTIONS,
  reportContext,
  sortReports,
  UNPUBLISH_CONFIRM,
  UNPUBLISH_DONE,
  UNPUBLISH_LABEL,
} from "../../lib/compliance";
import type { AdminReport, ReportStatus } from "../../types";
import { relativeTime } from "./logic";

type Load = { kind: "loading" } | { kind: "ready"; items: AdminReport[] } | { kind: "error"; text: string; technical: string | null };

const EMPTY: Record<ReportStatus, string> = {
  open: "Không có báo cáo nào cần xem.",
  reviewed: "Chưa có báo cáo nào đã xem.",
  dismissed: "Chưa có báo cáo nào bị bỏ qua.",
};

function ReportCard({
  report,
  now,
  busy,
  onStatus,
  onUnpublish,
}: {
  report: AdminReport;
  now: Date;
  busy: boolean;
  onStatus: (r: AdminReport, s: ReportStatus) => void;
  onUnpublish: (r: AdminReport) => void;
}) {
  const isCard = report.target === "character";
  const context = reportContext(report);
  const when = relativeTime(report.created_at, now);
  return (
    <li className="flex flex-col gap-3 rounded-card border border-edge bg-surface px-4 py-4">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <Badge tone={report.reason === "minor_safety" ? "danger" : "accent"}>{reasonLabel(report.reason)}</Badge>
        <span className="text-[13px] text-muted">{[when, context].filter(Boolean).join(" · ")}</span>
      </div>
      {report.note && (
        <p className="text-[14px] leading-relaxed text-fg [overflow-wrap:anywhere]">
          <span className="text-muted">Ghi chú: </span>
          {report.note}
        </p>
      )}
      {isCard ? null : report.shared_text && report.message_text ? (
        <div className="flex flex-col gap-1.5">
          <p className="text-[13px] font-medium text-muted">Câu trả lời được gửi kèm</p>
          <p
            lang={report.language ?? "vi"}
            className="scroll-thin max-h-56 overflow-y-auto rounded-control bg-surface-2 px-3.5 py-3 font-story text-[15px] leading-relaxed whitespace-pre-wrap text-prose [overflow-wrap:anywhere]"
          >
            {report.message_text}
          </p>
        </div>
      ) : (
        <p className="text-[13px] leading-snug text-muted">Người báo cáo không gửi kèm câu trả lời.</p>
      )}
      {report.public_card_name && (
        <p className="text-[13px] leading-snug text-muted">
          Nhân vật công khai:{" "}
          <a
            href={report.public_card_id !== null ? `#/character/${report.public_card_id}` : undefined}
            className="font-medium text-fg underline decoration-line-strong underline-offset-2 hover:decoration-accent"
          >
            {report.public_card_name}
          </a>
          {report.public_card_creator ? ` · bởi @${report.public_card_creator}` : ""}
        </p>
      )}
      <div className="-ml-2 flex flex-wrap gap-1">
        {report.status !== "reviewed" && (
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus(report, "reviewed")} className="max-sm:h-11">
            Đánh dấu đã xem
          </Button>
        )}
        {report.status !== "dismissed" && (
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus(report, "dismissed")} className="max-sm:h-11">
            Bỏ qua
          </Button>
        )}
        {report.status !== "open" && (
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus(report, "open")} className="max-sm:h-11">
            Mở lại
          </Button>
        )}
        {report.public_card_id !== null && report.public_card_name && (
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onUnpublish(report)} className="max-sm:h-11">
            {UNPUBLISH_LABEL}
          </Button>
        )}
      </div>
    </li>
  );
}

/**
 * "Báo cáo" (owner, docs/compliance.md §2): reports of AI replies and of public characters, never
 * who sent them nor whose story. The reply's text is there only when the reporter chose to send it.
 * A reported public character can be hidden (made private) from here.
 */
export function ReportsView() {
  const [status, setStatus] = useState<ReportStatus>("open");
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [busyId, setBusyId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<{ text: string; technical: string | null } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [hiding, setHiding] = useState<AdminReport | null>(null);
  const now = useMemo(() => new Date(), [load]);

  const reload = useCallback(async (s: ReportStatus) => {
    setLoad({ kind: "loading" });
    try {
      setLoad({ kind: "ready", items: sortReports(await api.listReports(s)) });
    } catch (e) {
      setLoad({ kind: "error", text: errorMessage(e), technical: errorTechnical(e) });
    }
  }, []);

  useEffect(() => {
    void reload(status);
  }, [status, reload]);

  const change = async (r: AdminReport, next: ReportStatus) => {
    setBusyId(r.id);
    setActionError(null);
    try {
      await api.setReportStatus(r.id, next);
      // It leaves this list (each list shows one status).
      setLoad((l) => (l.kind === "ready" ? { kind: "ready", items: l.items.filter((x) => x.id !== r.id) } : l));
    } catch (e) {
      setActionError({ text: errorMessage(e), technical: errorTechnical(e) });
    } finally {
      setBusyId(null);
    }
  };

  const unpublish = async (r: AdminReport) => {
    setHiding(null);
    if (r.public_card_id === null) return;
    setBusyId(r.id);
    setActionError(null);
    setNotice(null);
    try {
      await api.unpublishCard(r.public_card_id);
      setNotice(UNPUBLISH_DONE);
      // The character's name disappears from every report once it is private: read the list again.
      await reload(status);
    } catch (e) {
      setActionError({ text: errorMessage(e), technical: errorTechnical(e) });
    } finally {
      setBusyId(null);
    }
  };

  let body: ReactNode;
  if (load.kind === "loading") {
    body = (
      <div aria-busy="true" className="flex flex-col gap-3">
        <span className="sr-only">Đang tải…</span>
        <Skeleton shape="card" height={140} />
        <Skeleton shape="card" height={140} />
      </div>
    );
  } else if (load.kind === "error") {
    body = <InlineAlert tone="error" text={`Không tải được báo cáo. ${load.text}`} technical={load.technical} onRetry={() => void reload(status)} />;
  } else if (load.items.length === 0) {
    body = <EmptyState text={EMPTY[status]} />;
  } else {
    body = (
      <ul className="flex flex-col gap-3">
        {load.items.map((r) => (
          <ReportCard
            key={r.id}
            report={r}
            now={now}
            busy={busyId !== null}
            onStatus={(x, s) => void change(x, s)}
            onUnpublish={setHiding}
          />
        ))}
      </ul>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-[13px] leading-snug text-muted">
        Báo cáo về câu trả lời của nhân vật và về nhân vật công khai. Bạn không thấy ai đã báo cáo và không mở được story của họ.
      </p>
      <SegmentedControl label="Trạng thái báo cáo" options={[...REPORT_STATUS_OPTIONS]} value={status} onChange={setStatus} size="sm" />
      {actionError && <InlineAlert tone="error" text={actionError.text} technical={actionError.technical} />}
      {notice && <InlineAlert tone="info" text={notice} />}
      {body}
      <Modal
        open={hiding !== null}
        onClose={() => setHiding(null)}
        title={UNPUBLISH_LABEL}
        size="sm"
        footer={
          <>
            <Button size="sm" variant="ghost" onClick={() => setHiding(null)} className="max-sm:h-11">
              Giữ nguyên
            </Button>
            <Button size="sm" variant="danger" onClick={() => hiding && void unpublish(hiding)} className="max-sm:h-11">
              {UNPUBLISH_LABEL}
            </Button>
          </>
        }
      >
        <p className="text-[15px] leading-relaxed text-fg">{UNPUBLISH_CONFIRM}</p>
      </Modal>
    </div>
  );
}
