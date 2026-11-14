import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, errorMessage, errorTechnical } from "../api/client";
import { PRIVACY_TITLE, TERMS_TITLE } from "../lib/compliance";
import { parseMarkdown } from "../lib/markdown";
import type { Block, Inline } from "../lib/markdown";
import type { LegalDoc } from "../types";
import { InlineAlert, Modal, Skeleton } from "./ui";

export function legalTitle(doc: LegalDoc): string {
  return doc === "privacy" ? PRIVACY_TITLE : TERMS_TITLE;
}

type Load = { kind: "loading" } | { kind: "ready"; blocks: Block[]; version: string } | { kind: "error"; text: string; technical: string | null };

/** GET /api/legal/{doc} parsed into blocks; `reload` after an error. */
export function useLegal(doc: LegalDoc): { load: Load; reload: () => void } {
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [nonce, setNonce] = useState(0);
  useEffect(() => {
    const ctrl = new AbortController();
    setLoad({ kind: "loading" });
    api
      .getLegal(doc, ctrl.signal)
      .then((out) => setLoad({ kind: "ready", blocks: parseMarkdown(out.markdown), version: out.version }))
      .catch((e: unknown) => {
        if (!ctrl.signal.aborted) setLoad({ kind: "error", text: errorMessage(e), technical: errorTechnical(e) });
      });
    return () => ctrl.abort();
  }, [doc, nonce]);
  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { load, reload };
}

const LINK = "font-medium text-fg underline decoration-line-strong underline-offset-2 transition-colors duration-150 hover:decoration-accent";

function Inlines({ parts, onInternalLink }: { parts: readonly Inline[]; onInternalLink?: (href: string) => void }): ReactNode {
  return parts.map((p, i) => {
    switch (p.kind) {
      case "text":
        return <span key={i}>{p.text}</span>;
      case "strong":
        return (
          <strong key={i} className="font-semibold text-fg">
            <Inlines parts={p.children} onInternalLink={onInternalLink} />
          </strong>
        );
      case "em":
        return (
          <em key={i} className="text-muted">
            <Inlines parts={p.children} onInternalLink={onInternalLink} />
          </em>
        );
      case "code":
        return (
          <code key={i} className="rounded-full bg-surface-2 px-1.5 py-0.5 font-sans text-[0.92em] font-medium whitespace-nowrap text-fg">
            {p.text}
          </code>
        );
      case "link":
        return p.external ? (
          <a key={i} href={p.href} target="_blank" rel="noreferrer noopener" className={LINK}>
            <Inlines parts={p.children} onInternalLink={onInternalLink} />
          </a>
        ) : (
          <a
            key={i}
            href={p.href}
            className={LINK}
            onClick={
              onInternalLink
                ? (e) => {
                    e.preventDefault();
                    onInternalLink(p.href);
                  }
                : undefined
            }
          >
            <Inlines parts={p.children} onInternalLink={onInternalLink} />
          </a>
        );
    }
  });
}

/**
 * A legal text drawn from its blocks: comfortable reading measure (the column is set by the caller),
 * 16px/1.65 body, quiet headings, tables that scroll sideways inside their own box on a phone.
 * `skipTitle` drops the first "# " heading (the page or dialog already shows it).
 */
export function LegalBody({
  blocks,
  skipTitle = true,
  onInternalLink,
}: {
  blocks: readonly Block[];
  skipTitle?: boolean;
  onInternalLink?: (href: string) => void;
}) {
  const shown = skipTitle && blocks[0]?.kind === "heading" && blocks[0].level === 1 ? blocks.slice(1) : blocks;
  return (
    <div className="flex flex-col gap-4 text-[16px] leading-[1.65] text-prose">
      {shown.map((b, i) => {
        switch (b.kind) {
          case "heading":
            return b.level <= 2 ? (
              <h2 key={i} id={b.id} className="mt-5 scroll-mt-20 text-[20px] leading-snug font-semibold text-fg first:mt-0">
                <Inlines parts={b.text} onInternalLink={onInternalLink} />
              </h2>
            ) : (
              <h3 key={i} id={b.id} className="mt-3 scroll-mt-20 text-[17px] leading-snug font-semibold text-fg">
                <Inlines parts={b.text} onInternalLink={onInternalLink} />
              </h3>
            );
          case "paragraph":
            return (
              <p key={i} className="[overflow-wrap:anywhere]">
                <Inlines parts={b.text} onInternalLink={onInternalLink} />
              </p>
            );
          case "list": {
            const items = b.items.map((it, j) => (
              <li key={j} className="pl-1 [overflow-wrap:anywhere]">
                <Inlines parts={it} onInternalLink={onInternalLink} />
              </li>
            ));
            return b.ordered ? (
              <ol key={i} start={b.start} className="flex list-decimal flex-col gap-2 pl-6 marker:text-muted">
                {items}
              </ol>
            ) : (
              <ul key={i} className="flex list-disc flex-col gap-2 pl-6 marker:text-muted">
                {items}
              </ul>
            );
          }
          case "table":
            return (
              <div key={i} className="scroll-thin -mx-1 overflow-x-auto rounded-card border border-edge bg-surface">
                <table className="w-full min-w-[480px] border-collapse text-left text-[14px] leading-snug">
                  <thead>
                    <tr className="border-b border-line">
                      {b.header.map((c, j) => (
                        <th key={j} scope="col" className="px-4 py-2.5 font-semibold text-fg">
                          <Inlines parts={c} onInternalLink={onInternalLink} />
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {b.rows.map((row, r) => (
                      <tr key={r} className="border-b border-line last:border-b-0">
                        {row.map((c, j) => (
                          <td key={j} className="px-4 py-2.5 align-top text-prose">
                            <Inlines parts={c} onInternalLink={onInternalLink} />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          case "rule":
            return <hr key={i} className="my-4 border-line" />;
        }
      })}
    </div>
  );
}

/** Loading and error states of a legal text, shared by the page and the dialog. */
export function LegalContent({ doc, onInternalLink }: { doc: LegalDoc; onInternalLink?: (href: string) => void }) {
  const { load, reload } = useLegal(doc);
  if (load.kind === "loading") {
    return (
      <div aria-busy="true" className="flex flex-col gap-4">
        <span className="sr-only">Đang tải…</span>
        <Skeleton shape="text" width="40%" height={14} />
        <Skeleton shape="text" lines={4} height={16} />
        <Skeleton shape="text" width="55%" height={20} />
        <Skeleton shape="text" lines={5} height={16} />
      </div>
    );
  }
  if (load.kind === "error") {
    return <InlineAlert tone="error" text={`Chưa tải được văn bản. ${load.text}`} technical={load.technical} onRetry={reload} />;
  }
  return <LegalBody blocks={load.blocks} onInternalLink={onInternalLink} />;
}

/**
 * The Terms or the Privacy Policy over the current screen (signup, owner setup): reading them must
 * not lose what was typed in the form. A link to the other text swaps the dialog's content.
 */
export function LegalDialog({ doc, onClose }: { doc: LegalDoc | null; onClose: () => void }) {
  const [shown, setShown] = useState<LegalDoc | null>(doc);
  useEffect(() => setShown(doc), [doc]);
  const onLink = useMemo(
    () => (href: string) => {
      if (href === "#/privacy") setShown("privacy");
      else if (href === "#/terms") setShown("terms");
    },
    [],
  );
  return (
    <Modal open={shown !== null} onClose={onClose} title={shown ? legalTitle(shown) : ""} size="lg">
      {shown && <LegalContent key={shown} doc={shown} onInternalLink={onLink} />}
    </Modal>
  );
}
