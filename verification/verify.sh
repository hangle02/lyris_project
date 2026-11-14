#!/usr/bin/env bash
# ③ VERIFICATION — giám khảo chấm đậu/rớt của Lyris. Chế độ model_led:
#   Model làm xong tính năng nào thì `node memory/features.mjs claim F02` (🟡). Rồi chạy verify:
#     bash verification/verify.sh                  → chấm mọi tính năng 🟡 claimed + soát hồi quy mọi tính năng ✅
#     bash verification/verify.sh F02 F03          → chấm đúng các tính năng này
#     bash verification/verify.sh --quick F02      → bỏ bộ test đầy đủ (bước 2): chỉ để sửa nhanh, KHÔNG BAO GIỜ ✅
#     bash verification/verify.sh --real-model F03 → chạy thêm các kịch bản model thật (dòng "model: <id>" trong Tests)
#                                                    trên Ollama thật (chỉ khi chủ dự án không dùng app)
#   Xanh → CHÍNH verify.sh chuyển 🟡 → ✅ passing (memory/features.mjs promote --gate). Model không tự làm được việc đó.
#   Một lần chạy đầy đủ mất 3–5 phút: chạy bằng tool Bash với timeout 600000, hoặc chạy nền.
#
# Các bước:
#   S) node memory/features.mjs sync: sổ luôn khớp wiki (Done when/Tests đổi sau khi ✅ → ⏳).
#   0) Mỗi tính năng: có "## Tests", mọi tham chiếu tồn tại (file, hàm test, kịch bản model); có Done when "Unit:" thì
#      có test unit, có "Bot:" thì có dòng "bot: <tên check>"; mỗi dòng "Model thật:" nhắc `id` một kịch bản "model:".
#   1) Chạy đúng các test mà tính năng tham chiếu. Mỗi tham chiếu phải có ít nhất 1 test THẬT SỰ qua; test bị skip
#      (node id cụ thể) hay file không có test nào chạy thì đỏ.
#   2) Bộ test đầy đủ: backend pytest · frontend npm test · npm run typecheck · npm run build (--quick bỏ qua).
#   3) Bot: node environment/bot.mjs --quiet (kịch bản chuẩn environment/e2e.mjs, server LLM giả, cổng 8066/8067) →
#      mọi "bot: …" của tính năng phải có trong reports/latest/report.json và xanh.
#   4) Model thật: không có --real-model thì "bỏ qua (cần model thật) — chưa thể ✅", tính năng vẫn 🟡.
#   Đỏ → +1 lần đỏ; lần thứ 3 thì sổ tự ⛔ blocked (Model ghi learned.md + Câu hỏi cho PO). Lỗi đồ nghề (cổng bận,
#   thiếu Chrome/venv/node_modules, Chrome chết) không tính lần đỏ. ✅ mà test của nó đỏ → hạ về ⏳ (hồi quy).
#   Kết quả: reports/verify.json. Mã thoát: 0 = xanh · 1 = đỏ · 2 = sai tham số/cấu hình · 3 = xanh nhưng còn 🟡
#   (--quick, hoặc cần model thật).
#
# Tự kiểm harness trên dữ liệu giả: LYRIS_HARNESS_HOME=<thư mục KHÁC repo, có wiki/ memory/> (wiki, sổ, reports nằm
# ở đó; code và test vẫn là của repo). Chỉ ở chế độ đó mới được thay bot bằng LYRIS_HARNESS_BOT="<lệnh>", và chế độ đó
# không chấm tính năng nào trùng id + tên với sổ thật.
set -u
cd "$(dirname "$0")/.." || exit 1
set -a
# shellcheck source=../harness.config
source ./harness.config
set +a
exec node - "$@" <<'EOF'
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { pathToFileURL } = require('url');

const real = (p) => { try { return fs.realpathSync(p); } catch { return path.resolve(p); } };
const REPO = real(process.cwd());
const env = process.env;
const inRepo = (p) => { const r = path.relative(REPO, real(p)); return r && !r.startsWith('..') && !path.isAbsolute(r); };
const BACKEND = path.join(REPO, env.BACKEND_DIR || 'backend');
const FRONTEND = path.join(REPO, env.FRONTEND_DIR || 'frontend');
if (!inRepo(BACKEND) || !inRepo(FRONTEND)) {
  console.error(`harness.config: BACKEND_DIR/FRONTEND_DIR phải là thư mục trong repo (${env.BACKEND_DIR} · ${env.FRONTEND_DIR}).`);
  process.exit(2);
}
const PYTEST = path.join(BACKEND, '.venv', 'bin', 'pytest');
const PY = path.join(BACKEND, '.venv', 'bin', 'python');
const HOME = env.LYRIS_HARNESS_HOME ? real(env.LYRIS_HARNESS_HOME) : REPO;
const REAL_LEDGER = path.join(REPO, 'memory', 'features.json');
const FEATURES = path.join(HOME, 'memory', 'features.json');
// Chế độ tự kiểm chỉ khi HOME thật sự là chỗ khác: so sau khi giải symlink, cả thư mục lẫn file sổ.
const FIXTURE = HOME !== REPO && real(path.join(HOME, 'memory')) !== real(path.join(REPO, 'memory'))
  && !(fs.existsSync(FEATURES) && real(FEATURES) === real(REAL_LEDGER));
