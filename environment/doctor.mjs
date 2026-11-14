#!/usr/bin/env node
// ② ENVIRONMENT — KIỂM TRA MÁY: đủ đồ nghề để harness của Lyris chạy chưa?
// Chạy tự động khi mở dự án trong Claude Code (hook SessionStart, chế độ --hook), và gõ tay được:
//   node environment/doctor.mjs          → in từng dòng ✓ / ! / ✗ kèm cách sửa
//   node environment/doctor.mjs --hook   → im lặng khi ổn; có vấn đề thì in JSON ngắn cho Claude báo người dùng
//   node environment/doctor.mjs --ollama → thêm: HỎI Ollama danh sách model (GET /api/tags, 2 giây), không nạp model
// Không cài gì, không sửa gì. Mặc định (và luôn luôn ở --hook) KHÔNG gọi Ollama: luật "không gọi Ollama trừ
// verify.sh --real-model" (environment/rules.md). Chỉ hỏi khi người dùng gõ --ollama.
import { spawnSync } from 'node:child_process';
import { accessSync, constants, existsSync, mkdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const HOOK = process.argv.includes('--hook');
const ASK_OLLAMA = process.argv.includes('--ollama') && !HOOK;
const checks = [];
const add = (level, name, fix = "", hookQuiet = false) => checks.push({ level, name, fix, hookQuiet }); // level: ok | warn | fail · hookQuiet: không nhắc ở --hook

// Cấu hình harness (cổng bot) từ harness.config.
const cfg = {};
try {
  for (const line of readFileSync(path.join(ROOT, 'harness.config'), 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Z_]+)=("?)([^"#\s]*)\2/);
    if (m) cfg[m[1]] = m[3];
  }
} catch { add('fail', 'Thiếu harness.config ở thư mục gốc', 'Tạo lại harness.config (STACK=fullstack, BOT_BACKEND_PORT=8066, BOT_FRONTEND_PORT=8067).'); }
const BACKEND = path.join(ROOT, cfg.BACKEND_DIR || 'backend');
const FRONTEND = path.join(ROOT, cfg.FRONTEND_DIR || 'frontend');

// 1) Node 22+: bot điều khiển Chrome bằng WebSocket có sẵn từ Node 22; frontend test dùng --experimental-strip-types.
const major = Number(process.versions.node.split('.')[0]);
if (major >= 22) add('ok', `Node.js ${process.versions.node}`);
else add('fail', `Node.js ${process.versions.node} quá cũ (cần ≥ 22)`, 'Cài Node.js 22 LTS rồi mở lại Claude.');

// 2) Trình duyệt cho bot.
const browsers = [
  process.env.CHROME,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser',
].filter(Boolean);
const browser = browsers.find((p) => existsSync(p));
if (browser) add('ok', `Trình duyệt cho bot: ${path.basename(browser)}`);
else add('fail', 'Không tìm thấy Google Chrome cho bot', 'Cài Google Chrome, hoặc đặt biến CHROME=/đường/dẫn/chrome.');

// 3) Python của backend (chỉ dùng backend/.venv, không bao giờ python3 của hệ thống).
const py = path.join(BACKEND, '.venv', 'bin', 'python');
if (!existsSync(py)) add('fail', 'Thiếu backend/.venv', 'cd backend && uv sync   (tạo môi trường Python 3.12 cho backend)');
else {
  const v = spawnSync(py, ['--version'], { encoding: 'utf8' });
  const ver = `${v.stdout || ''}${v.stderr || ''}`.trim();
  if (/^Python 3\.12\./.test(ver)) add('ok', `backend/.venv: ${ver}`);
  else add('fail', `backend/.venv là ${ver || 'không chạy được'} (cần Python 3.12)`, 'cd backend && uv sync --python 3.12');
  if (!existsSync(path.join(BACKEND, '.venv', 'bin', 'pytest'))) add('fail', 'backend/.venv thiếu pytest', 'cd backend && uv sync   (nhóm dev có pytest)');
}

// 4) uv (tuỳ chọn: chỉ cần khi tạo lại backend/.venv).
const uv = spawnSync('uv', ['--version'], { encoding: 'utf8' });
if (uv.status === 0) add('ok', `${uv.stdout.trim()}`);
else add('warn', 'Không có uv (chỉ cần khi tạo lại backend/.venv)', 'brew install uv', true);

// 5) Thư viện frontend.
if (existsSync(path.join(FRONTEND, 'node_modules'))) add('ok', 'frontend/node_modules có sẵn');
else add('fail', 'Thiếu frontend/node_modules', 'cd frontend && npm install   (chỉ cài đúng package.json, không thêm thư viện mới)');

// 6) Ghi được reports/ (bot ghi ảnh, verify ghi verify.json).
try { mkdirSync(path.join(ROOT, 'reports'), { recursive: true }); accessSync(path.join(ROOT, 'reports'), constants.W_OK); add('ok', 'Ghi được vào reports/'); }
catch { add('fail', 'Không ghi được vào reports/', 'Kiểm quyền thư mục dự án.'); }

// 7) Cổng của bot và server test (8066–8069) phải trống. 8000/5173 là app của chủ dự án: không đụng, không kiểm.
const busy = [];
for (const port of [Number(cfg.BOT_BACKEND_PORT || 8066), Number(cfg.BOT_FRONTEND_PORT || 8067), 8068, 8069]) {
  const r = spawnSync('lsof', ['-nP', `-iTCP:${port}`, '-sTCP:LISTEN', '-t'], { encoding: 'utf8' });
  if (r.status === 0 && r.stdout.trim()) busy.push(`${port} (pid ${r.stdout.trim().split('\n').join(',')})`);
}
if (!busy.length) add('ok', 'Cổng bot 8066–8069 đang trống');
else add('warn', `Cổng bot đang bị chiếm: ${busy.join(', ')}`, 'Có thể là bot/server test lần trước chưa tắt. Tắt đúng tiến trình đó (không đụng cổng 8000/5173 của app).');

// 8) Ollama + gemma4:12b — chỉ lưu ý: verify thường chạy trên LLM giả; chỉ --real-model mới cần.
const OLLAMA = (process.env.OLLAMA_URL || 'http://127.0.0.1:11434').replace(/\/$/, '');
const CHAT_MODEL = process.env.LYRIS_CHAT_MODEL || 'gemma4:12b';
if (!ASK_OLLAMA) {
  add('ok', `Ollama: không kiểm (không gọi Ollama khi không cần). Muốn kiểm: node environment/doctor.mjs --ollama`);
} else try {
  const res = await fetch(`${OLLAMA}/api/tags`, { signal: AbortSignal.timeout(2000) });
  const names = res.ok ? ((await res.json()).models || []).map((m) => m.name) : [];
  if (!res.ok) add('warn', `Ollama trả HTTP ${res.status}`, 'Chỉ cần cho verify.sh --real-model và app thật.', true);
  else if (names.includes(CHAT_MODEL) || names.includes(`${CHAT_MODEL}:latest`)) add('ok', `Ollama có ${CHAT_MODEL}`);
  else add('warn', `Ollama chưa có ${CHAT_MODEL}`, 'Không tự tải model. Hỏi chủ dự án (ollama pull do chủ dự án làm).', true);
} catch {
  add('warn', `Ollama không trả lời ở ${OLLAMA}`, 'Không sao: test và bot dùng LLM giả. Chỉ verify.sh --real-model và app thật mới cần Ollama.', true);
}

const bad = checks.filter((c) => c.level !== 'ok');
if (HOOK) {
  // Hook SessionStart: chỉ lên tiếng khi có vấn đề cần sửa (Ollama tắt, thiếu uv: không nhắc), ngắn gọn.
  const loud = bad.filter((c) => !c.hookQuiet);
  if (loud.length) {
    const text = 'KIỂM TRA MÁY (environment/doctor.mjs): '
      + loud.map((c) => `${c.level === "fail" ? "LỖI" : "lưu ý"} — ${c.name}${c.fix ? ` (sửa: ${c.fix})` : ''}`).join('; ')
      + (loud.some((c) => c.level === "fail") ? '. Báo người dùng bằng lời đơn giản trước khi build.' : '.');
    console.log(JSON.stringify({ hookSpecificOutput: { hookEventName: 'SessionStart', additionalContext: text } }));
  }
  process.exit(0);
}
for (const c of checks) console.log(`${c.level === 'ok' ? '✓' : c.level === 'warn' ? '!' : '✗'} ${c.name}${c.fix && c.level !== 'ok' ? `\n    → ${c.fix}` : ''}`);
const failed = checks.some((c) => c.level === 'fail');
console.log(failed ? '\n🔴 Máy chưa sẵn sàng: sửa các dòng ✗ ở trên.' : '\n🟢 Máy sẵn sàng.');
process.exit(failed ? 1 : 0);
