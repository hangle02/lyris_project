import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { ApiError, errorMessage } from "../../api/client";
import { Avatar } from "../../components/Avatar";
import { Button, InlineAlert, Modal, Skeleton, Spinner, TextArea, TextField } from "../../components/ui";
import { cx } from "../../components/ui/logic";
import { useAccount } from "../../hooks/useAccount";
import type { AccountOut } from "../../types";
import { avatarFileError } from "../studio/AvatarField";
import {
  BIO_MAX,
  HANDLE_MAX,
  HANDLE_MIN,
  charCount,
  cleanBio,
  cleanDisplayName,
  handleError,
  handleFromName,
  normalizeHandle,
  serverErrorField,
  validateProfile,
} from "./logic";
import type { ProfileField } from "./logic";
import { ProfileBanner } from "./ProfileBanner";

const ACCEPT = "image/png,image/jpeg,image/webp,image/gif";

type ImageKind = "avatar" | "banner";

/** Hidden file input + the buttons that open it ("Chọn ảnh" / "Đổi ảnh", "Xoá"). */
function ImageActions({
  kind,
  hasImage,
  busy,
  disabled,
  onPick,
  onRemove,
}: {
  kind: ImageKind;
  hasImage: boolean;
  busy: boolean;
  disabled: boolean;
  onPick: (file: File) => void;
  onRemove: () => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const what = kind === "avatar" ? "ảnh đại diện" : "ảnh bìa";
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        size="sm"
        variant="secondary"
        loading={busy}
        disabled={disabled}
        onClick={() => input.current?.click()}
        aria-label={`${hasImage ? "Đổi" : "Chọn"} ${what}`}
      >
        {hasImage ? "Đổi ảnh" : "Chọn ảnh"}
      </Button>
      {hasImage && (
        <Button size="sm" variant="ghost" disabled={disabled || busy} onClick={onRemove} aria-label={`Xoá ${what}`}>
          Xoá
        </Button>
      )}
      <input
        ref={input}
        type="file"
        accept={ACCEPT}
        className="hidden"
        tabIndex={-1}
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = "";
          if (file) onPick(file);
        }}
      />
    </div>
  );
}

