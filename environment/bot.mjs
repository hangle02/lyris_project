#!/usr/bin/env node
// ② ENVIRONMENT — bot tự mở Lyris trong Chrome, tự bấm như người dùng điện thoại, chụp ảnh từng bước rồi viết
// báo cáo. Đây là "mắt" của harness: Model không tự nhìn được giao diện, bot nhìn thay.
//
//   node environment/bot.mjs           → chạy kịch bản environment/e2e.mjs, ghi reports/latest/report.{json,html} + NN-*.png
//   node environment/bot.mjs --quiet   → chỉ in kết quả cuối (verify.sh dùng)
//   node environment/bot.mjs --look    → chỉ CHỤP các màn chính vào reports/look/ (Model mở ảnh bằng Read để tự nhìn)
//
// Bot tự bật hai server rồi tự tắt khi xong (kể cả khi lỗi):
//   - backend THẬT + LLM giả: backend/.venv/bin/python environment/fake-server.py  (cổng BOT_BACKEND_PORT=8066)
//     DB tạm ở reports/bot/, không bao giờ đụng data/ và không gọi Ollama.
//   - frontend: Vite dev (cổng BOT_FRONTEND_PORT=8067), proxy /api sang 8066.
// Cổng 8000/5173 (app người dùng đang chạy) không bao giờ bị đụng tới.
//
// Lỗi ĐỒ NGHỀ (cổng bận, thiếu Chrome/venv/node_modules, server không lên, Chrome chết giữa chừng, bot quá giờ) được
// ghi vào report.json là "infra" và thoát mã 2: verify.sh không tính đó là một lần đỏ của tính năng.
// Tiến trình con (server giả, Vite, Chrome) được ghi vào reports/.bot-pids.json; lần chạy sau tự dọn nếu lần trước
// bị giết ngang (kill -9) mà còn sót. Chỉ dọn đúng tiến trình bot đã ghi, sau khi đối chiếu dòng lệnh.
//
// Không cần cài gì thêm: điều khiển Chrome qua DevTools Protocol bằng WebSocket có sẵn của Node 22.
import { spawn, spawnSync } from 'node:child_process';
import { createWriteStream, existsSync, readFileSync, readdirSync, rmSync, statSync, unlinkSync, writeFileSync } from 'node:fs';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { connect as netConnect } from 'node:net';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const LOOK = process.argv.includes('--look');
const QUIET = process.argv.includes('--quiet');
const OUT = path.join(ROOT, 'reports', LOOK ? 'look' : 'latest');
// Cổng: biến môi trường > harness.config (BOT_BACKEND_PORT, BOT_FRONTEND_PORT) > mặc định 8066/8067.
const CONFIG = (() => {
  try {
    return Object.fromEntries(readFileSync(path.join(ROOT, 'harness.config'), 'utf8').split('\n')
      .map((l) => l.match(/^\s*([A-Z_]+)=["']?([^"'#\s]*)/)).filter(Boolean).map((m) => [m[1], m[2]]));
  } catch { return {}; }
})();
const BACKEND_PORT = Number(process.env.BOT_BACKEND_PORT ?? CONFIG.BOT_BACKEND_PORT ?? 8066);
const FRONTEND_PORT = Number(process.env.BOT_FRONTEND_PORT ?? CONFIG.BOT_FRONTEND_PORT ?? 8067);
const BASE = `http://127.0.0.1:${FRONTEND_PORT}/`;
const CREDS = { handle: process.env.BOT_HANDLE ?? 'chumay', password: process.env.BOT_PASSWORD ?? 'bot mat khau 2026' };
// Tài khoản thành viên thứ hai (fake-server.py tạo sẵn: chưa đặt profile, chưa có story).
const MEMBER = { handle: process.env.BOT_MEMBER_HANDLE ?? 'thanhvien', password: process.env.BOT_MEMBER_PASSWORD ?? 'bot mat khau 2026' };
const PYTHON = path.join(ROOT, 'backend', '.venv', 'bin', 'python');
const VITE = path.join(ROOT, 'frontend', 'node_modules', 'vite', 'bin', 'vite.js');
const PHONE = { width: 390, height: 844, deviceScaleFactor: 2, mobile: true };
const DESKTOP = { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false };
const log = (...a) => { if (!QUIET) console.log(...a); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const PIDFILE = path.join(ROOT, 'reports', '.bot-pids.json');
// Cả lượt chạy không được quá mức này (mặc định 15 phút): quá thì ghi báo cáo "infra" và tắt hết.
const RUN_TIMEOUT_MS = Number(process.env.BOT_TIMEOUT_MS || 15 * 60 * 1000);
// Một lệnh CDP (evaluate, chụp ảnh…) không được treo quá 60 giây.
const CDP_TIMEOUT_MS = 60 * 1000;
// Kịch bản: verify.sh chạy bot với --quiet → LUÔN là e2e.mjs, bỏ qua BOT_SCENARIO.
const SCENARIO = !QUIET && process.env.BOT_SCENARIO ? path.resolve(process.env.BOT_SCENARIO) : path.join(HERE, 'e2e.mjs');
const SCENARIO_REL = path.relative(ROOT, SCENARIO);

/** Lỗi của máy/đồ nghề, không phải của app. */
class InfraError extends Error {
  constructor(message) { super(message); this.infra = true; }
}

if ([BACKEND_PORT, FRONTEND_PORT].some((p) => p === 8000 || p === 5173)) {
  console.error('Bot không được dùng cổng 8000/5173 (app thật của người dùng). Dùng 8066-8069.');
  process.exit(2);
}

export function findChrome() {
  const candidates = [
    process.env.CHROME,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  ].filter(Boolean);
  const found = candidates.find((p) => existsSync(p));
  if (!found) throw new InfraError('Không tìm thấy Chrome. Cài Google Chrome hoặc đặt biến CHROME=/đường/dẫn/chrome');
  return found;
}

// ---------------------------------------------------------------- dọn đồ sót của lần chạy trước

const alive = (pid) => { try { process.kill(pid, 0); return true; } catch { return false; } };
const commandOf = (pid) => {
  const r = spawnSync('ps', ['-o', 'command=', '-p', String(pid)], { encoding: 'utf8' });
  return r.status === 0 ? r.stdout.trim() : '';
};
/** Ghi danh sách tiến trình con hiện tại (để lần sau dọn được nếu bot bị giết ngang). */
function writePidfile(extra = {}) {
  try {
    const procs = children.filter((p) => p.pid).map((p) => ({ pid: p.pid, group: Boolean(p.__group), hint: p.__hint }));
    writeFileSync(PIDFILE, JSON.stringify({ bot: process.pid, at: new Date().toISOString(), procs, ...extra }, null, 2));
  } catch { /* reports/ chưa có: bỏ qua */ }
}
/** Lần trước bot bị giết ngang: tắt đúng các tiến trình nó đã ghi (đối chiếu dòng lệnh để không giết nhầm). */
async function cleanStale() {
  let old = null;
  try { old = JSON.parse(readFileSync(PIDFILE, 'utf8')); } catch { return; }
  if (old.bot && old.bot !== process.pid && alive(old.bot) && /bot\.mjs/.test(commandOf(old.bot))) {
    throw new InfraError(`Một bot khác đang chạy (pid ${old.bot}). Chờ nó xong rồi chạy lại.`);
  }
  const killed = [];
  for (const p of old.procs || []) {
    if (!p.pid || !alive(p.pid) || !p.hint || !commandOf(p.pid).includes(p.hint)) continue;
    try { process.kill(p.group ? -p.pid : p.pid, 'SIGTERM'); killed.push(p.pid); } catch { /* đã tắt */ }
  }
  if (killed.length) {
    await sleep(1500);
    for (const pid of killed) if (alive(pid)) { try { process.kill(pid, 'SIGKILL'); } catch { /* đã tắt */ } }
    log(`Đã dọn ${killed.length} tiến trình sót của lần chạy bot trước (pid ${killed.join(', ')}).`);
  }
  if (old.profile && path.basename(old.profile).startsWith('lyris-bot-')) rmSync(old.profile, { recursive: true, force: true, maxRetries: 3 });
  try { unlinkSync(PIDFILE); } catch { /* đã xoá */ }
}
/** Thư mục profile Chrome tạm (lyris-bot-*) cũ hơn 2 giờ: chắc chắn không còn ai dùng. */
function cleanOldProfiles() {
  const dir = tmpdir();
  let n = 0;
  for (const name of readdirSync(dir)) {
    if (!name.startsWith('lyris-bot-')) continue;
    const p = path.join(dir, name);
    try {
      if (Date.now() - statSync(p).mtimeMs < 2 * 3600 * 1000) continue;
      rmSync(p, { recursive: true, force: true, maxRetries: 3 });
      n += 1;
    } catch { /* đang bị dùng / không quyền: bỏ qua */ }
  }
  if (n) log(`Đã xoá ${n} thư mục profile Chrome tạm cũ (lyris-bot-*).`);
}

// ---------------------------------------------------------------- server

/** Cổng có ai đang nghe không (không đụng vào tiến trình đó). */
function portBusy(port) {
  return new Promise((resolve) => {
    const s = netConnect({ port, host: '127.0.0.1' });
    s.once('connect', () => { s.destroy(); resolve(true); });
    s.once('error', () => resolve(false));
  });
}

async function waitHttp(url, label, proc, timeoutMs = 60000) {
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    if (proc.exitCode !== null) throw new InfraError(`${label} đã thoát (mã ${proc.exitCode}) — xem log trong ${OUT}`);
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(2000) });
      if (r.status < 500) return;
    } catch { /* chưa lên */ }
    await sleep(250);
  }
  throw new InfraError(`${label} không lên sau ${timeoutMs / 1000}s (${url})`);
}

const children = [];
/** Chạy tiến trình con trong nhóm riêng để tắt được cả cây (vite, uvicorn). Log vào OUT/<name>.log. */
function startChild(name, cmd, args, opts, hint) {
  const logFile = createWriteStream(path.join(OUT, `${name}.log`));
  const proc = spawn(cmd, args, { ...opts, detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
  proc.stdout.pipe(logFile);
  proc.stderr.pipe(logFile);
  proc.__group = true;
  proc.__hint = hint;
  children.push(proc);
  writePidfile();
  return proc;
}

const signal = (p, sig) => {
  if (p.exitCode !== null || p.signalCode !== null) return;
  try { process.kill(p.__group ? -p.pid : p.pid, sig); } catch { try { p.kill(sig); } catch { /* đã tắt */ } }
};
/** Tắt mọi tiến trình con ngay (đồng bộ — dùng lúc process 'exit'). */
function killAll() {
  for (const p of children.splice(0)) signal(p, 'SIGTERM');
}
/** Tắt mọi tiến trình con và CHỜ chúng thoát (tối đa 5 giây, rồi SIGKILL). */
async function stopAll() {
  const procs = children.splice(0);
  const exited = (p) => p.exitCode !== null || p.signalCode !== null;
  for (const p of procs) signal(p, 'SIGTERM');
  const until = Date.now() + 5000;
  while (Date.now() < until && !procs.every(exited)) await sleep(100);
  for (const p of procs) if (!exited(p)) signal(p, 'SIGKILL');
  await sleep(200);
}
let finishing = null; // hàm ghi báo cáo dở dang khi bị ngắt / quá giờ
for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, async () => {
    if (finishing) await finishing(`bot bị dừng (${sig})`).catch(() => {});
    await stopAll().catch(() => {});
    process.exit(130);
  });
}
process.on('exit', killAll);

async function startServers() {
  for (const port of [BACKEND_PORT, FRONTEND_PORT]) {
    if (await portBusy(port)) throw new InfraError(`Cổng ${port} đang bận. Tắt tiến trình đang dùng nó (lsof -nP -iTCP:${port}) rồi chạy lại.`);
  }
  if (!existsSync(PYTHON)) throw new InfraError(`Không thấy ${PYTHON}. Tạo môi trường backend: cd backend && uv sync`);
  if (!existsSync(VITE)) throw new InfraError(`Không thấy ${VITE}. Chạy: cd frontend && npm install`);
  const backend = startChild('backend', PYTHON, [path.join(HERE, 'fake-server.py')], {
    cwd: ROOT,
    env: { ...process.env, BOT_BACKEND_PORT: String(BACKEND_PORT), PYTHONDONTWRITEBYTECODE: '1' },
  }, 'fake-server.py');
  const frontend = startChild('frontend', process.execPath, [VITE, '--port', String(FRONTEND_PORT), '--strictPort', '--host', '127.0.0.1', '--clearScreen', 'false'], {
    cwd: path.join(ROOT, 'frontend'),
    env: { ...process.env, LYRIS_API_URL: `http://127.0.0.1:${BACKEND_PORT}`, BROWSER: 'none' },
  }, 'vite');
  await waitHttp(`http://127.0.0.1:${BACKEND_PORT}/api/auth/me`, 'Backend giả', backend);
  await waitHttp(BASE, 'Frontend (Vite)', frontend);
  log(`Server: backend giả :${BACKEND_PORT}, frontend :${FRONTEND_PORT}`);
}

// ---------------------------------------------------------------- Chrome

async function launchChrome() {
  const chromePath = findChrome();
  const profile = await mkdtemp(path.join(tmpdir(), 'lyris-bot-'));
  const proc = spawn(chromePath, [
    '--headless=new', '--disable-gpu', '--enable-unsafe-swiftshader', '--no-first-run', '--no-default-browser-check',
    '--hide-scrollbars', '--mute-audio', '--disable-extensions', '--lang=vi-VN',
    '--remote-debugging-port=0', `--user-data-dir=${profile}`, `--window-size=${PHONE.width},${PHONE.height}`, 'about:blank',
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  proc.__hint = profile; // dòng lệnh của Chrome có --user-data-dir=<profile>: đối chiếu khi dọn đồ sót
  children.push(proc);
  writePidfile({ profile });
  const wsUrl = await new Promise((resolve, reject) => {
    let buf = '';
    const timer = setTimeout(() => reject(new InfraError('Chrome không khởi động được sau 15 giây')), 15000);
    proc.once('exit', (code) => { clearTimeout(timer); reject(new InfraError(`Chrome thoát ngay khi mở (mã ${code})`)); });
    proc.stderr.on('data', (d) => {
      buf += d;
      const m = buf.match(/DevTools listening on (ws:\/\/\S+)/);
      if (m) { clearTimeout(timer); resolve(m[1]); }
    });
  });
  return { proc, profile, wsUrl };
}

/** Kết nối CDP tối giản: send(method, params) và nghe sự kiện. Chrome chết → mọi lệnh đang chờ báo lỗi ngay. */
async function connectCdp(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = () => j(new InfraError('Không kết nối được DevTools của Chrome')); });
  let id = 0;
  let closed = null;
  const pending = new Map();
  const listeners = [];
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject, timer } = pending.get(msg.id);
      clearTimeout(timer);
      pending.delete(msg.id);
      msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
    } else if (msg.method) listeners.forEach((fn) => fn(msg));
  };
  ws.onclose = () => {
    closed = new InfraError('Chrome đã tắt giữa chừng (mất kết nối DevTools)');
    for (const { reject, timer } of pending.values()) { clearTimeout(timer); reject(closed); }
    pending.clear();
  };
  const send = (method, params = {}, sessionId) =>
    new Promise((resolve, reject) => {
      if (closed) { reject(closed); return; }
      const msgId = ++id;
      const timer = setTimeout(() => {
        pending.delete(msgId);
        reject(new Error(`Chrome không trả lời ${method} sau ${CDP_TIMEOUT_MS / 1000}s`));
      }, CDP_TIMEOUT_MS);
      pending.set(msgId, { resolve, reject, timer });
      ws.send(JSON.stringify({ id: msgId, method, params, sessionId }));
    });
  return { send, on: (fn) => listeners.push(fn), close: () => ws.close(), closed: () => closed };
}

