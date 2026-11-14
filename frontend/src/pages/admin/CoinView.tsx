import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../../api/client";
import { IconCoin, IconPlus } from "../../components/icons";
import { Badge, Button, ChoiceGroup, EmptyState, InlineAlert, Modal, TextField } from "../../components/ui";
import { cx } from "../../components/ui/logic";
import { formatCoinNumber, formatCoins, formatDelta } from "../../lib/coins";
import type { AdminAccount, InviteDays } from "../../types";
import {
  adjustRequest,
  CODE_NOTE_MAX,
  codeRequest,
  coinLogTitle,
  newRequestId,
  PACK_CHOICES,
  REASON_MAX,
  topupCodeBadge,
} from "./adminCoinLogic";
import type { CodeChoice, CoinLog, TopupCodeCreated, TopupCodeItem } from "./adminCoinLogic";
import { DEFAULT_EXPIRY, EXPIRY_OPTIONS, inviteDateLine, inviteLabel, relativeTime } from "./logic";
import { ConfirmDialog, CopyButton, RowsSkeleton, SecretText, SectionHead, failure } from "./parts";
import type { Failure, Load } from "./parts";

const CODE_ONCE = "Mã chỉ hiện một lần và dùng được một lần. Người nhận nhập mã ở Ví coin → Nạp coin.";

// ---- top-up codes ----

