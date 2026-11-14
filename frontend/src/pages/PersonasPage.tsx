import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import { Avatar } from "../components/Avatar";
import { IconEdit, IconPlus, IconTrash } from "../components/icons";
import { SubpageHeader } from "../components/shell/SubpageHeader";
import { Badge, Button, ChoiceGroup, EmptyState, IconButton, Skeleton } from "../components/ui";
import { MAX_NAME_CHARS } from "../lib/cardForm";
import { routeHref } from "../lib/router";
import type { Option } from "../lib/storyOptions";
import type { Gender, Persona, PersonaOut } from "../types";
import { defaultPersonaId, personaBody, personaMeta, replacePersona } from "./personaLogic";
import { AvatarField, avatarFileError } from "./studio/AvatarField";
import { DeleteDialog, LinkButton, Notice, TextAreaField, TextField, UserPlaceholderBadge } from "./studio/ui";

const GENDER_OPTIONS: Option<Gender>[] = [
  { value: "female", label: "Nữ" },
  { value: "male", label: "Nam" },
  { value: "other", label: "Khác" },
];

/** Side of the portrait on a persona card (same as the Studio character tiles). */
const CARD_AVATAR = 72;

function emptyPersona(): Persona {
  return { id: null, name: "", gender: "female", description: "", avatar: null };
}

/**
 * Inline form to add or edit a persona: avatar beside name and gender (like the Studio editor),
 * description below. A saved persona's picture uploads at once; a new persona's waits for "Thêm".
 */
function PersonaForm({
  initial,
  onCancel,
  onSaved,
  onAvatarChanged,
}: {
  initial: PersonaOut | null;
  onCancel: () => void;
  /** `note` explains a partial success (saved, but the picture did not upload). */
  onSaved: (p: PersonaOut, note: string | null) => void;
  /** A saved persona's picture changed (the form stays open). */
  onAvatarChanged: (p: PersonaOut) => void;
}) {
  const [p, setP] = useState<Persona>(() => initial ?? emptyPersona());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** File name and URL the server last returned for this persona's picture. */
  const [avatar, setAvatar] = useState<{ file: string | null; url: string | null }>({
    file: initial?.avatar ?? null,
    url: initial?.avatar_url ?? null,
  });
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pendingUrl, setPendingUrl] = useState<string | null>(null);
  const id = initial?.id ?? null;
  const isNew = id === null;

  // Preview of a picked picture for a persona not saved yet.
  useEffect(() => {
    if (!pendingFile) {
      setPendingUrl(null);
      return;
    }
    const url = URL.createObjectURL(pendingFile);
    setPendingUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [pendingFile]);

  const applyAvatar = (out: PersonaOut) => {
    setAvatar({ file: out.avatar ?? null, url: out.avatar_url });
    onAvatarChanged(out);
  };

  const pickAvatar = async (file: File) => {
    const err = avatarFileError(file);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    if (id === null) {
      setPendingFile(file);
      return;
    }
    setAvatarBusy(true);
    try {
      applyAvatar(await api.uploadPersonaAvatar(id, file));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setAvatarBusy(false);
    }
  };

  const removeAvatar = async () => {
    if (id === null) {
      setPendingFile(null);
      return;
    }
    if (!window.confirm(`Xoá ảnh đại diện của “${initial?.name ?? p.name}”?`)) return;
    setAvatarBusy(true);
    setError(null);
    try {
      applyAvatar(await api.deletePersonaAvatar(id));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setAvatarBusy(false);
    }
  };

  const submit = async () => {
    const body = personaBody(p, avatar.file);
    if (!body.name) {
      setError("Tên persona không được để trống.");
      return;
    }
    if (Array.from(body.name).length > MAX_NAME_CHARS) {
      setError(`Tên persona dài quá ${MAX_NAME_CHARS} ký tự.`);
      return;
    }
    if (body.description.length > 20_000) {
      setError("Mô tả dài quá 20.000 ký tự.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (id !== null) {
        onSaved(await api.updatePersona(id, body), null);
        return;
      }
      let out = await api.createPersona(body);
      let note: string | null = null;
      if (pendingFile && out.id !== null) {
        try {
          out = await api.uploadPersonaAvatar(out.id, pendingFile);
        } catch (e) {
          note = `Đã thêm “${out.name}”, nhưng chưa tải được ảnh: ${errorMessage(e)}`;
        }
      }
      onSaved(out, note);
    } catch (e) {
      setError(errorMessage(e));
      setSaving(false);
    }
  };

  const avatarUrl = isNew ? pendingUrl : avatar.url;
  const canRemove = isNew ? pendingFile !== null : avatar.url !== null;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
      aria-label={isNew ? "Persona mới" : `Sửa ${initial?.name ?? ""}`}
      className="flex flex-col gap-5 rounded-card border border-edge bg-surface p-4 sm:p-5"
    >
      <h2 className="text-[16px] leading-tight font-semibold text-fg">{isNew ? "Persona mới" : `Sửa “${initial?.name ?? ""}”`}</h2>
      {error && <Notice tone="error" lines={[error]} onDismiss={() => setError(null)} />}
      <fieldset disabled={saving} className="m-0 flex min-w-0 flex-col gap-5 border-0 p-0">
        <div className="flex items-start gap-4">
          <AvatarField
            name={p.name}
            url={avatarUrl}
            note={isNew && pendingFile ? "Tải lên khi thêm" : null}
            busy={avatarBusy}
            disabled={saving}
            onPick={(f) => void pickAvatar(f)}
            onRemove={canRemove ? () => void removeAvatar() : null}
          />
          <div className="flex min-w-0 flex-1 flex-col gap-5">
            <TextField
              label="Tên"
              required
              value={p.name}
              onChange={(v) => setP({ ...p, name: v })}
              placeholder="ví dụ: Lâm Vãn"
              maxLength={MAX_NAME_CHARS * 2}
              autoFocus
            />
            <ChoiceGroup<Gender>
              label="Giới tính"
              value={p.gender}
              onChange={(g) => setP({ ...p, gender: g })}
              options={GENDER_OPTIONS}
              disabled={saving}
            />
          </div>
        </div>
        <p className="-mt-2 text-[13px] leading-snug text-muted">
          Tên thay cho <UserPlaceholderBadge /> trong card và lời mở đầu; giới tính dùng để chọn kiểu quan hệ và đại từ dẫn
          truyện mặc định.
        </p>
        <TextAreaField
          label="Mô tả"
          value={p.description}
          onChange={(v) => setP({ ...p, description: v })}
          placeholder="ví dụ: 18 tuổi, học sinh lớp 12, hiền nhưng bướng, sợ sấm."
          hint="Ngắn gọn: tuổi, thân phận, vài nét tính cách. Nhân vật đọc phần này để hiểu bạn là ai."
          minRows={3}
        />
      </fieldset>
      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel} disabled={saving || avatarBusy}>
          Huỷ
        </Button>
        <Button type="submit" variant="primary" size="sm" loading={saving} disabled={!p.name.trim() || avatarBusy}>
          {saving ? "Đang lưu…" : isNew ? "Thêm persona" : "Lưu"}
        </Button>
      </div>
    </form>
  );
}