// Trợ lý trong trang: tìm phần tử theo vai trò / aria-label / chữ (như người dùng nhìn), chỉ lấy cái đang HIỆN.
const PAGE_HELPERS = `window.__bot = (() => {
  const norm = (s) => String(s ?? '').replace(/\\s+/g, ' ').trim();
  const visible = (el) => {
    if (!el || !el.isConnected) return false;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    for (let e = el; e; e = e.parentElement) {
      const s = getComputedStyle(e);
      if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) return false;
    }
    return true;
  };
  const CLICKABLE = 'button, a[href], [role=button], [role=radio], [role=switch], [role=menuitem], [role=tab], input, textarea, select, label';
  const all = (spec) => {
    if (typeof spec === 'string') spec = { css: spec };
    let roots = [document];
    if (spec.within) {
      roots = [...document.querySelectorAll(spec.within)].filter(visible);
      if (spec.withinLast) roots = roots.slice(-1);
    }
    let els;
    if (spec.field != null) {
      // Ô nhập theo NHÃN đang hiện (<label for>), như người dùng đọc: { field: 'Tên hiển thị' } (khớp phần đầu).
      els = roots.flatMap((r) => [...r.querySelectorAll('label')])
        .filter((l) => norm(l.innerText).startsWith(spec.field))
        .map((l) => l.control || l.querySelector('input, textarea, select'))
        .filter(Boolean);
    } else els = roots.flatMap((r) => [...r.querySelectorAll(spec.css || CLICKABLE)]);
    const label = (e) => norm(e.getAttribute('aria-label'));
    if (spec.label != null) els = els.filter((e) => label(e) === spec.label);
    if (spec.labelStarts != null) els = els.filter((e) => label(e).startsWith(spec.labelStarts));
    if (spec.labelEnds != null) els = els.filter((e) => label(e).endsWith(spec.labelEnds));
    if (spec.text != null) els = els.filter((e) => norm(e.innerText) === spec.text);
    if (spec.textHas != null) els = els.filter((e) => norm(e.innerText).includes(spec.textHas));
    if (spec.visible !== false) els = els.filter(visible);
    return els;
  };
  const find = (spec) => { const els = all(spec); return spec && spec.last ? els[els.length - 1] ?? null : els[0] ?? null; };
  const name = (el) => !el ? 'khoảng trống' : el.tagName.toLowerCase() + (el.getAttribute('aria-label') ? '[' + el.getAttribute('aria-label') + ']' : '') + (norm(el.innerText) ? ' "' + norm(el.innerText).slice(0, 30) + '"' : '');
  return { norm, visible, all, find, name };
})();`;

