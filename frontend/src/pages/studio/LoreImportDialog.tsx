import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage, errorTechnical, isAbortError } from "../../api/client";
import { Badge, Button, Disclosure, InlineAlert, Modal, Spinner, Toggle } from "../../components/ui";
import type { LoreImportResult } from "../../types";
import {
  importFileError,
  importItemGroups,
  importNotes,
  importSummaryLines,
  missingToggleLabel,
  nothingNew,
  playerOnlyLine,
  reviewLine,
} from "./loreLogic";
import { Notice } from "./ui";

/** What is being imported: a world file the user picked, or the book an old Card V2 still carries. */
export type ImportSource = { kind: "file"; file: File } | { kind: "book" };

interface Props {
  cardId: number;
  characterName: string;
  source: ImportSource;
  onClose: () => void;
  /** Imported for real: the section reloads its list and says "Đã nhập thế giới.". */
  onImported: () => void;
  /** "Chọn file khác" after an error (file imports only). */
  onPickAnother: () => void;
}

type Phase =
  | { kind: "reading" }
  | { kind: "preview"; result: LoreImportResult; refreshing: boolean }
  | { kind: "error"; text: string; technical: string | null };

/**
 * Import preview (phase4.md §9 "Nhập file"): read the file, ask the server for a dry run, show what
 * would change in plain counts (and who becomes "Chỉ bạn", which sentences were left out), then import
 * for real. Nothing is written before "Nhập".
 */
