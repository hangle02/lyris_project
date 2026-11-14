#!/usr/bin/env bash
# ③ VERIFICATION cho Harness Plan — Wiki của Lyris đã "đủ để build" chưa? (kiểm tự động, không cần AI, không gọi model)
#   bash verification/plan-check.sh
# Thoát 0 = 🟢 đủ. Khác 0 = 🔴 còn thiếu, in ra thiếu gì. Dòng "!" là lưu ý, không làm đỏ.
#
# Kiểm:
#   - wiki/overview.md trả lời đủ 8 phần của wiki/plan-checklist.md
#   - mỗi trang wiki/features/F<NN>-*.md đúng hợp đồng (dòng đầu, Giai đoạn, Done when có Unit:/Bot:/Model thật:, không tick [x])
#   - tính năng "Đã có": ≥ 2 dòng Done when và ≥ 1 tham chiếu trong "## Tests": file và tên hàm test phải có thật,
#     "bot: <tên>" phải có trong CHECKS của environment/e2e.mjs, "model: <id>" phải có trong harness/scenarios/
#   - không có dòng Done when mơ hồ (chữ cảm tính mà không có số đo, selector, route hay tên hàm; mã F01 hay § không tính)
#   - memory/features.json khớp wiki (không thì: node memory/features.mjs sync)
#   - lưu ý: dòng "Model thật:" chưa có kịch bản "model: <id>" chứng minh
#   - wiki/design/style.md có ≥ 5 mã màu và nói rõ font
#   - không còn TODO / ??? trong wiki (trừ raw/ và các chỗ nhóm điền đã biết trong WHITELIST)
# Tự kiểm trên dữ liệu giả: LYRIS_HARNESS_HOME=<thư mục có wiki/> bash verification/plan-check.sh
set -u
cd "$(dirname "$0")/.." || exit 1
exec node - <<'EOF'
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
(async () => {
const REPO = process.cwd();
const fmod = await import(pathToFileURL(path.join(REPO, 'memory', 'features.mjs')).href);
let botNames = null;
try { botNames = (await import(pathToFileURL(path.join(REPO, 'environment', 'e2e.mjs')).href)).CHECKS.map((n) => n.normalize('NFC').replace(/^bot\s*:\s*/i, '').trim()); } catch { botNames = null; }
const knownScenarios = fmod.scenarioIds();
const HOME = process.env.LYRIS_HARNESS_HOME ? path.resolve(process.env.LYRIS_HARNESS_HOME) : REPO;
const W = path.join(HOME, 'wiki');
const read = (p) => (fs.existsSync(p) ? fs.readFileSync(p, 'utf8').normalize('NFC') : '');
const checks = [];
const check = (name, ok, detail = '', level = 'fail') => checks.push({ name, ok, detail, level });

// Chỗ nhóm sẽ điền đã biết (README mục Nhóm, video demo, email liên hệ…): dòng có TODO/??? mà khớp một mẫu dưới đây thì bỏ qua.
const WHITELIST = [/Nhóm sẽ điền/i, /to be filled by the team/i, /video demo/i, /LYRIS_CONTACT/, /thành viên nhóm/i];

// ---------------------------------------------------------------- overview: 8 phần của plan-checklist
const ovRaw = read(path.join(W, 'overview.md'));
const ov = ovRaw.toLowerCase();
check('overview.md có nội dung', ov.replace(/[#\s(|*-]/g, '').length > 400, `${ov.length} ký tự`);
const parts = [
  ['1 cho ai (ý tưởng và người dùng)', /cho ai|người dùng|người chơi|chủ máy/],
  ['2 vòng trải nghiệm chính', /trải nghiệm chính|vòng trải nghiệm|vòng chơi|bước vào câu chuyện/],
  ['3 tính năng + Done when', /features\/|tính năng/],
  ['4 màn hình & điều hướng', /màn hình|screens\/|route|#\//],
  ['5 dữ liệu & tài khoản', /(dữ liệu|sqlite|\bdb\b)[\s\S]*tài khoản|tài khoản[\s\S]*(dữ liệu|sqlite|\bdb\b)/],
  ['6 model/AI & giới hạn phần cứng', /(model|ollama|gemma)[\s\S]*(ram|\bgb\b|context|num_ctx|token|phần cứng)/],
  ['7 phong cách thiết kế', /phong cách|design\/style|thiết kế|design\.md/],
  ['8 kiểm tra & tiêu chí xong', /(kiểm tra|tiêu chí xong|verify|pytest|npm test)/],
];
for (const [name, re] of parts) check(`overview trả lời phần ${name}`, re.test(ov));

// ---------------------------------------------------------------- trang tính năng
const fdir = path.join(W, 'features');
const files = fs.existsSync(fdir) ? fs.readdirSync(fdir).filter((f) => f.endsWith('.md')).sort() : [];
const pages = files.filter((f) => /^F\d+/.test(f));
const others = files.filter((f) => !/^F\d+/.test(f) && f.toLowerCase() !== 'readme.md');
check('có trang tính năng F<NN>-*.md', pages.length > 0, `${pages.length} trang`);
check('mọi trang trong features/ đều đặt tên F<NN>-<slug>.md', others.length === 0, others.slice(0, 5).join(', '));

const VAGUE = /(đẹp|tốt|mượt|hợp lý|phù hợp|nhanh|ổn|dễ dùng|dễ hiểu|rõ ràng|tự nhiên|hay hơn|đúng cách|thân thiện|hấp dẫn|ấn tượng|chuyên nghiệp|hiện đại)/i;
const CONCRETE = /\d|`|#\/|#[\w-]|\[[^\]]+\]|aria-label|data-|::|\.(py|ts|tsx)\b|(?<![\p{L}\d_])[A-Za-z_][\w.]*\(/u;
// Mã tính năng (F01), mục tài liệu (§10.3) và "()" trơ trọi không phải là thứ đo được.
const concrete = (d) => CONCRETE.test(d.replace(/\bF\d{2,}\b/g, '').replace(/§\s*[\d.]+/g, '').replace(/\(\s*\)/g, ''));
const kindOf = (d) => (/^Unit\s*:/i.test(d) ? 'unit' : /^Bot\s*:/i.test(d) ? 'bot' : /^Model thật\s*:/i.test(d) ? 'real' : null);
const bad = [];
const vagueLines = [];
const missingTests = [];
const noScenario = [];
let built = 0;
let planned = 0;
const ids = new Map();
for (const p of pages) {
  const t = read(path.join(fdir, p)).replace(/\r\n/g, '\n');
  const why = [];
  const head = (t.split('\n').find((l) => l.trim()) || '').match(/^#\s+(F\d{2,})\s+—\s+.+$/);
  if (!/^F\d{2,}-[^\s]+\.md$/.test(p)) why.push('tên file không phải F<NN>-<slug>.md');
  if (!head) why.push('dòng đầu không phải "# F01 — Tên"');
  else {
    if (!p.startsWith(`${head[1]}-`)) why.push(`id ${head[1]} khác tên file`);
    if (ids.has(head[1])) why.push(`trùng id với ${ids.get(head[1])}`);
    ids.set(head[1], p);
  }
  const meta = t.split(/^##\s+/m)[0].split('\n').filter((l) => !/^\s*#/.test(l)).join('\n');
  const st = meta.match(/Giai đoạn\**[ \t]*:[ \t]*\**[ \t]*([^·\n]+)/i);
  const stage = st ? (/^đã có/i.test(st[1].replace(/\*/g, '').trim()) ? 'built' : /^kế hoạch/i.test(st[1].replace(/\*/g, '').trim()) ? 'planned' : null) : null;
  if (!stage) why.push('thiếu "Giai đoạn: Đã có | Kế hoạch"');
  if (stage === 'built') built += 1;
  if (stage === 'planned') planned += 1;
  const section = (name) => {
    const m = t.split(/^##\s+/m).find((s) => s.split('\n')[0].trim().toLowerCase() === name);
    return m === undefined ? null : m.split('\n').slice(1).join('\n');
  };
  const doneSec = section('done when');
  const boxes = doneSec ? [...doneSec.matchAll(/^\s*[-*]\s+\[(.)\]\s+(.+)$/gm)] : [];
  if (doneSec === null) why.push('thiếu "## Done when"');
  if (boxes.some((b) => b[1] !== ' ')) why.push('có dòng đã tick [x] (trạng thái chỉ nằm trong memory/features.json)');
  const done = boxes.map((b) => b[2].trim());
  const noKind = done.filter((d) => !kindOf(d));
  if (noKind.length) why.push(`${noKind.length} dòng Done when không bắt đầu bằng Unit:/Bot:/Model thật:`);
  for (const d of done) if (VAGUE.test(d) && !concrete(d)) vagueLines.push(`${p}: "${d.slice(0, 70)}"`);
  const unboxed = doneSec ? doneSec.split('\n').filter((l) => /^\s*[-*]\s+/.test(l) && !/^\s*[-*]\s+\[.\]\s+/.test(l)) : [];
  if (unboxed.length) why.push(`${unboxed.length} gạch đầu dòng trong Done when thiếu ô "[ ]" (sẽ không bao giờ được chấm)`);
  const testSec = section('tests');
  const refs = testSec ? [...testSec.matchAll(/^\s*[-*]\s+(.+)$/gm)].map((m) => m[1].replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").trim()) : [];
  if (stage === 'built') {
    if (done.length < 2) why.push(`Done when ${done.length} dòng (cần ≥ 2)`);
    if (!refs.length) why.push('chưa có tham chiếu nào trong "## Tests"');
    for (const r of refs) {
      const parsed = fmod.parseTestRef(r);
      if (parsed.error) { why.push(`Tests: ${parsed.error.slice(0, 90)}`); continue; }
      const ref = parsed.ref;
      if (ref.startsWith('bot:')) {
        const name = ref.slice(4).normalize('NFC').trim();
        if (!botNames) missingTests.push(`${p}: không đọc được CHECKS của environment/e2e.mjs`);
        else if (!botNames.includes(name)) missingTests.push(`${p}: bot "${name.slice(0, 50)}" không có trong environment/e2e.mjs`);
        continue;
      }
      const miss = fmod.refMissing(ref, knownScenarios);
      if (miss) missingTests.push(`${p}: ${miss}`);
    }
    const realLines = done.filter((d) => kindOf(d) === 'real');
    if (realLines.length) {
      const cov = fmod.realCoverage({ done, tests: refs.map((r) => fmod.parseTestRef(r).ref).filter(Boolean) });
      if (cov.uncovered.length) noScenario.push(`${p.slice(0, 3)} (${cov.uncovered.length}/${realLines.length})`);
    }
    if (done.some((d) => kindOf(d) === 'bot') && !refs.some((r) => /^`?bot\s*:/i.test(r))) why.push('có Done when "Bot:" nhưng Tests không có "bot: <tên check>"');
  }
  if (why.length) bad.push(`${p} (${why.join('; ')})`);
}
check('mọi trang tính năng đúng hợp đồng (dòng đầu, Giai đoạn, Done when, Tests)', pages.length > 0 && bad.length === 0, bad.slice(0, 4).join(' · ') + (bad.length > 4 ? ` · +${bad.length - 4}` : ''));
check('không có dòng Done when mơ hồ (cảm tính mà không có số/selector)', vagueLines.length === 0, vagueLines.slice(0, 3).join(' · ') + (vagueLines.length > 3 ? ` · +${vagueLines.length - 3}` : ''));
check('test mà tính năng "Đã có" tham chiếu đều có thật (file, tên hàm, check bot, kịch bản model)', missingTests.length === 0, missingTests.slice(0, 3).join(' · ') + (missingTests.length > 3 ? ` · +${missingTests.length - 3}` : ''));
const contract = fmod.readPages().errors;
check('trang tính năng qua được bộ đọc của memory/features.mjs (sync)', contract.length === 0, contract.slice(0, 3).join(' · ') + (contract.length > 3 ? ` · +${contract.length - 3}` : ''));
const drift = contract.length ? [] : fmod.driftFromWiki();
check('memory/features.json khớp wiki (không thì: node memory/features.mjs sync)', drift.length === 0, drift.slice(0, 3).join(' · ') + (drift.length > 3 ? ` · +${drift.length - 3}` : ''));
check('dòng "Model thật" có kịch bản "model: <id>" chứng minh (thiếu thì tính năng đó không ✅ được)', noScenario.length === 0, noScenario.join(', '), 'warn');
check(`tính năng: ${built} đã có · ${planned} kế hoạch`, true, '', 'info');

// ---------------------------------------------------------------- màn hình, thiết kế
const sdir = path.join(W, 'screens');
check('có ít nhất 1 trang màn hình (screens/)', fs.existsSync(sdir) && fs.readdirSync(sdir).some((f) => f.endsWith('.md')));
const st = read(path.join(W, 'design', 'style.md'));
const colors = new Set((st.match(/#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|oklch\([^)]*\)/g) || []).map((c) => c.toLowerCase()));
check('design/style.md: có ≥ 5 màu', colors.size >= 5, `${colors.size} mã màu`);
check('design/style.md: nói rõ font', /font/i.test(st) && /(@fontsource|google fonts|fonts\.googleapis|font-family|[A-Z][a-z]+ (Sans|Serif|Pro|Garamond|Mono))/.test(st));

// ---------------------------------------------------------------- TODO / ???
const todo = [];
const walk = (dir) => {
  if (!fs.existsSync(dir)) return;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (path.relative(W, p) !== 'raw') walk(p); continue; }
    if (!e.name.endsWith('.md')) continue;
    read(p).split('\n').forEach((line, i) => {
      if (/\bTODO\b|\?\?\?/.test(line) && !WHITELIST.some((re) => re.test(line))) todo.push(`${path.relative(W, p)}:${i + 1}`);
    });
  }
};
walk(W);
check('không còn TODO / ??? trong wiki (trừ raw/ và chỗ nhóm điền đã biết)', todo.length === 0, todo.slice(0, 5).join(', ') + (todo.length > 5 ? ` · +${todo.length - 5}` : ''));

// ---------------------------------------------------------------- lưu ý (không làm đỏ)
const idx = read(path.join(W, 'index.md'));
const notIndexed = pages.filter((p) => !idx.includes(p));
check('index.md liệt kê mọi trang tính năng', notIndexed.length === 0, notIndexed.slice(0, 4).join(', '), 'warn');
check('có learned.md và log.md', fs.existsSync(path.join(W, 'learned.md')) && fs.existsSync(path.join(W, 'log.md')), '', 'warn');

let fail = 0;
console.log('┌─ PLAN CHECK · Wiki của Lyris đủ để build chưa?');
for (const c of checks) {
  const mark = c.level === 'info' ? '·' : c.ok ? '✓' : c.level === 'warn' ? '!' : '✗';
  console.log(`│ ${mark} ${c.name}${c.detail ? ` — ${c.detail}` : ""}`);
  if (!c.ok && c.level === 'fail') fail = 1;
}
console.log(fail ? '└─ 🔴 Còn thiếu: bổ sung Wiki rồi chạy lại' : '└─ 🟢 Wiki đủ để build');
process.exit(fail);
})().catch((e) => { console.error(`plan-check lỗi nội bộ: ${e.stack || e}`); process.exit(1); });
EOF
