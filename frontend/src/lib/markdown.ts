// A small Markdown reader for the legal pages (docs/legal/*.md, served by GET /api/legal/{doc}). Pure:
// text in, a block tree out; components/LegalDocument draws it with React (no HTML string is ever
// injected). Covers what those files use: # headings, paragraphs, - and 1. lists, | tables |, ---,
// **bold**, *italic*, `code` and [links](…). Anything else stays plain text.

export type Inline =
  | { kind: "text"; text: string }
  | { kind: "strong"; children: Inline[] }
  | { kind: "em"; children: Inline[] }
  | { kind: "code"; text: string }
  | { kind: "link"; href: string; external: boolean; children: Inline[] };

export type Block =
  | { kind: "heading"; level: 1 | 2 | 3; text: Inline[]; id: string }
  | { kind: "paragraph"; text: Inline[] }
  | { kind: "list"; ordered: boolean; start: number; items: Inline[][] }
  | { kind: "table"; header: Inline[][]; rows: Inline[][][] }
  | { kind: "rule" };

/**
 * Where a link may go: the other legal page inside the app ("privacy.md" -> "#/privacy"), an in-app
 * hash, or an http(s)/mailto address. Anything else (javascript:, data:, relative files) -> null and
 * the link text stays plain.
 */
export function safeHref(raw: string): { href: string; external: boolean } | null {
  const href = raw.trim();
  const doc = /^(?:\.\/)?(privacy|terms)\.md(#.*)?$/i.exec(href);
  if (doc) return { href: `#/${(doc[1] ?? "").toLowerCase()}`, external: false };
  if (/^#\/[A-Za-z0-9\-._~%/?=&]*$/.test(href)) return { href, external: false };
  if (/^https?:\/\/[^\s"'<>]+$/i.test(href)) return { href, external: true };
  if (/^mailto:[^\s"'<>]+$/i.test(href)) return { href, external: true };
  return null;
}

function pushText(out: Inline[], text: string): void {
  if (!text) return;
  const last = out[out.length - 1];
  if (last && last.kind === "text") last.text += text;
  else out.push({ kind: "text", text });
}

/** Inline marks of one line or paragraph. Unclosed marks stay as the characters typed. */
export function parseInline(src: string): Inline[] {
  const out: Inline[] = [];
  let i = 0;
  while (i < src.length) {
    const ch = src[i];
    if (ch === "`") {
      const end = src.indexOf("`", i + 1);
      if (end > i + 1) {
        out.push({ kind: "code", text: src.slice(i + 1, end) });
        i = end + 1;
        continue;
      }
    } else if (ch === "*" && src[i + 1] === "*") {
      const end = src.indexOf("**", i + 2);
      if (end > i + 2) {
        out.push({ kind: "strong", children: parseInline(src.slice(i + 2, end)) });
        i = end + 2;
        continue;
      }
    } else if (ch === "*" && src[i + 1] !== " ") {
      // A single star closed by the next single star ("**" pairs inside are skipped).
      let j = i + 1;
      let end = -1;
      while ((j = src.indexOf("*", j)) >= 0) {
        if (src[j + 1] === "*") {
          j += 2;
          continue;
        }
        end = j;
        break;
      }
      if (end > i + 1) {
        out.push({ kind: "em", children: parseInline(src.slice(i + 1, end)) });
        i = end + 1;
        continue;
      }
    } else if (ch === "[") {
      const close = src.indexOf("](", i + 1);
      const end = close >= 0 ? src.indexOf(")", close + 2) : -1;
      if (close > i && end > close) {
        const label = parseInline(src.slice(i + 1, close));
        const target = safeHref(src.slice(close + 2, end));
        if (target) out.push({ kind: "link", href: target.href, external: target.external, children: label });
        else for (const part of label) part.kind === "text" ? pushText(out, part.text) : out.push(part);
        i = end + 1;
        continue;
      }
    }
    pushText(out, ch ?? "");
    i += 1;
  }
  return out;
}

/** Plain text of inline marks (heading ids, screen-reader labels, tests). */
export function inlineText(parts: readonly Inline[]): string {
  return parts.map((p) => (p.kind === "text" || p.kind === "code" ? p.text : inlineText(p.children))).join("");
}

/** "## 4. Dữ liệu sử dụng" -> "4-du-lieu-su-dung" (anchor ids; ASCII only). */
export function slugify(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
}

function cells(line: string): string[] {
  let l = line.trim();
  if (l.startsWith("|")) l = l.slice(1);
  if (l.endsWith("|")) l = l.slice(0, -1);
  // "\|" inside a cell is a literal bar.
  return l.split(/(?<!\\)\|/).map((c) => c.replace(/\\\|/g, "|").trim());
}

const LIST_ITEM = /^(\s*)([-*]|(\d{1,3})\.)\s+(.*)$/;
const TABLE_RULE = /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/;

/** Markdown text -> blocks. */
export function parseMarkdown(src: string): Block[] {
  const lines = src.replace(/\r\n?/g, "\n").split("\n");
  const blocks: Block[] = [];
  const used = new Map<string, number>();
  let para: string[] = [];

  const endPara = () => {
    if (para.length) blocks.push({ kind: "paragraph", text: parseInline(para.join(" ")) });
    para = [];
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? "";
    const trimmed = line.trim();
    if (!trimmed) {
      endPara();
      continue;
    }
    const h = /^(#{1,6})\s+(.*)$/.exec(trimmed);
    if (h) {
      endPara();
      const text = parseInline((h[2] ?? "").replace(/\s+#+\s*$/, ""));
      const level = Math.min(3, (h[1] ?? "#").length) as 1 | 2 | 3;
      const base = slugify(inlineText(text)) || "muc";
      const n = used.get(base) ?? 0;
      used.set(base, n + 1);
      blocks.push({ kind: "heading", level, text, id: n === 0 ? base : `${base}-${n + 1}` });
      continue;
    }
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      endPara();
      blocks.push({ kind: "rule" });
      continue;
    }
    if (trimmed.startsWith("|") && TABLE_RULE.test(lines[i + 1] ?? "")) {
      endPara();
      const header = cells(trimmed).map(parseInline);
      const rows: Inline[][][] = [];
      i += 2;
      while (i < lines.length && (lines[i] ?? "").trim().startsWith("|")) {
        rows.push(cells(lines[i] ?? "").map(parseInline));
        i++;
      }
      i--;
      blocks.push({ kind: "table", header, rows });
      continue;
    }
    const li = LIST_ITEM.exec(line);
    if (li) {
      endPara();
      const ordered = li[3] !== undefined;
      const start = ordered ? Number(li[3]) : 1;
      const items: string[] = [];
      let j = i;
      while (j < lines.length) {
        const cur = lines[j] ?? "";
        const m = LIST_ITEM.exec(cur);
        if (m && (m[3] !== undefined) === ordered) {
          items.push(m[4] ?? "");
          j++;
        } else if (cur.trim() && /^\s{2,}/.test(cur) && items.length) {
          // An indented continuation line belongs to the item above.
          items[items.length - 1] += ` ${cur.trim()}`;
          j++;
        } else {
          break;
        }
      }
      blocks.push({ kind: "list", ordered, start, items: items.map(parseInline) });
      i = j - 1;
      continue;
    }
    para.push(trimmed);
  }
  endPara();
  return blocks;
}