/** One picture's row under the preview: its name on the left, its buttons on the right, its error below. */
function ImageRow({ label, actions, error, className }: { label: string; actions: ReactNode; error: string | null; className?: string }) {
  return (
    <div className={cx("flex min-w-0 flex-1 flex-col gap-1", className)}>
      <div className="flex min-h-11 flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <p className="text-[14px] leading-tight font-medium text-fg">{label}</p>
        {actions}
      </div>
      {error && (
        <p role="alert" className="text-[13px] leading-snug text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

interface FormState {
  display_name: string;
  handle: string;
  bio: string;
}

function initialForm(a: AccountOut): FormState {
  return { display_name: a.display_name, handle: a.handle, bio: a.bio };
}

export interface EditProfileSheetProps {
  open: boolean;
  onClose: () => void;
  /** Called after a successful save (the shared account store is already updated). */
  onSaved?: (account: AccountOut) => void;
}

/**
 * "Sửa profile" (docs/accounts.md §5): avatar and cover (saved as soon as they are picked), display
 * name, @handle checked as you type with the backend's rules (a taken handle comes back as a 422
 * and shows under the field), and the bio with a counter. Saving marks the profile completed.
 */
export function EditProfileSheet({ open, onClose, onSaved }: EditProfileSheetProps) {
  const state = useAccount();
  const { account } = state;
  const formId = useId();
  // null until the first keystroke: the form shows the saved account, so its fields exist on the first
  // render of the sheet (the overlay focuses "Tên hiển thị" right away).
  const [edited, setEdited] = useState<FormState | null>(null);
  const form: FormState | null = edited ?? (account ? initialForm(account) : null);
  const [handleTouched, setHandleTouched] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [saving, setSaving] = useState(false);
  const [serverErrors, setServerErrors] = useState<Partial<Record<ProfileField, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [imageBusy, setImageBusy] = useState<ImageKind | null>(null);
  const [imageError, setImageError] = useState<Record<ImageKind, string | null>>({ avatar: null, banner: null });
  const nameRef = useRef<HTMLInputElement>(null);
  const handleRef = useRef<HTMLInputElement>(null);
  const bioRef = useRef<HTMLTextAreaElement>(null);

  // A fresh form each time the sheet opens.
  useEffect(() => {
    setEdited(null);
    setHandleTouched(false);
    setSubmitted(false);
    setServerErrors({});
    setFormError(null);
    setImageError({ avatar: null, banner: null });
  }, [open]);

  const firstSetup = account !== null && !account.profile_completed;

  const setField = (field: ProfileField, value: string) => {
    setEdited((f) => {
      const base = f ?? (account ? initialForm(account) : null);
      if (!base) return f;
      const next = { ...base, [field]: value };
      // While the account is not set up yet, the handle follows the name until it is edited by hand.
      if (field === "display_name" && firstSetup && !handleTouched) {
        const suggested = handleFromName(value);
        if (suggested) next.handle = suggested;
      }
      return next;
    });
    if (serverErrors[field]) setServerErrors((e) => ({ ...e, [field]: undefined }));
    if (field === "display_name" && firstSetup && !handleTouched && serverErrors.handle) {
      setServerErrors((e) => ({ ...e, handle: undefined }));
    }
  };

  const runImage = async (kind: ImageKind, call: () => Promise<unknown>) => {
    setImageBusy(kind);
    setImageError((e) => ({ ...e, [kind]: null }));
    try {
      await call();
    } catch (err) {
      setImageError((e) => ({ ...e, [kind]: errorMessage(err) }));
    } finally {
      setImageBusy(null);
    }
  };

  const pick = (kind: ImageKind, file: File) => {
    const bad = avatarFileError(file);
    if (bad) {
      setImageError((e) => ({ ...e, [kind]: bad }));
      return;
    }
    void runImage(kind, () => (kind === "avatar" ? state.uploadAvatar(file) : state.uploadBanner(file)));
  };

  const remove = (kind: ImageKind) =>
    void runImage(kind, () => (kind === "avatar" ? state.removeAvatar() : state.removeBanner()));

  const clientErrors = form ? validateProfile(form) : {};
  const initial = account ? initialForm(account) : null;
  const handleValue = form ? normalizeHandle(form.handle) : "";
  // Live: the handle shows its error as soon as it differs from the saved one; the rest after "Lưu".
  const handleDirty = form !== null && initial !== null && handleValue !== initial.handle;
  const shown = (field: ProfileField): string | undefined => {
    if (serverErrors[field]) return serverErrors[field];
    if (field === "handle" && (handleDirty || submitted)) return clientErrors.handle;
    if (field === "bio" && clientErrors.bio) return clientErrors.bio; // over the limit: say it right away
    return submitted ? clientErrors[field] : undefined;
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form || saving) return;
    setSubmitted(true);
    setFormError(null);
    const errs = validateProfile(form);
    if (errs.display_name) return nameRef.current?.focus();
    if (errs.handle) return handleRef.current?.focus();
    if (errs.bio) return bioRef.current?.focus();
    setSaving(true);
    try {
      const saved = await state.update({
        display_name: cleanDisplayName(form.display_name),
        handle: normalizeHandle(form.handle),
        bio: cleanBio(form.bio),
      });
      onSaved?.(saved);
      onClose();
    } catch (err) {
      const msg = errorMessage(err);
      const field = err instanceof ApiError && (err.status === 422 || err.status === 409) ? serverErrorField(msg) : null;
      if (field) {
        setServerErrors((x) => ({ ...x, [field]: msg }));
        (field === "handle" ? handleRef : field === "bio" ? bioRef : nameRef).current?.focus();
      } else {
        setFormError(msg);
      }
    } finally {
      setSaving(false);
    }
  };

  const bioCount = form ? charCount(cleanBio(form.bio)) : 0;
  const busy = saving || imageBusy !== null;

  let body: ReactNode;
  if (!account || !form) {
    body = state.error ? (
      <InlineAlert tone="error" text={`Không tải được tài khoản. ${state.error}`} onRetry={() => void state.refresh()} />
    ) : (
      <div aria-busy="true" className="flex flex-col gap-5">
        <Skeleton className="aspect-[3/1] rounded-card" height="auto" />
        <Skeleton height={44} />
        <Skeleton height={44} />
        <Skeleton height={88} />
      </div>
    );
  } else {
    body = (
      <form id={formId} onSubmit={(e) => void submit(e)} noValidate className="flex flex-col gap-6">
        {formError && <InlineAlert tone="error" text={formError} onDismiss={() => setFormError(null)} />}

        {/* The pictures as the profile shows them: the cover with the avatar over its lower edge. */}
        <div className="flex flex-col">
          <div className="relative overflow-hidden rounded-card">
            <ProfileBanner url={account.banner_url} />
            {imageBusy === "banner" && (
              <span className="absolute inset-0 flex items-center justify-center bg-scrim text-fg">
                <Spinner size={20} label="Đang tải ảnh bìa" />
              </span>
            )}
          </div>
          <div className="flex items-end gap-3 pl-3">
            <span className="relative z-10 -mt-9 flex shrink-0 rounded-full bg-surface p-1">
              <Avatar name={cleanDisplayName(form.display_name) || account.display_name} url={account.avatar_url} size={72} />
              {imageBusy === "avatar" && (
                <span className="absolute inset-1 flex items-center justify-center rounded-full bg-scrim text-fg">
                  <Spinner size={18} label="Đang tải ảnh đại diện" />
                </span>
              )}
            </span>
            <ImageRow
              className="pt-2"
              label="Ảnh đại diện"
              error={imageError.avatar}
              actions={
                <ImageActions
                  kind="avatar"
                  hasImage={account.avatar_url !== null}
                  busy={imageBusy === "avatar"}
                  disabled={saving || imageBusy === "banner"}
                  onPick={(f) => pick("avatar", f)}
                  onRemove={() => remove("avatar")}
                />
              }
            />
          </div>
          <div className="mt-1 flex">
            <ImageRow
              label="Ảnh bìa"
              error={imageError.banner}
              actions={
                <ImageActions
                  kind="banner"
                  hasImage={account.banner_url !== null}
                  busy={imageBusy === "banner"}
                  disabled={saving || imageBusy === "avatar"}
                  onPick={(f) => pick("banner", f)}
                  onRemove={() => remove("banner")}
                />
              }
            />
          </div>
          <p className="mt-1 text-[13px] leading-snug text-muted">Ảnh lưu ngay khi chọn. Ảnh bìa nên là ảnh ngang, tỉ lệ 3:1.</p>
        </div>

        <fieldset disabled={saving} className="m-0 flex min-w-0 flex-col gap-5 border-0 p-0">
          <TextField
            ref={nameRef}
            label="Tên hiển thị"
            value={form.display_name}
            onChange={(v) => setField("display_name", v)}
            error={shown("display_name")}
            hint="Hiện trên profile và trên nhân vật bạn tạo."
            autoComplete="nickname"
            enterKeyHint="next"
          />
          <TextField
            ref={handleRef}
            label="Handle"
            icon={<span className="text-[16px] leading-none">@</span>}
            value={form.handle}
            onChange={(v) => {
              setHandleTouched(true);
              setField("handle", v.replace(/^@+/, "").toLowerCase());
            }}
            error={shown("handle")}
            hint={
              handleDirty && handleError(handleValue) === null
                ? `Lyris sẽ kiểm tra @${handleValue} còn trống khi bạn lưu.`
                : `${HANDLE_MIN}-${HANDLE_MAX} ký tự: chữ a-z, số, dấu gạch dưới _ và dấu chấm (không ở đầu hay cuối).`
            }
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            inputMode="text"
            maxLength={HANDLE_MAX + 10}
            enterKeyHint="next"
          />
          <TextArea
            ref={bioRef}
            label="Giới thiệu"
            value={form.bio}
            onChange={(v) => setField("bio", v)}
            error={shown("bio")}
            hint={
              <span className="flex items-baseline justify-between gap-3">
                <span>Vài dòng về bạn, hiện trên profile.</span>
                <span className="shrink-0 tabular-nums">
                  {bioCount}/{BIO_MAX}
                </span>
              </span>
            }
            maxHeight={220}
          />
        </fieldset>
      </form>
    );
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={firstSetup ? "Đặt tên cho tài khoản" : "Sửa profile"}
      description={firstSetup ? "Tên và @handle là của bạn bên ngoài story. Persona vẫn là vai bạn đóng trong story." : undefined}
      size="md"
      dismissible={!busy}
      initialFocusRef={nameRef}
      footer={
        <>
          <Button size="sm" variant="ghost" onClick={onClose} disabled={busy}>
            Huỷ
          </Button>
          <Button size="sm" variant="primary" type="submit" form={formId} loading={saving} disabled={!form || imageBusy !== null}>
            Lưu
          </Button>
        </>
      }
    >
      {body}
    </Modal>
  );
}