// ---------------------------------------------------------------- chạy

async function run() {
  await rm(OUT, { recursive: true, force: true });
  await mkdir(OUT, { recursive: true });
  const checks = [];
  const shots = [];
  let infra = '';
  let reported = false;
  const check = (name, ok, detail = '') => {
    if (reported) return; // báo cáo đã ghi (quá giờ / bị dừng): bỏ qua check đến muộn
    checks.push({ name, ok: !!ok, detail: String(detail ?? '') });
    log(`${ok ? '✓' : '✗'} ${name}${detail ? ` — ${detail}` : ''}`);
  };
  /** Ghi report.json/html đúng một lần (kể cả khi bị dừng giữa chừng). */
  const writeReport = async () => {
    if (reported) return checks.length > 0 && checks.every((c) => c.ok) && !infra;
    reported = true;
    const passed = checks.length > 0 && checks.every((c) => c.ok) && !infra;
    await writeFile(path.join(OUT, 'report.json'), JSON.stringify({ passed, look: LOOK, scenario: SCENARIO_REL, infra, checks, shots, at: new Date().toISOString() }, null, 2));
    await writeFile(path.join(OUT, 'report.html'), reportHtml(passed, checks, shots));
    return passed;
  };
  finishing = async (why) => {
    if (!infra) infra = why;
    check('Bot chạy hết kịch bản', false, why);
    await writeReport();
  };
  const watchdog = setTimeout(async () => {
    const limit = `${Math.round(RUN_TIMEOUT_MS / 1000)} giây`;
    console.error(`Bot chạy quá ${limit} — dừng.`);
    await finishing(`bot chạy quá ${limit} (treo?)`).catch(() => {});
    await stopAll().catch(() => {});
    if (chrome) rmSync(chrome.profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
    try { unlinkSync(PIDFILE); } catch { /* không có */ }
    process.exit(2);
  }, RUN_TIMEOUT_MS);

  let chrome = null;
  let cdp = null;
  try {
    await cleanStale();
    cleanOldProfiles();
    await startServers();
    chrome = await launchChrome();
    cdp = await connectCdp(chrome.wsUrl);
    const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
    const page = (m, p) => cdp.send(m, p, sessionId);

    // Lỗi trên trang: exception, console.error, và lỗi mạng/tài nguyên Chrome tự ghi (Log domain).
    const errors = [];
    let where = '';
    cdp.on((msg) => {
      if (msg.sessionId !== sessionId) return;
      if (msg.method === 'Runtime.exceptionThrown') {
        const d = msg.params.exceptionDetails;
        errors.push(`[${where}] ${d.exception?.description ?? d.text}`.slice(0, 300));
      }
      if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
        errors.push(`[${where}] ${msg.params.args.map((a) => a.value ?? a.description).join(' ')}`.slice(0, 300));
      }
      if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') {
        const e = msg.params.entry;
        errors.push(`[${where}] ${e.text}${e.url ? ` (${e.url.replace(BASE, '/')})` : ''}`.slice(0, 300));
      }
    });
    // Mọi request trang gửi đi (để soát "không gọi ra ngoài", "/api/system chỉ gọi khi mở Nâng cao"…).
    const requests = [];
    // Mọi hộp thoại của trình duyệt (confirm, beforeunload…): GHI LẠI để kịch bản kiểm được, rồi trả lời như người
    // dùng. Mặc định bấm OK; kịch bản đổi bằng c.answerDialogs(false) để thử nút Huỷ.
    const dialogs = [];
    let dialogAnswer = true;
    cdp.on((msg) => {
      if (msg.sessionId !== sessionId) return;
      if (msg.method === 'Network.requestWillBeSent') requests.push({ url: msg.params.request.url, method: msg.params.request.method, where, at: Date.now() });
      if (msg.method === 'Page.javascriptDialogOpening') {
        dialogs.push({ type: msg.params.type, message: msg.params.message, where, accepted: dialogAnswer, at: Date.now() });
        page('Page.handleJavaScriptDialog', { accept: dialogAnswer }).catch(() => {});
      }
    });
    await page('Runtime.enable');
    await page('Log.enable');
    await page('Network.enable');
    await page('Page.enable');
    await page('Page.addScriptToEvaluateOnNewDocument', { source: PAGE_HELPERS });
    // Tab đang ở trước và có focus: Chrome không hãm khung hình/cuộn mượt của tab nền.
    await page('Page.bringToFront').catch(() => {});
    await page('Emulation.setFocusEmulationEnabled', { enabled: true }).catch(() => {});

    // 'phone' (390), 'desktop' (1280) hoặc một cỡ riêng { width, height } (vd 800 cho lưới 3 cột).
    const viewport = async (kind) => page('Emulation.setDeviceMetricsOverride',
      typeof kind === 'object' ? { deviceScaleFactor: 1, mobile: false, height: 800, ...kind } : kind === 'desktop' ? DESKTOP : PHONE);
    await viewport('phone');

    const evaluate = async (expression) => {
      const r = await page('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
      return r.result.value;
    };
    const ensureHelpers = () => evaluate(`window.__bot ? true : (eval(${JSON.stringify(PAGE_HELPERS)}), true)`);

    /** Chờ biểu thức JS trong trang ra giá trị truthy; hết giờ thì ném lỗi có tên điều đang chờ. */
    const waitFor = async (expression, label = expression, timeout = 10000) => {
      const until = Date.now() + timeout;
      let last;
      while (Date.now() < until) {
        try { last = await evaluate(expression); if (last) return last; } catch (e) { if (e.infra) throw e; /* trang đang chuyển */ }
        await sleep(80);
      }
      throw new Error(`Hết ${timeout / 1000}s chờ: ${label}`);
    };

    const goto = async (hash, { reload = false } = {}) => {
      where = hash;
      if (reload) {
        // Page.navigate tới URL chỉ khác phần #hash là điều hướng TRONG trang (không tải lại). Qua about:blank
        // trước thì lần tải sau là tải thật một lần (localStorage, cookie vẫn giữ; URL như "#/signup?code=…"
        // được app đọc đúng một lần như người dùng mở link).
        await page('Page.navigate', { url: 'about:blank' });
        await waitFor('location.href === "about:blank"', 'trang trống', 10000);
        await page('Page.navigate', { url: BASE + hash });
        await waitFor('location.href.startsWith(' + JSON.stringify(BASE) + ') && document.readyState === "complete"', 'trang tải xong', 20000);
      } else {
        await evaluate(`location.hash = ${JSON.stringify(hash)}`);
        await waitFor(`location.hash === ${JSON.stringify(hash)}`, `địa chỉ ${hash}`);
      }
      await ensureHelpers();
      await sleep(150);
    };

    /** Chạm như NGÓN TAY vào giữa phần tử (không gọi el.click()): bị che thì báo lỗi, đúng như người dùng gặp. */
    const click = async (spec, desc = typeof spec === 'string' ? spec : JSON.stringify(spec)) => {
      await ensureHelpers();
      const hit = await evaluate(`(() => {
        const el = __bot.find(${JSON.stringify(spec)});
        if (!el) return { err: 'Không thấy ' + ${JSON.stringify(desc)} };
        el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
        const r = el.getBoundingClientRect(), x = r.x + r.width / 2, y = r.y + r.height / 2;
        const top = document.elementFromPoint(x, y);
        const label = top && top.closest('label');
        if (!top || !(el === top || el.contains(top) || (label && label.contains(el))))
          return { err: 'Chạm giữa ' + ${JSON.stringify(desc)} + ' nhưng trúng ' + __bot.name(top) + ' (bị che)' };
        return { x, y };
      })()`);
      if (hit.err) throw new Error(hit.err);
      await page('Input.dispatchMouseEvent', { type: 'mouseMoved', x: hit.x, y: hit.y });
      for (const type of ['mousePressed', 'mouseReleased']) {
        await page('Input.dispatchMouseEvent', { type, x: hit.x, y: hit.y, button: 'left', clickCount: 1 });
      }
      await sleep(120);
    };
    const tap = async (x, y) => {
      for (const type of ['mousePressed', 'mouseReleased']) await page('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: 1 });
      await sleep(120);
    };
    /** Gõ chữ vào ô đang focus (như bàn phím). */
    const type = async (text) => { await page('Input.insertText', { text }); await sleep(80); };
    const KEYS = { Escape: 27, Enter: 13, Tab: 9, Backspace: 8, ArrowDown: 40, ArrowUp: 38, Home: 36, End: 35 };
    const press = async (key) => {
      for (const t of ['keyDown', 'keyUp']) {
        await page('Input.dispatchKeyEvent', { type: t, key, code: key, windowsVirtualKeyCode: KEYS[key] ?? 0, nativeVirtualKeyCode: KEYS[key] ?? 0 });
      }
      await sleep(150);
    };
    const exists = (spec) => evaluate(`!!__bot.find(${JSON.stringify(spec)})`);
    /** Chạm vào ô, chọn hết chữ cũ rồi gõ đè (như người dùng bôi đen rồi gõ). */
    const fill = async (spec, text, desc) => {
      await click(spec, desc);
      await evaluate(`(() => { const el = __bot.find(${JSON.stringify(spec)}); el.focus(); el.select?.(); })()`);
      if (text === '') await press('Backspace');
      else await type(text);
    };
    /** Chọn file cho một <input type=file> (như hộp chọn file của hệ điều hành). */
    const setFiles = async (css, files) => {
      const r = await page('Runtime.evaluate', { expression: `document.querySelector(${JSON.stringify(css)})`, returnByValue: false });
      if (!r.result?.objectId) throw new Error(`Không thấy ô chọn file ${css}`);
      await page('DOM.setFileInputFiles', { files, objectId: r.result.objectId });
      await sleep(200);
    };

    const slug = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D')
      .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40);
    const shot = async (label) => {
      await sleep(250);
      // Ảnh đang hiện (lazy) tải xong rồi mới chụp, tối đa 3 giây.
      await waitFor('[...document.images].filter((i) => window.__bot?.visible(i)).every((i) => i.complete)', 'ảnh tải xong', 3000).catch(() => {});
      const { data } = await page('Page.captureScreenshot', { format: 'png' });
      const file = `${String(shots.length + 1).padStart(2, '0')}-${slug(label) || 'anh'}.png`;
      await writeFile(path.join(OUT, file), Buffer.from(data, 'base64'));
      shots.push({ file, label });
      return file;
    };
    /** Một bước của kịch bản: lỗi ở bước này ghi ✗ cho đúng check đó rồi chạy tiếp bước sau. */
    const step = async (name, fn) => {
      try {
        const r = await fn();
        if (r === undefined || r === true) check(name, true);
        else if (r === false) check(name, false);
        else check(name, !!r.ok, r.detail ?? '');
      } catch (e) {
        if (e.infra) throw e; // Chrome chết: dừng cả kịch bản, đó là lỗi đồ nghề chứ không phải của bước này
        check(name, false, e.message.split('\n')[0]);
        await shot(`LỖI ${name}`).catch(() => {});
      }
    };

    const ctx = {
      base: BASE, creds: CREDS, member: MEMBER, errors, requests, dialogs, out: OUT, evaluate, waitFor, goto, click, tap, type, press, exists,
      fill, setFiles, shot, check, step, sleep, viewport,
      setWhere: (w) => { where = w; },
      answerDialogs: (accept) => { dialogAnswer = Boolean(accept); },
    };
    // BOT_SCENARIO=<file.mjs>: chạy một kịch bản khác — chỉ để gỡ lỗi kịch bản bằng tay. Với --quiet (verify.sh)
    // biến này bị bỏ qua: kịch bản luôn là e2e.mjs, và report.json ghi rõ kịch bản đã chạy.
    if (SCENARIO_REL !== 'environment/e2e.mjs') console.log(`! Kịch bản gỡ lỗi: ${SCENARIO_REL} — báo cáo này không dùng làm bằng chứng cho verify.sh.`);
    const mod = await import(pathToFileURL(SCENARIO).href);
    if (LOOK) await mod.look(ctx);
    else await mod.play(ctx);
  } catch (e) {
    if (e.infra) infra = e.message.split('\n')[0];
    check('Bot chạy hết kịch bản', false, `${e.infra ? '(đồ nghề) ' : ''}${e.message.split('\n')[0]}`);
  } finally {
    clearTimeout(watchdog);
    try { cdp?.close(); } catch { /* đã đóng */ }
    await stopAll(); // chờ Chrome thoát hẳn rồi mới xoá profile (tránh xoá đua lúc Chrome còn ghi)
    if (chrome) await rm(chrome.profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }).catch(() => {});
    try { unlinkSync(PIDFILE); } catch { /* không có */ }
  }

  const passed = await writeReport();
  if (LOOK) {
    console.log(passed ? `📸 Đã chụp ${shots.length} ảnh vào ${OUT} — mở bằng Read để xem` : '🔴 --look gặp lỗi (xem report.json)');
  } else {
    const failed = checks.filter((c) => !c.ok).length;
    console.log(passed ? `🟢 Bot: ĐẠT (${checks.length} check)` : infra ? `🔴 Bot: KHÔNG CHẠY ĐƯỢC (đồ nghề): ${infra}` : `🔴 Bot: CHƯA ĐẠT (${failed}/${checks.length} check đỏ)`);
    if (QUIET && !passed) for (const c of checks.filter((x) => !x.ok)) console.log(`✗ ${c.name}${c.detail ? ` — ${c.detail}` : ''}`);
  }
  if (!QUIET) console.log(`Báo cáo: ${path.join(OUT, 'report.html')}`);
  return passed ? 0 : infra ? 2 : 1;
}

