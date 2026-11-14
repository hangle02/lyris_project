import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, api, errorMessage } from "../../api/client";
import {
  applyOverrides,
  cardHints,
  defaultTestSettings,
  emptyCard,
  isDirty,
  prepareForSave,
  toCard,
  saveProblems,
} from "../../lib/cardForm";
import type { SettingsOverrides } from "../../lib/cardForm";
import { clearNotice, clearPendingDraft, peekNotice, peekPendingDraft, setNotice } from "../../lib/draftStore";
import type { PendingDraft } from "../../lib/draftStore";
import { characterRoute, navigate, routeHref } from "../../lib/router";
import type { CardOut, CharacterCard, PersonaOut, StorySettings, StyleProfileInfo, TemplateInfo, Visibility } from "../../types";
import { creatorLine, installedTemplateIds, isInstalledTemplate, isTemplateCard } from "../explore/logic";
import { canShare, isPublic, shareDescription, unshareNote, visibilityBadge } from "./shareLogic";
import { PublicPreviewDialog } from "../character/PublicPreview";
import { IconDownload, IconMessageCircle } from "../../components/icons";
import { Button, Skeleton, Toggle, cx } from "../../components/ui";
import { AvatarField, avatarFileError } from "./AvatarField";
import { CardForm } from "./CardForm";
import type { CardUpdater } from "./CardForm";
import { PromptPreviewPanel } from "./PromptPreviewPanel";
import { useAdvancedTools } from "../../hooks/useAdvancedTools";
import { TestChatPanel } from "./TestChatPanel";
import { TestSettings } from "./TestSettings";
import { SubpageHeader } from "../../components/shell/SubpageHeader";
import { DeleteDialog, LinkButton, Notice, Section, formatDate } from "./ui";
import { LorebookSection } from "./LorebookSection";
import { bookConvertedOnSave, withoutBook } from "./loreLogic";
import { useUnsavedGuard } from "./useUnsavedGuard";
import { nextEditorInstance } from "./editorInstance";
import type { AdoptedId, EditorInstance } from "./editorInstance";

type Tab = "form" | "preview" | "chat";
type SideTab = "preview" | "chat";

interface Meta {
  avatar_url: string | null;
  story_count: number;
  updated_at: string | null;
  visibility: Visibility;
  /** Inputs of the credit line ("bởi @handle" or "Mẫu của Lyris"), decided with the templates list. */
  card_id: number | null;
  creator_handle: string | null;
  extensions: Record<string, unknown> | null;
}

function metaOf(out: CardOut): Meta {
  return {
    avatar_url: out.avatar_url,
    story_count: out.story_count,
    updated_at: out.updated_at,
    visibility: out.visibility ?? "private",
    card_id: out.id,
    creator_handle: out.creator_handle,
    extensions: out.extensions ?? null,
  };
}

/** Credit line of a saved card, by the same rule as the Studio list, Khám phá and Profile. */
function creditOf(meta: Meta | null, installedIds: ReadonlySet<number> | null): string | null {
  if (!meta) return null;
  return creatorLine({
    template: isInstalledTemplate(meta.card_id, meta.extensions, installedIds),
    handle: meta.creator_handle,
  });
}

const STUDIO_HREF = routeHref({ name: "studio" });

/**
 * "#/studio/new" and "#/studio/<id>". A different card id remounts the editor, except the id this
 * editor itself just created (new card saved for the first time), so the test chat and tabs survive.
 * See nextEditorInstance for the exact rule.
 */
export function CardEditorPage({ cardId }: { cardId: number | null }) {
  const adopted = useRef<AdoptedId | null>(null);
  const [inst, setInst] = useState<EditorInstance>({ key: 0, cardId });
  const current = nextEditorInstance(inst, cardId, adopted.current);
  if (current !== inst) setInst(current);
  const key = current.key;
  const adopt = useCallback(
    (id: number) => {
      adopted.current = { key, id };
    },
    [key],
  );
  return <CardEditor key={key} initialId={current.cardId} onAdopt={adopt} />;
}