function CreateCodeDialog({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [choice, setChoice] = useState<CodeChoice>("p100");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [days, setDays] = useState<`${InviteDays}`>(DEFAULT_EXPIRY);
  const [sending, setSending] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [error, setError] = useState<Failure | null>(null);
  const [created, setCreated] = useState<TopupCodeCreated | null>(null);

  useEffect(() => {
    if (!open) return;
    setChoice("p100");
    setAmount("");
    setNote("");
    setDays(DEFAULT_EXPIRY);
    setSending(false);
    setProblem(null);
    setError(null);
    setCreated(null);
  }, [open]);

  const create = async () => {
    if (sending) return;
    const req = codeRequest(choice, amount, note, days);
    if (!req.ok) {
      setProblem(req.problem);
      return;
    }
    setSending(true);
    setProblem(null);
    setError(null);
    try {
      const res = await api.createTopupCode(req.body);
      setCreated(res);
      onCreated();
    } catch (e) {
      setError(failure(e));
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={created ? "Mã nạp mới" : "Tạo mã nạp"}
      description={created ? undefined : "Tặng thành viên một mã để nạp coin. Mã nạp được tặng, không bán."}
      size="sm"
      // The code is shown once: once it is on screen, only "Xong" or the close button end the dialog.
      dismissible={!sending && !created}
      footer={
        created ? (
          <Button size="sm" variant="primary" onClick={onClose}>
            Xong
          </Button>
        ) : (
          <>
            <Button size="sm" variant="ghost" onClick={onClose} disabled={sending}>
              Huỷ
            </Button>
            <Button size="sm" variant="primary" onClick={() => void create()} loading={sending}>
              Tạo mã
            </Button>
          </>
        )
      }
    >
      {created ? (
        <div className="flex flex-col gap-4">
          <p className="flex items-center gap-2 text-[15px] font-medium text-fg">
            <IconCoin aria-hidden="true" className="text-[18px] text-accent-2" />
            {formatCoins(created.item.amount)}
            {created.item.note && <span className="min-w-0 truncate font-normal text-muted">· {created.item.note}</span>}
          </p>
          <SecretText>{created.code}</SecretText>
          <div>
            <CopyButton text={created.code} label="Sao chép mã" />
          </div>
          <p className="text-[13px] leading-snug text-muted">{CODE_ONCE}</p>
        </div>
      ) : (
        <form
          className="flex flex-col gap-5"
          onSubmit={(e) => {
            e.preventDefault();
            void create();
          }}
        >
          <ChoiceGroup
            label="Gói"
            options={PACK_CHOICES}
            value={choice}
            onChange={(v) => {
              setChoice(v);
              setProblem(null);
            }}
            disabled={sending}
          />
          {choice === "custom" && (
            <TextField
              label="Số coin"
              value={amount}
              onChange={(v) => {
                setAmount(v);
                setProblem(null);
              }}
              inputMode="numeric"
              placeholder="1–10.000"
              error={problem ?? undefined}
              disabled={sending}
            />
          )}
          <TextField
            label="Ghi chú"
            value={note}
            onChange={setNote}
            maxLength={CODE_NOTE_MAX}
            placeholder="Ví dụ: cho Mai"
            hint="Chỉ bạn thấy."
            disabled={sending}
          />
          <ChoiceGroup label="Hết hạn sau" options={EXPIRY_OPTIONS} value={days} onChange={setDays} disabled={sending} />
          {error && <InlineAlert tone="error" text={error.text} technical={error.technical} />}
        </form>
      )}
    </Modal>
  );
}

function CodeRow({ item, onRevoke }: { item: TopupCodeItem; onRevoke: (i: TopupCodeItem) => void }) {
  const badge = topupCodeBadge(item);
  const dateLine = inviteDateLine(item);
  return (
    <li className="flex items-center gap-3 px-4 py-3">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-[15px] font-semibold text-fg tabular-nums">{inviteLabel(item.hint)}</span>
          <span className="text-[14px] font-medium text-fg tabular-nums">{formatCoins(item.amount)}</span>
          <Badge tone={badge.tone} className="max-w-full truncate">
            {badge.label}
          </Badge>
        </div>
        {(item.note || dateLine) && (
          <p className="truncate text-[13px] leading-snug text-muted">{[item.note, dateLine].filter(Boolean).join(" · ")}</p>
        )}
      </div>
      {item.status === "active" && (
        <Button size="sm" variant="ghost" onClick={() => onRevoke(item)} aria-label={`Huỷ mã nạp ${inviteLabel(item.hint)}`} className="shrink-0">
          Huỷ
        </Button>
      )}
    </li>
  );
}

function CodesSection() {
  const [load, setLoad] = useState<Load<TopupCodeItem>>({ kind: "loading" });
  const [creating, setCreating] = useState(false);
  const [revoking, setRevoking] = useState<TopupCodeItem | null>(null);

  const reload = useCallback(async () => {
    try {
      setLoad({ kind: "ready", items: await api.listTopupCodes() });
    } catch (e) {
      setLoad({ kind: "error", error: failure(e) });
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  let body: ReactNode;
  if (load.kind === "loading") body = <RowsSkeleton rows={2} height={64} />;
  else if (load.kind === "error")
    body = <InlineAlert tone="error" text={`Không tải được mã nạp. ${load.error.text}`} technical={load.error.technical} onRetry={() => void reload()} />;
  else if (load.items.length === 0) body = <EmptyState text="Chưa có mã nạp nào. Tạo một mã để tặng coin cho thành viên." />;
  else
    body = (
      <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-card border border-edge bg-surface">
        {load.items.map((i) => (
          <CodeRow key={i.id} item={i} onRevoke={setRevoking} />
        ))}
      </ul>
    );

  return (
    <section aria-labelledby="admin-topup-codes" className="flex flex-col gap-3">
      <SectionHead
        id="admin-topup-codes"
        title="Mã nạp"
        action={
          <Button size="sm" variant="primary" icon={<IconPlus />} onClick={() => setCreating(true)}>
            Tạo mã nạp
          </Button>
        }
      />
      <p className="text-[14px] leading-snug text-muted">Chế độ thử: Lyris chưa bán coin. Mã nạp được tặng, không bán.</p>
      {body}
      <CreateCodeDialog open={creating} onClose={() => setCreating(false)} onCreated={() => void reload()} />
      <ConfirmDialog
        open={revoking !== null}
        title="Huỷ mã nạp"
        text={revoking ? `Huỷ mã ${inviteLabel(revoking.hint)}? Ai đang giữ mã này sẽ không dùng được nữa.` : ""}
        confirmLabel="Huỷ mã"
        danger
        onCancel={() => setRevoking(null)}
        run={async () => {
          if (!revoking) return;
          await api.revokeTopupCode(revoking.id);
          setRevoking(null);
          await reload();
        }}
      />
    </section>
  );
}

// ---- coin log ----

function Total({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex min-w-0 flex-col gap-1 rounded-card border border-edge bg-surface px-3 py-3">
      <span className="text-[20px] leading-tight font-semibold text-fg tabular-nums">{formatCoinNumber(value)}</span>
      <span className="text-[12px] leading-snug text-muted">{label}</span>
    </div>
  );
}

function LogSection() {
  const [log, setLog] = useState<{ kind: "loading" } | { kind: "ready"; log: CoinLog } | { kind: "error"; error: Failure }>({ kind: "loading" });
  const reload = useCallback(async () => {
    try {
      setLog({ kind: "ready", log: await api.coinLog() });
    } catch (e) {
      setLog({ kind: "error", error: failure(e) });
    }
  }, []);
  useEffect(() => {
    void reload();
  }, [reload]);
  const now = useMemo(() => new Date(), [log]);

  let body: ReactNode;
  if (log.kind === "loading") body = <RowsSkeleton rows={3} height={56} />;
  else if (log.kind === "error")
    body = <InlineAlert tone="error" text={`Không tải được nhật ký. ${log.error.text}`} technical={log.error.technical} onRetry={() => void reload()} />;
  else
    body = (
      <>
        <div className="grid grid-cols-3 gap-2">
          <Total label="Coin đã phát" value={log.log.totals.granted} />
          <Total label="Coin đã nạp" value={log.log.totals.topped_up} />
          <Total label="Coin đã tiêu" value={log.log.totals.spent} />
        </div>
        <p className="text-[13px] leading-snug text-muted">{`${log.log.totals.days} ngày gần nhất. Danh sách: 50 lần nạp, điều chỉnh và thưởng mốc mới nhất.`}</p>
        {log.log.items.length === 0 ? (
          <EmptyState text="Chưa có lần nạp, điều chỉnh hay thưởng mốc nào." />
        ) : (
          <ul aria-label="Nhật ký coin" className="flex flex-col divide-y divide-line overflow-hidden rounded-card border border-edge bg-surface">
            {log.log.items.map((i) => (
              <li key={i.id} className="flex min-h-14 items-center gap-3 px-4 py-2.5">
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="text-[15px] leading-snug text-fg [overflow-wrap:anywhere]">{coinLogTitle(i)}</span>
                  <span className="truncate text-[13px] leading-snug text-muted">
                    {[i.handle ? `@${i.handle}` : null, relativeTime(i.created_at, now)].filter(Boolean).join(" · ")}
                  </span>
                </span>
                <span className={cx("shrink-0 text-[15px] font-semibold tabular-nums", i.delta > 0 ? "text-ok" : "text-muted")}>
                  {formatDelta(i.delta)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </>
    );

  return (
    <section aria-labelledby="admin-coin-log" className="flex flex-col gap-3">
      <SectionHead id="admin-coin-log" title="Nhật ký" />
      {body}
    </section>
  );
}

/** "Coin" tab of "#/admin" (F43, docs/coins.md §4.3, §4.5): top-up codes and the coin log. */
export function CoinView() {
  return (
    <div className="flex flex-col gap-8">
      <CodesSection />
      <LogSection />
    </div>
  );
}

// ---- "Cộng/trừ coin" of a member (from the "…" sheet of the accounts tab) ----

export function AdjustCoinsDialog({
  account,
  onClose,
  onSaved,
}: {
  account: AdminAccount | null;
  onClose: () => void;
  onSaved: (account: AdminAccount, balance: number) => void;
}) {
  const open = account !== null;
  const [delta, setDelta] = useState("");
  const [reason, setReason] = useState("");
  const [problems, setProblems] = useState<{ delta?: string; reason?: string }>({});
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<Failure | null>(null);
  // One id per opening: pressing "Lưu" again after a network hiccup writes the change once.
  const requestId = useRef(newRequestId());
  const deltaRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setDelta("");
    setReason("");
    setProblems({});
    setSending(false);
    setError(null);
    requestId.current = newRequestId();
  }, [open, account?.id]);

  const save = async () => {
    if (!account || sending) return;
    const req = adjustRequest(delta, reason, requestId.current);
    if (!req.ok) {
      setProblems(req.problems);
      return;
    }
    setProblems({});
    setSending(true);
    setError(null);
    try {
      const res = await api.adjustCoins(account.id, req.body);
      onSaved(account, res.balance);
    } catch (e) {
      setError(failure(e));
    } finally {
      setSending(false);
    }
  };

  const balance = typeof account?.coin_balance === "number" ? formatCoins(account.coin_balance) : null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Cộng/trừ coin"
      description={account ? [`@${account.handle}`, balance ? `Hiện có ${balance}` : null].filter(Boolean).join(" · ") : undefined}
      size="sm"
      dismissible={!sending}
      initialFocusRef={deltaRef}
      footer={
        <>
          <Button size="sm" variant="ghost" onClick={onClose} disabled={sending}>
            Huỷ
          </Button>
          <Button size="sm" variant="primary" onClick={() => void save()} loading={sending}>
            Lưu
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-5"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <TextField
          ref={deltaRef}
          label="Số coin"
          value={delta}
          onChange={(v) => {
            setDelta(v);
            setProblems((p) => ({ ...p, delta: undefined }));
          }}
          placeholder="Ví dụ: 20 hoặc -20"
          hint="Số âm là trừ. Không trừ quá số coin dùng được."
          error={problems.delta}
          autoComplete="off"
          disabled={sending}
        />
        <TextField
          label="Lý do"
          value={reason}
          onChange={(v) => {
            setReason(v);
            setProblems((p) => ({ ...p, reason: undefined }));
          }}
          maxLength={REASON_MAX}
          placeholder="Ví dụ: bù lỗi máy"
          hint="Bắt buộc, 3–120 ký tự. Thành viên thấy lý do trong lịch sử ví."
          error={problems.reason}
          disabled={sending}
        />
        {error && <InlineAlert tone="error" text={error.text} technical={error.technical} />}
      </form>
    </Modal>
  );
}
