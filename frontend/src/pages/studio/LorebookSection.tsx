import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { api, errorMessage, errorTechnical, isAbortError } from "../../api/client";
import { LiveStatus } from "../../components/LiveStatus";
import { IconPlus, IconSearch, IconUpload } from "../../components/icons";
import { Badge, Button, Disclosure, EmptyState, InlineAlert, Skeleton, TextField, cx } from "../../components/ui";
import { useAdvancedTools } from "../../hooks/useAdvancedTools";
import { replaceRoute } from "../../lib/router";
import type { LoreCategory, LoreEntry } from "../../types";
import { LoreEntryDialog } from "./LoreEntryDialog";
import { LoreImportDialog } from "./LoreImportDialog";
import type { ImportSource } from "./LoreImportDialog";
import {
  activeQuery,
  searchShown,
  audienceBadge,
  bookEntryCount,
  filterEntries,
  groupEntries,
  keysLine,
  sectionHint,
} from "./loreLogic";
import { Notice, Section } from "./ui";

interface Props {
  /** Saved card id; null while the card has never been saved (entries need a card). */
  cardId: number | null;
  characterName: string;
  /** The card's extensions: an old Card V2 import may still carry its character_book there. */
  extensions: Record<string, unknown>;
  /** The server used that book (and dropped it from the card): drop it from the editor's copy too. */
  onBookUsed: () => void;
  /** Bumped by the editor when "Lưu nhân vật" turned the card's old book into entries: reload the list. */
  reloadKey?: number;
}

type Load =
  | { kind: "loading" }
  | { kind: "ready"; entries: LoreEntry[] }
  | { kind: "error"; text: string; technical: string | null };