export function LoreImportDialog({ cardId, characterName, source, onClose, onImported, onPickAnother }: Props) {
  const [phase, setPhase] = useState<Phase>({ kind: "reading" });
  const [deleteMissing, setDeleteMissing] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<{ text: string; technical: string | null } | null>(null);
  const [itemsOpen, setItemsOpen] = useState(false);
  const [droppedOpen, setDroppedOpen] = useState(false);
  const text = useRef<string | null>(null);
  const req = useRef(0);
  const fileName = source.kind === "file" ? source.file.name : null;

  const preview = useCallback(
    async (withDelete: boolean, signal?: AbortSignal) => {
      const id = ++req.current;
      setPhase((p) => (p.kind === "preview" ? { ...p, refreshing: true } : { kind: "reading" }));
      try {
        let result: LoreImportResult;
        if (source.kind === "book") {
          result = await api.importCardBook(cardId, true, signal);
        } else {
          if (text.current === null) {
            const tooBig = importFileError(source.file);
            if (tooBig) {
              setPhase({ kind: "error", text: tooBig, technical: null });
              return;
            }
            text.current = await source.file.text();
          }
          result = await api.importLore(
            cardId,
            { text: text.current, filename: source.file.name, dry_run: true, delete_missing: withDelete },
            signal,
          );
        }
        if (id === req.current) setPhase({ kind: "preview", result, refreshing: false });
      } catch (e) {
        if (isAbortError(e) || id !== req.current) return;
        setPhase({ kind: "error", text: errorMessage(e), technical: errorTechnical(e) });
      }
    },
    [cardId, source],
  );

  useEffect(() => {
    const ctrl = new AbortController();
    void preview(false, ctrl.signal);
    return () => ctrl.abort();
  }, [preview]);

  const toggleDelete = (on: boolean) => {
    setDeleteMissing(on);
    void preview(on);
  };

  const apply = async () => {
    if (applying) return;
    setApplying(true);
    setApplyError(null);
    try {
      if (source.kind === "book") await api.importCardBook(cardId, false);
      else
        await api.importLore(cardId, {
          text: text.current ?? "",
          filename: source.file.name,
          dry_run: false,
          delete_missing: deleteMissing,
        });
      onImported();
    } catch (e) {
      setApplyError({ text: errorMessage(e), technical: errorTechnical(e) });
      setApplying(false);
    }
  };

  const title = source.kind === "book" ? "Dùng các mục từ card gốc" : `Nhập thế giới từ ${fileName}`;
  const result = phase.kind === "preview" ? phase.result : null;
  const empty = result !== null && nothingNew(result);

  let footer;
  if (phase.kind === "error") {
    footer = (
      <>
        <Button size="sm" variant="ghost" onClick={onClose}>
          Đóng
        </Button>
        {source.kind === "file" && (
          <Button size="sm" variant="secondary" onClick={onPickAnother}>
            Chọn file khác
          </Button>
        )}
      </>
    );
  } else if (empty) {
    footer = (
      <Button size="sm" variant="primary" onClick={onClose}>
        Đóng
      </Button>
    );
  } else {
    footer = (
      <>
        <Button size="sm" variant="ghost" onClick={onClose} disabled={applying}>
          Huỷ
        </Button>
        <Button
          size="sm"
          variant="primary"
          onClick={() => void apply()}
          loading={applying}
          disabled={phase.kind !== "preview" || phase.refreshing}
        >
          Nhập
        </Button>
      </>
    );
  }

  return (
    <Modal open onClose={onClose} title={title} size="md" dismissible={!applying} footer={footer}>
      <div className="flex flex-col gap-5 pt-1" aria-busy={phase.kind === "reading" || (phase.kind === "preview" && phase.refreshing)}>
        {phase.kind === "reading" && (
          <p className="flex items-center gap-2.5 text-[15px] text-muted">
            <Spinner />
            {source.kind === "book" ? "Đang đọc các mục…" : "Đang đọc file…"}
          </p>
        )}

        {phase.kind === "error" && <InlineAlert tone="error" text={phase.text} technical={phase.technical} />}

        {result && (
          <>
            <ul className="flex flex-col gap-1.5 text-[15px] leading-snug text-fg">
              {importSummaryLines(result).map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>

            {missingToggleLabel(result) && (
              <Toggle
                label={missingToggleLabel(result) ?? ""}
                description="Chỉ bật nếu file này thay hẳn file cũ."
                checked={deleteMissing}
                onChange={toggleDelete}
                disabled={phase.kind === "preview" && phase.refreshing}
              />
            )}

            {!empty && playerOnlyLine(result.player_only, characterName) && (
              <Notice tone="info" lines={[playerOnlyLine(result.player_only, characterName) ?? ""]} />
            )}

            {!empty && <p className="text-[14px] leading-snug text-muted">{reviewLine(characterName)}</p>}

            {!empty && (importNotes(result).length > 0 || result.warnings.length > 0) && (
              <ul className="flex list-disc flex-col gap-1 pl-5 text-[13px] leading-snug text-muted">
                {importNotes(result).map((n) => (
                  <li key={`n-${n}`}>{n}</li>
                ))}
                {result.warnings.map((w) => (
                  <li key={`w-${w}`} className="text-warn">
                    {w}
                  </li>
                ))}
              </ul>
            )}

            {result.items.length > 0 && (
              <Disclosure title="Xem các mục" open={itemsOpen} onToggle={setItemsOpen}>
                <div className="flex flex-col gap-4">
                  {importItemGroups(result.items).map((g) => (
                    <section key={g.category} className="flex flex-col gap-1.5">
                      <h3 className="text-[14px] font-semibold text-fg">
                        {g.title} <span className="font-normal text-muted tabular-nums">· {g.entries.length}</span>
                      </h3>
                      <ul className="flex flex-col gap-1">
                        {g.entries.map((i, n) => (
                          <li key={`${i.title}-${n}`} className="flex items-baseline gap-2 text-[14px] leading-snug text-prose">
                            <span className="min-w-0 [overflow-wrap:anywhere]">{i.title}</span>
                            {i.tag && <Badge tone={i.tag === "mới" ? "accent" : "neutral"}>{i.tag}</Badge>}
                          </li>
                        ))}
                      </ul>
                    </section>
                  ))}
                </div>
              </Disclosure>
            )}

            {result.dropped_sentences.length > 0 && (
              <Disclosure title="Xem các câu đã bỏ" open={droppedOpen} onToggle={setDroppedOpen}>
                <ul className="flex list-disc flex-col gap-1.5 pl-5 text-[13px] leading-snug text-muted">
                  {result.dropped_sentences.map((s, i) => (
                    <li key={i} className="[overflow-wrap:anywhere]">
                      {s}
                    </li>
                  ))}
                </ul>
              </Disclosure>
            )}

            {applyError && <InlineAlert tone="error" text={applyError.text} technical={applyError.technical} />}
          </>
        )}
      </div>
    </Modal>
  );
}
