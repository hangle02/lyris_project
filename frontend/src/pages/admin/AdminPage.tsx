import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../../api/client";
import { Avatar } from "../../components/Avatar";
import { IconMoreHorizontal, IconPlus } from "../../components/icons";
import { SubpageHeader } from "../../components/shell/SubpageHeader";
import { Badge, Button, ChoiceGroup, EmptyState, IconButton, InlineAlert, Modal, SegmentedControl, TextField } from "../../components/ui";
import { cx } from "../../components/ui/logic";
import { inviteLink, formatInvite } from "../../lib/inviteCode";
import { initialTab } from "../../lib/overlayParam";
import { routeHref } from "../../lib/router";
import type { AdminAccount, InviteCreated, InviteDays, InviteOut } from "../../types";
import {
  accountBadges,
  DEFAULT_EXPIRY,
  devicesLine,
  disableConfirm,
  EXPIRY_OPTIONS,
  INVITE_ONCE,
  inviteBadge,
  inviteDateLine,
  inviteLabel,
  isLocalOrigin,
  lastSeenLine,
  NOTE_MAX,
  resetConfirm,
  resetNote,
  revokeConfirm,
  sortAccounts,
  sortInvites,
} from "./logic";
import { AdjustCoinsDialog, CoinView } from "./CoinView";
import { memberCoinLine } from "./adminCoinLogic";
import { MetricsView } from "./MetricsView";
import { ConfirmDialog, CopyButton, RowsSkeleton, SecretText, SectionHead, failure } from "./parts";
import type { Failure, Load } from "./parts";
import { ReportsView } from "./ReportsView";

type AdminTab = "accounts" | "coins" | "metrics" | "reports";
const ADMIN_TABS: { value: AdminTab; label: string }[] = [
  { value: "accounts", label: "Tài khoản" },
  { value: "coins", label: "Coin" },
  { value: "metrics", label: "Số liệu" },
  { value: "reports", label: "Báo cáo" },
];

// ---- invites ----