/** One persona: portrait, name, gender · story count · default, description, edit and delete. */
function PersonaCard({
  persona: p,
  isDefault,
  onEdit,
  onDelete,
}: {
  persona: PersonaOut;
  isDefault: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    // Phone: portrait, name and actions on one row, the description under them at full width (a
    // 150px column beside the portrait wrapped it every two words). From 640px it sits beside the portrait.
    <li className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-x-4 rounded-card border border-edge bg-surface p-4">
      <Avatar name={p.name} url={p.avatar_url} size={CARD_AVATAR} shape="portrait" className="sm:row-span-2" />
      <div className="min-w-0 self-center sm:self-start">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="truncate text-[16px] leading-tight font-semibold text-fg">{p.name}</h2>
          {isDefault && <Badge tone="accent">Mặc định</Badge>}
        </div>
        <p className="mt-1.5 truncate text-[13px] leading-tight text-muted tabular-nums">{personaMeta(p, false)}</p>
      </div>
      <div className="-mt-1 -mr-2 flex shrink-0 items-center">
        <IconButton label={`Sửa ${p.name}`} icon={<IconEdit />} size="sm" onClick={onEdit} />
        <IconButton label={`Xoá ${p.name}`} icon={<IconTrash />} size="sm" onClick={onDelete} className="hover:text-danger" />
      </div>
      {p.description ? (
        <p className="col-span-3 mt-3 line-clamp-3 text-[14px] leading-snug whitespace-pre-line text-prose [overflow-wrap:anywhere] sm:col-span-2 sm:col-start-2 sm:mt-2">
          {p.description}
        </p>
      ) : (
        <p className="col-span-3 mt-3 text-[14px] leading-snug text-muted sm:col-span-2 sm:col-start-2 sm:mt-2">Chưa có mô tả.</p>
      )}
    </li>
  );
}

function CardSkeleton() {
  return (
    <li className="flex items-start gap-4 rounded-card border border-edge bg-surface p-4">
      <Skeleton shape="card" width={CARD_AVATAR} height={CARD_AVATAR} />
      <div className="flex flex-1 flex-col gap-2 pt-0.5">
        <Skeleton shape="text" width="40%" height={16} />
        <Skeleton shape="text" width="55%" height={13} />
        <Skeleton shape="text" lines={2} height={13} className="mt-1" />
      </div>
    </li>
  );
}

