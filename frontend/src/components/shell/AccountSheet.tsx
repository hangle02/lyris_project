import { useEffect, useRef, useState } from "react";
import type { ReactNode, RefObject } from "react";
import { api, downloadAccountData, errorMessage, errorTechnical } from "../../api/client";
import { useAdvancedTools } from "../../hooks/useAdvancedTools";
import { accountDeleted, signOut, useAuthAccount } from "../../hooks/useAuth";
import { setAccount } from "../../hooks/useAccount";
import { refreshWallet, useWallet } from "../../hooks/useWallet";
import { COIN_COPY } from "../../lib/coinCopy";
import { formatCoins, noteWalletFrom } from "../../lib/coins";
import { PasswordField } from "../../pages/auth/AuthLayout";
import {
  ABOUT_TEXT,
  DELETE_CONFIRM,
  DELETE_KEPT,
  DELETE_LABEL,
  DELETE_OWNER,
  DELETE_WHAT,
  EXPORT_HINT,
  EXPORT_LABEL,
  PRIVACY_LABEL,
  SHARING_HINT,
  SHARING_LABEL,
  SHARING_OFF_NOTE,
  TERMS_LABEL,
} from "../../lib/compliance";
import { ChangePasswordForm } from "../../pages/auth/ChangePasswordForm";
import { logoutAllConfirm, PASSWORD_CHANGED } from "../../pages/auth/logic";
import type { AccountState } from "../../hooks/useAccount";
import type { HealthLevel } from "../../hooks/useHealth";
import { useSystemInfo } from "../../hooks/useHealth";
import { navigate, routeHref } from "../../lib/router";
import { plainMessage } from "../../lib/text";
import { templateImageCredit } from "../../pages/explore/logic";
import type { ImageCredit } from "../../pages/explore/logic";
import { GENDER_LABELS } from "../../lib/storyOptions";
import { Avatar } from "../Avatar";
import { Wordmark } from "../brand";
import { IconCheck, IconChevronLeft, IconCoin, IconDownload } from "../icons";
import { Badge, Button, Disclosure, EmptyState, ErrorDetails, InlineAlert, Meter, Modal, Select, Skeleton, Spinner, Toggle } from "../ui";
import type { BadgeTone } from "../ui";
import { cx } from "../ui/logic";
import { formatGb, machineStatus, memorySearchRow, memoryText, onOff, plainMachineLine } from "./status";
import type { MachineTone } from "./status";
import type { PersonaSettingsState } from "./usePersonaSettings";

const SYSTEM_POLL_MS = 10_000;

const TONE_BADGE: Record<MachineTone, BadgeTone> = {
  checking: "neutral",
  ok: "ok",
  power: "warn",
  warn: "warn",
  down: "danger",
};

