import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, errorMessage } from "../../api/client";
import { Avatar } from "../../components/Avatar";
import { IconEdit, IconPlus, IconSearch, IconUpload } from "../../components/icons";
import { SHELL_CONTAINER } from "../../components/shell/layout";
import { Badge, Button, EmptyState, Skeleton, TextField, cx } from "../../components/ui";
import { GENDER_LABEL, LANGUAGE_LABEL, filterCards, summaryRole } from "../../lib/cardForm";
import { clearNotice, clearPendingDraft, peekNotice, setPendingDraft } from "../../lib/draftStore";
import { characterRoute, navigate, routeHref } from "../../lib/router";
import type { CardDraftResult, CardSummary, PersonaOut, StyleProfileInfo, TemplateInfo } from "../../types";
import { creatorLine, installedTemplateIds } from "../explore/logic";
import { visibilityBadge } from "./shareLogic";
import { DraftDialog } from "./DraftDialog";
import { LinkButton, Notice, formatDate } from "./ui";

const MAX_IMPORT_BYTES = 8 * 1024 * 1024;
/** The search box appears once the list is long enough to need it. */
const SEARCH_FROM = 5;

function CardTile({ card, styleTitle, fromTemplate }: { card: CardSummary; styleTitle: string; fromTemplate: boolean }) {
  const editHref = routeHref({ name: "card", cardId: card.id });
  const role = summaryRole(card);
  // "bởi @handle" with a "Riêng tư" / "Công khai" badge (Phase 4b), or just "Mẫu của Lyris" for a template.
  const credit = creatorLine({ template: fromTemplate, handle: card.creator_handle });
  const badge = visibilityBadge({ template: fromTemplate, visibility: card.visibility });
  const meta = [
    GENDER_LABEL[card.gender],
    LANGUAGE_LABEL[card.language],
    card.story_count > 0 ? `${card.story_count} story` : "chưa có story",
  ].join(" · ");
  const edited = card.updated_at ? `Sửa ${formatDate(card.updated_at)}` : "";
  return (
    <li className="relative flex gap-4 rounded-card border border-edge bg-surface p-4 transition-colors duration-150 hover:bg-surface-2">
      <Avatar name={card.name} url={card.avatar_url} size={72} shape="portrait" />
      <div className="flex min-w-0 flex-1 flex-col">
        <h3 className="truncate text-[16px] leading-tight font-semibold text-fg">
          <a
            href={editHref}
            className="outline-none after:absolute after:inset-0 after:rounded-card focus-visible:after:outline-2 focus-visible:after:outline-offset-2 focus-visible:after:outline-accent"
          >
            {card.name}
          </a>
        </h3>
        {role && <p className="mt-1 truncate text-[14px] leading-tight font-medium text-accent-2">{role}</p>}
        {(credit || badge) && (
          <p className="mt-1 flex min-w-0 items-center gap-2 text-[13px] leading-tight text-muted">
            {credit && <span className="min-w-0 truncate">{credit}</span>}
            {badge && (
              <Badge tone={badge.tone} className="shrink-0">
                {badge.label}
              </Badge>
            )}
          </p>
        )}
        <p className="mt-1.5 truncate text-[13px] leading-tight text-muted tabular-nums" title={styleTitle}>
          {meta}
        </p>
        {card.description && (
          <p className="mt-2 line-clamp-2 text-[14px] leading-snug text-prose [overflow-wrap:anywhere]">{card.description}</p>
        )}
        <div className="mt-auto flex items-center gap-2 pt-2">
          <p className="min-w-0 flex-1 truncate text-[13px] text-muted">{edited}</p>
          <LinkButton
            href={routeHref(characterRoute(card.id, true))}
            variant="ghost"
            size="sm"
            className="relative z-10 -mr-2"
            aria-label={`Bước vào câu chuyện với ${card.name}`}
          >
            Bước vào câu chuyện
          </LinkButton>
        </div>
      </div>
    </li>
  );
}

function TileSkeleton() {
  return (
    <li className="flex gap-4 rounded-card border border-edge bg-surface p-4">
      <Skeleton width={72} height={72} shape="card" />
      <div className="flex min-w-0 flex-1 flex-col gap-2 pt-0.5">
        <Skeleton shape="text" width="55%" height={16} />
        <Skeleton shape="text" width="40%" height={14} />
        <Skeleton shape="text" width="35%" height={13} />
        <Skeleton shape="text" width="70%" height={13} />
        <Skeleton shape="text" lines={2} height={13} className="mt-1" />
      </div>
    </li>
  );
}