if (env.LYRIS_HARNESS_HOME && !FIXTURE) {
  console.error(`LYRIS_HARNESS_HOME=${env.LYRIS_HARNESS_HOME} trỏ về chính repo / sổ thật — không phải chế độ tự kiểm. Bỏ biến này.`);
  process.exit(2);
}
if (env.LYRIS_HARNESS_BOT && !FIXTURE) {
  console.error('LYRIS_HARNESS_BOT chỉ dùng được trong chế độ tự kiểm (LYRIS_HARNESS_HOME=<thư mục khác repo>).');
  process.exit(2);
}
const REPORTS = path.join(HOME, 'reports');
const LOG = path.join(HOME, 'wiki', 'log.md');
const BOT_OVERRIDE = FIXTURE && env.LYRIS_HARNESS_BOT ? env.LYRIS_HARNESS_BOT : '';
const BOT_SCRIPT = path.join(REPO, 'environment', 'bot.mjs');
const BOT_SCENARIO = 'environment/e2e.mjs';
const BOT_REPORT = BOT_OVERRIDE ? path.join(REPORTS, 'latest', 'report.json') : path.join(REPO, 'reports', 'latest', 'report.json');
const SCENARIOS = path.join(REPO, 'harness', 'scenarios');
const OLLAMA = (env.OLLAMA_URL || 'http://127.0.0.1:11434').replace(/\/$/, '');
const CHAT_MODEL = env.LYRIS_CHAT_MODEL || 'gemma4:12b';
const MIN = 60 * 1000;

// ---------------------------------------------------------------- tham số
let QUICK = false;
let REAL = false;
const asked = [];
for (const a of process.argv.slice(2)) {
  if (a === '--quick') QUICK = true;
  else if (a === '--real-model') REAL = true;
  else if (a === '-h' || a === '--help') {
    console.log('Dùng: bash verification/verify.sh [--quick] [--real-model] [F01 F02 …]');
    process.exit(0);
  } else if (/^F\d+$/i.test(a)) asked.push(`F${String(Number(a.slice(1))).padStart(2, '0')}`);
  else { console.error(`Không hiểu tham số "${a}". Dùng: bash verification/verify.sh [--quick] [--real-model] [F01 …]`); process.exit(2); }
}

const say = (s = '') => console.log(`│ ${s}`.trimEnd());
const sub = (text, n = 25) => text.split('\n').filter((l) => l.trim()).slice(0, n).forEach((l) => say(`   ${l}`));
const tail = (text, n = 15) => text.split('\n').filter((l) => l.trim()).slice(-n).forEach((l) => say(`   ${l}`));
const run = (cmd, args, opts = {}) => {
  const r = spawnSync(cmd, args, { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, killSignal: 'SIGTERM', ...opts });
  const timedOut = Boolean(r.error && r.error.code === 'ETIMEDOUT');
  return { rc: r.status ?? (r.error ? 127 : 1), out: `${r.stdout || ''}${r.stderr || ''}`, error: r.error, timedOut };
};
const fm = (...args) => run(process.execPath, [path.join(REPO, 'memory', 'features.mjs'), ...args], { env: { ...env, LYRIS_HARNESS_HOME: HOME } });
const today = () => new Date().toISOString().slice(0, 10);
const kindOf = (d) => (/^Unit\s*:/i.test(d) ? 'unit' : /^Bot\s*:/i.test(d) ? 'bot' : /^Model thật\s*:/i.test(d) ? 'real' : null);
const isBot = (r) => r.startsWith('bot:');
const isModel = (r) => r.startsWith('model:');
const isCode = (r) => !isBot(r) && !isModel(r);
const normName = (s) => String(s).normalize('NFC').replace(/^bot\s*:\s*/i, '').trim();