function Section({
  title,
  hideTitle,
  aside,
  children,
}: {
  title: string;
  /** Keep the heading for screen readers only (the account block speaks for itself). */
  hideTitle?: boolean;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3 border-t border-line pt-5 first:border-t-0 first:pt-1">
      {hideTitle ? (
        <h3 className="sr-only">{title}</h3>
      ) : (
        <div className="flex min-h-9 items-center justify-between gap-3">
          <h3 className="text-[16px] leading-tight font-semibold text-fg">{title}</h3>
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

/** Block 1: who you are outside stories (avatar, display name, @handle) and the way to the profile. */
function AccountSection({
  state,
  onLeave,
  onChangePassword,
  notice,
}: {
  state: AccountState;
  onLeave: () => void;
  onChangePassword: () => void;
  /** "Đã đổi mật khẩu…" after the password view saved. */
  notice: string | null;
}) {
  const isOwner = useAuthAccount()?.role === "owner";
  const { account, error, loading, refresh } = state;
  const toProfile = () => {
    onLeave();
    navigate(routeHref({ name: "profile", handle: null }));
  };

  let body: ReactNode;
  if (!account && error) {
    body = (
      <div role="alert" className="flex flex-col items-start gap-3">
        <p className="text-[14px] text-muted [overflow-wrap:anywhere]">Không tải được tài khoản. {error}</p>
        <Button size="sm" loading={loading} onClick={() => void refresh()}>
          Thử lại
        </Button>
      </div>
    );
  } else if (!account) {
    body = (
      <div aria-busy="true" className="flex items-center gap-3.5">
        <Skeleton shape="circle" width={56} height={56} />
        <span className="flex flex-1 flex-col gap-2">
          <Skeleton shape="text" width="45%" height={15} />
          <Skeleton shape="text" width="30%" height={13} />
        </span>
      </div>
    );
  } else {
    body = (
      <div className="flex items-center gap-3.5">
        <Avatar name={account.display_name} url={account.avatar_url} size={56} />
        <span className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="truncate text-[17px] leading-snug font-semibold text-fg">{account.display_name}</span>
          <span className="truncate text-[14px] leading-snug text-muted">@{account.handle}</span>
        </span>
        <Button size="sm" variant="secondary" onClick={toProfile} className="shrink-0">
          Xem profile
        </Button>
      </div>
    );
  }

  return (
    <Section title="Tài khoản" hideTitle>
      {body}
      {notice && (
        <p role="status" className="rounded-control bg-surface-2 px-4 py-3 text-[14px] leading-snug text-fg">
          {notice}
        </p>
      )}
      {account && <div className="-ml-4 flex flex-wrap gap-x-1">
        <Button size="sm" variant="ghost" onClick={onChangePassword} className="max-sm:h-11">
          Đổi mật khẩu
        </Button>
        {isOwner && (
          <Button
            size="sm"
            variant="ghost"
            className="max-sm:h-11"
            onClick={() => {
              onLeave();
              navigate(routeHref({ name: "admin" }));
            }}
          >
            Quản lý tài khoản
          </Button>
        )}
      </div>}
    </Section>
  );
}

/**
 * F42 (docs/coins.md §10.4): the "Coin" row under the account block: balance and "Mở ví coin" for a
 * member; one line for the owner (never charged); nothing while coins are off on this server.
 */
function CoinSection({ onLeave }: { onLeave: () => void }) {
  const { wallet } = useWallet();
  useEffect(() => {
    refreshWallet();
  }, []);
  if (!wallet || !wallet.enabled) return null;
  const owner = wallet.unlimited;
  return (
    <section aria-label={COIN_COPY.accountRow} className="flex items-center gap-3 rounded-card border border-line px-4 py-3">
      <IconCoin className="shrink-0 text-[22px] text-accent-2" />
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-[13px] leading-snug text-muted">{COIN_COPY.accountRow}</span>
        {owner ? (
          <span className="text-[14px] leading-snug text-fg">{COIN_COPY.ownerNote}</span>
        ) : (
          <span className="text-[16px] leading-snug font-semibold text-fg tabular-nums">{formatCoins(wallet.balance)}</span>
        )}
      </span>
      {!owner && (
        <Button
          size="sm"
          variant="secondary"
          className="shrink-0"
          onClick={() => {
            noteWalletFrom("account");
            onLeave();
            navigate("#/coins");
          }}
        >
          {COIN_COPY.openWallet}
        </Button>
      )}
    </section>
  );
}

/** End of the sheet: "Đăng xuất" and "Đăng xuất mọi thiết bị" (asks first, names the handle). */
function SignOutSection() {
  const account = useAuthAccount();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState<"one" | "all" | null>(null);
  const [error, setError] = useState<{ text: string; technical: string | null } | null>(null);
  const keepRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (confirming) keepRef.current?.focus();
  }, [confirming]);

  const run = async (everywhere: boolean) => {
    setBusy(everywhere ? "all" : "one");
    setError(null);
    try {
      await signOut(everywhere);
    } catch (e) {
      setError({ text: errorMessage(e), technical: errorTechnical(e) });
      setBusy(null);
    }
  };

  return (
    <section className="flex flex-col gap-3 border-t border-line pt-5">
      <h3 className="sr-only">Đăng xuất</h3>
      {confirming ? (
        <div role="group" aria-label="Đăng xuất mọi thiết bị" className="flex flex-col gap-3 rounded-control bg-surface-2 p-4">
          <p className="text-[14px] leading-snug text-fg">{logoutAllConfirm(account?.handle ?? "")}</p>
          <div className="flex flex-wrap justify-end gap-2">
            <Button ref={keepRef} size="sm" variant="ghost" onClick={() => setConfirming(false)} disabled={busy !== null} className="max-sm:h-11">
              Giữ nguyên
            </Button>
            <Button size="sm" variant="danger" onClick={() => void run(true)} loading={busy === "all"} className="max-sm:h-11">
              Đăng xuất mọi thiết bị
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Button variant="secondary" onClick={() => void run(false)} loading={busy === "one"} disabled={busy !== null} className="max-sm:w-full">
            Đăng xuất
          </Button>
          <Button variant="ghost" onClick={() => setConfirming(true)} disabled={busy !== null} className="max-sm:w-full">
            Đăng xuất mọi thiết bị
          </Button>
        </div>
      )}
      {error && <InlineAlert tone="error" text={error.text} technical={error.technical} />}
    </section>
  );
}

/** "Đổi mật khẩu" inside the sheet (same frame as "Giới thiệu"): current, new, repeat. */
function PasswordView({ onBack, backRef, onDone }: { onBack: () => void; backRef: RefObject<HTMLButtonElement>; onDone: () => void }) {
  const account = useAuthAccount();
  return (
    <div className="flex flex-col gap-5">
      <div className="-ml-2 pt-1">
        <Button ref={backRef} size="sm" variant="ghost" icon={<IconChevronLeft />} onClick={onBack} className="max-sm:h-11">
          Tài khoản
        </Button>
      </div>
      <p className="text-[14px] leading-snug text-muted">Đổi xong, mọi thiết bị khác đang đăng nhập sẽ phải đăng nhập lại.</p>
      <ChangePasswordForm
        currentLabel="Mật khẩu hiện tại"
        submitLabel="Lưu mật khẩu"
        handle={account?.handle ?? null}
        autoFocus={false}
        onDone={onDone}
        secondary={
          <Button variant="ghost" onClick={onBack} className="max-sm:w-full">
            Huỷ
          </Button>
        }
      />
    </div>
  );
}

/** One row of a definition list: label left (muted), value right (ink, tabular). Missing value: a grey dash. */
function Row({ label, value }: { label: string; value: ReactNode | null }) {
  return (
    <div className="flex min-h-11 items-center justify-between gap-4 border-b border-line py-2 last:border-b-0">
      <dt className="text-[14px] text-muted">{label}</dt>
      <dd className="min-w-0 text-right text-[14px] font-medium text-fg tabular-nums [overflow-wrap:anywhere]">
        {value === null || value === "" ? <span className="text-faint">—</span> : value}
      </dd>
    </div>
  );
}

function PersonaSection({ state, onLeave }: { state: PersonaSettingsState; onLeave: () => void }) {
  const { personas, activePersona, error, reload, save } = state;
  const [savingId, setSavingId] = useState<number | null>(null);
  const [saveError, setSaveError] = useState<{ text: string; technical: string | null } | null>(null);

  const pick = async (id: number) => {
    if (savingId !== null || id === activePersona?.id) return;
    setSavingId(id);
    setSaveError(null);
    try {
      await save({ default_persona_id: id });
    } catch (e) {
      setSaveError({ text: errorMessage(e), technical: errorTechnical(e) });
    } finally {
      setSavingId(null);
    }
  };

  const manage = (
    <Button
      size="sm"
      variant="ghost"
      onClick={() => {
        onLeave();
        navigate(routeHref({ name: "personas" }));
      }}
    >
      Quản lý persona
    </Button>
  );

  let body: ReactNode;
  if (personas === null && error) {
    body = (
      <div role="alert" className="flex flex-col items-start gap-3">
        <p className="text-[14px] text-muted">Không tải được danh sách persona. {error}</p>
        <Button size="sm" onClick={reload}>
          Thử lại
        </Button>
      </div>
    );
  } else if (personas === null) {
    body = (
      <div aria-busy="true" className="flex flex-col gap-2">
        <Skeleton height={56} />
        <Skeleton height={56} />
      </div>
    );
  } else if (personas.length === 0) {
    body = (
      <EmptyState
        text="Chưa có persona nào. Tạo một persona để bước vào story."
        action={
          <Button
            size="sm"
            variant="primary"
            onClick={() => {
              onLeave();
              navigate(routeHref({ name: "personas" }));
            }}
          >
            Tạo persona
          </Button>
        }
      />
    );
  } else {
    body = (
      <>
        <p className="text-[14px] leading-snug text-muted">
          Persona là vai bạn đóng trong story. Story mới sẽ dùng persona này; đổi được ở từng story khi tạo.
        </p>
        <div role="radiogroup" aria-label="Persona đang dùng" className="flex flex-col gap-1.5">
          {personas.map((p) => {
            const on = p.id === activePersona?.id;
            return (
              <button
                key={p.id}
                type="button"
                role="radio"
                aria-checked={on}
                disabled={savingId !== null}
                onClick={() => p.id !== null && void pick(p.id)}
                className={cx(
                  "flex min-h-14 w-full items-center gap-3 rounded-control px-3 py-2 text-left transition-colors duration-150",
                  on ? "bg-accent/12 ring-1 ring-inset ring-accent/50" : "hover:bg-surface-2",
                  "disabled:cursor-default",
                )}
              >
                <Avatar name={p.name} url={p.avatar_url} size={36} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[15px] font-medium text-fg">{p.name}</span>
                  <span className="block truncate text-[13px] text-muted">
                    {GENDER_LABELS[p.gender]}
                    {p.description ? ` · ${p.description}` : ""}
                  </span>
                </span>
                <span aria-hidden="true" className="flex w-5 shrink-0 justify-center text-[18px] text-accent">
                  {savingId === p.id ? <Spinner size={16} /> : on ? <IconCheck /> : null}
                </span>
              </button>
            );
          })}
        </div>
        {saveError && (
          <div role="alert">
            <p className="text-[13px] text-danger">{saveError.text}</p>
            <ErrorDetails technical={saveError.technical} />
          </div>
        )}
        <div className="-ml-4">{manage}</div>
      </>
    );
  }

  return <Section title="Persona cho story mới">{body}</Section>;
}

function MachineSection({ level, state }: { level: HealthLevel; state: PersonaSettingsState }) {
  const { info, error, updatedAt, refresh } = useSystemInfo(SYSTEM_POLL_MS);
  const [modelSaving, setModelSaving] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);
  const [modelErrorTech, setModelErrorTech] = useState<string | null>(null);

  // /api/health may lag /api/system by a few seconds; a reachable Ollama in /api/system wins over "checking".
  const effectiveLevel: HealthLevel = info && !info.ollama_reachable ? "down" : level === "checking" && info ? "ok" : level;
  const status = machineStatus(effectiveLevel, info);

  if (!info) {
    if (error) {
      return (
        <Section title="Máy MacBook M2">
          <div role="alert" className="flex flex-col items-start gap-3">
            <p className="text-[14px] text-muted">Không đọc được trạng thái máy. {error}</p>
            <Button size="sm" onClick={refresh}>
              Thử lại
            </Button>
          </div>
        </Section>
      );
    }
    return (
      <Section title="Máy MacBook M2">
        <div aria-busy="true" className="flex flex-col gap-3">
          <Skeleton shape="pill" width={140} height={20} />
          <Skeleton shape="text" width="40%" height={14} />
          <Skeleton shape="pill" height={8} />
          <Skeleton height={44} />
        </div>
      </Section>
    );
  }

  const mem = memoryText(info.memory_used_gb, info.memory_total_gb);
  const memorySearch = memorySearchRow(info);
  const serverDefault = info.chat_model_default;
  const current = state.settings?.default_chat_model ?? "";
  const modelOptions = [
    { value: "", label: `Theo máy chủ (${serverDefault})` },
    ...info.models.map((m) => ({
      value: m.name,
      label: [m.name, m.parameter_size, m.size_gb !== null ? formatGb(m.size_gb) : null].filter(Boolean).join(" · "),
    })),
  ];
  // A saved model Ollama no longer lists stays visible (and selected) instead of silently vanishing.
  if (current && !info.models.some((m) => m.name === current)) {
    modelOptions.push({ value: current, label: `${current} (không còn trong Ollama)` });
  }

  const changeModel = async (name: string) => {
    setModelSaving(true);
    setModelError(null);
    setModelErrorTech(null);
    try {
      await state.save({ default_chat_model: name || null });
    } catch (e) {
      setModelError(errorMessage(e));
      setModelErrorTech(errorTechnical(e));
    } finally {
      setModelSaving(false);
    }
  };

  const stamp = updatedAt
    ? new Date(updatedAt).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : null;

  return (
    <Section title="Máy MacBook M2" aside={<Badge tone={TONE_BADGE[status.tone]}>{status.long}</Badge>}>
      {error && (
        <p role="status" className="text-[13px] text-muted">
          Lần đọc gần nhất bị lỗi, đang hiện số liệu lúc {stamp}.
        </p>
      )}
      {!info.ollama_reachable && info.ollama_error && (
        <p className="text-[13px] leading-snug text-muted [overflow-wrap:anywhere]">{plainMessage(info.ollama_error)}</p>
      )}

      <Meter
        label="Bộ nhớ hợp nhất"
        value={info.memory_used_gb ?? 0}
        max={info.memory_total_gb ?? 100}
        valueText={mem ?? undefined}
        empty={mem === null}
      />

      <div className="flex flex-col gap-1.5">
        <p className="text-[14px] font-medium text-fg">Model đang nạp</p>
        {info.loaded.length === 0 ? (
          <p className="text-[14px] text-muted">Chưa nạp model nào.</p>
        ) : (
          <ul className="flex flex-col">
            {info.loaded.map((m) => (
              <li key={m.name} className="flex items-center justify-between gap-3 py-1 text-[14px]">
                <span className="min-w-0 truncate text-fg">{m.name}</span>
                <span className="shrink-0 text-muted tabular-nums">{m.size_gb !== null ? formatGb(m.size_gb) : "—"}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <Select
        label="Model chat mặc định"
        value={current}
        onChange={(v) => void changeModel(v)}
        options={modelOptions}
        disabled={modelSaving || !info.ollama_reachable}
        hint={
          info.ollama_reachable
            ? "Áp dụng cho story mới. Story đang có đổi model trong thiết lập của nó."
            : "Cần Ollama đang chạy để chọn model."
        }
        error={modelError ?? undefined}
      />
      <ErrorDetails technical={modelErrorTech} />

      <dl className="flex flex-col">
        <Row label="KV cache" value={info.kv_cache_type} />
        <Row label="Flash Attention" value={onOff(info.flash_attention)} />
        <Row label="Lượt sinh song song" value={info.num_parallel !== null ? String(info.num_parallel) : null} />
        <Row label="Model nạp cùng lúc" value={info.max_loaded_models !== null ? String(info.max_loaded_models) : null} />
        <Row label="Phiên bản Ollama" value={info.ollama_version} />
        <Row label="Ký ức" value={memorySearch.value} />
      </dl>
      {memorySearch.pull && (
        <p className="text-[13px] leading-snug text-muted">
          Muốn nhân vật tìm ký ức theo nghĩa, chạy{" "}
          {/* The command never breaks across lines; UI face, not a monospace (design-impl §10). */}
          <code className="rounded-full bg-surface-2 px-2 py-0.5 font-sans text-[13px] font-medium whitespace-nowrap text-fg">
            {memorySearch.pull}
          </code>{" "}
          trong Terminal.
        </p>
      )}
      {stamp && <p className="text-[13px] text-muted tabular-nums">Cập nhật lúc {stamp}, tự làm mới mỗi 10 giây.</p>}
    </Section>
  );
}

interface CreditRow {
  slug: string;
  name: string;
  credit: ImageCredit;
}

function CreditsList() {
  const [rows, setRows] = useState<CreditRow[] | null>(null);
  useEffect(() => {
    let alive = true;
    api
      .listTemplates()
      .then((list) => {
        if (!alive) return;
        setRows(
          list.flatMap((t) => {
            const credit = templateImageCredit(t);
            return credit ? [{ slug: t.slug, name: t.card.name, credit }] : [];
          }),
        );
      })
      // Credits are a courtesy list; without templates there is nothing to credit.
      .catch(() => alive && setRows([]));
    return () => {
      alive = false;
    };
  }, []);

  if (rows === null) {
    return (
      <div aria-busy="true" className="flex flex-col gap-2">
        <Skeleton shape="text" lines={3} height={14} />
      </div>
    );
  }
  if (rows.length === 0) return <p className="text-[14px] leading-snug text-muted">Chưa có ảnh nào cần ghi nguồn.</p>;
  return (
    <section aria-labelledby="credits-title" className="flex flex-col gap-3">
      <h3 id="credits-title" className="text-[16px] leading-tight font-semibold text-fg">
        Bản quyền ảnh
      </h3>
      <p className="text-[14px] leading-snug text-muted">Ảnh bối cảnh của nhân vật mẫu, dùng theo giấy phép mở.</p>
      <ul className="flex flex-col gap-3">
        {rows.map(({ slug, name, credit }) => (
          <li key={slug} className="text-[14px] leading-snug">
            <span className="font-medium text-fg">{name}</span>
            <span className="text-muted">
              {": "}
              <a
                href={credit.source_url}
                target="_blank"
                rel="noreferrer noopener"
                className="text-fg underline decoration-line-strong underline-offset-2 hover:decoration-accent"
              >
                {credit.title}
              </a>
              {credit.creator ? `, ${credit.creator}` : ""}
              {credit.licence && (
                <>
                  {", "}
                  {credit.licence_url ? (
                    <a
                      href={credit.licence_url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="underline decoration-line-strong underline-offset-2 hover:text-fg"
                    >
                      {credit.licence}
                    </a>
                  ) : (
                    credit.licence
                  )}
                </>
              )}
              .{credit.changes ? ` ${credit.changes}` : ""}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/**
 * "Nâng cao" (Phase 3b): everything technical, folded away. The machine (memory, loaded models,
 * default chat model, KV cache, versions, memory search) and the advanced-tools switch. /api/system
 * is polled only while it is open.
 */
function AdvancedSection({ level, state }: { level: HealthLevel; state: PersonaSettingsState }) {
  const [open, setOpen] = useState(false);
  const [advanced, setAdvanced] = useAdvancedTools();
  // The machine and the default model are the owner's (docs/auth.md §1.1); a member only has the tools.
  const isOwner = useAuthAccount()?.role === "owner";
  return (
    <section className="border-t border-line pt-4">
      <Disclosure
        title="Nâng cao"
        hint={isOwner ? "Thông tin máy và công cụ cho người tạo nhân vật." : "Công cụ cho người tạo nhân vật."}
        open={open}
        onToggle={setOpen}
      >
        <div className="flex flex-col gap-5">
          {isOwner && <MachineSection level={level} state={state} />}
          <Section title="Công cụ">
            <Toggle
              label="Công cụ nâng cao"
              description="Hiện xem trước prompt, ước lượng token và thời gian sinh trong Studio."
              checked={advanced}
              onChange={setAdvanced}
            />
          </Section>
        </div>
      </Disclosure>
    </section>
  );
}

/** Saves a downloaded file (an object URL clicked through a hidden link). */
function saveFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/**
 * "Dữ liệu & quyền riêng tư" (docs/compliance.md §4, docs/tracking-plan.md §2): the usage-sharing
 * switch, "Tải dữ liệu của tôi" and the way to "Xoá tài khoản". Plain words only.
 */
function PrivacySection({ state, onDelete }: { state: AccountState; onDelete: () => void }) {
  const { account } = state;
  const sharing = account ? account.analytics_opt_out !== true : true;
  const [saving, setSaving] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<{ text: string; technical: string | null } | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<{ text: string; technical: string | null } | null>(null);

  const toggle = async (on: boolean) => {
    setSaving(true);
    setError(null);
    setNote(null);
    try {
      setAccount(await api.patchAccount({ analytics_opt_out: !on }));
      if (!on) setNote(SHARING_OFF_NOTE);
    } catch (e) {
      setError({ text: errorMessage(e), technical: errorTechnical(e) });
    } finally {
      setSaving(false);
    }
  };

  const download = async () => {
    setExporting(true);
    setExportError(null);
    try {
      const { blob, filename } = await downloadAccountData();
      saveFile(blob, filename);
    } catch (e) {
      setExportError({ text: errorMessage(e), technical: errorTechnical(e) });
    } finally {
      setExporting(false);
    }
  };

  return (
    <Section title="Dữ liệu & quyền riêng tư">
      <Toggle
        label={SHARING_LABEL}
        description={SHARING_HINT}
        checked={sharing}
        onChange={(on) => void toggle(on)}
        disabled={!account}
        busy={saving}
      />
      {note && (
        <p role="status" className="-mt-1 text-[13px] leading-snug text-muted">
          {note}
        </p>
      )}
      {error && <InlineAlert tone="error" text={error.text} technical={error.technical} />}
      <div className="flex flex-col items-start gap-1.5">
        <Button size="sm" variant="secondary" icon={<IconDownload />} loading={exporting} onClick={() => void download()} className="max-sm:h-11">
          {EXPORT_LABEL}
        </Button>
        <p className="text-[13px] leading-snug text-muted">{EXPORT_HINT}</p>
        {exportError && <InlineAlert tone="error" text={exportError.text} technical={exportError.technical} />}
      </div>
      <div className="-ml-3">
        <button
          type="button"
          onClick={onDelete}
          className="inline-flex h-11 items-center rounded-full px-3 text-[14px] font-semibold text-danger transition-colors duration-150 hover:bg-surface-2 sm:h-9"
        >
          {DELETE_LABEL}
        </button>
      </div>
    </Section>
  );
}

/** "Xoá tài khoản" inside the sheet: what goes, what stays, the owner's case, then the password. */
function DeleteView({ onBack, backRef }: { onBack: () => void; backRef: RefObject<HTMLButtonElement> }) {
  const account = useAuthAccount();
  const isOwner = account?.role === "owner";
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ text: string; technical: string | null } | null>(null);
  const [missing, setMissing] = useState(false);
  const passwordRef = useRef<HTMLInputElement>(null);

  const run = async () => {
    if (busy) return;
    if (!password) {
      setMissing(true);
      passwordRef.current?.focus();
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.deleteAccount(password);
      accountDeleted(res.setup_required);
    } catch (e) {
      setError({ text: errorMessage(e), technical: errorTechnical(e) });
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="-ml-2 pt-1">
        <Button ref={backRef} size="sm" variant="ghost" icon={<IconChevronLeft />} onClick={onBack} disabled={busy} className="max-sm:h-11">
          Tài khoản
        </Button>
      </div>
      <div className="flex flex-col gap-3 text-[14px] leading-relaxed">
        <p className="text-fg">{DELETE_WHAT}</p>
        <p className="text-muted">{DELETE_KEPT}</p>
        {isOwner && <p className="rounded-control bg-surface-2 px-4 py-3 text-fg">{DELETE_OWNER}</p>}
        <p className="text-muted">Muốn giữ lại một bản? Hãy tải dữ liệu trước khi xoá.</p>
      </div>
      <form
        noValidate
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          void run();
        }}
      >
        <PasswordField
          ref={passwordRef}
          label="Mật khẩu hiện tại"
          value={password}
          onChange={(v) => {
            setPassword(v);
            setMissing(false);
          }}
          autoComplete="current-password"
          error={missing ? "Hãy nhập mật khẩu để xác nhận." : undefined}
          disabled={busy}
        />
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="ghost" onClick={onBack} disabled={busy} className="max-sm:w-full">
            Giữ tài khoản
          </Button>
          <Button type="submit" variant="danger" loading={busy} className="max-sm:w-full">
            {DELETE_CONFIRM}
          </Button>
        </div>
        {error && <InlineAlert tone="error" text={error.text} technical={error.technical} />}
      </form>
    </div>
  );
}

/** "Giới thiệu & bản quyền ảnh": the wordmark, one line about Lyris and the image credits. */
function AboutView({ onBack, backRef }: { onBack: () => void; backRef: RefObject<HTMLButtonElement> }) {
  return (
    <div className="flex flex-col gap-5">
      <div className="-ml-2 pt-1">
        <Button ref={backRef} size="sm" variant="ghost" icon={<IconChevronLeft />} onClick={onBack} className="max-sm:h-11">
          Tài khoản
        </Button>
      </div>
      <div className="flex flex-col items-start gap-2">
        <Wordmark size={34} />
        <p className="text-[15px] leading-relaxed text-prose">
          {ABOUT_TEXT}
        </p>
      </div>
      <CreditsList />
    </div>
  );
}

export interface AccountSheetProps {
  open: boolean;
  onClose: () => void;
  /** Level from useHealth (the header already polls it). */
  healthLevel: HealthLevel;
  /** From useAccount (shared with the header's avatar). */
  accountState: AccountState;
  /** Personas and app settings, shared with the header. */
  personaState: PersonaSettingsState;
  /** Open straight on the about view ("?open=about", for screenshots). */
  initialView?: "main" | "about" | "password" | "delete";
}

/**
 * "Tài khoản" (docs/accounts.md §5; was "Persona & máy chủ", DESIGN.md page 4). Phase 3b: the main
 * view says nothing technical: the account (avatar, name, @handle, "Xem profile"), the default
 * persona for new stories, a plain line only when the machine cannot answer, then a folded
 * "Nâng cao" (machine, models, advanced tools) and a small link to "Giới thiệu & bản quyền ảnh".
 * "?open=system" opens it on load, "?open=about" on the about view.
 */
export function AccountSheet({ open, onClose, healthLevel, accountState, personaState, initialView = "main" }: AccountSheetProps) {
  const [view, setView] = useState<"main" | "about" | "password" | "delete">(initialView);
  const [notice, setNotice] = useState<string | null>(null);
  const backRef = useRef<HTMLButtonElement>(null);
  const aboutLinkRef = useRef<HTMLButtonElement>(null);
  const moved = useRef(false);

  // Every opening starts on the main view (unless asked otherwise on load).
  useEffect(() => {
    if (!open) {
      setView("main");
      setNotice(null);
      moved.current = false;
    }
  }, [open]);

  // Focus follows the swap between the views (not on first render).
  useEffect(() => {
    if (!moved.current) return;
    (view !== "main" ? backRef.current : aboutLinkRef.current)?.focus();
  }, [view]);

  const go = (next: "main" | "about" | "password" | "delete") => {
    moved.current = true;
    setView(next);
  };

  const machineLine = plainMachineLine(healthLevel);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={
        view === "about" ? "Giới thiệu & bản quyền ảnh" : view === "password" ? "Đổi mật khẩu" : view === "delete" ? "Xoá tài khoản" : "Tài khoản"
      }
      size="md"
    >
      {open &&
        (view === "about" ? (
          <AboutView onBack={() => go("main")} backRef={backRef} />
        ) : view === "delete" ? (
          <DeleteView onBack={() => go("main")} backRef={backRef} />
        ) : view === "password" ? (
          <PasswordView
            onBack={() => go("main")}
            backRef={backRef}
            onDone={() => {
              setNotice(PASSWORD_CHANGED);
              go("main");
            }}
          />
        ) : (
          <div className="flex flex-col gap-5">
            <AccountSection
              state={accountState}
              onLeave={onClose}
              notice={notice}
              onChangePassword={() => {
                setNotice(null);
                go("password");
              }}
            />
            <CoinSection onLeave={onClose} />
            <PersonaSection state={personaState} onLeave={onClose} />
            <PrivacySection state={accountState} onDelete={() => go("delete")} />
            {machineLine && (
              <p role="status" className="rounded-control bg-surface-2 px-4 py-3 text-[14px] leading-snug text-fg">
                {machineLine}
              </p>
            )}
            <AdvancedSection level={healthLevel} state={personaState} />
            <SignOutSection />
            <div className="-mt-1 flex flex-wrap items-center justify-center gap-x-1 border-t border-line pt-3">
              <button
                ref={aboutLinkRef}
                type="button"
                onClick={() => go("about")}
                className="inline-flex min-h-11 items-center rounded-full px-3 text-[13px] text-muted underline decoration-line-strong underline-offset-2 transition-colors duration-150 hover:text-fg"
              >
                Giới thiệu & bản quyền ảnh
              </button>
              <a
                href="#/privacy"
                onClick={onClose}
                className="inline-flex min-h-11 items-center rounded-full px-3 text-[13px] text-muted underline decoration-line-strong underline-offset-2 transition-colors duration-150 hover:text-fg"
              >
                {PRIVACY_LABEL}
              </a>
              <a
                href="#/terms"
                onClick={onClose}
                className="inline-flex min-h-11 items-center rounded-full px-3 text-[13px] text-muted underline decoration-line-strong underline-offset-2 transition-colors duration-150 hover:text-fg"
              >
                {TERMS_LABEL}
              </a>
            </div>
          </div>
        ))}
    </Modal>
  );
}