/** The row's switch: no visible label (the row says what it is), "Dùng mục …" for screen readers. */
function RowSwitch({ checked, label, onChange }: { checked: boolean; label: string; onChange: (on: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className="flex h-11 w-14 shrink-0 items-center justify-center rounded-control"
    >
      <span
        aria-hidden="true"
        className={cx("relative inline-flex h-6 w-10 rounded-full transition-colors duration-200", checked ? "bg-fg" : "bg-surface-3")}
      >
        <span
          className={cx(
            "absolute top-0.5 left-0.5 h-5 w-5 rounded-full transition-transform duration-200 motion-reduce:transition-none",
            checked ? "translate-x-4 bg-bg" : "translate-x-0 bg-muted",
          )}
        />
      </span>
    </button>
  );
}

function EntryRow({
  entry,
  characterName,
  advanced,
  error,
  onOpen,
  onToggle,
}: {
  entry: LoreEntry;
  characterName: string;
  advanced: boolean;
  error: string | null;
  onOpen: () => void;
  onToggle: (on: boolean) => void;
}) {
  const badge = audienceBadge(entry.audience, characterName);
  const keys = keysLine(entry.keys);
  return (
    <li className="flex flex-col py-1">
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={onOpen}
          className={cx(
            "-ml-2 flex min-h-11 min-w-0 flex-1 flex-col items-start gap-1 rounded-control px-2 py-2 text-left transition-colors duration-150 hover:bg-surface-2",
            !entry.enabled && "opacity-60",
          )}
        >
          <span className="flex max-w-full flex-wrap items-center gap-x-2 gap-y-1">
            <span className="min-w-0 text-[15px] leading-snug font-medium text-fg [overflow-wrap:anywhere]">{entry.title}</span>
            <Badge tone={badge.tone}>{badge.label}</Badge>
            {advanced && entry.edited && entry.source !== "manual" && <span className="text-[12px] text-muted">Đã sửa</span>}
          </span>
          {keys ? (
            <span className="max-w-full truncate text-[13px] leading-snug text-muted">{keys}</span>
          ) : (
            <span className="text-[13px] leading-snug text-warn">Chưa có từ khoá gợi nhớ</span>
          )}
        </button>
        <RowSwitch checked={entry.enabled} label={`Dùng mục ${entry.title}`} onChange={onToggle} />
      </div>
      {error && (
        <p role="alert" className="pb-1 text-[13px] leading-snug text-danger">
          {error}
        </p>
      )}
    </li>
  );
}

/**
 * "Thế giới" in the character editor (phase4.md §9): people, places and old stories around the
 * character, each brought back when the story mentions one of its words. Entries save straight to the
 * server (not with "Lưu nhân vật"); a world file (world.md) or an old card's book can be imported.
 */
export function LorebookSection({ cardId, characterName, extensions, onBookUsed, reloadKey = 0 }: Props) {
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<Record<LoreCategory, boolean>>({ lore: true, character: false, place: false });
  const [editing, setEditing] = useState<{ entry: LoreEntry | null } | null>(null);
  const [importing, setImporting] = useState<ImportSource | null>(null);
  const [rowErrors, setRowErrors] = useState<Record<number, string>>({});
  const [status, setStatus] = useState("");
  /** A visible "Đã nhập thế giới." after an import (dismissible). */
  const [imported, setImported] = useState(false);
  const [advanced] = useAdvancedTools();
  const fileInput = useRef<HTMLInputElement>(null);
  const reqRef = useRef(0);
  const name = characterName.trim() || "nhân vật";
  const bookCount = bookEntryCount(extensions);

  const reload = useCallback(
    async (signal?: AbortSignal) => {
      if (cardId === null) return;
      const id = ++reqRef.current;
      setLoad((cur) => (cur.kind === "ready" ? cur : { kind: "loading" }));
      try {
        const entries = await api.listLore(cardId, signal);
        if (id === reqRef.current) setLoad({ kind: "ready", entries });
      } catch (e) {
        if (isAbortError(e) || id !== reqRef.current) return;
        setLoad({ kind: "error", text: errorMessage(e), technical: errorTechnical(e) });
      }
    },
    [cardId],
  );

  useEffect(() => {
    if (cardId === null) return;
    setLoad({ kind: "loading" });
    const ctrl = new AbortController();
    void reload(ctrl.signal);
    return () => ctrl.abort();
  }, [cardId, reload]);

  // Saving the card converted its old book on the server: fetch the new entries (keeps the list on screen).
  useEffect(() => {
    if (reloadKey === 0 || cardId === null) return;
    const ctrl = new AbortController();
    void reload(ctrl.signal);
    return () => ctrl.abort();
  }, [reloadKey, cardId, reload]);

  // "#/studio/<id>?section=world" (the heart drawer's "Thêm trong Studio"): once the list is there,
  // bring this section into view and drop the flag (a reload does not jump again).
  const sectionRef = useRef<HTMLDivElement>(null);
  const ready = load.kind !== "loading";
  useEffect(() => {
    if (cardId === null || !ready || !/[?&]section=world\b/.test(window.location.hash)) return;
    sectionRef.current?.closest("section")?.scrollIntoView({ block: "start" });
    replaceRoute({ name: "card", cardId });
  }, [cardId, ready]);

  const announce = (text: string) => {
    setStatus("");
    window.setTimeout(() => setStatus(text), 30);
  };

  const entries = load.kind === "ready" ? load.entries : [];
  const canSearch = searchShown(entries.length);
  // The field hides once the list is short again (a delete): its query must stop filtering too.
  const effectiveQuery = activeQuery(entries.length, query);
  const shown = useMemo(() => filterEntries(entries, effectiveQuery), [entries, effectiveQuery]);
  const groups = groupEntries(shown);
  const searching = effectiveQuery.trim() !== "";
  useEffect(() => {
    if (!canSearch && load.kind === "ready") setQuery("");
  }, [canSearch, load.kind]);

  const setEntries = (fn: (list: LoreEntry[]) => LoreEntry[]) =>
    setLoad((cur) => (cur.kind === "ready" ? { kind: "ready", entries: fn(cur.entries) } : cur));

  const toggle = async (entry: LoreEntry, on: boolean) => {
    if (cardId === null) return;
    setRowErrors((errs) => {
      const next = { ...errs };
      delete next[entry.id];
      return next;
    });
    setEntries((list) => list.map((e) => (e.id === entry.id ? { ...e, enabled: on } : e)));
    try {
      const saved = await api.patchLore(cardId, entry.id, { enabled: on });
      setEntries((list) => list.map((e) => (e.id === saved.id ? saved : e)));
    } catch (e) {
      setEntries((list) => list.map((x) => (x.id === entry.id ? { ...x, enabled: !on } : x)));
      setRowErrors((errs) => ({ ...errs, [entry.id]: `Chưa đổi được. ${errorMessage(e)}` }));
    }
  };

  const pickFile = () => {
    if (fileInput.current) {
      fileInput.current.value = "";
      fileInput.current.click();
    }
  };

  const onFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Cleared at once, so picking the same file again (after editing it) fires a change again.
    e.target.value = "";
    if (file) setImporting({ kind: "file", file });
  };

  const addButton = (
    <Button size="sm" variant="secondary" icon={<IconPlus />} onClick={() => setEditing({ entry: null })}>
      Thêm mục
    </Button>
  );
  const importButton = (
    <Button size="sm" variant="ghost" icon={<IconUpload />} onClick={pickFile}>
      Nhập từ file
    </Button>
  );

  let body;
  if (cardId === null) {
    body = <EmptyState text={`Lưu nhân vật trước, rồi thêm thế giới cho ${name}.`} />;
  } else if (load.kind === "loading") {
    body = (
      <div aria-busy="true" className="flex flex-col gap-2">
        <span className="sr-only">Đang tải thế giới…</span>
        <Skeleton shape="card" height={56} />
        <Skeleton shape="card" height={56} />
        <Skeleton shape="card" height={56} />
      </div>
    );
  } else if (load.kind === "error") {
    body = (
      <InlineAlert
        tone="error"
        text={`Không tải được thế giới của ${name}.`}
        technical={[load.text, load.technical].filter(Boolean).join("\n") || null}
        onRetry={() => void reload()}
      />
    );
  } else if (entries.length === 0) {
    body = (
      <EmptyState
        text="Chưa có mục nào. Thêm một mục, hoặc nhập từ file thế giới (như world.md)."
        action={
          <div className="flex flex-wrap gap-2">
            {addButton}
            {importButton}
          </div>
        }
      />
    );
  } else {
    body = (
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          {addButton}
          {importButton}
          {canSearch && (
            <TextField
              label="Tìm trong thế giới"
              hideLabel
              icon={<IconSearch />}
              placeholder="Tìm trong thế giới"
              value={query}
              onChange={setQuery}
              className="w-full sm:ml-auto sm:w-64"
              type="search"
            />
          )}
        </div>
        {groups.length === 0 ? (
          <p className="text-[14px] text-muted">Không có mục nào khớp “{effectiveQuery.trim()}”.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {groups.map((g) => (
              <Disclosure
                key={g.category}
                title={`${g.title} · ${g.entries.length}`}
                open={searching || open[g.category]}
                onToggle={(o) => setOpen((cur) => ({ ...cur, [g.category]: o }))}
              >
                <ul className="flex flex-col divide-y divide-line">
                  {g.entries.map((e) => (
                    <EntryRow
                      key={e.id}
                      entry={e}
                      characterName={characterName}
                      advanced={advanced}
                      error={rowErrors[e.id] ?? null}
                      onOpen={() => setEditing({ entry: e })}
                      onToggle={(on) => void toggle(e, on)}
                    />
                  ))}
                </ul>
              </Disclosure>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <Section id="sec-world" title="Thế giới" hint={sectionHint(characterName)}>
      <div ref={sectionRef} hidden />
      <LiveStatus text={status} />
      <input
        ref={fileInput}
        type="file"
        accept=".md,.markdown,.txt,text/markdown,text/plain"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={onFile}
      />
      {cardId !== null && bookCount > 0 && (
        <Notice
          tone="info"
          lines={[`Card này có sẵn ${bookCount} mục thế giới từ file gốc.`]}
          action={
            <Button size="sm" variant="secondary" onClick={() => setImporting({ kind: "book" })}>
              Dùng các mục này
            </Button>
          }
        />
      )}
      {imported && <Notice tone="ok" lines={["Đã nhập thế giới."]} onDismiss={() => setImported(false)} />}
      {body}

      {editing && cardId !== null && (
        <LoreEntryDialog
          cardId={cardId}
          characterName={characterName}
          entry={editing.entry}
          advanced={advanced}
          onClose={() => setEditing(null)}
          onSaved={(saved) => {
            setEditing(null);
            setEntries((list) => (list.some((e) => e.id === saved.id) ? list.map((e) => (e.id === saved.id ? saved : e)) : [...list, saved]));
            setOpen((cur) => ({ ...cur, [saved.category]: true }));
            announce(editing.entry ? "Đã lưu mục." : "Đã thêm mục.");
          }}
          onDeleted={(id) => {
            setEditing(null);
            setEntries((list) => list.filter((e) => e.id !== id));
            announce("Đã xoá mục.");
          }}
        />
      )}

      {importing && cardId !== null && (
        <LoreImportDialog
          cardId={cardId}
          characterName={characterName}
          source={importing}
          onClose={() => setImporting(null)}
          onPickAnother={() => {
            setImporting(null);
            pickFile();
          }}
          onImported={() => {
            if (importing.kind === "book") onBookUsed();
            setImporting(null);
            setImported(true);
            void reload();
            announce("Đã nhập thế giới.");
          }}
        />
      )}
    </Section>
  );
}