(async () => {
  const fmod = await import(pathToFileURL(path.join(REPO, 'memory', 'features.mjs')).href);
  const result = { at: new Date().toISOString(), quick: QUICK, real_model_flag: REAL, fixture: FIXTURE, suites: {}, bot: null, real_model: null, targets: [], regressions: [] };

  // ---------------------------------------------------------------- S) sổ khớp wiki
  const s = fm('sync');
  const headIds = asked.length ? asked.join(' ') : 'mọi 🟡 claimed (+ soát hồi quy ✅)';
  console.log(`┌─ VERIFICATION · stack=${env.STACK || '?'} · chấm: ${headIds}${QUICK ? ' · --quick' : ''}${REAL ? ' · --real-model' : ''}`);
  if (FIXTURE) say(`(chế độ tự kiểm: dữ liệu ở ${HOME}${BOT_OVERRIDE ? ', bot giả' : ''})`);
  say();
  say('S) Đồng bộ sổ với wiki (node memory/features.mjs sync)');
  if (s.rc !== 0) {
    sub(s.out, 15);
    console.log('└─ 🔴 ĐỎ — trang wiki sai hợp đồng, sổ không đồng bộ được. Sửa trang rồi chạy lại (không tính lần đỏ).');
    process.exit(1);
  }
  sub(s.out, 15);

  const list = JSON.parse(fs.readFileSync(FEATURES, 'utf8'));
  if (FIXTURE && fs.existsSync(REAL_LEDGER)) {
    // Bản sao sổ không phải chỗ để "chạy thử khỏi mất lượt đỏ": tính năng thật chỉ được chấm trên sổ thật.
    const realList = JSON.parse(fs.readFileSync(REAL_LEDGER, 'utf8'));
    const clash = list.filter((f) => realList.some((r) => r.id === f.id && r.title === f.title));
    if (clash.length) {
      console.log(`└─ ⛔ Chế độ tự kiểm không chấm tính năng thật (${clash.map((f) => f.id).join(', ')} trùng id + tên với memory/features.json). Chấm trên sổ thật.`);
      process.exit(2);
    }
  }
  const ids = asked.length ? asked : list.filter((f) => f.state === 'claimed').map((f) => f.id);
  const mk = (id, watch = false) => {
    const f = list.find((x) => x.id === id);
    return { id, f, title: f ? f.title : '', ok: true, reasons: [], realSkipped: false, realWhy: '', watch, countable: Boolean(f && f.state === 'claimed') };
  };
  const targets = ids.map((id) => mk(id));
  // Soát hồi quy: mọi ✅ không có trong danh sách chấm cũng được đối chiếu với kết quả bộ test đầy đủ và bot.
  const watched = QUICK ? [] : list.filter((f) => f.state === 'passing' && !ids.includes(f.id)).map((f) => mk(f.id, true));
  const fail = (t, why) => { t.ok = false; t.reasons.push(why); };
  let suitesOk = true;   // bước 2 + bot chạy được và xanh: lỗi chung của cả app
  let infraOnly = true;  // đỏ chỉ vì lỗi đồ nghề → không tính lần đỏ
  const general = [];
  const generalFail = (why, infra = false) => { suitesOk = false; general.push(infra ? `${why} (đồ nghề)` : why); if (!infra) infraOnly = false; };
  const knownScenarios = fmod.scenarioIds();

  // ---------------------------------------------------------------- 0) luật "viết test trước"
  say();
  say('0) Mỗi tính năng có test (trang wiki "## Tests") và test đó tồn tại');
  const refMissing = (r) => fmod.refMissing(r, knownScenarios);
  const structure = (t) => {
    const f = t.f;
    const tests = f.tests || [];
    const kinds = new Set((f.done || []).map(kindOf));
    if (!tests.length) fail(t, `trang ${f.page} chưa có "## Tests" — luật: viết test trước rồi mới code`);
    if (kinds.has('unit') && !tests.some(isCode)) fail(t, 'có Done when "Unit:" nhưng "## Tests" không có test backend/frontend');
    if (kinds.has('bot') && !tests.some(isBot)) fail(t, 'có Done when "Bot:" nhưng "## Tests" không có dòng "bot: <tên check>"');
    for (const r of tests.filter((x) => !isBot(x))) { const miss = refMissing(r); if (miss) fail(t, `Tests: ${miss}`); }
  };
  for (const t of targets) {
    const f = t.f;
    if (!f) { fail(t, 'không có trong memory/features.json (trang wiki/features/ chưa có?)'); say(`✗ ${t.id}: không có trong sổ`); continue; }
    if (f.stage === 'planned') fail(t, 'Giai đoạn: Kế hoạch — chưa thể ✅');
    else if (f.state === 'pending') fail(t, 'chưa claim (node memory/features.mjs claim ' + t.id + ')');
    else if (f.state === 'blocked') fail(t, `đang ⛔ (${f.reason || 'không lý do'}) — chờ PO, rồi reopen ${t.id} "PO: …"`);
    structure(t);
    say(`${t.ok ? '✓' : '✗'} ${t.id} — ${t.title}${t.ok ? ` (${(f.tests || []).length} tham chiếu test)` : ''}`);
    for (const why of t.reasons) say(`     ✗ ${why}`);
  }
  for (const t of watched) structure(t);
  const brokenWatch = watched.filter((t) => !t.ok);
  if (watched.length) say(`${brokenWatch.length ? '✗' : '✓'} ${watched.length} tính năng ✅ (soát hồi quy): ${brokenWatch.length ? brokenWatch.map((t) => `${t.id} — ${t.reasons.join(' · ')}`).join(' | ') : 'tham chiếu test vẫn còn đủ'}`);

  // ---------------------------------------------------------------- 1) test của từng tính năng
  say();
  say('1) Test mà các tính năng tham chiếu (mỗi tham chiếu phải có test thật sự qua)');
  const existing = (t) => (t.f ? (t.f.tests || []).filter((r) => isCode(r) && !refMissing(r)) : []);
  const backRefs = [...new Set(targets.flatMap((t) => existing(t).filter((r) => r.startsWith('backend/'))))];
  const frontRefs = [...new Set(targets.flatMap((t) => existing(t).filter((r) => r.startsWith('frontend/'))))];
  const badRef = new Map(); // ref → lý do đỏ
  const relBack = (r) => path.relative(BACKEND, path.join(REPO, r.split('::')[0])) + (r.includes('::') ? '::' + r.split('::').slice(1).join('::') : '');
  const underRef = (rel, id) => (rel.includes('::') ? id === rel || id.startsWith(`${rel}[`) || id.startsWith(`${rel}::`) : id === rel || id.startsWith(`${rel}::`));
  if (!backRefs.length && !frontRefs.length) say('– không có test để chạy');
  if (backRefs.length) {
    if (!fs.existsSync(PYTEST)) {
      say(`✗ không có ${path.relative(REPO, PYTEST)} (cd backend && uv sync)`);
      generalFail(`thiếu ${path.relative(REPO, PYTEST)}`, true);
    } else {
      const rels = backRefs.map(relBack);
      // -v: một dòng "<node id> PASSED|FAILED|SKIPPED…" cho từng test → biết tham chiếu nào thật sự có test qua.
      const r = run(PYTEST, ['-v', '-rfE', '-p', 'no:cacheprovider', '--color=no', ...rels], { cwd: BACKEND, timeout: 20 * MIN });
      const outcome = [...r.out.matchAll(/^(\S+::\S+?(?:\[.*?\])?) (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b/gm)].map((m) => ({ id: m[1], st: m[2] }));
      const summary = r.out.split('\n').filter((l) => /\b(passed|failed|error|no tests ran)\b/.test(l)).pop() || `pytest rc=${r.rc}`;
      if (r.timedOut) { say('✗ pytest treo quá 20 phút'); for (const ref of backRefs) badRef.set(ref, 'pytest treo quá 20 phút'); }
      else if (r.rc !== 0 && r.rc !== 1) { say(`✗ pytest không chạy được (rc=${r.rc})`); tail(r.out, 12); for (const ref of backRefs) badRef.set(ref, `pytest không chạy được (rc=${r.rc})`); }
      for (const ref of backRefs) {
        if (badRef.has(ref)) continue;
        const rel = relBack(ref);
        const mine = outcome.filter((o) => underRef(rel, o.id));
        const bad = mine.filter((o) => o.st === 'FAILED' || o.st === 'ERROR');
        const passed = mine.filter((o) => o.st === 'PASSED');
        const skipped = mine.filter((o) => o.st !== 'PASSED' && o.st !== 'FAILED' && o.st !== 'ERROR');
        if (bad.length) badRef.set(ref, `pytest đỏ: ${bad.slice(0, 3).map((o) => o.id).join(', ')}${bad.length > 3 ? ` (+${bad.length - 3})` : ''}`);
        else if (!passed.length) badRef.set(ref, mine.length ? `không có test nào qua (${skipped.length} bị skip/xfail) — test bị skip không phải bằng chứng` : 'không có test nào chạy');
        else if (ref.includes('::') && skipped.length) badRef.set(ref, `${skipped.length} test bị skip/xfail trong tham chiếu cụ thể này`);
      }
      const badN = backRefs.filter((x) => badRef.has(x)).length;
      say(`${badN ? '✗' : '✓'} pytest (${backRefs.length} tham chiếu, ${outcome.length} test): ${summary.replace(/=/g, '').trim()}`);
      for (const ref of backRefs.filter((x) => badRef.has(x))) say(`   ✗ ${ref}: ${badRef.get(ref)}`);
      sub(r.out.split('\n').filter((l) => /^(FAILED|ERROR)\s/.test(l)).join('\n'), 12);
    }
  }
  const nodeTest = (ref) => {
    const rel = path.relative(FRONTEND, path.join(REPO, ref));
    const r = run(process.execPath, ['--experimental-strip-types', '--no-warnings', '--test', rel], { cwd: FRONTEND, timeout: 5 * MIN });
    const n = (k) => Number((r.out.match(new RegExp(`^(?:ℹ|#) ${k} (\\d+)`, 'm')) || [])[1] ?? NaN);
    const counts = { tests: n('tests'), pass: n('pass'), fail: n('fail'), skipped: n('skipped'), todo: n('todo') };
    const text = `tests ${counts.tests} · pass ${counts.pass} · fail ${counts.fail}${counts.skipped ? ` · skipped ${counts.skipped}` : ''}${counts.todo ? ` · todo ${counts.todo}` : ''}`;
    let why = '';
    if (r.timedOut) why = 'node --test treo quá 5 phút';
    else if (r.rc !== 0) why = `node --test đỏ (${Number.isNaN(counts.tests) ? `rc=${r.rc}` : text})`;
    else if (!(counts.pass > 0)) why = `không có test nào qua (${text}) — test bị skip/todo không phải bằng chứng`;
    else if (counts.skipped > 0 || counts.todo > 0) why = `có test bị skip/todo (${text})`;
    return { why, text, out: r.out };
  };
  for (const ref of frontRefs) {
    const r = nodeTest(ref);
    if (!r.why) say(`✓ node --test ${ref}: ${r.text}`);
    else {
      badRef.set(ref, r.why);
      say(`✗ node --test ${ref}: ${r.why}`);
      sub(r.out.split('\n').filter((l) => /✖|Error|expected|actual/.test(l)).join('\n'), 12);
    }
  }
  for (const t of targets) for (const r of existing(t)) if (badRef.has(r)) fail(t, `${r}: ${badRef.get(r)}`);

  // ---------------------------------------------------------------- 2) bộ test đầy đủ
  say();
  let fullPytestFailed = null; // node id đỏ trong bộ đầy đủ (để tìm ✅ bị hồi quy)
  let npmTestRed = false;
  if (QUICK) {
    say('2) Bộ test đầy đủ — bỏ qua (--quick). Chạy lại không có --quick thì mới ✅ được.');
  } else {
    say('2) Bộ test đầy đủ (backend pytest · npm test · typecheck · build)');
    const nm = path.join(FRONTEND, 'node_modules');
    const suites = [
      ['backend pytest -q', PYTEST, ['-q', '-rfE', '-p', 'no:cacheprovider', '--color=no'], BACKEND, /\b\d+ (passed|failed)\b.*$/m, () => (fs.existsSync(PYTEST) ? '' : `thiếu ${path.relative(REPO, PYTEST)}`)],
      ['frontend npm test', 'npm', ['test', '--silent'], FRONTEND, null, () => (fs.existsSync(nm) ? '' : 'thiếu frontend/node_modules (npm install)')],
      ['frontend npm run typecheck', 'npm', ['run', 'typecheck', '--silent'], FRONTEND, null, () => (fs.existsSync(nm) ? '' : 'thiếu frontend/node_modules')],
      ['frontend npm run build', 'npm', ['run', 'build', '--silent'], FRONTEND, null, () => (fs.existsSync(nm) ? '' : 'thiếu frontend/node_modules')],
    ];
    for (const [name, cmd, args, cwd, re, pre] of suites) {
      const missing = pre();
      if (missing) { say(`✗ ${name}: ${missing}`); result.suites[name] = { ok: false, infra: missing }; generalFail(`${name}: ${missing}`, true); continue; }
      const t0 = Date.now();
      const r = run(cmd, args, { cwd, timeout: 20 * MIN });
      const secs = ((Date.now() - t0) / 1000).toFixed(0);
      let info = '';
      if (re) info = (r.out.match(re) || [''])[0].replace(/=/g, '').trim();
      else info = r.out.split('\n').filter((l) => /^(?:ℹ|#) (tests|pass|fail|skipped) \d/.test(l)).map((l) => l.slice(2)).join(' · ');
      result.suites[name] = { ok: r.rc === 0, rc: r.rc, info, seconds: Number(secs), timed_out: r.timedOut };
      if (name.startsWith('backend')) fullPytestFailed = [...r.out.matchAll(/^(?:FAILED|ERROR)\s+(\S+)/gm)].map((m) => m[1]);
      if (r.rc === 0) say(`✓ ${name} (${secs}s)${info ? ` — ${info}` : ''}`);
      else {
        say(`✗ ${name} (${r.timedOut ? 'treo quá 20 phút' : `rc=${r.rc}`}, ${secs}s)${info ? ` — ${info}` : ''}`);
        const lines = r.out.split('\n').filter((l) => /^(FAILED|ERROR)\s|✖|error TS|Error:|failed/.test(l));
        if (lines.length) sub(lines.join('\n'), 15); else tail(r.out, 15);
        if (name === 'frontend npm test') npmTestRed = true;
        generalFail(`${name} đỏ`, r.timedOut);
      }
    }
  }

  // ---------------------------------------------------------------- 3) bot
  say();
  say('3) Bot (Chrome tự bấm app trên server LLM giả)');
  let report = null;
  let botInfra = '';
  let botComplete = false;
  let checks = [];
  if (!BOT_OVERRIDE && !fs.existsSync(BOT_SCRIPT)) {
    say('✗ Không có environment/bot.mjs — Environment chưa có bot nên KHÔNG thể ✅ (không tự bỏ qua bước này).');
    botInfra = 'thiếu environment/bot.mjs';
    generalFail(botInfra, true);
  } else {
    try { fs.rmSync(BOT_REPORT, { force: true }); } catch {}
    const t0 = Date.now();
    // Bot luôn chạy kịch bản chuẩn: bỏ BOT_SCENARIO thừa hưởng từ shell (chỉ để gỡ lỗi kịch bản bằng tay).
    const botEnv = { ...env };
    delete botEnv.BOT_SCENARIO;
    const r = BOT_OVERRIDE
      ? run('bash', ['-c', BOT_OVERRIDE], { cwd: REPO, env: { ...botEnv, LYRIS_HARNESS_HOME: HOME }, timeout: 25 * MIN })
      : run(process.execPath, [BOT_SCRIPT, '--quiet'], { cwd: REPO, env: botEnv, timeout: 25 * MIN });
    const secs = ((Date.now() - t0) / 1000).toFixed(0);
    sub(r.out, 20);
    if (fs.existsSync(BOT_REPORT)) {
      try { report = JSON.parse(fs.readFileSync(BOT_REPORT, 'utf8')); } catch (e) { say(`✗ report.json hỏng: ${e.message}`); }
    }
    checks = (report && Array.isArray(report.checks)) ? report.checks : [];
    const failed = checks.filter((c) => !c.ok);
    result.bot = { rc: r.rc, seconds: Number(secs), report: path.relative(HOME, BOT_REPORT), checks: checks.length, failed: failed.map((c) => c.name), infra: (report && report.infra) || '' };
    if (r.timedOut) { botInfra = 'bot treo quá 25 phút (verify đã tắt nó)'; say(`✗ ${botInfra}`); generalFail(botInfra, true); }
    else if (!report) { say(`✗ Bot không ghi ${path.relative(REPO, BOT_REPORT)} (rc=${r.rc})`); generalFail('bot không ra báo cáo'); }
    else if (report.infra) { botInfra = `bot không chạy được: ${report.infra}`; say(`✗ ${botInfra} — lỗi đồ nghề, không tính lần đỏ`); generalFail(botInfra, true); }
    else if (!BOT_OVERRIDE && report.scenario !== BOT_SCENARIO) {
      say(`✗ Bot chạy kịch bản "${report.scenario || '?'}", không phải ${BOT_SCENARIO} — không dùng làm bằng chứng.`);
      generalFail('bot không chạy kịch bản chuẩn');
      report = null;
    } else {
      botComplete = !checks.some((c) => c.name === 'Bot chạy hết kịch bản' && !c.ok);
      if (r.rc !== 0 || failed.length || report.passed === false) {
        say(`✗ Bot đỏ (rc=${r.rc}, ${failed.length}/${checks.length} check đỏ, ${secs}s)`);
        for (const c of failed.slice(0, 15)) say(`   ✗ ${c.name}${c.detail ? ` — ${c.detail}` : ''}`);
        generalFail('bot đỏ');
      } else say(`✓ Bot xanh: ${checks.length} check (${secs}s)`);
    }
    if (!botInfra && report) {
      for (const t of targets) {
        for (const ref of ((t.f && t.f.tests) || []).filter(isBot)) {
          const name = ref.slice(4).trim();
          const c = checks.find((x) => normName(x.name) === normName(name));
          if (!c) fail(t, botComplete ? `bot chưa có check "${name}" (thêm vào environment/e2e.mjs, tên phải khớp đúng từng chữ)` : `bot dừng giữa chừng trước check "${name}"`);
          else if (!c.ok) fail(t, `bot: "${name}" đỏ${c.detail ? ` — ${c.detail}` : ''}`);
        }
      }
      const mine = targets.filter((t) => t.f && (t.f.tests || []).some(isBot));
      for (const t of mine) {
        const bad = t.reasons.filter((x) => x.startsWith('bot'));
        say(`${bad.length ? '✗' : '✓'} ${t.id}: check bot của tính năng${bad.length ? '' : ' có mặt và xanh'}`);
        for (const b of bad) say(`     ✗ ${b}`);
      }
    } else if (botInfra) say('– không chấm check bot của từng tính năng (bot không chạy được).');
  }

  // ---------------------------------------------------------------- hồi quy của các tính năng ✅
  if (watched.length) {
    const frontBad = new Map();
    if (npmTestRed) {
      for (const ref of [...new Set(watched.flatMap((t) => existing(t).filter((r) => r.startsWith('frontend/'))))]) {
        const r = nodeTest(ref);
        if (r.why) frontBad.set(ref, r.why);
      }
    }
    for (const t of watched) {
      for (const ref of existing(t)) {
        if (ref.startsWith('backend/') && fullPytestFailed) {
          const rel = relBack(ref);
          const hit = fullPytestFailed.filter((id) => underRef(rel, id));
          if (hit.length) fail(t, `${ref}: pytest đỏ (${hit.slice(0, 2).join(', ')})`);
        }
        if (frontBad.has(ref)) fail(t, `${ref}: ${frontBad.get(ref)}`);
      }
      if (!botInfra && report) {
        for (const ref of (t.f.tests || []).filter(isBot)) {
          const c = checks.find((x) => normName(x.name) === normName(ref.slice(4)));
          if (c && !c.ok) fail(t, `bot: "${ref.slice(4).trim()}" đỏ${c.detail ? ` — ${c.detail}` : ''}`);
          else if (!c && botComplete) fail(t, `bot không còn check "${ref.slice(4).trim()}"`);
        }
      }
    }
  }

  // ---------------------------------------------------------------- 4) model thật
  say();
  say('4) Model thật (Done when "Model thật:" ↔ Tests "model: <id kịch bản>")');
  const realTargets = targets.filter((t) => t.f && (t.f.done || []).some((d) => kindOf(d) === 'real'));
  for (const t of realTargets) {
    const cover = fmod.realCoverage(t.f);
    t.modelIds = cover.ids;
    if (cover.uncovered.length) {
      t.realSkipped = true;
      t.realWhy = `${cover.uncovered.length} dòng "Model thật" chưa có kịch bản chứng minh (dòng phải nhắc \`id\` của một "model: <id>" trong Tests)`;
    }
  }
  if (!realTargets.length) say('– không tính năng nào cần model thật');
  else if (!REAL) {
    for (const t of realTargets) { t.realSkipped = true; say(`– ${t.id}: bỏ qua (cần model thật) — chưa thể ✅.${t.realWhy ? ` Lưu ý: ${t.realWhy}.` : ' Chạy lại với --real-model khi chủ dự án không dùng app.'}`); }
  } else {
    for (const t of realTargets.filter((x) => x.realWhy)) say(`– ${t.id}: chưa thể ✅ — ${t.realWhy}.`);
    const runnable = realTargets.filter((t) => !t.realWhy && t.ok);
    const wanted = [...new Set(runnable.flatMap((t) => t.modelIds))];
    if (!wanted.length) say('– không có tính năng nào đủ kịch bản model thật để chạy.');
    else if (!suitesOk) { for (const t of runnable) t.realSkipped = true; say('– bỏ qua: các bước trước đã đỏ, không tốn thời gian gọi model.'); }
    else {
      let tags = null;
      try {
        const res = await fetch(`${OLLAMA}/api/tags`, { signal: AbortSignal.timeout(2500) });
        tags = res.ok ? await res.json() : null;
      } catch { tags = null; }
      const names = tags && Array.isArray(tags.models) ? tags.models.map((m) => m.name) : [];
      if (!tags) {
        for (const t of runnable) t.realSkipped = true;
        say(`– Ollama không trả lời ở ${OLLAMA} — bỏ qua (cần model thật), chưa thể ✅. (Không tự bật Ollama, không tải model.)`);
        result.real_model = { ran: false, reason: 'ollama-unreachable' };
      } else if (!names.includes(CHAT_MODEL) && !names.includes(`${CHAT_MODEL}:latest`)) {
        for (const t of runnable) t.realSkipped = true;
        say(`– Ollama chưa có ${CHAT_MODEL} — bỏ qua, chưa thể ✅. (Không tự tải model: hỏi chủ dự án.)`);
        result.real_model = { ran: false, reason: 'model-missing' };
      } else {
        say(`… chạy ${path.relative(REPO, PY)} harness/run_eval.py --no-judge cho ${wanted.join(', ')} (vài phút, dùng chung GPU với app)`);
        const t0 = Date.now();
        const r = run(PY, ['harness/run_eval.py', '--model', CHAT_MODEL, '--no-judge', '--ollama-url', OLLAMA, ...wanted.flatMap((id) => ['--only', id])], { cwd: REPO, timeout: 60 * MIN });
        const secs = Math.round((Date.now() - t0) / 1000);
        const dir = ((r.out.match(/Đã ghi kết quả vào (.+)$/m) || [])[1] || '').trim();
        let per = new Map();
        try {
          const raw = JSON.parse(fs.readFileSync(path.join(dir, 'raw.json'), 'utf8'));
          for (const x of raw.results || []) per.set(x.id, x);
        } catch { per = new Map(); }
        tail(r.out, 8);
        const scen = Object.fromEntries(wanted.map((id) => {
          const x = per.get(id);
          const why = r.rc !== 0 ? `run_eval rc=${r.rc}` : !x ? 'không có trong kết quả' : x.error ? `lỗi sinh: ${String(x.error).slice(0, 80)}` : (x.problems || []).length ? (x.problems || []).slice(0, 2).join('; ') : '';
          return [id, why];
        }));
        result.real_model = { ran: true, rc: r.rc, scenarios: scen, results: dir ? path.relative(REPO, dir) : '', seconds: secs };
        for (const [id, why] of Object.entries(scen)) say(`${why ? '✗' : '✓'} model: ${id}${why ? ` — ${why}` : ''}`);
        for (const t of runnable) {
          const bad = t.modelIds.filter((id) => scen[id]);
          if (bad.length) fail(t, `model thật đỏ: ${bad.map((id) => `${id} (${scen[id]})`).join(' · ')}`);
        }
        fm('note', `verify --real-model: ${wanted.join(', ')} → ${Object.values(scen).some(Boolean) ? 'đỏ' : 'xanh'} (${result.real_model.results || 'không có thư mục kết quả'})`);
      }
    }
  }

  // ---------------------------------------------------------------- kết luận
  say();
  if (general.length) say(`Lỗi chung: ${general.join(' · ')}`);
  let waiting = 0;
  let red = !suitesOk;
  const logLines = [];
  for (const t of targets) {
    const rec = { id: t.id, title: t.title, ok: t.ok && suitesOk, reasons: [...t.reasons], real_model_skipped: t.realSkipped, promoted: false };
    result.targets.push(rec);
    const passingNow = Boolean(t.f && t.f.state === 'passing');
    if (t.ok && suitesOk && !t.realSkipped && !QUICK) {
      const p = fm('promote', t.id, '--gate');
      if (p.rc === 0) {
        rec.promoted = true;
        const link = t.f.page.replace(/^wiki\//, '');
        logLines.push(`- ${today()} · verify.sh: ${t.id} ✅ passing (${t.title}) · [${path.basename(link, '.md')}](${link})`);
        say(`✅ ${t.id} → passing`);
      } else { red = true; say(`✗ ${t.id}: không promote được — ${p.out.trim()}`); }
    } else if (t.ok && suitesOk && passingNow) {
      say(`✅ ${t.id} vẫn passing (lần chấm lại này xanh nhưng ${QUICK ? '--quick' : 'bỏ qua model thật'}: không cập nhật verified_at)`);
    } else if (t.ok && suitesOk) {
      waiting += 1;
      const why = [QUICK && 'chạy --quick (chưa chạy bộ test đầy đủ)', t.realSkipped && (t.realWhy || 'cần model thật (--real-model)')].filter(Boolean).join(' · ');
      say(`🟡 ${t.id} vẫn claimed: ${why}`);
    } else {
      red = true;
      if (passingNow) {
        if (!t.ok) {
          fm('demote', t.id, '--gate', t.reasons.join(' · '));
          result.regressions.push(t.id);
          say(`🔴 ${t.id} đang ✅ nhưng lần chấm này đỏ → hạ về ⏳: ${t.reasons.join(' · ')}`);
        } else say(`🔴 ${t.id} đang ✅; lần chấm này đỏ vì lỗi chung (${general.join(', ')}) — chưa hạ`);
        continue;
      }
      if (!t.countable) { say(`🔴 ${t.id}: ${t.reasons[0] || 'đỏ'}`); continue; }
      if (t.ok && infraOnly) { say(`🔴 ${t.id}: đỏ vì lỗi đồ nghề (${general.join(', ')}) — không tính lần đỏ`); continue; }
      const why = (t.reasons.length ? t.reasons : general).join(' · ');
      const n = Number(fm('fail', t.id, '--gate', why).out.trim()) || 0;
      rec.attempts = n;
      say(`🔴 ${t.id} đỏ (lần ${n}/3): ${why}`);
      if (n >= 3) {
        say(`   ⛔ ${t.id} đã đỏ ${n} lần → sổ đã tự chuyển ⛔ blocked. Dừng sửa mò.`);
        say('      Thêm một mục bài học vào cuối wiki/learned.md (Sai · Vì sao · Luật rút ra · Nguồn) và một dòng');
        say(`      "Câu hỏi cho PO: …" vào memory/po-questions.md. Chỉ PO mở lại: reopen ${t.id} "PO: …".`);
      }
    }
  }
  for (const t of watched) {
    if (t.ok) continue;
    red = true;
    fm('demote', t.id, '--gate', t.reasons.join(' · '));
    result.regressions.push(t.id);
    say(`🔴 ${t.id} đang ✅ nhưng test của nó đỏ (hồi quy) → hạ về ⏳: ${t.reasons.join(' · ')}`);
  }
  if (!red && watched.length) say(`✓ ${watched.length} tính năng ✅ không bị hồi quy`);
  if (logLines.length) fs.appendFileSync(LOG, `${logLines.join('\n')}\n`);
  result.ok = !red && !QUICK;
  result.waiting = waiting;
  fs.mkdirSync(REPORTS, { recursive: true });
  fs.writeFileSync(path.join(REPORTS, 'verify.json'), `${JSON.stringify(result, null, 2)}\n`);
  const after = JSON.parse(fs.readFileSync(FEATURES, 'utf8'));
  const cnt = (st) => after.filter((f) => f.stage !== 'planned' && f.state === st).length;
  const tally = `Sổ: ✅ ${cnt('passing')} · 🟡 ${cnt('claimed')} · ⏳ ${cnt('pending')} · ⛔ ${cnt('blocked')}`;
  if (red) {
    const onlyInfra = infraOnly && targets.every((t) => t.ok) && watched.every((t) => t.ok);
    console.log(`└─ 🔴 ĐỎ — chưa đạt${onlyInfra ? ' (chỉ vì lỗi đồ nghề: sửa máy rồi chạy lại, không tính lần đỏ)' : ': sửa đúng lỗi ở trên rồi chạy lại verify (tối đa 3 lần đỏ mỗi tính năng)'}. ${tally}`);
    process.exit(1);
  }
  if (QUICK) {
    console.log(`└─ 🟡 --quick: phần đã chạy xanh, nhưng chưa chạy bộ test đầy đủ — không có gì được ✅. Chạy lại không có --quick. ${tally}`);
    process.exit(3);
  }
  if (waiting) {
    console.log(`└─ 🟢 XANH nhưng ${waiting} tính năng còn 🟡 (cần model thật / kịch bản model thật) — chưa phải ✅. ${tally}`);
    process.exit(3);
  }
  console.log(`└─ 🟢 XANH — đạt${targets.length ? '' : ' (không có tính năng 🟡 để chấm; đã soát hồi quy)'}. ${tally}`);
  process.exit(0);
})().catch((e) => { console.error(`verify.sh lỗi nội bộ: ${e.stack || e}`); process.exit(1); });
EOF