function reportHtml(passed, checks, shots) {
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  return `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Báo cáo bot Lyris</title>
<style>body{font:15px/1.5 system-ui;margin:24px;background:#F6F1E7;color:#1D1B26}h1{margin:0 0 4px}.ok{color:#0F7A70}.no{color:#B23A2A}
ul{padding-left:20px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-top:16px}
figure{margin:0;background:#fff;border-radius:12px;padding:8px}img{width:100%;border-radius:8px}figcaption{font-size:13px;margin-top:6px}</style>
<h1 class="${passed ? 'ok' : 'no'}">${passed ? '🟢 ĐẠT' : '🔴 CHƯA ĐẠT'}</h1><p>${esc(new Date().toLocaleString('vi-VN'))}</p>
<ul>${checks.map((c) => `<li class="${c.ok ? 'ok' : 'no'}">${c.ok ? '✓' : '✗'} ${esc(c.name)}${c.detail ? ` — ${esc(c.detail)}` : ''}</li>`).join('')}</ul>
<div class="grid">${shots.map((s) => `<figure><a href="${s.file}"><img src="${s.file}" loading="lazy"></a><figcaption>${esc(s.file)} · ${esc(s.label)}</figcaption></figure>`).join('')}</div>`;
}

const code = await run();
await sleep(300); // để log của server ghi nốt
process.exit(code);
