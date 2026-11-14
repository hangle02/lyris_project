#!/usr/bin/env node
// ② ENVIRONMENT — ghi lời chủ dự án vào wiki/raw/ mà KHÔNG BAO GIỜ sửa file cũ.
// Quyền Edit/Write vào wiki/raw/** bị chặn trong .claude/settings.json; /plan ghi lời gốc bằng lệnh này:
//   node environment/raw.mjs <chủ-đề-ngắn> "lời nguyên văn"
//   node environment/raw.mjs <chủ-đề-ngắn> < file.txt          (đọc từ stdin)
// Tạo wiki/raw/YYYY-MM-DD-<chủ-đề>.md với dòng "## YYYY-MM-DD HH:MM" rồi lời nguyên văn.
// File đã có thì tạo file mới có hậu tố -2, -3… (không ghi đè, không nối thêm vào file cũ).
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const HOME = process.env.LYRIS_HARNESS_HOME ? path.resolve(process.env.LYRIS_HARNESS_HOME) : ROOT;
const RAW = path.join(HOME, 'wiki', 'raw');
const [topic, ...rest] = process.argv.slice(2);
if (!topic) {
  console.error('Dùng: node environment/raw.mjs <chủ-đề-ngắn> "lời nguyên văn"   (hoặc đưa lời qua stdin)');
  process.exit(1);
}
const slug = topic.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D')
  .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60);
if (!slug) { console.error('Chủ đề phải có chữ hoặc số.'); process.exit(1); }
let text = rest.join(' ');
if (!text && !process.stdin.isTTY) text = readFileSync(0, 'utf8');
if (!text.trim()) { console.error('Thiếu lời nguyên văn.'); process.exit(1); }

const now = new Date();
const pad = (n) => String(n).padStart(2, '0');
const day = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
const stamp = `${day} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
mkdirSync(RAW, { recursive: true });
let file = path.join(RAW, `${day}-${slug}.md`);
for (let n = 2; existsSync(file); n += 1) file = path.join(RAW, `${day}-${slug}-${n}.md`);
writeFileSync(file, `## ${stamp}\n\n${text.replace(/\s+$/, '')}\n`, { flag: 'wx' });
console.log(`Đã ghi ${path.relative(HOME, file)} (file mới, không sửa file cũ).`);
