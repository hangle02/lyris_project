#!/usr/bin/env node
// ④ MEMORY — sổ trạng thái memory/features.json của Lyris. Chế độ duy nhất: model_led.
// Nội dung tính năng (tên, Giai đoạn, "Done when", "Tests") lấy từ Wiki: wiki/features/F<NN>-*.md.
// Sổ này chỉ giữ TRẠNG THÁI. Không ai sửa tay features.json.
//
//   Model (AI) được dùng:
//     node memory/features.mjs sync                 → đọc lại wiki/features/F*.md. Giữ trạng thái khi cùng id + cùng tên
//                                                     + cùng nội dung; ✅ mà Done when/Tests/Giai đoạn đổi thì về ⏳
//     node memory/features.mjs list                 → mỗi tính năng một dòng
//     node memory/features.mjs brief                → xem việc: trạng thái + Done when + Tests của tính năng chưa ✅
//     node memory/features.mjs show F02             → JSON của một tính năng
//     node memory/features.mjs claim F02            → "đã làm, chưa chứng minh"  (⏳ → 🟡 claimed)
//     node memory/features.mjs block F02 "lý do"    → bỏ cuộc, ghi lý do  (→ ⛔). Đỏ 3 lần thì verify.sh tự block.
//     node memory/features.mjs reopen F02 ["PO: …"] → ✅/🟡 → ⏳ (GIỮ số lần đỏ). Mở ⛔ cần lý do (câu trả lời của PO):
//                                                     chỉ lúc đó số lần đỏ mới về 0
//     node memory/features.mjs note "đang làm F03"  → ghi tiến độ vào memory/progress.md
//   CHỈ Verification được dùng (Model KHÔNG gọi):
//     node memory/features.mjs promote F02 --gate          → 🟡 claimed → ✅ passing, khi verify.sh xanh
//     node memory/features.mjs fail F02 --gate ["lý do"]   → verify đỏ thêm một lần; tới 3 lần thì ⛔ blocked
//     node memory/features.mjs demote F02 --gate "lý do"   → ✅ bị hồi quy → ⏳ (verify.sh thấy test của nó đỏ)
//
// Kế hoạch (Giai đoạn: Kế hoạch) luôn ⏳ pending cho tới khi trang đổi sang "Đã có": không claim, không ✅ được.
// Thử trên dữ liệu khác: LYRIS_HARNESS_HOME=<thư mục có wiki/ và memory/> node memory/features.mjs …
import { appendFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOME = process.env.LYRIS_HARNESS_HOME ? path.resolve(process.env.LYRIS_HARNESS_HOME) : REPO;
const FILE = path.join(HOME, 'memory', 'features.json');
const PAGES = path.join(HOME, 'wiki', 'features');
const PROGRESS = path.join(HOME, 'memory', 'progress.md');

export const STATES = ['pending', 'claimed', 'passing', 'blocked'];
export const MAX_ATTEMPTS = 3;
export const ICON = { pending: '⏳', claimed: '🟡', passing: '✅', blocked: '⛔' };
const STAGE_LABEL = { built: 'Đã có', planned: 'Kế hoạch' };
const today = () => new Date().toISOString().slice(0, 10);
const note = (line) => {
  mkdirSync(path.dirname(PROGRESS), { recursive: true });
  appendFileSync(PROGRESS, `- ${today()} · ${line}\n`);
};

const load = () => (existsSync(FILE) ? JSON.parse(readFileSync(FILE, 'utf8')) : []);
const save = (list) => {
  mkdirSync(path.dirname(FILE), { recursive: true });
  writeFileSync(FILE, `${JSON.stringify(list, null, 2)}\n`);
};
const num = (id) => Number(id.slice(1));

/** Một mục trong "## Done when" thuộc loại nào: unit | bot | real (Model thật). */
export function doneKind(line) {
  const m = line.match(/^(Unit|Bot|Model thật)\s*:/i);
  if (!m) return null;
  const k = m[1].toLowerCase();
  return k === 'unit' ? 'unit' : k === 'bot' ? 'bot' : 'real';
}

/**
 * Chuẩn hoá một dòng trong "## Tests". Trả { ref } hoặc { error }.
 *   backend/tests/test_x.py  ·  backend/tests/test_x.py::test_name  ·  frontend/src/…/x.test.ts  ·  bot: <tên check>
 *   model: <id kịch bản trong harness/scenarios/*.yaml>  (chứng minh dòng "Model thật:", chỉ chạy với verify --real-model)
 * Frontend chỉ nhận .test.ts: npm test chỉ chạy src/**\/*.test.ts.
 */
export function parseTestRef(raw) {
  // Cho phép dạng link markdown: [backend/tests/test_x.py](../../backend/tests/test_x.py) → lấy chữ hiện.
  const s = raw.replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").trim();
  const bot = s.match(/^`?bot\s*:\s*(.+?)`?$/i);
  if (bot) {
    const name = bot[1].trim().replace(/^bot\s*:\s*/i, '').replace(/^["“'`]|["”'`]$/g, '').trim();
    return name ? { ref: `bot: ${name}` } : { error: `"${s}": thiếu tên check sau "bot:"` };
  }
  const model = s.match(/^`?model\s*:\s*`?([\w.-]+)`?\s*$/i);
  if (model) return { ref: `model: ${model[1]}` };
  if (/^`?model\s*:/i.test(s)) return { error: `"${s}": sau "model:" phải là đúng một id kịch bản (vd model: 07-co-trang)` };
  const tick = s.match(/`([^`]+)`/);
  const token = (tick ? tick[1] : s.split(/\s+/)[0]).trim();
  if (/^backend\/tests\/[\w./-]+\.py(::[^\s]+)?$/.test(token)) return { ref: token };
  if (/^frontend\/src\/[\w./-]+\.test\.ts$/.test(token)) return { ref: token };
  if (/^frontend\/src\/[\w./-]+\.test\.tsx$/.test(token)) return { error: `"${s}": npm test chỉ chạy *.test.ts — đổi file test sang .test.ts` };
  return { error: `"${s}": không phải backend/tests/…py[::tên], frontend/src/….test.ts, "bot: <tên check>" hay "model: <id kịch bản>"` };
}

/** Các id kịch bản model thật được nhắc trong một dòng "Model thật:" (chữ trong `…` trùng id kịch bản). */
export function modelIdsInLine(line, knownIds) {
  return [...line.matchAll(/`([^`]+)`/g)].map((m) => m[1].trim()).filter((x) => knownIds.includes(x));
}

/** Id các kịch bản model thật có trong harness/scenarios/*.yaml (dòng "id: …"). */
export function scenarioIds(dir = path.join(REPO, 'harness', 'scenarios')) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter((f) => /\.ya?ml$/.test(f))
    .map((f) => (readFileSync(path.join(dir, f), 'utf8').match(/^id:\s*["']?([\w.-]+)/m) || [])[1]).filter(Boolean);
}

/**
 * Dòng "Model thật:" nào đã có kịch bản chứng minh: dòng phải nhắc `id` của một "model: <id>" trong Tests.
 * Trả { ids (các model: của tính năng), uncovered (dòng chưa có kịch bản) }.
 */
export function realCoverage(f) {
  const ids = (f.tests || []).filter((r) => r.startsWith('model:')).map((r) => r.slice(6).trim());
  const uncovered = (f.done || []).filter((d) => doneKind(d) === 'real' && !modelIdsInLine(d, ids).length);
  return { ids, uncovered };
}

/** Tham chiếu test có thật không. Trả '' nếu có, hoặc lý do thiếu. */
export function refMissing(ref, known = scenarioIds()) {
  if (ref.startsWith('bot:')) return '';
  if (ref.startsWith('model:')) {
    const id = ref.slice(6).trim();
    return known.includes(id) ? '' : `không có kịch bản "${id}" trong harness/scenarios/`;
  }
  const [file, ...parts] = ref.split('::');
  const abs = path.join(REPO, file);
  if (!existsSync(abs)) return `không có file ${file}`;
  if (!parts.length) return '';
  const src = readFileSync(abs, 'utf8');
  for (const p of parts) {
    const name = p.replace(/\[.*$/, '');
    const esc = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    if (!new RegExp(`^\\s*(async\\s+def|def|class)\\s+${esc}\\b`, 'm').test(src)) return `${file} không có ${name}`;
  }
  return '';
}

/** Đọc một trang feature theo hợp đồng chung. Trả { feature, errors }. */
export function parsePage(rawText, file) {
  const text = rawText.normalize('NFC').replace(/\r\n/g, '\n');
  const errors = [];
  const err = (m) => errors.push(`${file}: ${m}`);
  const firstLine = text.split('\n').find((l) => l.trim() !== '') ?? '';
  const head = firstLine.match(/^#\s+(F\d{2,})\s+—\s+(.+?)\s*$/);
  if (!head) err('dòng đầu phải đúng dạng "# F01 — Tên tính năng" (hai chữ số, gạch dài —)');
  const fileId = file.match(/^(F\d+)-/)?.[1];
  if (head && fileId !== head[1]) err(`tên file (${fileId ?? '?'}) khác id ở dòng đầu (${head[1]})`);

  const sections = {};
  const parts = text.split(/^##\s+/m);
  const intro = parts[0];
  for (const part of parts.slice(1)) {
    const nl = part.indexOf('\n');
    const name = (nl === -1 ? part : part.slice(0, nl)).trim();
    sections[name.toLowerCase()] = nl === -1 ? '' : part.slice(nl + 1);
  }

  // Dòng metadata (không tính dòng tiêu đề "# …"): "- **Phase:** …", "- **Giai đoạn:** Đã có" …
  const meta = intro.split('\n').filter((l) => !/^\s*#/.test(l)).join('\n');
  const phaseLine = meta.match(/Phase\**[ \t]*:[ \t]*\**[ \t]*([^·\n]+)/);
  const phase = phaseLine ? phaseLine[1].replace(/\*/g, '').trim() : '';
  const stageLine = meta.match(/Giai đoạn\**[ \t]*:[ \t]*\**[ \t]*([^·\n]+)/i);
  let stage = null;
  if (!stageLine) err('thiếu dòng "Giai đoạn: Đã có" hoặc "Giai đoạn: Kế hoạch"');
  else {
    const v = stageLine[1].replace(/\*/g, '').trim().toLowerCase();
    if (v.startsWith('đã có')) stage = 'built';
    else if (v.startsWith('kế hoạch')) stage = 'planned';
    else err(`Giai đoạn "${stageLine[1].trim()}" phải là "Đã có" hoặc "Kế hoạch"`);
  }

  const done = [];
  const doneSec = sections['done when'];
  if (doneSec === undefined) err('thiếu mục "## Done when"');
  else {
    for (const line of doneSec.split('\n')) {
      const box = line.match(/^\s*[-*]\s+\[(.)\]\s+(.+)$/);
      if (!box) {
        // Gạch đầu dòng không có ô [ ] trong Done when: trước đây bị bỏ qua im lặng (dòng đó không bao giờ được chấm).
        const bullet = line.match(/^\s*[-*]\s+(.+)$/);
        if (bullet) err(`dòng Done when thiếu ô "[ ]" (viết "- [ ] Unit: …"): "${bullet[1].trim()}"`);
        continue;
      }
      const item = box[2].trim();
      if (box[1] !== ' ') { err(`Done when không được tick [${box[1]}] (trạng thái chỉ nằm trong memory/features.json): "${item}"`); continue; }
      if (!doneKind(item)) { err(`dòng Done when phải bắt đầu bằng "Unit:", "Bot:" hoặc "Model thật:": "${item}"`); continue; }
      done.push(item);
    }
    if (done.length === 0 && !errors.some((e) => e.includes('Done when'))) err('"## Done when" cần ít nhất một dòng "- [ ] Unit: …" / "- [ ] Bot: …" / "- [ ] Model thật: …"');
  }

  const tests = [];
  const testSec = sections.tests;
  if (testSec !== undefined) {
    for (const line of testSec.split('\n')) {
      const b = line.match(/^\s*[-*]\s+(.+)$/);
      if (!b) continue;
      const r = parseTestRef(b[1]);
      if (r.error) err(`Tests: ${r.error}`);
      else if (!tests.includes(r.ref)) tests.push(r.ref);
    }
  }

  if (!head) return { feature: null, errors };
  return {
    feature: { id: head[1], title: head[2].trim(), page: `wiki/features/${file}`, phase, stage, done, tests },
    errors,
  };
}

export function readPages(dir = PAGES) {
  if (!existsSync(dir)) return { pages: [], errors: [`không có thư mục ${path.relative(REPO, dir) || dir}`] };
  const errors = [];
  const pages = [];
  const files = readdirSync(dir).filter((f) => /^F\d+.*\.md$/.test(f)).sort();
  for (const f of files) {
    if (!/^F\d{2,}-[^\s]+\.md$/.test(f)) errors.push(`${f}: tên file phải dạng F<NN>-<slug>.md (hai chữ số)`);
    const r = parsePage(readFileSync(path.join(dir, f), 'utf8'), f);
    errors.push(...r.errors);
    if (r.feature) pages.push(r.feature);
  }
  const seen = new Map();
  for (const p of pages) {
    if (seen.has(p.id)) errors.push(`trùng id ${p.id}: ${seen.get(p.id)} và ${p.page}`);
    seen.set(p.id, p.page);
  }
  pages.sort((a, b) => num(a.id) - num(b.id));
  return { pages, errors };
}

function sync() {
  const { pages, errors } = readPages();
  if (errors.length) {
    console.error(`⛔ Không đồng bộ được (${errors.length} lỗi trong wiki/features/). Sửa trang rồi chạy lại:`);
    for (const e of errors) console.error(`  - ${e}`);
    process.exit(1);
  }
  const oldList = load();
  const old = Object.fromEntries(oldList.map((f) => [f.id, f]));
  const changes = [];
  const logged = [];
  const eq = (a, b) => JSON.stringify(a ?? []) === JSON.stringify(b ?? []);
  // Giữ trạng thái khi cùng id và cùng tên; tính năng đổi nghĩa (đổi tên) thì làm lại từ đầu.
  // ✅ chỉ đúng với ĐÚNG nội dung đã được chấm: Done when / Tests / Giai đoạn đổi thì ✅ về ⏳ (claim + verify lại).
  // Số lần đỏ (attempts) đi theo tính năng, không mất khi sửa trang.
  const list = pages.map((p) => {
    const o = old[p.id];
    const same = Boolean(o && o.title === p.title);
    if (!o) changes.push(`+ ${p.id} mới`);
    else if (!same) changes.push(`↺ ${p.id} đổi tên ("${o.title}" → "${p.title}"): trạng thái về ⏳`);
    let entry = { ...p, state: 'pending' };
    const contentChanged = same && (!eq(o.done, p.done) || !eq(o.tests, p.tests) || o.stage !== p.stage);
    if (same && contentChanged) {
      const added = p.done.filter((d) => !(o.done || []).includes(d));
      const removed = (o.done || []).filter((d) => !p.done.includes(d));
      const tAdded = p.tests.filter((d) => !(o.tests || []).includes(d));
      const tRemoved = (o.tests || []).filter((d) => !p.tests.includes(d));
      const parts = [
        ...removed.map((d) => `bỏ Done when "${d}"`), ...added.map((d) => `thêm Done when "${d}"`),
        ...tRemoved.map((d) => `bỏ Tests "${d}"`), ...tAdded.map((d) => `thêm Tests "${d}"`),
        ...(o.stage !== p.stage ? [`Giai đoạn ${STAGE_LABEL[o.stage] ?? o.stage} → ${STAGE_LABEL[p.stage] ?? p.stage}`] : []),
      ];
      // Ghi lại để chủ dự án (PO) thấy Done when bị sửa thế nào (kể cả khi bị nới cho khớp app).
      logged.push(`${p.id} trang đổi: ${parts.join(' · ') || 'đổi thứ tự dòng'}`);
    }
    if (same && p.stage === 'built') {
      entry.state = STATES.includes(o.state) ? o.state : 'pending';
      if (o.attempts) entry.attempts = o.attempts;
      if (o.verified_at) entry.verified_at = o.verified_at;
      if (o.state === 'blocked' && o.reason) entry.reason = o.reason;
      if (contentChanged && o.state === 'passing') {
        entry.state = 'pending';
        delete entry.verified_at;
        changes.push(`↺ ${p.id} đổi Done when/Tests sau khi ✅: về ⏳ — làm cho đủ rồi claim ${p.id} và chạy verify lại`);
      } else if (contentChanged) changes.push(`~ ${p.id} đổi Done when/Tests (vẫn ${ICON[entry.state]})`);
    } else if (same && p.stage === 'planned') {
      if (o.attempts) entry.attempts = o.attempts;
      if (o.state !== 'pending') changes.push(`↺ ${p.id} là Kế hoạch: trạng thái về ⏳`);
    }
    return entry;
  });
  for (const o of oldList) if (!pages.some((p) => p.id === o.id)) changes.push(`- ${o.id} không còn trang wiki: bỏ khỏi sổ`);
  save(list);
  for (const l of logged) note(`sync: ${l}`);
  return { list, changes };
}

/** Sổ có khớp wiki không (plan-check, verify dùng). Trả danh sách lệch, rỗng = khớp. */
export function driftFromWiki(list = load()) {
  const { pages, errors } = readPages();
  if (errors.length) return errors.map((e) => `wiki lỗi hợp đồng: ${e}`);
  const out = [];
  const eq = (a, b) => JSON.stringify(a ?? []) === JSON.stringify(b ?? []);
  for (const p of pages) {
    const f = list.find((x) => x.id === p.id);
    if (!f) { out.push(`${p.id} có trang wiki nhưng chưa có trong sổ`); continue; }
    const diff = ['title', 'stage', 'page'].filter((k) => f[k] !== p[k]);
    if (!eq(f.done, p.done)) diff.push('done');
    if (!eq(f.tests, p.tests)) diff.push('tests');
    if (diff.length) out.push(`${p.id}: sổ khác wiki ở ${diff.join(', ')}`);
  }
  for (const f of list) if (!pages.some((p) => p.id === f.id)) out.push(`${f.id} có trong sổ nhưng không còn trang wiki`);
  return out;
}

function find(list, id) {
  const f = list.find((x) => x.id === id);
  if (!f) {
    console.error(`Không có tính năng ${id} trong memory/features.json. Chạy: node memory/features.mjs sync`);
    process.exit(1);
  }
  return f;
}

function main(argv) {
  const [cmd, a, b] = argv;
  switch (cmd) {
    case 'sync': {
      const { list, changes } = sync();
      for (const c of changes) console.log(c);
      const planned = list.filter((f) => f.stage === 'planned').length;
      console.log(`Đã đồng bộ ${list.length} tính năng từ wiki/features/ (${list.length - planned} đã có, ${planned} kế hoạch).`);
      break;
    }
    case 'list':
      for (const f of load()) {
        const tag = f.stage === 'planned' ? '  [Kế hoạch]' : '';
        const extra = f.state === 'blocked' && f.reason ? `  — ${f.reason}` : f.attempts ? `  (đỏ ${f.attempts} lần)` : '';
        console.log(`${ICON[f.state]} ${f.id.padEnd(4)} ${f.title}${tag}${extra}`);
      }
      break;
    case 'ids': {
      // Dùng nội bộ (verify.sh): in id theo trạng thái, ví dụ: ids claimed
      for (const f of load()) if (!a || f.state === a) console.log(f.id);
      break;
    }
    case 'brief': {
      const list = load();
      if (!list.length) { console.log('Sổ trống. Chạy: node memory/features.mjs sync'); break; }
      const built = list.filter((f) => f.stage !== 'planned');
      const planned = list.filter((f) => f.stage === 'planned');
      const count = (s) => built.filter((f) => f.state === s).length;
      console.log(`model_led · ⏳ ${count('pending')} chờ · 🟡 ${count('claimed')} đã làm chưa chứng minh · ✅ ${count('passing')} đạt · ⛔ ${count('blocked')} bị chặn · ${planned.length} kế hoạch`);
      console.log('Bạn tự xếp thứ tự: phụ thuộc trước → quan trọng trước → theo số F. Chỉ verification/verify.sh được đánh ✅.');
      for (const f of built) {
        const extra = f.state === 'blocked' && f.reason ? `  — ${f.reason}` : f.attempts ? `  (verify đỏ ${f.attempts}/3)` : '';
        console.log(`\n${ICON[f.state]} ${f.id} — ${f.title}  (${f.page})${extra}`);
        if (f.state === 'passing') continue;
        for (const d of f.done) console.log(`   - ${d}`);
        if (f.tests.length) console.log(`   Tests: ${f.tests.join(' · ')}`);
        else console.log('   Tests: (chưa có — verify sẽ đỏ)');
      }
      if (planned.length) {
        console.log('\nKế hoạch (chưa làm, luôn ⏳ tới khi trang đổi "Giai đoạn: Đã có"):');
        for (const f of planned) console.log(`   ${f.id} — ${f.title}`);
      }
      break;
    }
    case 'show':
      console.log(JSON.stringify(find(load(), a), null, 2));
      break;
    case 'claim': {
      const list = load();
      const f = find(list, a);
      if (f.stage === 'planned') { console.error(`⛔ ${a} là Kế hoạch: đổi trang sang "Giai đoạn: Đã có" (khi code đã có) rồi sync, mới claim được.`); process.exit(1); }
      if (f.state === 'passing') { console.log(`${a} đã ✅ passing rồi. Sửa lại thì: reopen ${a} rồi claim.`); break; }
      if (f.state === 'blocked') { console.error(`⛔ ${a} đang bị chặn (${f.reason ?? 'không có lý do'}). Hỏi PO, rồi: node memory/features.mjs reopen ${a}`); process.exit(1); }
      f.state = 'claimed';
      save(list);
      note(`${a} 🟡 claimed (Model báo đã làm) — chờ verify.sh chứng minh`);
      console.log(`🟡 ${a} claimed. Chưa phải xong: chạy bash verification/verify.sh để chứng minh.`);
      if (!f.tests.length) console.log(`   Lưu ý: trang ${f.page} chưa có "## Tests" — verify sẽ đỏ.`);
      if (f.done.some((d) => doneKind(d) === 'real')) console.log('   Có dòng "Model thật": cần verify.sh --real-model mới ✅ được.');
      break;
    }
    case 'block': {
      if (!b) { console.error('Cần lý do: node memory/features.mjs block F02 "lý do"'); process.exit(1); }
      const list = load();
      const f = find(list, a);
      f.state = 'blocked';
      f.reason = b;
      save(list);
      note(`${a} ⛔ blocked — ${b}`);
      console.log(`⛔ ${a} blocked. Nhớ ghi một mục bài học vào wiki/learned.md và một dòng Câu hỏi cho PO nếu cần.`);
      break;
    }
    case 'reopen': {
      const list = load();
      const f = find(list, a);
      if (f.state === 'blocked') {
        // Mở ⛔ là quyết định của PO (đã trả lời câu hỏi). Chỉ lúc này số lần đỏ mới về 0.
        if (!b || b.trim().length < 5) {
          console.error(`⛔ ${a} đang bị chặn. Mở lại cần câu trả lời của PO: node memory/features.mjs reopen ${a} "PO: …"`);
          process.exit(1);
        }
        const was = f.attempts ?? 0;
        f.state = 'pending';
        delete f.reason;
        delete f.attempts;
        delete f.verified_at;
        save(list);
        note(`${a} ⏳ mở lại sau ⛔ (đã đỏ ${was} lần) — ${b}`);
        console.log(`⏳ ${a} mở lại (${b}). Số lần đỏ về 0.`);
        break;
      }
      // ✅ / 🟡 / ⏳ → ⏳: GIỮ số lần đỏ (mở lại không phải cách xoá bộ đếm).
      f.state = 'pending';
      delete f.verified_at;
      save(list);
      note(`${a} ⏳ mở lại${f.attempts ? ` (vẫn giữ ${f.attempts}/${MAX_ATTEMPTS} lần đỏ)` : ''}${b ? ` — ${b}` : ''}`);
      console.log(`⏳ ${a} mở lại.${f.attempts ? ` Vẫn tính ${f.attempts}/${MAX_ATTEMPTS} lần đỏ.` : ''}`);
      break;
    }
    case 'note':
      if (!a) { console.error('Dùng: node memory/features.mjs note "…"'); process.exit(1); }
      note(a);
      break;
    case 'promote': {
      if (b !== '--gate') { console.error('⛔ Chỉ verify.sh được đánh dấu passing. Model: dùng claim rồi chạy bash verification/verify.sh'); process.exit(1); }
      const list = load();
      const f = find(list, a);
      if (f.stage === 'planned') { console.error(`⛔ ${a} là Kế hoạch: không thể ✅.`); process.exit(1); }
      if (f.state !== 'claimed' && f.state !== 'passing') { console.error(`⛔ ${a} đang ${ICON[f.state]} ${f.state}, không phải 🟡 claimed.`); process.exit(1); }
      if ((f.attempts ?? 0) >= MAX_ATTEMPTS) { console.error(`⛔ ${a} đã đỏ ${f.attempts} lần: phải ⛔ block và chờ PO, không ✅ được.`); process.exit(1); }
      // ✅ chỉ cho ĐÚNG nội dung đang có trên wiki: trang đổi mà sổ chưa sync thì lần chấm này chấm bản cũ.
      const drift = driftFromWiki(list).filter((d) => d.startsWith(`${a}:`) || d.startsWith(`${a} `) || d.startsWith('wiki lỗi'));
      if (drift.length) { console.error(`⛔ ${a}: sổ khác wiki (${drift.join(' · ')}). Chạy node memory/features.mjs sync rồi verify lại.`); process.exit(1); }
      // Dòng "Model thật" phải có kịch bản chứng minh (model: <id> trong Tests, dòng nhắc `id` đó).
      const { uncovered } = realCoverage(f);
      if (uncovered.length) { console.error(`⛔ ${a}: ${uncovered.length} dòng "Model thật" chưa có kịch bản chứng minh (vd "${uncovered[0].slice(0, 80)}"). Chưa thể ✅.`); process.exit(1); }
      f.state = 'passing';
      f.verified_at = new Date().toISOString();
      delete f.attempts;
      delete f.reason;
      save(list);
      note(`${a} ✅ passing (verify.sh xanh)`);
      break;
    }
    case 'fail': {
      if (b !== '--gate') { console.error('⛔ Chỉ verify.sh được ghi một lần đỏ.'); process.exit(1); }
      const list = load();
      const f = find(list, a);
      f.attempts = (f.attempts ?? 0) + 1;
      const why = argv[3] ? String(argv[3]).slice(0, 300) : '';
      // Luật "tối đa 3 lần đỏ": tới lần thứ 3 thì sổ tự ⛔, không chờ Model tự giác.
      if (f.attempts >= MAX_ATTEMPTS && f.state === 'claimed') {
        f.state = 'blocked';
        f.reason = `verify.sh đỏ ${f.attempts} lần${why ? `: ${why}` : ''}`;
      }
      save(list);
      note(`${a} 🔴 verify đỏ lần ${f.attempts}${why ? ` — ${why}` : ''}${f.state === 'blocked' ? ' → ⛔ blocked' : ''}`);
      console.log(f.attempts);
      break;
    }
    case 'demote': {
      if (b !== '--gate') { console.error('⛔ Chỉ verify.sh được hạ ✅ khi thấy hồi quy.'); process.exit(1); }
      const list = load();
      const f = find(list, a);
      if (f.state !== 'passing') { console.log(`${a} đang ${ICON[f.state]} ${f.state}, không có gì để hạ.`); break; }
      f.state = 'pending';
      delete f.verified_at;
      save(list);
      note(`${a} ✅ → ⏳ hồi quy (verify.sh)${argv[3] ? ` — ${String(argv[3]).slice(0, 300)}` : ''}`);
      break;
    }
    default:
      console.error('Dùng: sync | list | brief | show <id> | claim <id> | block <id> "lý do" | reopen <id> ["PO: …"] | note "…"');
      process.exit(1);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) main(process.argv.slice(2));