/** Underlined tab: ink text and an ink bar when active (no coloured pill). */
function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: string }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cx(
        "relative h-11 flex-1 px-2 text-[14px] font-semibold transition-colors",
        active ? "text-fg" : "text-muted hover:text-fg",
      )}
    >
      {children}
      {active && <span aria-hidden="true" className="absolute inset-x-4 bottom-0 h-0.5 rounded-full bg-fg" />}
    </button>
  );
}

function CardEditor({ initialId, onAdopt }: { initialId: number | null; onAdopt: (id: number) => void }) {
  // The pending draft (AI draft / import) is read once, for a new card only.
  const [draft] = useState<PendingDraft | null>(() => (initialId === null ? peekPendingDraft() : null));
  const [status, setStatus] = useState<"loading" | "ready" | "missing" | "failed">(
    initialId === null ? "ready" : "loading",
  );
  const [loadError, setLoadError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<number | null>(initialId);
  /** Bumped when a save converted the card's old character_book (LorebookSection reloads its list). */
  const [loreReload, setLoreReload] = useState(0);
  const [card, setCard] = useState<CharacterCard>(() => (draft ? toCard(draft.card) : emptyCard()));
  /** Last saved version; null = an unsaved draft (always counts as changed). */
  const [baseline, setBaseline] = useState<CharacterCard | null>(() => (draft ? null : emptyCard()));
  const [meta, setMeta] = useState<Meta | null>(null);
  /** Cards installed from a template (GET /api/templates); null until loaded or when that failed. */
  const [templateIds, setTemplateIds] = useState<ReadonlySet<number> | null>(null);
  const [warnings, setWarnings] = useState<string[]>(() => draft?.warnings ?? []);
  const [avatarToken, setAvatarToken] = useState<string | null>(() => draft?.avatar_token ?? null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pendingUrl, setPendingUrl] = useState<string | null>(null);
  const [avatarBusy, setAvatarBusy] = useState(false);

  const [styles, setStyles] = useState<StyleProfileInfo[]>([]);
  const [personas, setPersonas] = useState<PersonaOut[] | null>(null);
  const [personaId, setPersonaId] = useState<number | null>(null);
  const [overrides, setOverrides] = useState<SettingsOverrides>({});

  const [saving, setSaving] = useState(false);
  const [busyAction, setBusyAction] = useState<"duplicate" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveErrors, setSaveErrors] = useState<string[]>([]);
  const [okText, setOkText] = useState<string | null>(() => peekNotice(routeHref({ name: "card", cardId: initialId })));
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("form");
  const [sideTab, setSideTab] = useState<SideTab>("preview");
  const formTop = useRef<HTMLDivElement>(null);

  // The pending draft stays in sessionStorage while this editor is open at "#/studio/new", so a
  // reload there restores it. It is cleared after the first save (see save) and once the editor is
  // really left. A reload runs no cleanups, and StrictMode's test unmount leaves the hash at
  // "#/studio/new", so neither clears it.
  useEffect(() => {
    clearNotice();
    return () => {
      if (window.location.hash !== routeHref({ name: "card", cardId: null })) clearPendingDraft();
    };
  }, []);

  // ---- loading ----
  useEffect(() => {
    let alive = true;
    api
      .listStyles()
      .then((s) => alive && setStyles(s))
      .catch((e) => alive && setError(`Không tải được danh sách style: ${errorMessage(e)}`));
    // Test chat starts with the default persona (Persona & máy chủ), else the first one.
    Promise.all([api.listPersonas(), api.getSettings().catch(() => null)])
      .then(([ps, settings]) => {
        if (!alive) return;
        setPersonas(ps);
        const preferred = ps.find((p) => p.id !== null && p.id === settings?.default_persona_id)?.id ?? null;
        setPersonaId((cur) => cur ?? preferred ?? ps.find((p) => p.id !== null)?.id ?? null);
      })
      .catch(() => alive && setPersonas([]));
    // Only for the credit line ("Mẫu của Lyris"); on failure the card's template tag decides.
    api
      .listTemplates()
      .then((t: TemplateInfo[]) => alive && setTemplateIds(installedTemplateIds(t)))
      .catch(() => undefined);
    if (initialId !== null) {
      api
        .getCard(initialId)
        .then((out) => {
          if (!alive) return;
          const c = toCard(out);
          setCard(c);
          setBaseline(c);
          setMeta(metaOf(out));
          setStatus("ready");
        })
        .catch((e) => {
          if (!alive) return;
          if (e instanceof ApiError && e.status === 404) setStatus("missing");
          else {
            setLoadError(errorMessage(e));
            setStatus("failed");
          }
        });
    }
    return () => {
      alive = false;
    };
  }, [initialId]);

  // Object URL for a picked (not yet uploaded) avatar of a new card.
  useEffect(() => {
    if (!pendingFile) {
      setPendingUrl(null);
      return;
    }
    const url = URL.createObjectURL(pendingFile);
    setPendingUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [pendingFile]);

  // ---- derived ----
  const dirty = status === "ready" && (baseline === null || isDirty(baseline, card) || pendingFile !== null);
  const guard = useUnsavedGuard(dirty, routeHref({ name: "card", cardId: initialId }));

  const update: CardUpdater = useCallback((fn) => setCard((c) => fn(c)), []);
  const prepared = useMemo(() => prepareForSave(card), [card]);
  const styleNames = useMemo(() => styles.map((s) => s.name), [styles]);
  const errors = useMemo(() => saveProblems(card, styleNames), [card, styleNames]);
  const profile = useMemo(() => styles.find((s) => s.name === card.style_profile) ?? null, [styles, card.style_profile]);
  const hints = useMemo(() => cardHints(card, profile), [card, profile]);
  const persona = personas?.find((p) => p.id === personaId) ?? null;
  const credit = creditOf(meta, templateIds);
  // Phase 4b: a template is never shared nor "Riêng tư"; the user's own cards say "Riêng tư" or "Công khai".
  const fromTemplate = meta ? isInstalledTemplate(meta.card_id, meta.extensions, templateIds) : isTemplateCard(card.extensions);
  const privateLabel = visibilityBadge({ template: fromTemplate, visibility: meta?.visibility ?? "private" })?.label ?? null;
  const shareOn = isPublic(card.visibility);
  const savedPublic = isPublic(meta?.visibility);
  const [previewOpen, setPreviewOpen] = useState(false);

  const settingsJson = useMemo(() => {
    if (!persona) return null;
    const defaults = defaultTestSettings(prepared, persona, profile, overrides.language ?? prepared.language);
    return JSON.stringify(applyOverrides(defaults, overrides));
  }, [prepared, persona, profile, overrides]);
  // Stable object while the values are equal, so panels do not refetch for nothing.
  const settings = useMemo<StorySettings | null>(
    () => (settingsJson ? (JSON.parse(settingsJson) as StorySettings) : null),
    [settingsJson],
  );

  // ---- save ----
  const save = useCallback(async () => {
    if (saving || status !== "ready") return;
    const errs = saveProblems(card, styleNames);
    if (errs.length > 0) {
      setSaveErrors(errs);
      setTab("form");
      formTop.current?.scrollIntoView({ block: "start", behavior: "smooth" });
      return;
    }
    setSaving(true);
    setError(null);
    setSaveErrors([]);
    setOkText(null);
    try {
      let out: CardOut;
      let note = "Đã lưu.";
      if (savedId === null) {
        const via = draft?.source === "draft" ? "ai_draft" : draft?.source === "import" ? "import" : "form";
        out = await api.createCard(prepared, pendingFile ? null : avatarToken, via, pendingFile !== null);
        const newId = out.id as number;
        // Saved: the draft is now a real card, a later "Tạo nhân vật" must start empty.
        clearPendingDraft();
        if (pendingFile) {
          try {
            out = await api.uploadAvatar(newId, pendingFile);
          } catch (e) {
            note = `Đã lưu nhân vật, nhưng chưa tải được ảnh: ${errorMessage(e)}`;
          }
        }
        setPendingFile(null);
        setAvatarToken(null);
        setSavedId(newId);
        onAdopt(newId);
        const href = routeHref({ name: "card", cardId: newId });
        // The app may remount the editor for the new address: hand it the notice.
        setNotice(note, href);
        guard.moveTo(href);
      } else {
        out = await api.updateCard(savedId, prepared);
        // The server turned a leftover character_book into world entries: "Thế giới" must show them.
        if (bookConvertedOnSave(prepared.extensions, out.extensions)) setLoreReload((n) => n + 1);
      }
      const saved = toCard(out);
      setCard(saved);
      setBaseline(saved);
      setMeta(metaOf(out));
      setOkText(note);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }, [saving, status, card, prepared, styleNames, savedId, pendingFile, avatarToken, onAdopt, guard]);

  // Ctrl/⌘ + S saves.
  const saveRef = useRef(save);
  saveRef.current = save;
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        void saveRef.current();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // ---- avatar ----
  const pickAvatar = async (file: File) => {
    const err = avatarFileError(file);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    if (savedId === null) {
      setPendingFile(file);
      return;
    }
    setAvatarBusy(true);
    try {
      const out = await api.uploadAvatar(savedId, file);
      setMeta(metaOf(out));
      setCard((c) => ({ ...c, avatar: out.avatar }));
      setBaseline((b) => (b ? { ...b, avatar: out.avatar } : b));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setAvatarBusy(false);
    }
  };

  const removeAvatar = async () => {
    if (savedId === null) {
      if (pendingFile) setPendingFile(null);
      else setAvatarToken(null);
      return;
    }
    if (!window.confirm("Xoá ảnh đại diện của nhân vật này?")) return;
    setAvatarBusy(true);
    setError(null);
    try {
      const out = await api.deleteAvatar(savedId);
      setMeta(metaOf(out));
      setCard((c) => ({ ...c, avatar: null }));
      setBaseline((b) => (b ? { ...b, avatar: null } : b));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setAvatarBusy(false);
    }
  };

  const avatarUrl = savedId === null ? pendingUrl : (meta?.avatar_url ?? null);
  const avatarNote =
    savedId === null && !pendingFile && avatarToken
      ? "Ảnh từ card PNG, gắn khi lưu"
      : savedId === null && pendingFile
        ? "Tải lên khi lưu"
        : null;
  const canRemoveAvatar = savedId === null ? !!pendingFile || !!avatarToken : !!meta?.avatar_url;

  // Phase 4: the server turned the card's leftover character_book into world entries and dropped it from
  // the card; drop it from the editor's copy too, so the next "Lưu" does not send it back.
  const dropBook = useCallback(() => {
    setCard((c) => ({ ...c, extensions: withoutBook(c.extensions) }));
    setBaseline((b) => (b ? { ...b, extensions: withoutBook(b.extensions) } : b));
  }, []);

  // ---- other actions ----
  const duplicate = async () => {
    if (savedId === null || dirty) return;
    setBusyAction("duplicate");
    setError(null);
    try {
      const out = await api.duplicateCard(savedId);
      const target = routeHref({ name: "card", cardId: out.id });
      setNotice(`Đã tạo bản sao “${out.name}”. Bạn đang sửa bản sao.`, target);
      navigate(target);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusyAction(null);
    }
  };

  // The prompt preview and token estimates are for the advanced tools only (Tài khoản → Nâng cao).
  const [advanced] = useAdvancedTools();
  const shownTab: Tab = !advanced && tab === "preview" ? "chat" : tab;
  const shownSide: SideTab = advanced ? sideTab : "chat";

  const selectTab = (t: Tab) => {
    setTab(t);
    if (t !== "form") setSideTab(t);
  };

  // ---- render ----
  const title = card.name.trim() || (savedId === null ? "Nhân vật mới" : "Nhân vật");
  const subtitle = saving
    ? "Đang lưu…"
    : status !== "ready"
      ? "Đang tải…"
      : savedId === null
        ? draft
          ? draft.source === "draft"
            ? "Bản nháp AI · chưa lưu"
            : "Card import · chưa lưu"
          : "Chưa lưu"
        : dirty
          ? "Có thay đổi chưa lưu"
          : [
              meta?.updated_at ? `Đã lưu ${formatDate(meta.updated_at)}` : "Đã lưu",
              meta && meta.story_count > 0 ? `${meta.story_count} story` : null,
            ]
              .filter(Boolean)
              .join(" · ");

  if (status === "missing" || status === "failed") {
    return (
      <div className="flex h-dvh flex-col bg-bg">
        <SubpageHeader backHref={STUDIO_HREF} backLabel="Về Studio" title="Nhân vật" />
        <main className="mx-auto w-full max-w-[720px] px-4 py-8">
          <Notice
            tone="error"
            lines={[status === "missing" ? "Không tìm thấy nhân vật này (có thể đã bị xoá)." : (loadError ?? "Không tải được nhân vật.")]}
            action={
              <LinkButton href={STUDIO_HREF} size="sm">
                Về danh sách nhân vật
              </LinkButton>
            }
          />
        </main>
      </div>
    );
  }

  const upToDate = savedId !== null && !dirty && !saving;
  const saveLabel = savedId === null ? "Lưu nhân vật" : upToDate ? "Đã lưu" : "Lưu";
  const canSave = status === "ready" && !saving && (savedId === null || dirty);

  return (
    <div className="flex h-dvh flex-col bg-bg">
      <SubpageHeader
        backHref={STUDIO_HREF}
        backLabel="Về Studio"
        title={title}
        width="fluid"
        subtitle={
          <>
            <span className={dirty && savedId !== null ? "text-warn" : undefined}>{subtitle}</span>
            {credit && <span className="max-sm:hidden"> · {credit}</span>}
            {privateLabel && <span> · {privateLabel}</span>}
          </>
        }
      >
        <Button
          variant={upToDate ? "secondary" : "primary"}
          size="sm"
          loading={saving}
          onClick={() => void save()}
          disabled={!canSave}
          title="Lưu (Ctrl/⌘ + S)"
        >
          {saving ? "Đang lưu…" : saveLabel}
        </Button>
      </SubpageHeader>

      <div role="tablist" aria-label="Phần của trình sửa" className="flex shrink-0 border-b border-line bg-bg px-2 lg:hidden">
        <TabButton active={shownTab === "form"} onClick={() => selectTab("form")}>
          Hồ sơ
        </TabButton>
        {advanced && (
          <TabButton active={shownTab === "preview"} onClick={() => selectTab("preview")}>
            Xem trước
          </TabButton>
        )}
        <TabButton active={shownTab === "chat"} onClick={() => selectTab("chat")}>
          Chat thử
        </TabButton>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* ---- form ---- */}
        <main className={cx(shownTab === "form" ? "block" : "hidden", "scroll-thin h-full min-w-0 flex-1 overflow-y-auto lg:block")}>
          <div ref={formTop} className="mx-auto flex w-full max-w-[760px] flex-col gap-4 px-4 py-4 pb-[max(2rem,env(safe-area-inset-bottom))] sm:py-6">
            {draft && savedId === null && (
              <Notice
                tone={warnings.length > 0 ? "warn" : "info"}
                title={
                  draft.source === "draft"
                    ? "Bản nháp do AI viết, chưa lưu. Hãy duyệt giới tính, xưng hô và style profile rồi bấm Lưu."
                    : `Card import${draft.file_name ? ` từ “${draft.file_name}”` : ""}, chưa lưu. Hãy kiểm tra rồi bấm Lưu.`
                }
                lines={warnings}
              />
            )}
            {draft && savedId !== null && warnings.length > 0 && (
              <Notice tone="warn" title="Lưu ý từ bản nháp:" lines={warnings} onDismiss={() => setWarnings([])} />
            )}
            {okText && <Notice tone="ok" lines={[okText]} onDismiss={() => setOkText(null)} />}
            {error && <Notice tone="error" lines={[error]} onDismiss={() => setError(null)} />}
            {saveErrors.length > 0 && (
              <Notice tone="error" title="Chưa lưu được:" lines={saveErrors} onDismiss={() => setSaveErrors([])} />
            )}

            {status === "loading" ? (
              <div className="flex flex-col gap-4" aria-busy="true">
                <span className="sr-only">Đang tải nhân vật…</span>
                <div className="rounded-card border border-edge bg-surface p-4 sm:p-5">
                  <Skeleton shape="text" width={80} height={16} />
                  <div className="mt-5 flex gap-4">
                    <Skeleton width={96} height={96} shape="card" />
                    <div className="flex flex-1 flex-col gap-4">
                      <Skeleton height={44} />
                      <Skeleton height={44} />
                    </div>
                  </div>
                  <Skeleton height={36} width={220} shape="pill" className="mt-5" />
                </div>
                <Skeleton shape="card" height={320} />
              </div>
            ) : (
              <fieldset disabled={saving} className="m-0 min-w-0 border-0 p-0">
                <CardForm
                  card={card}
                  update={update}
                  styles={styles}
                  hints={hints}
                  disabled={saving}
                  share={
                    canShare({ template: fromTemplate }) ? (
                      <div className="flex flex-col gap-2 rounded-control bg-surface-2/60 px-4 py-3">
                        <Toggle
                          label="Công khai"
                          description={shareDescription(card.name)}
                          checked={shareOn}
                          onChange={(on) => update((c) => ({ ...c, visibility: on ? "public" : "private" }))}
                          disabled={saving}
                        />
                        {unshareNote(card.name, { checked: shareOn, savedPublic }) && (
                          <p className="text-[13px] leading-snug text-warn">{unshareNote(card.name, { checked: shareOn, savedPublic })}</p>
                        )}
                        {shareOn && savedPublic && savedId !== null && (
                          <div className="-ml-3">
                            <Button size="sm" variant="ghost" onClick={() => setPreviewOpen(true)}>
                              Người khác thấy gì
                            </Button>
                          </div>
                        )}
                        {shareOn && !savedPublic && <p className="text-[13px] leading-snug text-muted">Bấm Lưu để chia sẻ.</p>}
                      </div>
                    ) : null
                  }
                  world={
                    <LorebookSection
                      cardId={savedId}
                      characterName={card.name}
                      extensions={card.extensions}
                      onBookUsed={dropBook}
                      reloadKey={loreReload}
                    />
                  }
                  avatar={
                    <AvatarField
                      name={card.name}
                      url={avatarUrl}
                      note={avatarNote}
                      busy={avatarBusy}
                      disabled={saving}
                      onPick={(f) => void pickAvatar(f)}
                      onRemove={canRemoveAvatar ? () => void removeAvatar() : null}
                    />
                  }
                />
              </fieldset>
            )}

            {status === "ready" && (
              <Section
                title="Dùng nhân vật"
                hint={
                  savedId === null
                    ? "Lưu nhân vật trước để mở story, nhân bản hoặc xuất file."
                    : dirty
                      ? "Xuất file và nhân bản dùng bản đã lưu; hãy lưu trước nếu muốn gồm thay đổi mới."
                      : "Mở một story mới, tạo bản sao để thử hướng khác, hoặc xuất Character Card V2."
                }
              >
                {savedId !== null && (
                  <div className="flex flex-wrap gap-2">
                    <LinkButton href={routeHref(characterRoute(savedId, true))} size="sm" icon={<IconMessageCircle />}>
                      Mở story mới
                    </LinkButton>
                    <Button
                      size="sm"
                      onClick={() => void duplicate()}
                      loading={busyAction === "duplicate"}
                      disabled={dirty || busyAction !== null || saving}
                      title={dirty ? "Lưu thay đổi trước khi nhân bản" : "Tạo một bản sao của nhân vật"}
                    >
                      Nhân bản
                    </Button>
                    <LinkButton
                      href={api.exportCardUrl(savedId, "json")}
                      download
                      size="sm"
                      variant="ghost"
                      icon={<IconDownload />}
                      title={dirty ? "Xuất bản đã lưu (chưa gồm thay đổi đang sửa)" : "Character Card V2 dạng JSON"}
                    >
                      Xuất JSON
                    </LinkButton>
                    <LinkButton
                      href={api.exportCardUrl(savedId, "png")}
                      download
                      size="sm"
                      variant="ghost"
                      icon={<IconDownload />}
                      title={dirty ? "Xuất bản đã lưu (chưa gồm thay đổi đang sửa)" : "Character Card V2 nhúng trong ảnh PNG"}
                    >
                      Xuất PNG
                    </LinkButton>
                  </div>
                )}
              </Section>
            )}

            {status === "ready" && savedId !== null && (
              <section aria-labelledby="danger-title" className="flex flex-col gap-3 rounded-card border border-danger/30 p-4 sm:flex-row sm:items-center sm:p-5">
                <div className="min-w-0 flex-1">
                  <h2 id="danger-title" className="text-[16px] leading-tight font-semibold text-fg">
                    Xoá nhân vật
                  </h2>
                  <p className="mt-1.5 text-[14px] leading-snug text-muted">
                    Xoá {card.name.trim() || "nhân vật này"} và ảnh đại diện khỏi Studio.
                    {meta && meta.story_count > 0 ? ` ${meta.story_count} story đang dùng nhân vật này.` : ""} Không hoàn tác được.
                  </p>
                </div>
                <Button variant="danger" size="sm" onClick={() => setDeleteOpen(true)} disabled={saving} className="self-start sm:self-center">
                  Xoá nhân vật
                </Button>
              </section>
            )}
          </div>
        </main>

        {/* ---- side panel: prompt preview / test chat ---- */}
        <aside
          aria-label="Xem trước và chat thử"
          className={cx(
            shownTab === "form" ? "hidden" : "flex",
            "h-full min-w-0 flex-1 flex-col border-line lg:flex lg:w-[440px] lg:flex-none lg:border-l xl:w-[500px]",
          )}
        >
          <div role="tablist" aria-label="Bảng phụ" className={cx("hidden shrink-0 border-b border-line px-2", advanced && "lg:flex")}>
            <TabButton active={shownSide === "preview"} onClick={() => setSideTab("preview")}>
              Xem trước prompt
            </TabButton>
            <TabButton active={shownSide === "chat"} onClick={() => setSideTab("chat")}>
              Chat thử
            </TabButton>
          </div>
          <div className="shrink-0 px-4 pt-4">
            <TestSettings
              personas={personas}
              personaId={personaId}
              onPersona={setPersonaId}
              settings={settings}
              overrides={overrides}
              onOverrides={setOverrides}
              cardLanguage={card.language}
              disabled={false}
            />
          </div>
          <div
            className={cx(
              shownSide === "preview" ? "block" : "hidden",
              "scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-4 pb-[max(1rem,env(safe-area-inset-bottom))]",
            )}
          >
            <PromptPreviewPanel
              card={prepared}
              personaId={personaId}
              settings={settings}
              active={status === "ready" && shownSide === "preview"}
              blockers={errors}
            />
          </div>
          <div
            className={cx(
              shownSide === "chat" ? "flex" : "hidden",
              "min-h-0 flex-1 flex-col px-4 pt-4 pb-[max(0.75rem,env(safe-area-inset-bottom))]",
            )}
          >
            <TestChatPanel card={prepared} avatarUrl={avatarUrl} persona={persona} settings={settings} blockers={errors} />
          </div>
        </aside>
      </div>

      {savedId !== null && <PublicPreviewDialog open={previewOpen} cardId={savedId} onClose={() => setPreviewOpen(false)} />}

      {deleteOpen && savedId !== null && (
        <DeleteDialog
          title="Xoá nhân vật"
          body={
            <p>
              Xoá <b className="font-semibold text-fg">{card.name || "nhân vật này"}</b> khỏi Studio? Ảnh đại diện cũng bị xoá. Không
              hoàn tác được.
            </p>
          }
          storyCount={meta?.story_count}
          run={async (withStories) => {
            const res = await api.deleteCard(savedId, withStories);
            const n = res.deleted_stories;
            setNotice(`Đã xoá “${card.name.trim() || "nhân vật"}”${n > 0 ? ` và ${n} story` : ""}.`, STUDIO_HREF);
          }}
          onClose={() => setDeleteOpen(false)}
          onDeleted={() => {
            guard.allowLeave();
            navigate(STUDIO_HREF);
          }}
        />
      )}
    </div>
  );
}