/** The player's own characters, with the way to manage them. */
function PersonaCard({ personas }: { personas: PersonaOut[] | null | "error" }) {
  const shown = Array.isArray(personas) ? personas.slice(0, 3) : [];
  return (
    <section
      aria-labelledby="persona-title"
      className="grid items-start gap-x-10 rounded-card border border-edge bg-surface p-4 sm:p-5 md:grid-cols-2"
    >
      <div className="flex min-w-0 flex-col items-start">
        <h2 id="persona-title" className="text-[16px] leading-tight font-semibold text-fg">
          Persona của bạn
        </h2>
        <p className="mt-1.5 text-[13px] leading-snug text-muted">Người bạn nhập vai; thay cho {"{{user}}"} trong mọi card.</p>
        <LinkButton href={routeHref({ name: "personas" })} size="sm" className="mt-4">
          {Array.isArray(personas) && personas.length === 0 ? "Thêm persona" : "Quản lý persona"}
        </LinkButton>
      </div>
      {personas === null ? (
        <div className="mt-4 flex flex-col gap-3 md:mt-0" aria-busy="true">
          <Skeleton shape="text" width="60%" height={14} />
          <Skeleton shape="text" width="45%" height={14} />
        </div>
      ) : personas === "error" ? (
        <p className="mt-4 text-[14px] text-muted md:mt-0">Không tải được danh sách persona.</p>
      ) : shown.length === 0 ? (
        <p className="mt-4 text-[14px] text-muted md:mt-0">Chưa có persona nào.</p>
      ) : (
        <ul className="mt-4 flex flex-col gap-3 md:mt-0">
          {shown.map((p) => (
            <li key={p.id ?? p.name} className="flex items-center gap-3">
              <Avatar name={p.name} url={p.avatar_url} size={32} />
              <span className="min-w-0 flex-1 truncate text-[14px] font-medium text-fg">{p.name}</span>
              <span className="shrink-0 text-[13px] text-muted tabular-nums">
                {GENDER_LABEL[p.gender]} · {p.story_count > 0 ? `${p.story_count} story` : "chưa có story"}
              </span>
            </li>
          ))}
          {Array.isArray(personas) && personas.length > shown.length && (
            <li className="text-[13px] text-muted">và {personas.length - shown.length} persona khác</li>
          )}
        </ul>
      )}
    </section>
  );
}

/**
 * "#/studio", Xưởng dệt tâm hồn: the user's characters, the ways to add one (form, AI draft,
 * import) and the personas. Each character has its own "Thế giới" in the editor. Rendered inside the app shell (hub header, tab bar), so it
 * has no frame or scroll container of its own.
 */
