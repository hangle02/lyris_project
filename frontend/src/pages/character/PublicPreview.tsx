import { useEffect, useState } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { CharacterPicture } from "../../components/CharacterPicture";
import { Button, Chip, InlineAlert, Modal, Skeleton } from "../../components/ui";
import { signatureLinesFor } from "../../lib/signatureLines";
import type { PublicCardOut } from "../../types";
import { byHandle } from "../explore/logic";
import { cardFromPublic, introSections, profileTags } from "./logic";

/**
 * "Người khác thấy gì" from the Studio switch (docs/auth.md §7.3): the read-only profile other
 * accounts get (GET /api/cards/{id}/public), with the same sections as the character page. No
 * personality, background, goals, secrets or world book: the server never sends them.
 */
export function PublicPreviewDialog({ open, cardId, onClose }: { open: boolean; cardId: number; onClose: () => void }) {
  const [view, setView] = useState<PublicCardOut | null>(null);
  const [error, setError] = useState<{ text: string; technical: string | null } | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!open) return;
    let alive = true;
    setView(null);
    setError(null);
    api
      .getPublicCard(cardId)
      .then((v) => alive && setView(v))
      .catch((e: unknown) => alive && setError({ text: errorMessage(e), technical: errorTechnical(e) }));
    return () => {
      alive = false;
    };
  }, [open, cardId, tick]);

  const card = view ? cardFromPublic(view) : null;
  const lang = card?.language === "en" ? "en" : "vi";
  const sections = card ? introSections(card) : [];
  const lines = card ? signatureLinesFor(card).lines : [];
  const tags = view ? profileTags(view.tags) : [];

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Người khác thấy gì"
      description="Hồ sơ này là tất cả những gì tài khoản khác xem được. Họ không sửa được nhân vật."
      size="lg"
      footer={
        <Button size="sm" variant="primary" onClick={onClose}>
          Đóng
        </Button>
      }
    >
      {error ? (
        <InlineAlert tone="error" text={error.text} technical={error.technical} onRetry={() => setTick((n) => n + 1)} />
      ) : !view || !card ? (
        <div aria-busy="true" className="flex flex-col gap-3">
          <span className="sr-only">Đang tải…</span>
          <Skeleton shape="card" height={160} />
          <Skeleton shape="text" width="50%" height={24} />
          <Skeleton shape="text" lines={3} height={14} />
        </div>
      ) : (
        <div className="flex flex-col gap-5">
          <div className="flex items-start gap-4">
            <CharacterPicture url={view.avatar_url} name={view.name} className="aspect-[4/5] w-24 shrink-0 rounded-card sm:w-32" />
            <div className="flex min-w-0 flex-col gap-1">
              <p className="font-brand text-[28px] leading-[1.1] font-semibold text-fg italic">{view.name}</p>
              {view.role && <p className="text-[15px] leading-snug font-medium text-accent-2">{view.role}</p>}
              {byHandle(view.creator_handle) && <p className="text-[13px] leading-snug text-muted">{byHandle(view.creator_handle)}</p>}
              {tags.length > 0 && (
                <ul aria-label="Tag" className="mt-1 flex flex-wrap gap-1.5">
                  {tags.map((t) => (
                    <li key={t}>
                      <Chip size="sm">{t}</Chip>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          {lines.length > 0 && (
            <ul className="flex flex-col gap-2">
              {lines.map((line) => (
                <li key={line}>
                  <blockquote lang={lang} className="rounded-card border border-edge bg-surface px-4 py-3 font-story text-[16px] font-medium text-dialogue">
                    {line}
                  </blockquote>
                </li>
              ))}
            </ul>
          )}
          {sections.length === 0 ? (
            <p className="text-[15px] text-muted">Chưa có giới thiệu nào để người khác đọc.</p>
          ) : (
            sections.map((s) => (
              <section key={s.key} className="flex flex-col gap-2">
                <h3 className="text-[15px] leading-tight font-semibold text-fg">{s.title}</h3>
                {s.paragraphs.map((p, i) => (
                  <p key={i} lang={lang} className="font-story text-[16px] text-prose [overflow-wrap:anywhere]">
                    {p}
                  </p>
                ))}
              </section>
            ))
          )}
        </div>
      )}
    </Modal>
  );
}