/** "#/personas": the player's own characters (who {{user}} is in a story). */
export function PersonasPage() {
  const [personas, setPersonas] = useState<PersonaOut[] | null>(null);
  const [defaultId, setDefaultId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  /** "new", a persona id being edited, or null. */
  const [editing, setEditing] = useState<"new" | number | null>(null);
  const [deleting, setDeleting] = useState<PersonaOut | null>(null);

  // Marked "Mặc định": the saved default, else the first persona (what a new story uses).
  const defaultPid = personas ? defaultPersonaId(personas, defaultId) : null;

  const loadDefault = useCallback(() => {
    // Only marks "Mặc định"; the page works without it.
    api
      .getSettings()
      .then((s) => setDefaultId(s.default_persona_id))
      .catch(() => undefined);
  }, []);

  const load = useCallback(async () => {
    setError(null);
    try {
      setPersonas(await api.listPersonas());
    } catch (e) {
      setError(errorMessage(e));
      setPersonas((p) => p ?? []);
    }
  }, []);

  useEffect(() => {
    void load();
    loadDefault();
  }, [load, loadDefault]);

  const onSaved = (out: PersonaOut, isNew: boolean, note: string | null) => {
    setEditing(null);
    setOk(note ?? (isNew ? `Đã thêm “${out.name}”.` : `Đã lưu “${out.name}”.`));
    setPersonas((list) => {
      if (!isNew) return replacePersona(list, out);
      return [out, ...(list ?? []).filter((p) => p.id !== out.id)];
    });
    // The server may pick the first persona as the default.
    if (isNew) loadDefault();
  };

  const startNew = () => {
    setOk(null);
    setEditing("new");
  };

  return (
    <div className="flex h-dvh flex-col bg-bg">
      <SubpageHeader backHref="#/" backLabel="Về trang chính" title="Persona" subtitle="Nhân vật của bạn trong truyện">
        <LinkButton href={routeHref({ name: "studio" })} variant="ghost" size="sm" className="-mr-2">
          Studio
        </LinkButton>
      </SubpageHeader>

      <main className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-[720px] flex-col gap-4 px-4 py-5 pb-[max(2rem,env(safe-area-inset-bottom))] sm:py-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
            <p className="min-w-0 flex-1 text-[15px] leading-relaxed text-muted">
              Persona là người bạn nhập vai trong story, khác với tài khoản của bạn. Card nhân vật nhắc tới bạn bằng{" "}
              <UserPlaceholderBadge />; khi tạo story, nó được thay bằng tên persona bạn chọn.
            </p>
            {editing !== "new" && (
              <Button variant="primary" icon={<IconPlus />} onClick={startNew} className="self-start">
                Thêm persona
              </Button>
            )}
          </div>

          {editing === "new" && (
            <PersonaForm
              initial={null}
              onCancel={() => setEditing(null)}
              onSaved={(p, note) => onSaved(p, true, note)}
              onAvatarChanged={() => undefined}
            />
          )}

          {ok && <Notice tone="ok" lines={[ok]} onDismiss={() => setOk(null)} />}
          {error && (
            <Notice
              tone="error"
              lines={[`Không tải được danh sách persona: ${error}`]}
              onDismiss={() => setError(null)}
              action={
                <Button size="sm" onClick={() => void load()}>
                  Thử lại
                </Button>
              }
            />
          )}

          {personas === null ? (
            <div aria-busy="true">
              <span className="sr-only">Đang tải persona…</span>
              <ul className="flex flex-col gap-3">
                <CardSkeleton />
                <CardSkeleton />
              </ul>
            </div>
          ) : personas.length === 0 && !error ? (
            editing !== "new" && (
              <EmptyState
                text="Chưa có persona nào. Thêm một persona để bắt đầu story với bất kỳ nhân vật nào."
                action={
                  <Button size="sm" onClick={startNew}>
                    Thêm persona đầu tiên
                  </Button>
                }
              />
            )
          ) : (
            <ul className="flex flex-col gap-3">
              {personas.map((p) =>
                editing === p.id ? (
                  <li key={p.id}>
                    <PersonaForm
                      initial={p}
                      onCancel={() => setEditing(null)}
                      onSaved={(out, note) => onSaved(out, false, note)}
                      onAvatarChanged={(out) => setPersonas((list) => replacePersona(list, out))}
                    />
                  </li>
                ) : (
                  <PersonaCard
                    key={p.id ?? p.name}
                    persona={p}
                    isDefault={p.id !== null && p.id === defaultPid}
                    onEdit={() => {
                      setOk(null);
                      setEditing(p.id);
                    }}
                    onDelete={() => setDeleting(p)}
                  />
                ),
              )}
            </ul>
          )}
        </div>
      </main>

      {deleting && deleting.id !== null && (
        <DeleteDialog
          title="Xoá persona"
          body={
            <p>
              Xoá persona <b className="font-semibold text-fg">{deleting.name}</b>? Không hoàn tác được.
            </p>
          }
          storyCount={deleting.story_count}
          run={async (withStories) => {
            const res = await api.deletePersona(deleting.id as number, withStories);
            const n = res.deleted_stories;
            setOk(`Đã xoá “${deleting.name}”${n > 0 ? ` và ${n} story` : ""}.`);
          }}
          onClose={() => setDeleting(null)}
          onDeleted={() => {
            const id = deleting.id;
            setDeleting(null);
            if (editing === id) setEditing(null);
            setPersonas((list) => (list ?? []).filter((x) => x.id !== id));
            // Deleting the default persona moves the default on the server.
            loadDefault();
          }}
        />
      )}
    </div>
  );
}