function CreateInviteDialog({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (c: InviteCreated) => void }) {
  const [note, setNote] = useState("");
  const [days, setDays] = useState<`${InviteDays}`>(DEFAULT_EXPIRY);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<Failure | null>(null);
  const [created, setCreated] = useState<InviteCreated | null>(null);
  /** "Sao chép liên kết" failed (plain http on the Wi-Fi address): show the link to select by hand. */
  const [showLink, setShowLink] = useState(false);
  const noteRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setNote("");
    setDays(DEFAULT_EXPIRY);
    setError(null);
    setCreated(null);
    setShowLink(false);
    setSending(false);
  }, [open]);

  const create = async () => {
    if (sending) return;
    setSending(true);
    setError(null);
    try {
      const res = await api.createInvite(note.trim(), Number(days) as InviteDays);
      setCreated(res);
      onCreated(res);
    } catch (e) {
      setError(failure(e));
    } finally {
      setSending(false);
    }
  };

  const local = typeof window !== "undefined" && isLocalOrigin(window.location.hostname);
  const code = created ? formatInvite(created.code) : "";
  const link = created ? inviteLink(window.location.origin, code) : "";

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={created ? "Mã mời mới" : "Tạo mã mời"}
      description={created ? undefined : "Người nhận nhập mã này ở trang tạo tài khoản."}
      size="sm"
      // The code is shown once: once it is on screen, only "Xong" or the close button end the dialog
      // (a stray tap on the scrim or Escape must not lose it).
      dismissible={!sending && !created}
      initialFocusRef={noteRef}
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
          {created.invite.note && <p className="text-[14px] text-muted">{created.invite.note}</p>}
          <SecretText>{code}</SecretText>
          <div className="flex flex-wrap gap-2">
            <CopyButton text={code} label="Sao chép mã" />
            <CopyButton text={link} label="Sao chép liên kết" variant="ghost" onFailed={() => setShowLink(true)} />
          </div>
          {showLink && (
            <p className="rounded-control border border-line bg-surface-2 px-3 py-2 text-[13px] leading-snug text-fg select-all [overflow-wrap:anywhere]">
              {link}
            </p>
          )}
          <p className="text-[13px] leading-snug text-muted">{INVITE_ONCE}</p>
          {local && (
            <p className="text-[13px] leading-snug text-muted">
              Liên kết dùng địa chỉ bạn đang mở. Để gửi cho máy khác, hãy mở Lyris bằng địa chỉ Wi-Fi của Mac.
            </p>
          )}
        </div>
      ) : (
        <form
          className="flex flex-col gap-5"
          onSubmit={(e) => {
            e.preventDefault();
            void create();
          }}
        >
          <TextField
            ref={noteRef}
            label="Ghi chú"
            value={note}
            onChange={setNote}
            maxLength={NOTE_MAX}
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


function InviteRow({ invite, onRevoke }: { invite: InviteOut; onRevoke: (i: InviteOut) => void }) {
  const badge = inviteBadge(invite);
  const dateLine = inviteDateLine(invite);
  return (
    <li className="flex items-center gap-3 px-4 py-3">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-[15px] font-semibold text-fg tabular-nums">{inviteLabel(invite.hint)}</span>
          <Badge tone={badge.tone} className="max-w-full truncate">
            {badge.label}
          </Badge>
        </div>
        {(invite.note || dateLine) && (
          <p className="truncate text-[13px] leading-snug text-muted">{[invite.note, dateLine].filter(Boolean).join(" · ")}</p>
        )}
      </div>
      {invite.status === "active" && (
        <Button size="sm" variant="ghost" onClick={() => onRevoke(invite)} aria-label={`Huỷ mã ${inviteLabel(invite.hint)}`} className="shrink-0">
          Huỷ
        </Button>
      )}
    </li>
  );
}

function InvitesSection() {
  const [load, setLoad] = useState<Load<InviteOut>>({ kind: "loading" });
  const [creating, setCreating] = useState(false);
  const [revoking, setRevoking] = useState<InviteOut | null>(null);

  const reload = useCallback(async () => {
    try {
      setLoad({ kind: "ready", items: sortInvites(await api.listInvites()) });
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
    body = <InlineAlert tone="error" text={`Không tải được mã mời. ${load.error.text}`} technical={load.error.technical} onRetry={() => void reload()} />;
  else if (load.items.length === 0) body = <EmptyState text="Chưa có mã mời nào. Tạo một mã để mời người khác vào Lyris này." />;
  else
    body = (
      <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-card border border-edge bg-surface">
        {load.items.map((i) => (
          <InviteRow key={i.id} invite={i} onRevoke={setRevoking} />
        ))}
      </ul>
    );

  return (
    <section aria-labelledby="admin-invites" className="flex flex-col gap-3">
      <SectionHead
        id="admin-invites"
        title="Mã mời"
        action={
          <Button size="sm" variant="primary" icon={<IconPlus />} onClick={() => setCreating(true)}>
            Tạo mã mời
          </Button>
        }
      />
      {body}
      <CreateInviteDialog open={creating} onClose={() => setCreating(false)} onCreated={() => void reload()} />
      <ConfirmDialog
        open={revoking !== null}
        title="Huỷ mã mời"
        text={revoking ? revokeConfirm(revoking.hint) : ""}
        confirmLabel="Huỷ mã"
        danger
        onCancel={() => setRevoking(null)}
        run={async () => {
          if (!revoking) return;
          await api.revokeInvite(revoking.id);
          setRevoking(null);
          await reload();
        }}
      />
    </section>
  );
}

// ---- members ----

type MemberDialog =
  | { kind: "menu"; account: AdminAccount }
  | { kind: "reset"; account: AdminAccount }
  | { kind: "password"; account: AdminAccount; password: string }
  | { kind: "disable"; account: AdminAccount }
  | { kind: "coins"; account: AdminAccount };

function MemberRow({ account, now, onMenu }: { account: AdminAccount; now: Date; onMenu: (a: AdminAccount) => void }) {
  const badges = accountBadges(account);
  const coins = account.role === "owner" ? null : memberCoinLine(account.coin_balance);
  return (
    <li className="flex items-center gap-3 px-4 py-3">
      <Avatar name={account.display_name} url={account.avatar_url} size={40} />
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <span className="min-w-0 truncate text-[15px] font-semibold text-fg">{account.display_name}</span>
          {badges.map((b) => (
            <Badge key={b.label} tone={b.tone}>
              {b.label}
            </Badge>
          ))}
        </div>
        <span className="truncate text-[14px] leading-snug text-muted">@{account.handle}</span>
        <span className="text-[13px] leading-snug text-muted">
          {lastSeenLine(account.last_login_at, now)} · {devicesLine(account.session_count)}
        </span>
        {coins && (
          <span data-member-coins className="text-[13px] leading-snug font-medium text-fg tabular-nums">
            {coins}
          </span>
        )}
      </div>
      {account.role !== "owner" && (
        <IconButton
          size="sm"
          label={`Việc với @${account.handle}`}
          icon={<IconMoreHorizontal />}
          onClick={() => onMenu(account)}
          aria-haspopup="dialog"
          className="shrink-0"
        />
      )}
    </li>
  );
}

function MembersSection() {
  const [load, setLoad] = useState<Load<AdminAccount>>({ kind: "loading" });
  const [dialog, setDialog] = useState<MemberDialog | null>(null);
  const [enabling, setEnabling] = useState(false);
  const [menuError, setMenuError] = useState<Failure | null>(null);
  const now = useMemo(() => new Date(), [load]);

  const reload = useCallback(async () => {
    try {
      setLoad({ kind: "ready", items: sortAccounts(await api.listAdminAccounts()) });
    } catch (e) {
      setLoad({ kind: "error", error: failure(e) });
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const replace = (a: AdminAccount) =>
    setLoad((l) => (l.kind === "ready" ? { kind: "ready", items: l.items.map((x) => (x.id === a.id ? a : x)) } : l));

  const enable = async (a: AdminAccount) => {
    setEnabling(true);
    setMenuError(null);
    try {
      replace(await api.enableAccount(a.id));
      setDialog(null);
    } catch (e) {
      setMenuError(failure(e));
    } finally {
      setEnabling(false);
    }
  };

  let body: ReactNode;
  if (load.kind === "loading") body = <RowsSkeleton rows={2} height={84} />;
  else if (load.kind === "error")
    body = <InlineAlert tone="error" text={`Không tải được danh sách tài khoản. ${load.error.text}`} technical={load.error.technical} onRetry={() => void reload()} />;
  else
    body = (
      <>
        <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-card border border-edge bg-surface">
          {load.items.map((a) => (
            <MemberRow
              key={a.id}
              account={a}
              now={now}
              onMenu={(acc) => {
                setMenuError(null);
                setDialog({ kind: "menu", account: acc });
              }}
            />
          ))}
        </ul>
        {load.items.length <= 1 && <p className="text-[14px] leading-snug text-muted">Chưa có ai khác. Tạo mã mời ở trên để mời người khác.</p>}
      </>
    );

  const target = dialog?.account ?? null;

  return (
    <section aria-labelledby="admin-members" className="flex flex-col gap-3">
      <SectionHead id="admin-members" title="Thành viên" count={load.kind === "ready" ? load.items.length : undefined} />
      {body}

      {/* The "…" menu: a small sheet of actions (a bottom sheet on a phone). */}
      <Modal
        open={dialog?.kind === "menu"}
        onClose={() => setDialog(null)}
        title={target ? `@${target.handle}` : ""}
        description={target?.display_name}
        size="sm"
        dismissible={!enabling}
      >
        {target && (
          <div className="flex flex-col gap-2">
            <Button block onClick={() => setDialog({ kind: "coins", account: target })} disabled={enabling}>
              Cộng/trừ coin
            </Button>
            <Button block onClick={() => setDialog({ kind: "reset", account: target })} disabled={enabling}>
              Đặt lại mật khẩu
            </Button>
            {target.status === "disabled" ? (
              <Button block onClick={() => void enable(target)} loading={enabling}>
                Mở khoá
              </Button>
            ) : (
              <Button block variant="danger" onClick={() => setDialog({ kind: "disable", account: target })}>
                Tạm khoá
              </Button>
            )}
            {menuError && <InlineAlert tone="error" text={menuError.text} technical={menuError.technical} />}
          </div>
        )}
      </Modal>

      <ConfirmDialog
        open={dialog?.kind === "reset"}
        title="Đặt lại mật khẩu"
        text={target ? resetConfirm(target.handle) : ""}
        confirmLabel="Đặt lại"
        onCancel={() => setDialog(null)}
        run={async () => {
          if (!target) return;
          const res = await api.resetAccountPassword(target.id);
          replace(res.account);
          setDialog({ kind: "password", account: res.account, password: res.temporary_password });
        }}
      />

      <Modal
        open={dialog?.kind === "password"}
        onClose={() => setDialog(null)}
        title="Mật khẩu tạm"
        size="sm"
        // Shown once, and the member's old password is already gone: no closing by the scrim or Escape.
        dismissible={false}
        footer={
          <Button size="sm" variant="primary" onClick={() => setDialog(null)}>
            Xong
          </Button>
        }
      >
        {dialog?.kind === "password" && (
          <div className="flex flex-col gap-4">
            <SecretText>{dialog.password}</SecretText>
            <div>
              <CopyButton text={dialog.password} label="Sao chép" />
            </div>
            <p className="text-[14px] leading-relaxed text-muted">{resetNote(dialog.account.handle)}</p>
          </div>
        )}
      </Modal>

      <ConfirmDialog
        open={dialog?.kind === "disable"}
        title={target ? `Tạm khoá @${target.handle}` : "Tạm khoá"}
        text={target ? disableConfirm(target.handle) : ""}
        confirmLabel="Tạm khoá"
        danger
        onCancel={() => setDialog(null)}
        run={async () => {
          if (!target) return;
          replace(await api.disableAccount(target.id));
          setDialog(null);
        }}
      />

      <AdjustCoinsDialog
        account={dialog?.kind === "coins" ? dialog.account : null}
        onClose={() => setDialog(null)}
        onSaved={(account, balance) => {
          replace({ ...account, coin_balance: balance });
          setDialog(null);
        }}
      />
    </section>
  );
}

/**
 * "#/admin" (docs/auth.md §7.3), owner only. Four tabs: "Tài khoản" (invites: create, copy once,
 * revoke; accounts: status, last sign-in, devices, a member's coins; reset a password, disable, enable,
 * "Cộng/trừ coin"), "Coin" (top-up codes and the coin log, docs/coins.md §4), "Số liệu" (usage numbers
 * and the CSV, docs/tracking-plan.md) and "Báo cáo" (reports of AI replies, docs/compliance.md §2).
 * Nothing here opens anyone's stories or private characters. "?tab=coins" / "?tab=metrics" /
 * "?tab=reports" opens a tab on load (screenshots).
 */
export function AdminPage() {
  const [tab, setTab] = useState<AdminTab>(() => initialTab<AdminTab>(["accounts", "coins", "metrics", "reports"], "accounts"));
  useEffect(() => {
    document.title = "Quản lý tài khoản · Lyris";
  }, []);
  return (
    <div className="min-h-dvh bg-bg">
      <SubpageHeader backHref={routeHref({ name: "hub" })} backLabel="Về Tương tác" title="Quản lý tài khoản" />
      <main className={cx("mx-auto flex w-full max-w-[720px] flex-col gap-6 px-4 pt-5 pb-[max(3rem,env(safe-area-inset-bottom))] sm:px-6")}>
        <SegmentedControl label="Mục quản lý" options={ADMIN_TABS} value={tab} onChange={setTab} />
        {tab === "accounts" ? (
          <div className="flex flex-col gap-8">
            <InvitesSection />
            <MembersSection />
          </div>
        ) : tab === "coins" ? (
          <CoinView />
        ) : tab === "metrics" ? (
          <MetricsView />
        ) : (
          <ReportsView />
        )}
      </main>
    </div>
  );
}