export function CardListPage() {
  const [cards, setCards] = useState<CardSummary[] | null>(null);
  const [styles, setStyles] = useState<StyleProfileInfo[]>([]);
  const [personas, setPersonas] = useState<PersonaOut[] | null | "error">(null);
  /** Cards installed from a template: credited "Mẫu của Lyris" instead of the account. */
  const [templateIds, setTemplateIds] = useState<Set<number>>(() => new Set());
  const [error, setError] = useState<string | null>(null);
  const [notice, setNoticeText] = useState<string | null>(() => peekNotice(routeHref({ name: "studio" })));
  const [query, setQuery] = useState("");
  const [draftOpen, setDraftOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    clearNotice();
  }, []);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [list, st] = await Promise.all([api.listCards(), api.listStyles().catch(() => [] as StyleProfileInfo[])]);
      setCards(list);
      setStyles(st);
    } catch (e) {
      setError(errorMessage(e));
      setCards((c) => c ?? []);
    }
  }, []);

  useEffect(() => {
    void load();
    // Only for the credit line; without it every card reads "bởi @handle".
    api
      .listTemplates()
      .then((t: TemplateInfo[]) => setTemplateIds(installedTemplateIds(t)))
      .catch(() => undefined);
    api
      .listPersonas()
      .then(setPersonas)
      .catch(() => setPersonas("error"));
  }, [load]);

  const styleTitle = useMemo(() => {
    const m = new Map(styles.map((s) => [s.name, s.title]));
    return (name: string) => m.get(name) ?? name;
  }, [styles]);

  const filtered = useMemo(() => filterCards(cards ?? [], query), [cards, query]);

  const openDraft = (result: CardDraftResult, source: "draft" | "import", fileName?: string) => {
    setPendingDraft({
      source,
      card: result.card,
      warnings: result.warnings,
      avatar_token: result.avatar_token,
      file_name: fileName ?? null,
    });
    navigate(routeHref({ name: "card", cardId: null }));
  };

  const onImportFile = async (file: File | undefined) => {
    if (fileRef.current) fileRef.current.value = "";
    if (!file) return;
    setError(null);
    if (file.size > MAX_IMPORT_BYTES) {
      setError("File quá lớn (tối đa 8MB).");
      return;
    }
    const lower = file.name.toLowerCase();
    if (!lower.endsWith(".json") && !lower.endsWith(".png")) {
      setError("Chỉ import được card dạng .json hoặc .png (Character Card V1/V2).");
      return;
    }
    setImporting(true);
    try {
      const result = await api.importCard(file);
      openDraft(result, "import", file.name);
    } catch (e) {
      setError(`Không import được “${file.name}”: ${errorMessage(e)}`);
    } finally {
      setImporting(false);
    }
  };

  const newCard = () => {
    clearPendingDraft();
    navigate(routeHref({ name: "card", cardId: null }));
  };

  const count = cards?.length ?? 0;

  return (
    <div className={cx(SHELL_CONTAINER, "flex flex-col gap-6 pt-6 pb-8 sm:gap-8 sm:pt-10")}>
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <h1 className="text-[24px] leading-tight font-semibold text-fg">Xưởng dệt tâm hồn</h1>
          <p className="mt-1.5 text-[14px] leading-snug text-muted">
            Tạo nhân vật, đặt cảm xúc ban đầu và giữ thế giới của họ ở một chỗ.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 md:flex md:shrink-0">
          <Button variant="primary" icon={<IconPlus />} onClick={newCard} className="col-span-2">
            Tạo nhân vật
          </Button>
          <Button icon={<IconEdit />} onClick={() => setDraftOpen(true)}>
            AI viết nháp
          </Button>
          <Button
            icon={<IconUpload />}
            onClick={() => fileRef.current?.click()}
            loading={importing}
            title="Character Card V1/V2 dạng .json hoặc .png"
          >
            {importing ? "Đang đọc…" : "Nhập card"}
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept=".json,.png,application/json,image/png"
            className="hidden"
            aria-hidden="true"
            tabIndex={-1}
            onChange={(e) => void onImportFile(e.target.files?.[0])}
          />
        </div>
      </div>

      {notice && <Notice tone="ok" lines={[notice]} onDismiss={() => setNoticeText(null)} />}

      <div className="flex flex-col gap-6 sm:gap-8">
        <section aria-labelledby="cards-title" className="flex min-w-0 flex-col gap-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <h2 id="cards-title" className="flex-1 text-[18px] leading-tight font-semibold text-fg">
              Nhân vật của bạn{cards && count > 0 && <span className="font-normal text-muted tabular-nums"> · {count}</span>}
            </h2>
            {count >= SEARCH_FROM && (
              <TextField
                label="Tìm nhân vật"
                hideLabel
                type="search"
                icon={<IconSearch />}
                value={query}
                onChange={setQuery}
                placeholder="Tên, vai trò, tag…"
                className="sm:w-72"
              />
            )}
          </div>

          {error && (
            <Notice
              tone="error"
              lines={[error]}
              onDismiss={() => setError(null)}
              action={
                cards && cards.length === 0 ? (
                  <Button size="sm" onClick={() => void load()}>
                    Thử lại
                  </Button>
                ) : undefined
              }
            />
          )}

          {cards === null ? (
            <div aria-busy="true">
              <span className="sr-only">Đang tải nhân vật…</span>
              <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {[0, 1, 2, 3].map((i) => (
                  <TileSkeleton key={i} />
                ))}
              </ul>
            </div>
          ) : cards.length === 0 && !error ? (
            <EmptyState
              text="Chưa có nhân vật nào. Tạo bằng form, để AI viết nháp từ một dòng ý tưởng, hoặc import card .json/.png."
              action={
                <Button size="sm" onClick={newCard}>
                  Tạo nhân vật đầu tiên
                </Button>
              }
            />
          ) : filtered.length === 0 && query.trim() ? (
            <EmptyState text={`Không có nhân vật nào khớp “${query.trim()}”.`} />
          ) : (
            <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:[&>li:last-child:nth-child(odd)]:col-span-2">
              {filtered.map((c) => (
                <CardTile key={c.id} card={c} styleTitle={styleTitle(c.style_profile)} fromTemplate={templateIds.has(c.id)} />
              ))}
            </ul>
          )}
        </section>

        <div className="flex flex-col gap-4">
          <PersonaCard personas={personas} />
        </div>
      </div>

      {draftOpen && (
        <DraftDialog
          onClose={() => setDraftOpen(false)}
          onDone={(result) => {
            setDraftOpen(false);
            openDraft(result, "draft");
          }}
        />
      )}
    </div>
  );
}
