// Kịch bản của bot (environment/bot.mjs) cho Lyris — bấm như người dùng điện thoại 390×844.
//
// Tên mỗi check là "bot: …" và PHẢI giữ nguyên: trang wiki/features/F<NN>-*.md tham chiếu đúng chuỗi này trong
// mục "## Tests" (verify.sh đối chiếu). Đổi tên check = đổi luôn trang wiki.
// Chỉ tìm phần tử như người dùng thấy: vai trò, aria-label, chữ trên nút, nhãn của ô. Không gọi el.click().
// Dữ liệu dựng sẵn (DB tạm của fake-server.py): chủ máy @chumay, thành viên @thanhvien (chưa đặt profile), nhân
// vật mẫu và nhân vật seed của chủ máy kèm một story mặc định. Mọi thứ khác bot tự tạo qua giao diện.
//
// Ngữ cảnh `c` (bot.mjs đưa vào): goto(hash), click(spec), type(text), fill(spec, text), press(key), setFiles(css, files),
// waitFor(js, nhãn, ms), evaluate(js), exists(spec), shot(nhãn), step(tên, fn), check(tên, ok, chi tiết),
// viewport('phone'|'desktop'|{width}), errors (lỗi console), requests (mọi request), creds/member {handle, password}.
// spec của click/exists: chuỗi CSS, hoặc { css, field, label, labelStarts, labelEnds, text, textHas, within, withinLast, last, visible }.
import { writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// Ảnh thật có sẵn trong repo (ảnh nhân vật mẫu) để bot tải lên như người dùng chọn file.
const PHOTO_A = path.join(REPO, 'backend', 'lyris', 'seed', 'templates', 'tran-minh-khang.jpg');
const PHOTO_B = path.join(REPO, 'backend', 'lyris', 'seed', 'templates', 'ta-van-lan.jpg');

const C = {
  LOGIN: 'bot: trang đăng nhập hiện và đăng nhập được',
  LEGAL: 'bot: trang pháp lý mở được khi chưa đăng nhập',
  EXPLORE: 'bot: Khám phá tải xong, thẻ đều nhau, không tràn ngang 390px',
  FEATURED: 'bot: nhân vật nổi bật không lặp trong lưới',
  PROFILE: 'bot: hồ sơ nhân vật chỉ đọc, có nút Bước vào câu chuyện',
  START: 'bot: bắt đầu story qua sheet và persona, story mở với lời chào',
  PLAYER: 'bot: lượt người chơi có lời nói và hành động không bị bọc ngoặc kép ngoài',
  STREAM: 'bot: lời trả lời stream, chấm đang gõ rồi tới chữ',
  THOUGHT: 'bot: thẻ suy nghĩ bị làm mờ, chạm thì hiện',
  THOUGHTS_OFF: 'bot: tắt Đọc suy nghĩ thì ẩn suy nghĩ',
  REGEN: 'bot: tạo lại ra phiên bản mới',
  SUGGEST: 'bot: menu cộng, Nhận gợi ý hiện gợi ý',
  HEART: 'bot: ngăn trái tim mở với 6 cảm xúc',
  DM: 'bot: chuyển sang DM rồi quay lại Story',
  REPORT: 'bot: sheet báo cáo mở trên một lời trả lời',
  ACCOUNT: 'bot: sheet tài khoản có quyền riêng tư, chia sẻ dữ liệu, xuất, xoá tài khoản',
  ADMIN: 'bot: trang quản trị của chủ máy có tài khoản, mã mời, Số liệu',
  DESKTOP: 'bot: màn desktop 1280px không tràn ngang',
  CONSOLE: 'bot: không có lỗi console',
  TECH: 'bot: không lộ chữ kỹ thuật trên các trang',
  // --- F01 Story
  STOP: 'bot: đang sinh có nút Dừng',
  REPLY_BLOCKS: 'bot: lượt nhân vật có thẻ thoại, thẻ suy nghĩ, dẫn truyện nghiêng',
  WAIT_DOTS: 'bot: lúc chờ chỉ có ba chấm, không có chữ',
  // --- F02 DM
  DM_LOOK: 'bot: DM có avatar, chân Đã gửi/Đã xem, bong bóng ba chấm',
  DM_OTHER: 'bot: lượt mode kia thành một dòng nhãn',
  // --- F03, F04, F05, F06
  SETTINGS: 'bot: Thiết lập story có đủ ô, Xoá story hỏi lại',
  PLACEHOLDER: 'bot: placeholder ô nhập và lượt người chơi căn phải',
  DIRECTIVE: 'bot: chỉ đạo ((...)) hiện thành chip',
  ACTIONS: 'bot: hàng thao tác có Thích, Chê, Sửa, Xoá từ đây hỏi lại',
  LOCKED: 'bot: đang trả lời thì Sửa và Xoá từ đây bị khoá, có lý do (title)',
  // --- F07, F08 suy nghĩ
  DM_THOUGHT: 'bot: DM có thẻ suy nghĩ thu gọn',
  ALWAYS: 'bot: Luôn hiện suy nghĩ bỏ làm mờ',
  THOUGHT_STYLE: 'bot: đổi kiểu suy nghĩ ở menu Suy nghĩ',
  TEST_THOUGHT: 'bot: chat thử ở Studio vẫn có suy nghĩ',
  THOUGHT_SWITCHES: 'bot: Đọc suy nghĩ có ở header, sheet bắt đầu, Thiết lập story',
  // --- F09, F10, F11 ngăn trái tim và sự kiện
  HEART_DIRECTIVE: 'bot: ngăn trái tim có Chỉ dẫn diễn xuất và phần trăm',
  HEART_MEMORY: 'bot: ngăn trái tim có ký ức và nút Quên, header có cảnh',
  TIMELINE_JUMP: 'bot: chạm mục dòng thời gian thì nhảy tới lượt',
  EVENTS: 'bot: menu cộng mở sheet Sự kiện',
  // --- F15, F16 gợi ý và menu "+"
  SUGGEST_TAP: 'bot: chờ gợi ý có Huỷ gợi ý, chạm thẻ là gửi',
  MENU_IMAGE: 'bot: Gửi hình ảnh bị khoá, Sắp có',
  MENU_KEYS: 'bot: menu cộng đi bằng phím, Esc trả focus',
  MENU_SIZE: 'bot: nút Thêm 44px, sheet ở điện thoại, popover ở máy tính',
  // --- F17 sổ thế giới
  LORE_TEASER: 'bot: hồ sơ có phần Thế giới chỉ có tên',
  LORE_UNLOCK: 'bot: nhắc từ khoá thì mục thế giới mở khoá',
  LORE_WORDS: 'bot: sổ thế giới không có chữ lore, keys, token',
  LORE_ADD: 'bot: thêm mục thế giới lưu ngay',
  // --- F18, F19, F20 Studio
  TEST_CHAT: 'bot: chat thử có ba chấm rồi trả lời',
  SIGNATURE: 'bot: lời nói đặc trưng quá 3 dòng bị chặn',
  STUDIO_SAVE: 'bot: sửa và lưu nhân vật ở Studio',
  LEAVE_GUARD: 'bot: rời trình sửa còn thay đổi chưa lưu thì hỏi lại',
  NO_PREVIEW: 'bot: tắt công cụ nâng cao thì trình sửa không có Xem trước',
  DRAFT: 'bot: AI viết nháp mở hộp ý tưởng, lỗi không có chữ kỹ thuật',
  DRAFT_OPEN: 'bot: AI viết nháp xong thì mở trình sửa với card nháp, chưa lưu',
  IMPORT: 'bot: nhập card .json mở trình sửa',
  // --- F21 persona
  PERSONA_ADD: 'bot: thêm persona',
  PERSONA_DEFAULT: 'bot: đổi persona mặc định ở sheet Tài khoản',
  // --- F22, F23, F24, F25 khám phá, hồ sơ, bắt đầu, hub
  VIBE: 'bot: chip cảm xúc chỉ giữ nhân vật có tag đó, bấm lại thì lưới như cũ',
  GRID: 'bot: lưới Khám phá 2/3/5 cột',
  TEMPLATE_PROFILE: 'bot: hồ sơ mẫu không có Sửa nhân vật, có thanh dính đáy',
  CONTINUE_BAR: 'bot: đã có story thì thanh dính đáy của hồ sơ có Tiếp tục story',
  NOT_FOUND: 'bot: nhân vật không có thì báo không tìm thấy',
  LEGACY: 'bot: link new-story cũ chuyển sang hồ sơ',
  COPY_NOTE: 'bot: nhân vật công khai có dòng bản sao',
  START_DEFAULT: 'bot: sheet bắt đầu chọn sẵn persona mặc định, Tuỳ chỉnh gập',
  HUB_SEARCH: 'bot: Tìm story lọc danh sách, xem trước sạch',
  HUB_EMPTY: 'bot: hub rỗng có Mở Khám phá, khối mời đặt profile',
  LOGIN_HUB: 'bot: đăng nhập ở #/login thì vào Tương tác, không tự mở story',
  // --- F26, F27 giao diện, ẩn chữ kỹ thuật
  SIZE390: 'bot: 390px không tràn ngang, nút header và thanh tab ≥ 44px ở #/, #/studio, #/chat',
  TAP_ROW: 'bot: 390px nút dưới lượt chat và nút hộp Xác nhận xoá ≥ 44px',
  NO_EXTERNAL: 'bot: không có request ra ngoài',
  THEME: 'bot: nút đổi theme và nhớ lựa chọn',
  TABBAR: 'bot: thanh tab 3 tab, ẩn ở màn con',
  ADVANCED_FOLD: 'bot: Nâng cao gập, /api/system chỉ gọi khi mở',
  ADVANCED_TOOLS: 'bot: công tắc Công cụ nâng cao',
  ABOUT: 'bot: trang giới thiệu có nguồn ảnh',
  // --- F28, F29, F30, F31, F35 tài khoản
  ME: 'bot: #/me có số liệu và hai tab',
  EDIT_PROFILE: 'bot: Sửa profile đổi tên ngay, handle sai báo dưới ô',
  PUBLIC_PROFILE: 'bot: profile công khai theo handle',
  REDIRECT: 'bot: chưa đăng nhập thì sang login rồi quay lại',
  INVITE_LINK: 'bot: link mời điền mã và bỏ mã khỏi URL',
  SIGNOUT: 'bot: sheet Tài khoản có đổi mật khẩu và đăng xuất',
  INVITE: 'bot: chủ máy tạo mã mời',
  MEMBER_ADMIN: 'bot: thành viên mở #/admin thì về hub',
  SHARE: 'bot: công tắc Công khai trong phần Cơ bản, mẫu không có, lưu thì có Người khác thấy gì',
  SHARED: 'bot: tài khoản khác thấy nhân vật được chia sẻ',
  ADMIN_REPORTS: 'bot: chủ máy có mục Báo cáo',
  // --- ý của wiki cũ được đưa lại (2026-11-14): F03, F10, F18, F22, F24, F26, F28
  MODEL_ADVANCED: 'bot: chọn model của story chỉ có trong Nâng cao của Thiết lập story, chỉ chủ máy thấy',
  SUMMARY_DETAILS: 'bot: story dài (cửa sổ đã dịch) có Tóm tắt những lượt cũ trong ngăn trái tim',
  AVATAR_EVERYWHERE: 'bot: avatar tải lên ở Studio hiện ở Studio, Khám phá, hồ sơ và chat',
  TEST_PERSONA: 'bot: chat thử ở Studio dùng persona mặc định',
  FEATURED_START: 'bot: khung nổi bật có ảnh, nút Bước vào câu chuyện mở hồ sơ kèm sheet Chọn persona',
  PERSONA_RADIO: 'bot: danh sách persona trong sheet bắt đầu là radio thật, mỗi persona có avatar',
  PERSONA_FORM_OPEN: 'bot: chưa có persona thì sheet bắt đầu tự mở form Tạo persona mới',
  FONTS_VI: 'bot: chữ tiếng Việt có dấu vẽ bằng đúng ba font tự host, không rơi về font dự phòng',
  EDIT_PROFILE_MEDIA: 'bot: Sửa profile đổi giới thiệu, ảnh đại diện, ảnh bìa và #/me hiện đủ',
};
export const CHECKS = Object.values(C);

// Chữ kỹ thuật không được lộ ra giao diện (memory: hide-technical-ui) — trừ phần "Nâng cao" đang đóng.
const TECH_WORDS = /\b(ollama|tokens?|tok\/s|gemma[\w.:-]*|qwen[\w.:-]*|llama[\w.:-]*|num_ctx|kv cache|credits?|model)\b/i;
const QUOTES = /^["“”«»„'‘’]|["“”«»„'‘’]$/;
const J = JSON.stringify;

/** Văn bản đang hiện trên trang (innerText bỏ phần display:none). */
const pageText = (c) => c.evaluate('document.body.innerText');
const overflowX = (c) => c.evaluate('document.documentElement.scrollWidth - window.innerWidth');
const hashNow = (c) => c.evaluate('location.hash');
const dialogTitled = (title) => `!!__bot.find({ css: '[role=dialog] h2, [role=dialog] [id]', text: ${J(title)} })`;

/** Điền form đăng nhập đang mở rồi bấm Đăng nhập. */
async function submitLogin(c, who) {
  await c.waitFor('!!document.querySelector("input[autocomplete=username]")', 'ô Tên đăng nhập', 20000);
  await c.fill('input[autocomplete=username]', who.handle, 'ô Tên đăng nhập');
  await c.fill('input[autocomplete=current-password]', who.password, 'ô Mật khẩu');
  await c.click({ css: 'button[type=submit]', text: 'Đăng nhập' }, 'nút Đăng nhập');
}

/** Đóng mọi sheet/menu đang mở (Esc như người dùng), để lần chạm sau không trúng lớp phủ. */
async function closeOverlays(c) {
  for (let i = 0; i < 4; i++) {
    const open = await c.evaluate(`!!document.querySelector('[role=dialog], [role=menu], [role=alertdialog]')`);
    if (!open) return;
    await c.evaluate(`document.querySelector('[role=menu] [role=menuitem]')?.focus()`);
    await c.press('Escape');
    await c.sleep(250);
  }
}

/** Đóng menu "+" bằng Esc khi focus đang ở trong menu (như người dùng), rồi chờ menu biến mất. */
async function closeMenu(c) {
  await c.waitFor(`document.activeElement?.getAttribute('role') === 'menuitem'`, 'focus trong menu', 2000).catch(() => {});
  await c.press('Escape');
  await c.waitFor(`!document.querySelector('[role=menu]')`, 'menu đóng', 3000).catch(() => {});
  await closeOverlays(c);
}

async function openAccountSheet(c) {
  await closeOverlays(c);
  await c.click({ labelEnds: 'Mở tài khoản' }, 'nút tài khoản');
  await c.waitFor(dialogTitled('Tài khoản'), 'sheet Tài khoản');
  await c.sleep(400);
}

/** Mở "Nâng cao" trong sheet Tài khoản (nếu đang gập). */
async function openAdvanced(c) {
  const btn = { within: '[role=dialog]', css: 'button[aria-expanded]', textHas: 'Nâng cao' };
  if (await c.evaluate(`__bot.find(${J(btn)})?.getAttribute('aria-expanded') === 'false'`)) await c.click(btn, 'mục Nâng cao');
  await c.waitFor(`!!__bot.find({ within: '[role=dialog]', css: '[role=switch]', textHas: 'Công cụ nâng cao' })`, 'công tắc Công cụ nâng cao');
}

/** Bật/tắt "Công cụ nâng cao" từ sheet Tài khoản ở hub. */
async function setAdvancedTools(c, on) {
  await c.goto('#/');
  await openAccountSheet(c);
  await openAdvanced(c);
  const sw = { within: '[role=dialog]', css: '[role=switch]', textHas: 'Công cụ nâng cao' };
  if ((await c.evaluate(`__bot.find(${J(sw)}).getAttribute('aria-checked')`)) !== String(on)) await c.click(sw, 'công tắc Công cụ nâng cao');
  await c.waitFor(`__bot.find(${J(sw)}).getAttribute('aria-checked') === ${J(String(on))}`, 'công tắc đổi');
  await c.press('Escape');
}

/** Trình sửa nhân vật ở điện thoại: về tab "Hồ sơ" (form) nếu đang ở "Chat thử". */
async function showFormTab(c) {
  const tab = { within: '[role=tablist][aria-label="Phần của trình sửa"]', css: '[role=tab]', text: 'Hồ sơ' };
  await c.waitFor(`!!__bot.find(${J(tab)})`, 'tab Hồ sơ', 15000);
  if ((await c.evaluate(`__bot.find(${J(tab)}).getAttribute('aria-selected')`)) !== 'true') await c.click(tab, 'tab Hồ sơ');
}

/**
 * Ô chọn file (ẩn) mà nút `spec` mở — người dùng chạm nút rồi chọn ảnh. Đánh dấu ô gần nút nhất để
 * setFiles (hộp chọn file của hệ điều hành) đổ ảnh vào đúng ô đó.
 */
async function fileInputBeside(c, spec, mark) {
  const ok = await c.evaluate(`(() => {
    const b = __bot.find(${J(spec)});
    for (let e = b?.parentElement; e; e = e.parentElement) {
      const input = e.querySelector('input[type=file]');
      if (input) { input.setAttribute('data-bot-file', ${J(mark)}); return true; }
    }
    return false;
  })()`);
  if (!ok) throw new Error(`không thấy ô chọn ảnh của nút ${J(spec)}`);
  return `input[data-bot-file="${mark}"]`;
}

/** Số ảnh đang hiện có src chứa `part` và đã tải được (naturalWidth > 0); chờ tối đa `timeout`, 0 nếu không có. */
const imageShown = (c, part, label, timeout = 10000) => c.waitFor(`(() => {
  const imgs = [...document.images].filter((i) => (i.getAttribute('src') || '').includes(${J(part)}) && __bot.visible(i));
  imgs.find((i) => !i.complete)?.scrollIntoView({ block: 'center', behavior: 'instant' });
  return imgs.filter((i) => i.complete && i.naturalWidth > 0).length;
})()`, label, timeout).catch(() => 0);

/** Lượt nhân vật cuối cùng đang hiện trong Story. */
const LAST_REPLY = 'article[aria-label^="Lượt của "]:not([aria-label="Lượt của bạn"])';
const lastReplySel = { within: LAST_REPLY, withinLast: true };
const STORY_INPUT = { css: 'textarea', labelStarts: 'Lượt của bạn' };

async function waitReplyDone(c, timeout = 40000) {
  await c.waitFor('!__bot.find({ label: "Dừng" }) && !!__bot.find({ label: "Gửi (Enter)" })', 'nhân vật trả lời xong', timeout);
  await c.sleep(300);
}

/**
 * Theo dõi từng khung hình trong lúc chờ trả lời (Story hoặc DM): khi nào có chấm đang gõ, chữ đầu tiên, nút Dừng,
 * nút Sửa/Xoá có bị khoá không, có chữ "đang suy nghĩ" / số giây không. Kết quả ở window.__stream.
 */
/**
 * Chạy `body` mỗi khi DOM đổi (MutationObserver) và mỗi 40ms, tới khi `stop` đúng hoặc hết `maxMs`.
 * Không dùng requestAnimationFrame: Chrome headless chỉ vẽ khung hình khi cần, rAF có thể đứng yên vài giây.
 * Trong body có sẵn `now` (ms từ lúc bắt đầu). Lỗi trong body ghi vào window.__watchErr.
 */
const watchLoop = (setup, body, stop, maxMs = 45000) => `(() => {
  const t0 = performance.now();
  ${setup}
  let done = false;
  const run = () => {
    if (done) return;
    const now = performance.now() - t0;
    try { ${body} } catch (e) { (window.__watchErr ??= []).push(String(e)); }
    if (now > ${maxMs} || (${stop})) { done = true; obs.disconnect(); clearInterval(iv); }
  };
  const obs = new MutationObserver(run);
  obs.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true });
  const iv = setInterval(run, 40);
  run();
})()`;

/**
 * Theo dõi trong lúc chờ trả lời (Story hoặc DM): khi nào có chấm đang gõ, chữ đầu tiên, nút Dừng, nút Sửa/Xoá có
 * bị khoá không, có chữ "đang suy nghĩ" / số giây không, ba chấm có nằm cạnh avatar không. Kết quả ở window.__stream.
 */
const watchStream = (articleSel) => watchLoop(
  `const before = document.querySelectorAll(${J(articleSel)}).length;
  const log = window.__stream = { dotsAt: null, textAt: null, doneAt: null, stopSeen: false, sendWithStop: false,
    lockChecked: 0, unlocked: [], noReason: [], reason: '', waitWords: [], dotsBubbleAvatar: false };`,
  `const dots = [...document.querySelectorAll('.typing-bounce')].filter(__bot.visible);
    const live = document.querySelector('[aria-live=polite][aria-busy=true]');
    const hasText = !!live && live.innerText.trim().length > 5;
    if (dots.length && log.dotsAt === null) log.dotsAt = now;
    if (dots.length && !hasText) {
      const box = dots[0].closest('.flex.flex-col') || document.body;
      const m = (box.innerText || '').match(/đang suy nghĩ|đang ngập ngừng|\\d+\\s*(giây|s)\\b/i);
      if (m) log.waitWords.push(m[0]);
      // DM: bong bóng ba chấm nằm cạnh avatar nhân vật (span aria-hidden 28px).
      const row = dots[0].closest('.items-end');
      if (row && [...row.querySelectorAll('span[aria-hidden=true]')].some((x) => Math.round(x.getBoundingClientRect().width) === 28)) log.dotsBubbleAvatar = true;
    }
    if (log.textAt === null && hasText) log.textAt = now;
    if (__bot.find({ label: 'Dừng' })) {
      log.stopSeen = true;
      if (__bot.find({ label: 'Gửi (Enter)' })) log.sendWithStop = true;
      for (const b of __bot.all({ css: 'button', visible: false })) {
        const l = b.getAttribute('aria-label');
        if (l !== 'Sửa' && l !== 'Xoá từ đây') continue;
        log.lockChecked++;
        if (!b.disabled) log.unlocked.push(l);
        // Khoá thì phải nói vì sao: title là một câu lý do, không chỉ lặp lại tên nút.
        const t = (b.getAttribute('title') || '').trim();
        if (!t || t === l) log.noReason.push(l);
        else log.reason = t;
      }
    }
    if (document.querySelectorAll(${J(articleSel)}).length > before && log.doneAt === null) log.doneAt = now;`,
  'window.__stream.doneAt !== null',
);

const ms = (v) => (v === null || v === undefined ? '—' : `${Math.round(v)}ms`);
const tabCount = `__bot.all({ within: 'nav[aria-label="Điều hướng chính"]', css: 'a[href]' }).length`;

export async function play(c) {
  const seen = []; // [nhãn màn, chữ đang hiện] để soát chữ kỹ thuật
  const expectedErrors = []; // đoạn URL của lỗi mạng kịch bản cố ý gây ra (xem check CONSOLE)
  const scan = async (label) => seen.push([label, await pageText(c)]);
  const tabs = {}; // hash → số tab đang hiện của thanh "Điều hướng chính"
  const recordTabs = async (label) => { tabs[label] = await c.evaluate(tabCount); };
  const sizes = []; // [màn, vấn đề] cho check 390px
  const measure = async (label, withButtons) => {
    const over = await overflowX(c);
    if (over > 1) sizes.push(`${label}: tràn ngang ${over}px`);
    if (!withButtons) return;
    const small = await c.evaluate(`[...document.querySelectorAll('header button, header a[href], nav[aria-label="Điều hướng chính"] a[href]')]
      .filter(__bot.visible).map((b) => [__bot.name(b), Math.round(b.getBoundingClientRect().width), Math.round(b.getBoundingClientRect().height)])
      .filter(([, w, h]) => w < 44 || h < 44)`);
    for (const [n, w, h] of small) sizes.push(`${label}: ${n} ${w}×${h}px`);
  };
  const rowSizes = []; // [vấn đề] cho check TAP_ROW (nút dưới lượt chat, hộp Xác nhận xoá ở 390px)
  let rowMeasured = 0;
  const measureButtons = async (label, selector) => {
    const found = await c.evaluate(`[...document.querySelectorAll(${J(selector)})].filter(__bot.visible)
      .map((b) => [__bot.name(b), Math.round(b.getBoundingClientRect().width), Math.round(b.getBoundingClientRect().height)])`);
    rowMeasured += found.length;
    for (const [n, w, h] of found) if (w < 44 || h < 44) rowSizes.push(`${label}: ${n} ${w}×${h}px`);
    return found.length;
  };
  const thoughtSwitches = { headerLabel: false, dmHidden: null, sheet: false, settings: false };
  let storyOpen = false;
  let storyHash = '';
  let characterName = '';
  let ownCard = null; // { id, name, href } nhân vật seed của chủ máy (cài từ mẫu Lạc Dương; sửa được ở Studio)
  let sharedCard = null; // { id, name, href } card bot tự nhập rồi lưu (của chính chủ máy, chia sẻ được)
  let inviteCode = '';
  const loreTitle = 'Hồ Gươm';
  const loreKey = 'hồ gươm';
  const loreSecret = 'Nơi hai người hẹn nhau mỗi chiều thứ bảy.';

  // ================================================================ chưa đăng nhập
  await c.step(C.LEGAL, async () => {
    const out = [];
    for (const [hash, title] of [['#/privacy', 'Chính sách quyền riêng tư'], ['#/terms', 'Điều khoản sử dụng']]) {
      await c.goto(hash, { reload: true });
      await c.waitFor(`document.querySelector('h1')?.innerText.trim() === ${J(title)}`, `tiêu đề "${title}"`, 20000);
      const len = await c.evaluate('document.querySelector("main, body").innerText.length');
      const signedOut = await c.evaluate('!__bot.find({ labelEnds: "Mở tài khoản" })');
      // Không soát chữ kỹ thuật ở văn bản pháp lý: "session token" ở đó là mô tả bảo mật, không phải chữ của LLM.
      await c.shot(title);
      out.push({ hash, ok: len > 500 && signedOut, len });
    }
    const bad = out.filter((o) => !o.ok);
    return { ok: bad.length === 0, detail: bad.map((b) => `${b.hash}: ${b.len} ký tự`).join(', ') };
  });

  // Mở #/studio khi chưa đăng nhập → sang #/login; đăng nhập xong → quay lại #/studio.
  let redirect = { toLogin: '', back: '' };
  await c.step(C.LOGIN, async () => {
    await c.goto('#/studio', { reload: true });
    await c.waitFor('location.hash.startsWith("#/login")', 'chuyển sang #/login', 20000).catch(() => {});
    redirect.toLogin = await hashNow(c);
    if (!redirect.toLogin.startsWith('#/login')) await c.goto('#/login', { reload: true });
    await c.waitFor('!!document.querySelector("input[autocomplete=username]") && !!document.querySelector("input[autocomplete=current-password]")', 'form đăng nhập', 20000);
    const heading = await c.evaluate('[...document.querySelectorAll("h1,h2")].map((h) => h.innerText.trim()).join(" | ")');
    await scan('#/login');
    await c.shot('Trang đăng nhập');
    await submitLogin(c, c.creds);
    await c.waitFor('!location.hash.startsWith("#/login")', 'rời trang đăng nhập', 15000);
    await c.waitFor('location.hash === "#/studio"', 'quay lại #/studio', 8000).catch(() => {});
    redirect.back = await hashNow(c);
    const inApp = await c.waitFor('!!__bot.find({ labelEnds: "Mở tài khoản" })', 'nút … Mở tài khoản sau khi đăng nhập', 15000).catch(() => false);
    await c.shot('Sau khi đăng nhập');
    const ok = heading.includes('Đăng nhập') && !!inApp;
    return { ok, detail: ok ? '' : `tiêu đề: ${heading}${inApp ? '' : ' · KHÔNG thấy nút … Mở tài khoản sau khi đăng nhập'}` };
  });
  c.check(C.REDIRECT, redirect.toLogin.startsWith('#/login') && redirect.back === '#/studio',
    `chưa đăng nhập: ${redirect.toLogin || '—'} → sau đăng nhập: ${redirect.back || '—'}`);

  // ================================================================ hub, theme, thanh tab
  await c.step(C.THEME, async () => {
    await c.goto('#/');
    await c.waitFor('!!__bot.find({ labelEnds: "Mở tài khoản" })', 'hub sau đăng nhập', 15000);
    await scan('#/');
    await recordTabs('#/');
    await measure('#/', true);
    const read = () => c.evaluate(`({ theme: document.documentElement.dataset.theme ?? '', saved: localStorage.getItem('lyris.theme') })`);
    const t0 = await read();
    await c.click({ labelStarts: 'Chuyển sang giao diện' }, 'nút đổi giao diện');
    await c.sleep(200);
    const t1 = await read();
    await c.shot('Đổi giao diện');
    await c.goto('#/', { reload: true });
    await c.waitFor('!!__bot.find({ labelStarts: "Chuyển sang giao diện" })', 'nút đổi giao diện sau tải lại', 15000);
    const t2 = await read();
    await c.click({ labelStarts: 'Chuyển sang giao diện' }, 'nút đổi giao diện (trả lại)');
    const ok = t1.theme !== t0.theme && t1.saved === t1.theme && t2.theme === t1.theme;
    return { ok, detail: `${t0.theme || '—'} → ${t1.theme} (lưu "${t1.saved}") → tải lại: ${t2.theme}` };
  });

  // F26: chữ có dấu tiếng Việt trong cả ba font tự host, mọi cỡ chữ app dùng. Mỗi chữ được đo bằng canvas hai lần:
  // '"<font>", monospace' và '"<font>", serif'. Font có glyph thì hai lần bằng nhau (glyph của chính font); font
  // thiếu glyph (hoặc không tải được) thì Chrome lấy font dự phòng, mà monospace và serif rộng khác nhau → lệch.
  // Kèm: FontFace có dải tiếng Việt (U+1EA0-1EF9) đã tải, và token font của app đặt đúng font đó đầu tiên.
  await c.step(C.FONTS_VI, async () => {
    await c.goto('#/');
    const rows = await c.evaluate(`(async () => {
      const sample = 'Ặ ặ Ỡ ỡ Ừ ừ Ữ ữ Ấ ấ Ộ ộ Ệ ệ Ơ ơ Ư ư Ă ă Đ đ';
      const chars = [...new Set(sample.replace(/\\s+/g, ''))];
      const root = getComputedStyle(document.documentElement);
      const fonts = [
        ['Plus Jakarta Sans', '--font-sans', ['400', '500', '600', '700']],
        ['Be Vietnam Pro', '--font-story', ['300', '400', 'italic 400', '500']],
        ['Cormorant Garamond', '--font-brand', ['italic 600', 'italic 700']],
      ];
      const ctx = document.createElement('canvas').getContext('2d');
      const out = [];
      for (const [family, token, styles] of fonts) {
        const tokenOk = root.getPropertyValue(token).trim().startsWith('"' + family + '"');
        for (const st of styles) {
          const loaded = await document.fonts.load(st + ' 32px "' + family + '"', sample);
          const viet = loaded.some((f) => /1ea0-1ef9/i.test(f.unicodeRange) && f.status === 'loaded');
          const fallback = chars.filter((ch) => {
            ctx.font = st + ' 32px "' + family + '", monospace';
            const a = ctx.measureText(ch).width;
            ctx.font = st + ' 32px "' + family + '", serif';
            return Math.abs(a - ctx.measureText(ch).width) > 0.01;
          });
          out.push({ family, st, tokenOk, viet, fallback });
        }
      }
      return out;
    })()`);
    const bad = rows.filter((r) => !r.tokenOk || !r.viet || r.fallback.length);
    const families = [...new Set(rows.map((r) => r.family))];
    return {
      ok: families.length === 3 && bad.length === 0,
      detail: bad.map((r) => `${r.family} ${r.st}: ${!r.tokenOk ? 'token sai, ' : ''}${!r.viet ? 'không tải bộ chữ tiếng Việt, ' : ''}${r.fallback.length ? `rơi về font dự phòng: ${r.fallback.join(' ')}` : ''}`).join('; ')
        || `${families.join(', ')}: ${rows.length} kiểu chữ, mọi chữ có dấu vẽ bằng chính font`,
    };
  });

  // ================================================================ sheet Tài khoản
  await c.step(C.ACCOUNT, async () => {
    await c.goto('#/');
    await openAccountSheet(c);
    const d = '[role=dialog]';
    const r = {
      privacy: await c.exists({ within: d, css: 'a[href="#/privacy"]' }),
      terms: await c.exists({ within: d, css: 'a[href="#/terms"]' }),
      sharing: await c.exists({ within: d, css: '[role=switch]', textHas: 'Chia sẻ dữ liệu sử dụng ẩn danh' }),
      export: await c.exists({ within: d, css: 'button', textHas: 'Tải dữ liệu của tôi' }),
      del: await c.exists({ within: d, css: 'button', text: 'Xoá tài khoản' }),
    };
    await scan('sheet tài khoản');
    await c.shot('Sheet tài khoản');
    const missing = Object.entries(r).filter(([, v]) => !v).map(([k]) => k);
    return { ok: missing.length === 0, detail: missing.length ? `thiếu: ${missing.join(', ')}` : '' };
  });

  await c.step(C.ADVANCED_FOLD, async () => {
    // Sheet đang mở (bước trước). Chưa mở "Nâng cao" thì chưa có request nào tới /api/system.
    const sys = () => c.requests.filter((q) => new URL(q.url).pathname.startsWith('/api/system')).length;
    const btn = { within: '[role=dialog]', css: 'button[aria-expanded]', textHas: 'Nâng cao' };
    const folded = await c.evaluate(`__bot.find(${J(btn)})?.getAttribute('aria-expanded')`);
    const before = sys();
    await c.click(btn, 'mục Nâng cao');
    await c.waitFor(`!!__bot.find({ within: '[role=dialog]', css: '[role=switch]', textHas: 'Công cụ nâng cao' })`, 'nội dung Nâng cao');
    const until = Date.now() + 5000;
    while (sys() === before && Date.now() < until) await c.sleep(100);
    const after = sys();
    await c.shot('Nâng cao đã mở');
    await c.click(btn, 'gập Nâng cao');
    return { ok: folded === 'false' && before === 0 && after > 0, detail: `ban đầu aria-expanded=${folded}, /api/system trước khi mở: ${before}, sau khi mở: ${after}` };
  });

  await c.step(C.SIGNOUT, async () => {
    const d = '[role=dialog]';
    const has = {
      password: await c.exists({ within: d, css: 'button', text: 'Đổi mật khẩu' }),
      signout: await c.exists({ within: d, css: 'button', text: 'Đăng xuất' }),
      all: await c.exists({ within: d, css: 'button', text: 'Đăng xuất mọi thiết bị' }),
    };
    await c.click({ within: d, css: 'button', text: 'Đăng xuất mọi thiết bị' }, 'nút Đăng xuất mọi thiết bị');
    await c.waitFor(`!!__bot.find({ within: '[role=group][aria-label="Đăng xuất mọi thiết bị"]', css: 'button', text: 'Giữ nguyên' })`, 'câu hỏi lại');
    const asked = await c.evaluate(`__bot.find({ css: '[role=group][aria-label="Đăng xuất mọi thiết bị"] p' })?.innerText ?? ''`);
    await c.shot('Hỏi lại trước khi đăng xuất mọi thiết bị');
    await c.click({ within: '[role=group][aria-label="Đăng xuất mọi thiết bị"]', css: 'button', text: 'Giữ nguyên' }, 'nút Giữ nguyên');
    const stillIn = await c.exists({ labelEnds: 'Mở tài khoản' });
    const missing = Object.entries(has).filter(([, v]) => !v).map(([k]) => k);
    return { ok: missing.length === 0 && asked.length > 10 && stillIn, detail: missing.length ? `thiếu: ${missing.join(', ')}` : asked.slice(0, 80) };
  });

  await c.step(C.ABOUT, async () => {
    const d = '[role=dialog]';
    await c.click({ within: d, css: 'button, a', textHas: 'Giới thiệu & bản quyền ảnh' }, 'liên kết Giới thiệu & bản quyền ảnh');
    await c.waitFor(dialogTitled('Giới thiệu & bản quyền ảnh'), 'phần Giới thiệu');
    await c.waitFor(`!!document.querySelector('[role=dialog] section[aria-labelledby=credits-title]')`, 'mục nguồn ảnh', 8000);
    const n = await c.evaluate(`document.querySelectorAll('[role=dialog] section[aria-labelledby=credits-title] li').length`);
    await scan('sheet: giới thiệu');
    await c.shot('Giới thiệu và bản quyền ảnh');
    await c.click({ within: d, css: 'button', text: 'Tài khoản' }, 'nút quay về Tài khoản');
    await c.waitFor(dialogTitled('Tài khoản'), 'về sheet Tài khoản');
    await c.press('Escape');
    return { ok: n > 0, detail: `${n} nguồn ảnh` };
  });

  // ================================================================ persona
  const newPersona = 'Bot Persona Hai';
  await c.step(C.PERSONA_ADD, async () => {
    await c.goto('#/personas');
    await recordTabs('#/personas');
    await c.click({ css: 'button', text: 'Thêm persona' }, 'nút Thêm persona');
    await c.waitFor(`!!document.querySelector('form[aria-label="Persona mới"]')`, 'form Persona mới');
    await c.fill({ within: 'form[aria-label="Persona mới"]', field: 'Tên' }, newPersona, 'ô Tên');
    await c.click({ within: 'form[aria-label="Persona mới"]', css: 'button[type=submit], button', text: 'Thêm persona' }, 'nút Thêm persona trong form');
    await c.waitFor(`!document.querySelector('form[aria-label="Persona mới"]')`, 'form đóng sau khi lưu', 10000);
    const r = await c.evaluate(`(() => {
      const row = [...document.querySelectorAll('main li, main article, main [class*=grid]')].find((e) => e.innerText.includes(${J(newPersona)}) && e.innerText.length < 400);
      const letter = row ? [...row.querySelectorAll('span[aria-hidden=true]')].map((s) => s.innerText.trim()).find((t) => t.length === 1) : null;
      return { row: !!row, letter };
    })()`);
    await scan('#/personas');
    await c.shot('Persona mới trong danh sách');
    return { ok: r.row && r.letter === 'B', detail: r.row ? `avatar chữ "${r.letter}"` : 'không thấy persona mới' };
  });

  let defaultPersona = '';
  await c.step(C.PERSONA_DEFAULT, async () => {
    await c.goto('#/');
    await openAccountSheet(c);
    const group = '[role=dialog] [role=radiogroup][aria-label="Persona đang dùng"]';
    await c.waitFor(`__bot.all({ within: ${J(group)}, css: '[role=radio]' }).length > 1`, 'ít nhất hai persona', 10000);
    const nameOf = (on) => `__bot.all({ within: ${J(group)}, css: '[role=radio]' }).find((r) => r.getAttribute('aria-checked') === ${J(on)})?.innerText.split('\\n').map((l) => l.trim()).filter((l) => l.length > 1)[0] ?? ''`;
    const original = await c.evaluate(nameOf('true'));
    const target = await c.evaluate(nameOf('false')); // persona KHÔNG đang dùng → đổi sang nó
    const radio = { within: group, css: '[role=radio]', textHas: target };
    await c.click(radio, `persona ${target}`);
    await c.waitFor(`__bot.find(${J(radio)})?.getAttribute('aria-checked') === 'true'`, 'persona được chọn', 8000);
    await c.sleep(500);
    await c.goto('#/', { reload: true });
    await c.waitFor('!!__bot.find({ labelEnds: "Mở tài khoản" })', 'hub sau tải lại', 15000);
    await openAccountSheet(c);
    await c.waitFor(`!!__bot.find(${J(radio)})`, 'nhóm Persona đang dùng sau tải lại', 10000);
    const kept = await c.evaluate(`__bot.find(${J(radio)})?.getAttribute('aria-checked')`);
    await c.shot('Persona đang dùng sau khi tải lại');
    // Sheet bắt đầu story phải chọn sẵn persona ĐANG DÙNG này (không phải persona mới thêm gần nhất).
    if (kept === 'true') defaultPersona = target;
    await c.press('Escape');
    return { ok: kept === 'true' && !!target && target !== original, detail: `"${original || '?'}" → "${target}", sau tải lại aria-checked=${kept}` };
  });

  // ================================================================ profile tài khoản
  await c.step(C.ME, async () => {
    await c.goto('#/me');
    await c.waitFor(`!!document.querySelector('ul[aria-label="Số liệu"]')`, 'số liệu', 15000);
    const tabNames = await c.evaluate(`__bot.all({ within: '[role=tablist][aria-label="Nội dung profile"]', css: '[role=tab]' }).map((t) => t.innerText.trim())`);
    await scan('#/me');
    await c.shot('Profile của tôi');
    const ok = tabNames.length === 2 && tabNames[0].startsWith('Nhân vật') && tabNames[1].startsWith('Persona');
    return { ok, detail: tabNames.join(' | ') };
  });

  await c.step(C.EDIT_PROFILE, async () => {
    await c.evaluate('window.__noReload = 1');
    await c.click({ css: 'button', text: 'Sửa profile' }, 'nút Sửa profile');
    await c.waitFor(dialogTitled('Sửa profile'), 'sheet Sửa profile');
    const handle = { within: '[role=dialog]', field: 'Handle' };
    await c.fill(handle, 'chu may!', 'ô Handle');
    await c.waitFor(`__bot.find(${J(handle)})?.getAttribute('aria-invalid') === 'true'`, 'ô Handle báo lỗi', 5000).catch(() => {});
    const err = await c.evaluate(`(() => {
      const el = __bot.find(${J(handle)});
      const ids = (el.getAttribute('aria-describedby') || '').split(/\\s+/).filter(Boolean);
      const box = el.getBoundingClientRect();
      const msg = ids.map((id) => document.getElementById(id)).filter((e) => e && /danger|error/.test(e.className) && e.getBoundingClientRect().top >= box.bottom - 1);
      return { invalid: el.getAttribute('aria-invalid'), text: msg.map((e) => e.innerText.trim()).join(' ') };
    })()`);
    await c.shot('Handle sai báo lỗi');
    await c.fill(handle, c.creds.handle, 'ô Handle (sửa lại)');
    const newName = 'Chủ máy Bot';
    await c.fill({ within: '[role=dialog]', field: 'Tên hiển thị' }, newName, 'ô Tên hiển thị');
    await c.click({ within: '[role=dialog]', css: 'button', text: 'Lưu' }, 'nút Lưu');
    await c.waitFor(`!${dialogTitled('Sửa profile')}`, 'sheet đóng sau khi lưu', 10000);
    await c.goto('#/');
    await c.waitFor(`!!__bot.find({ labelStarts: ${J(`Tài khoản: ${newName}.`)} })`, 'tên mới trên nút tài khoản', 8000).catch(() => {});
    const label = await c.evaluate(`__bot.find({ labelEnds: 'Mở tài khoản' })?.getAttribute('aria-label') ?? ''`);
    const noReload = await c.evaluate('window.__noReload === 1');
    const ok = err.invalid === 'true' && err.text.length > 0 && label.startsWith(`Tài khoản: ${newName}.`) && noReload;
    return { ok, detail: `lỗi handle: "${err.text}" · nút: "${label}" · ${noReload ? 'không tải lại' : 'ĐÃ tải lại trang'}` };
  });

  await c.step(C.PUBLIC_PROFILE, async () => {
    await c.goto(`#/u/${c.creds.handle}`);
    await c.waitFor(`document.body.innerText.includes('@${c.creds.handle}')`, `profile @${c.creds.handle}`, 10000);
    const mine = await c.evaluate(`document.querySelector('main').innerText.includes('Chủ máy Bot')`);
    expectedErrors.push('/khong_ton_tai_xyz)');
    await c.goto('#/u/khong_ton_tai_xyz');
    await c.waitFor(`document.body.innerText.includes('Không có tài khoản @khong_ton_tai_xyz')`, 'trạng thái không tìm thấy', 10000);
    await c.shot('Profile không tồn tại');
    return { ok: mine, detail: mine ? '' : 'profile không có tên hiển thị' };
  });

  // F28: 'Sửa profile' đổi cả giới thiệu, ảnh đại diện và ảnh bìa (ảnh lưu ngay khi chọn, chữ lưu khi bấm Lưu);
  // #/me hiện đủ ba thứ sau khi lưu.
  await c.step(C.EDIT_PROFILE_MEDIA, async () => {
    const bio = 'Thích kể chuyện mưa Hà Nội và trà nóng đầu đông.';
    await c.goto('#/me');
    await c.waitFor(`!!__bot.find({ css: 'button', text: 'Sửa profile' })`, 'nút Sửa profile', 15000);
    await c.click({ css: 'button', text: 'Sửa profile' }, 'nút Sửa profile');
    await c.waitFor(dialogTitled('Sửa profile'), 'sheet Sửa profile');
    const d = '[role=dialog]';
    await c.setFiles(await fileInputBeside(c, { within: d, css: 'button', labelEnds: 'ảnh đại diện' }, 'account-avatar'), [PHOTO_A]);
    const avatarSaved = await c.waitFor(`!!__bot.find({ within: '${d}', css: 'button', label: 'Đổi ảnh đại diện' })`, 'ảnh đại diện đã lưu', 15000).catch(() => false);
    await c.setFiles(await fileInputBeside(c, { within: d, css: 'button', labelEnds: 'ảnh bìa' }, 'account-banner'), [PHOTO_B]);
    const bannerSaved = await c.waitFor(`!!__bot.find({ within: '${d}', css: 'button', label: 'Đổi ảnh bìa' })`, 'ảnh bìa đã lưu', 15000).catch(() => false);
    await c.fill({ within: d, field: 'Giới thiệu' }, bio, 'ô Giới thiệu');
    await c.shot('Sửa profile: ảnh đại diện, ảnh bìa, giới thiệu');
    await c.click({ within: d, css: 'button', text: 'Lưu' }, 'nút Lưu');
    await c.waitFor(`!${dialogTitled('Sửa profile')}`, 'sheet đóng sau khi lưu', 10000);
    await c.goto('#/me', { reload: true });
    await c.waitFor(`!!document.querySelector('ul[aria-label="Số liệu"]')`, 'profile sau tải lại', 15000);
    const shownBio = await c.waitFor(`document.querySelector('main').innerText.includes(${J(bio)})`, 'giới thiệu trên #/me', 8000).catch(() => false);
    const avatar = await imageShown(c, '/api/account/avatar', 'ảnh đại diện trên #/me');
    const banner = await imageShown(c, '/api/account/banner', 'ảnh bìa trên #/me');
    await c.shot('Profile có ảnh đại diện, ảnh bìa, giới thiệu');
    const ok = avatarSaved && bannerSaved && shownBio && avatar > 0 && banner > 0;
    return { ok, detail: `sheet: ảnh đại diện ${avatarSaved ? 'đã lưu' : 'KHÔNG lưu'}, ảnh bìa ${bannerSaved ? 'đã lưu' : 'KHÔNG lưu'} · #/me: giới thiệu ${shownBio ? 'có' : 'KHÔNG'}, ảnh đại diện ${avatar}, ảnh bìa ${banner}` };
  });

  // ================================================================ Studio (Công cụ nâng cao đang tắt)
  await c.step(C.STUDIO_SAVE, async () => {
    await c.goto('#/studio');
    await recordTabs('#/studio');
    await measure('#/studio', true);
    await c.waitFor(`!!document.querySelector('main a[href^="#/studio/"]')`, 'nhân vật trong Studio', 15000);
    await scan('#/studio');
    const href = await c.evaluate(`document.querySelector('main a[href^="#/studio/"]').getAttribute('href')`);
    await c.click(`main a[href="${href}"]`, 'nhân vật đầu tiên');
    await c.waitFor(`location.hash.startsWith(${J(href)})`, 'trình sửa nhân vật');
    const name = { field: 'Tên nhân vật' };
    await c.waitFor(`(__bot.find(${J(name)})?.value ?? '').length > 0`, 'tên đã lưu', 15000);
    const old = await c.evaluate(`__bot.find(${J(name)}).value`);
    const id = Number(href.match(/\d+/)?.[0]);
    const renamed = `${old} Bot`;
    await c.fill(name, renamed, 'ô Tên nhân vật');
    await c.click({ css: 'header button', text: 'Lưu' }, 'nút Lưu');
    await c.waitFor(`!!__bot.find({ css: 'header button', text: 'Đã lưu' })`, 'đã lưu', 10000);
    await c.goto(href, { reload: true });
    await c.waitFor(`(__bot.find(${J(name)})?.value ?? '').length > 0`, 'tên sau tải lại', 15000);
    const after = await c.evaluate(`__bot.find(${J(name)}).value`);
    ownCard = { id, name: after, href };
    await recordTabs('#/studio/<id>');
    await c.shot('Trình sửa sau khi lưu');
    return { ok: after === renamed, detail: `"${old}" → "${after}"` };
  });

  await c.step(C.NO_PREVIEW, async () => {
    if (!ownCard) throw new Error('chưa mở được nhân vật trong Studio');
    const r = await c.evaluate(`({
      tabs: __bot.all({ within: '[role=tablist][aria-label="Phần của trình sửa"]', css: '[role=tab]' }).map((t) => t.innerText.trim()),
      token: /token/i.test(document.body.innerText),
    })`);
    await scan('#/studio/<id>');
    return { ok: !r.tabs.includes('Xem trước') && r.tabs.length > 0 && !r.token, detail: `tab: ${r.tabs.join(', ')}${r.token ? ' · có chữ token' : ''}` };
  });

  await c.step(C.SIGNATURE, async () => {
    if (!ownCard) throw new Error('chưa mở được nhân vật trong Studio');
    const field = { field: 'Lời nói đặc trưng' };
    await c.fill(field, 'Câu một.\nCâu hai.\nCâu ba.\nCâu bốn.', 'ô Lời nói đặc trưng');
    await c.sleep(300);
    const saveBtn = `__bot.find({ css: 'header button', textHas: 'Lưu' })`;
    if (await c.evaluate(`!${saveBtn}?.disabled`)) await c.click({ css: 'header button', textHas: 'Lưu' }, 'nút Lưu');
    await c.sleep(800);
    const r = await c.evaluate(`(() => {
      const el = __bot.find(${J(field)});
      const ids = (el.getAttribute('aria-describedby') || '').split(/\\s+/).filter(Boolean);
      const fieldErr = ids.map((id) => document.getElementById(id)).filter((e) => e && /danger|error/.test(e.className)).map((e) => e.innerText.trim());
      const notice = [...document.querySelectorAll('main [role=alert], main')].map((e) => e.innerText).join(' ');
      return { fieldErr: fieldErr.join(' '), notSaved: notice.includes('Chưa lưu được'), status: ${saveBtn}?.innerText ?? '' };
    })()`);
    await c.shot('Lời nói đặc trưng 4 dòng');
    await c.goto(ownCard.href, { reload: true }); // còn thay đổi chưa lưu: bot đồng ý rời trang
    await c.waitFor(`(__bot.find(${J(field)}) && __bot.find({ field: 'Tên nhân vật' })?.value) ? true : false`, 'trình sửa sau tải lại', 15000);
    const lines = await c.evaluate(`__bot.find(${J(field)}).value.split('\\n').filter((l) => l.trim()).length`);
    const blocked = (r.fieldErr.length > 0 || r.notSaved) && lines <= 3;
    return { ok: blocked, detail: `lỗi: "${r.fieldErr || (r.notSaved ? 'Chưa lưu được' : '—')}" · sau tải lại ${lines} dòng` };
  });

  // Còn thay đổi chưa lưu mà bấm "Về Studio": trình duyệt phải hỏi lại (confirm). Huỷ → ở lại, chữ đang sửa còn;
  // OK → rời trang, tên đã lưu không đổi. Bot ghi lại mọi hộp thoại (c.dialogs) chứ không âm thầm bấm OK.
  await c.step(C.LEAVE_GUARD, async () => {
    if (!ownCard) throw new Error('chưa mở được nhân vật trong Studio');
    const name = { field: 'Tên nhân vật' };
    await c.goto(ownCard.href, { reload: true });
    await c.waitFor(`(__bot.find(${J(name)})?.value ?? '').length > 0`, 'tên đã lưu', 15000);
    const saved = await c.evaluate(`__bot.find(${J(name)}).value`);
    const draft = `${saved} chưa lưu`;
    await c.fill(name, draft, 'ô Tên nhân vật');
    await c.sleep(400);
    const asks = (from) => c.dialogs.slice(from).filter((d) => d.type === 'confirm' && d.message.includes('thay đổi chưa lưu'));
    c.answerDialogs(false);
    const n0 = c.dialogs.length;
    await c.click({ label: 'Về Studio' }, 'nút Về Studio');
    await c.sleep(700);
    const stay = await c.evaluate(`({ hash: location.hash, value: __bot.find(${J(name)})?.value ?? null })`);
    const cancelAsked = asks(n0).length;
    await c.shot('Rời trình sửa: bấm Huỷ thì ở lại');
    c.answerDialogs(true);
    const n1 = c.dialogs.length;
    await c.click({ label: 'Về Studio' }, 'nút Về Studio');
    await c.waitFor(`location.hash === '#/studio'`, 'về #/studio', 8000).catch(() => {});
    const left = await hashNow(c);
    const okAsked = asks(n1).length;
    await c.goto(ownCard.href, { reload: true });
    await c.waitFor(`(__bot.find(${J(name)})?.value ?? '').length > 0`, 'tên sau khi rời', 15000);
    const after = await c.evaluate(`__bot.find(${J(name)}).value`);
    const ok = cancelAsked > 0 && stay.hash === ownCard.href && stay.value === draft && okAsked > 0 && left === '#/studio' && after === saved;
    return { ok, detail: `Huỷ: ${cancelAsked ? 'có hỏi' : 'KHÔNG hỏi'} → ${stay.hash}, ô "${stay.value}" · OK: ${okAsked ? 'có hỏi' : 'KHÔNG hỏi'} → ${left} · tên đã lưu "${after}"` };
  });

  await c.step(C.TEST_CHAT, async () => {
    if (!ownCard) throw new Error('chưa mở được nhân vật trong Studio');
    await c.click({ within: '[role=tablist][aria-label="Phần của trình sửa"]', css: '[role=tab]', text: 'Chat thử' }, 'tab Chat thử');
    const input = { css: 'textarea', label: 'Tin nhắn chat thử' };
    await c.waitFor(`!!__bot.find(${J(input)}) && !__bot.find(${J(input)}).disabled`, 'ô chat thử', 15000);
    await c.click(input, 'ô chat thử');
    await c.type('Chào, hôm nay thế nào?');
    const aside = 'aside[aria-label="Xem trước và chat thử"]';
    // Câu trả lời Story của LLM giả (environment/fake-server.py): đếm số lần xuất hiện trước và sau khi gửi.
    const REPLY = '/đèn vàng hắt|tách trà xuống bàn|kéo ghế ngồi xuống đối diện/g';
    const replies = `(document.querySelector('${aside}').innerText.match(${REPLY}) || []).length`;
    const before = await c.evaluate(replies);
    const t0 = Date.now();
    await c.click({ within: aside, label: 'Gửi (Enter)' }, 'nút Gửi chat thử');
    const t = { dotsAt: null, textAt: null };
    // Hỏi trang mỗi ~80ms: ba chấm hiện (LLM giả chờ 0,9 giây trước chữ đầu), rồi chữ của câu trả lời.
    if (await c.waitFor(`[...document.querySelectorAll('${aside} .typing-bounce')].some(__bot.visible)`, 'ba chấm trong chat thử', 8000).catch(() => false)) t.dotsAt = Date.now() - t0;
    await c.waitFor(`${replies} > ${before}`, 'câu trả lời chat thử', 30000);
    t.textAt = Date.now() - t0;
    await c.waitFor(`!__bot.find({ within: '${aside}', label: 'Dừng' })`, 'chat thử trả lời xong', 30000);
    await c.sleep(300);
    const thoughts = await c.evaluate(`[...document.querySelectorAll('aside[aria-label="Xem trước và chat thử"] span.sr-only')].filter((s) => s.textContent.startsWith('Suy nghĩ')).length`);
    await c.shot('Chat thử ở Studio');
    c.check(C.TEST_THOUGHT, thoughts > 0, `${thoughts} thẻ suy nghĩ trong chat thử`);
    return { ok: t.dotsAt !== null && t.textAt !== null && t.dotsAt <= t.textAt, detail: `chấm ${ms(t.dotsAt)} → chữ ${ms(t.textAt)}` };
  });
  if (!ownCard) c.check(C.TEST_THOUGHT, false, 'chưa mở được nhân vật trong Studio');

  await c.step(C.LORE_ADD, async () => {
    if (!ownCard) throw new Error('chưa mở được nhân vật trong Studio');
    const worldHash = `#/studio/${ownCard.id}?section=world`;
    await c.goto(worldHash, { reload: true });
    await showFormTab(c);
    await c.waitFor(`!!__bot.find({ css: 'button', text: 'Thêm mục' })`, 'phần Thế giới', 15000);
    await c.click({ css: 'button', text: 'Thêm mục' }, 'nút Thêm mục');
    await c.waitFor(dialogTitled('Mục mới'), 'hộp Mục mới');
    await c.fill({ within: '[role=dialog]', field: 'Tên mục' }, loreTitle, 'ô Tên mục');
    await c.click({ within: '[role=dialog]', css: '[role=radio]', text: 'Nơi chốn' }, 'loại Nơi chốn');
    await c.click({ within: '[role=dialog]', field: 'Từ khoá gợi nhớ' }, 'ô Từ khoá gợi nhớ');
    await c.type(loreKey);
    await c.press('Enter');
    await c.fill({ within: '[role=dialog]', field: 'Nội dung' }, loreSecret, 'ô Nội dung');
    await c.shot('Mục thế giới mới');
    await c.click({ within: '[role=dialog]', css: 'button', text: 'Lưu' }, 'nút Lưu mục');
    await c.waitFor(`!${dialogTitled('Mục mới')}`, 'hộp đóng sau khi lưu', 10000);
    await c.goto(worldHash, { reload: true });
    await showFormTab(c);
    await c.waitFor(`!!__bot.find({ css: 'button', text: 'Thêm mục' })`, 'phần Thế giới sau tải lại', 15000);
    // Mục được xếp vào nhóm theo loại ("Nơi chốn · 1"), nhóm đang gập: mở nhóm rồi tìm mục.
    const group = { css: 'button[aria-expanded]', textHas: 'Nơi chốn' };
    await c.waitFor(`!!__bot.find(${J(group)})`, 'nhóm Nơi chốn', 10000).catch(() => {});
    if ((await c.evaluate(`__bot.find(${J(group)})?.getAttribute('aria-expanded')`)) === 'false') await c.click(group, 'nhóm Nơi chốn');
    const kept = await c.waitFor(`!!__bot.find({ css: 'li button', textHas: ${J(loreTitle)} })`, 'mục vừa thêm sau tải lại', 10000).catch(() => false);
    const words = await c.evaluate(`(document.body.innerText.match(/\\b(lore|keys|token)\\b/gi) || []).join(', ')`);
    await c.shot('Thế giới sau khi tải lại');
    // Hồ sơ nhân vật: phần "Thế giới" chỉ có tên, không có nội dung mục.
    await c.goto(`#/character/${ownCard.id}`);
    await c.waitFor(`!!__bot.find({ css: '[role=tab]', text: 'Giới thiệu' })`, 'hồ sơ nhân vật', 15000);
    const findWorld = `[...document.querySelectorAll('h4')].some((h) => h.innerText.trim() === 'Thế giới' && __bot.visible(h))`;
    if (!(await c.evaluate(findWorld))) {
      for (const tab of ['Thiết lập', 'Giới thiệu']) {
        await c.click({ css: '[role=tab]', text: tab }, `tab ${tab}`).catch(() => {});
        if (await c.evaluate(findWorld)) break;
      }
    }
    const teaser = await c.evaluate(`(() => {
      const h = [...document.querySelectorAll('h4')].find((x) => x.innerText.trim() === 'Thế giới');
      const sec = h?.closest('section');
      return { has: !!sec, names: sec ? [...sec.querySelectorAll('li')].map((l) => l.innerText.trim()) : [],
               secret: document.body.innerText.includes(${J(loreSecret)}),
               words: (document.body.innerText.match(/\\b(lore|keys|token)\\b/gi) || []).join(', ') };
    })()`);
    await recordTabs('#/character/<id>');
    await c.shot('Hồ sơ có phần Thế giới');
    c.check(C.LORE_TEASER, teaser.has && teaser.names.includes(loreTitle) && !teaser.secret,
      teaser.has ? `tên: ${teaser.names.join(', ')}${teaser.secret ? ' · LỘ nội dung mục' : ''}` : 'không có phần Thế giới');
    c.check(C.LORE_WORDS, !words && !teaser.words, `studio: ${words || 'sạch'} · hồ sơ: ${teaser.words || 'sạch'}`);
    return { ok: kept, detail: kept ? '' : 'mục không còn sau khi tải lại' };
  });
  if (!ownCard) { c.check(C.LORE_TEASER, false, 'chưa mở được nhân vật'); c.check(C.LORE_WORDS, false, 'chưa mở được nhân vật'); }

  await c.step(C.DRAFT, async () => {
    await c.goto('#/studio');
    await c.click({ css: 'button', text: 'AI viết nháp' }, 'nút AI viết nháp');
    await c.waitFor(dialogTitled('AI viết nháp nhân vật'), 'hộp AI viết nháp');
    const idea = { within: '[role=dialog]', field: 'Ý tưởng' };
    await c.click(idea, 'ô Ý tưởng');
    await c.type('Cô bạn cùng phòng ký túc xá, hay càu nhàu nhưng rất quan tâm.');
    expectedErrors.push('(/api/cards/draft)');
    await c.click({ within: '[role=dialog]', css: 'button', text: 'Viết nháp' }, 'nút Viết nháp');
    await c.waitFor(`!!__bot.find({ within: '[role=dialog]', css: 'summary, button', textHas: 'Chi tiết' })`, 'lỗi kèm Chi tiết', 20000);
    const text = await c.evaluate(`document.querySelector('[role=dialog]').innerText`);
    await c.shot('AI viết nháp báo lỗi');
    const leak = text.match(/\b(model|ollama)\b/i);
    await c.click({ within: '[role=dialog]', css: 'button', text: 'Đóng' }, 'nút Đóng').catch(() => c.press('Escape'));
    return { ok: !leak, detail: leak ? `lộ chữ "${leak[0]}"` : text.split('\n').find((l) => l.trim().length > 15)?.slice(0, 80) ?? '' };
  });

  await c.step(C.DRAFT_OPEN, async () => {
    // LLM giả (environment/fake-server.py) viết được card nháp khi ý tưởng có chữ "Thủ thư" (ý tưởng khác thì báo lỗi).
    const draftName = 'Mai Chi Nháp';
    await c.goto('#/studio');
    await c.click({ css: 'button', text: 'AI viết nháp' }, 'nút AI viết nháp');
    await c.waitFor(dialogTitled('AI viết nháp nhân vật'), 'hộp AI viết nháp');
    await c.click({ within: '[role=dialog]', field: 'Ý tưởng' }, 'ô Ý tưởng');
    await c.type('Thủ thư thư viện cũ phố Hàng Bài, trầm tính, tỉ mỉ, hay để dành sách cho người quen.');
    await c.click({ within: '[role=dialog]', css: 'button', text: 'Viết nháp' }, 'nút Viết nháp');
    await c.waitFor(`location.hash === '#/studio/new' && (__bot.find({ field: 'Tên nhân vật' })?.value ?? '') === ${J(draftName)}`, 'trình sửa với card nháp', 20000);
    const unsaved = await c.evaluate(`document.querySelector('header').innerText.includes('chưa lưu')`);
    const saved = await c.evaluate(`fetch('/api/cards').then((r) => r.json()).then((cards) => cards.some((x) => x.name === ${J(draftName)}))`);
    await c.shot('AI viết nháp: trình sửa với card nháp, chưa lưu');
    // Rời trình sửa không lưu (bot mặc định bấm OK ở hộp hỏi "thay đổi chưa lưu").
    await c.goto('#/studio');
    const after = await c.evaluate(`fetch('/api/cards').then((r) => r.json()).then((cards) => cards.some((x) => x.name === ${J(draftName)}))`);
    const ok = unsaved && !saved && !after;
    return { ok, detail: `#/studio/new, Tên nhân vật "${draftName}" · ${unsaved ? 'header "chưa lưu"' : 'KHÔNG thấy "chưa lưu"'} · ${saved || after ? 'card ĐÃ bị lưu' : 'chưa có trong /api/cards'}` };
  });

  await c.step(C.IMPORT, async () => {
    await c.goto('#/studio');
    const file = path.join(c.out, 'bot-card.json');
    const cardName = 'Mộc Lan Nhập';
    writeFileSync(file, JSON.stringify({
      spec: 'chara_card_v2', spec_version: '2.0',
      data: { name: cardName, description: 'Cô gái bán hoa ở chợ Bến Thành, nói nhiều, hay cười.', personality: 'vui vẻ', scenario: 'Sáng sớm ở chợ.',
        first_mes: 'Ơ, lại là cậu à? Mua hoa không?', mes_example: '', creator_notes: '', system_prompt: '', post_history_instructions: '',
        alternate_greetings: [], tags: ['vui vẻ'], creator: 'bot', character_version: '1', extensions: {} },
    }));
    const hasButton = await c.exists({ css: 'button', textHas: 'Nhập card' });
    await c.setFiles('input[type=file][accept*=".json"]', [file]);
    await c.waitFor(`location.hash.startsWith('#/studio/') && (__bot.find({ field: 'Tên nhân vật' })?.value ?? '') === ${J(cardName)}`, 'trình sửa với card vừa nhập', 15000);
    const unsaved = await c.evaluate(`document.querySelector('header').innerText.includes('chưa lưu')`);
    await c.shot('Card vừa nhập, chưa lưu');
    // Lưu lại: card này là của chủ máy (không cài từ mẫu), các bước sau chia sẻ nó.
    await c.click({ css: 'header button', text: 'Lưu nhân vật' }, 'nút Lưu nhân vật');
    await c.waitFor(`/^#\\/studio\\/\\d+/.test(location.hash) && !!__bot.find({ css: 'header button', text: 'Đã lưu' })`, 'card đã lưu', 15000);
    const href = (await hashNow(c)).split('?')[0];
    sharedCard = { id: Number(href.match(/\d+/)[0]), name: cardName, href };
    return { ok: hasButton && unsaved, detail: `${hasButton ? '' : 'không có nút Nhập card · '}${unsaved ? 'mở trình sửa, chưa lưu' : 'không thấy "chưa lưu"'} · lưu thành ${href}` };
  });

  await c.step(C.ADVANCED_TOOLS, async () => {
    if (!ownCard) throw new Error('chưa mở được nhân vật trong Studio');
    const tabsOf = `__bot.all({ within: '[role=tablist][aria-label="Phần của trình sửa"]', css: '[role=tab]' }).map((t) => t.innerText.trim())`;
    await setAdvancedTools(c, true);
    await c.goto(ownCard.href);
    await c.waitFor(`${tabsOf}.includes('Xem trước')`, 'tab Xem trước', 15000);
    await c.click({ within: '[role=tablist][aria-label="Phần của trình sửa"]', css: '[role=tab]', text: 'Xem trước' }, 'tab Xem trước');
    const est = await c.waitFor(`!!document.querySelector('section[aria-label="Ước lượng token"]')`, 'Ước lượng token', 15000).catch(() => false);
    await c.shot('Công cụ nâng cao bật: Xem trước');
    await setAdvancedTools(c, false);
    await c.goto(ownCard.href);
    await c.waitFor(`${tabsOf}.length > 0`, 'trình sửa', 15000);
    const off = await c.evaluate(tabsOf);
    return { ok: !!est && !off.includes('Xem trước'), detail: `bật: ${est ? 'có Ước lượng token' : 'không có Ước lượng token'} · tắt: ${off.join(', ')}` };
  });

  await c.step(C.SHARE, async () => {
    if (!ownCard || !sharedCard) throw new Error('chưa có nhân vật trong Studio');
    const sw = { css: '[role=switch]', textHas: 'Công khai' };
    // Nhân vật cài từ mẫu (Lạc Dương): không có công tắc Công khai.
    await c.goto(ownCard.href);
    await showFormTab(c);
    await c.waitFor(`(__bot.find({ field: 'Tên nhân vật' })?.value ?? '').length > 0`, 'trình sửa nhân vật mẫu', 15000);
    await c.sleep(300);
    const onTemplate = await c.exists(sw);
    await c.goto(sharedCard.href);
    await showFormTab(c);
    await c.waitFor(`!!__bot.find(${J(sw)})`, 'công tắc Công khai', 15000);
    if (onTemplate) throw new Error('nhân vật cài từ mẫu cũng có công tắc Công khai');
    // Công tắc nằm trong phần 'Cơ bản' của trình sửa (section có tiêu đề 'Cơ bản').
    const section = await c.evaluate(`(() => {
      const sec = __bot.find(${J(sw)}).closest('section[aria-labelledby]');
      return sec ? (document.getElementById(sec.getAttribute('aria-labelledby'))?.innerText.trim() ?? '') : '';
    })()`);
    if (section !== 'Cơ bản') throw new Error(`công tắc Công khai nằm ở phần "${section || 'không có tiêu đề'}", không phải 'Cơ bản'`);
    if ((await c.evaluate(`__bot.find(${J(sw)}).getAttribute('aria-checked')`)) !== 'true') await c.click(sw, 'công tắc Công khai');
    await c.click({ css: 'header button', textHas: 'Lưu' }, 'nút Lưu');
    await c.waitFor(`!!__bot.find({ css: 'button', text: 'Người khác thấy gì' })`, 'nút Người khác thấy gì', 10000);
    await c.shot('Nhân vật đã công khai');
    return { ok: true, detail: "mẫu: không có công tắc · nhân vật nhập từ .json: công tắc ở phần 'Cơ bản', lưu xong có 'Người khác thấy gì'" };
  });

  // ================================================================ Khám phá
  await c.step(C.EXPLORE, async () => {
    await c.goto('#/explore');
    await c.waitFor('document.querySelectorAll("section[aria-labelledby=explore-all] ul > li").length > 0', 'lưới nhân vật', 15000);
    await c.sleep(400);
    await recordTabs('#/explore');
    const r = await c.evaluate(`(() => {
      const cards = [...document.querySelectorAll('section[aria-labelledby=explore-all] ul > li > a')].map((a) => a.getBoundingClientRect());
      const widths = cards.map((r) => Math.round(r.width));
      const rows = {};
      for (const r of cards) (rows[Math.round(r.top)] ??= []).push(Math.round(r.height));
      const unevenRow = Object.values(rows).find((hs) => Math.max(...hs) - Math.min(...hs) > 1);
      return { n: cards.length, wSpread: Math.max(...widths) - Math.min(...widths), unevenRow: unevenRow ?? null,
               hero: !!document.querySelector('section[aria-labelledby=explore-featured]') };
    })()`);
    const over = await overflowX(c);
    await scan('#/explore');
    await c.shot('Khám phá');
    const problems = [];
    if (!r.hero) problems.push('không có nhân vật nổi bật');
    if (r.wSpread > 1) problems.push(`thẻ lệch rộng ${r.wSpread}px`);
    if (r.unevenRow) problems.push(`thẻ cùng hàng lệch cao: ${r.unevenRow.join('/')}`);
    if (over > 1) problems.push(`tràn ngang ${over}px`);
    return { ok: problems.length === 0, detail: problems.join('; ') || `${r.n} thẻ` };
  });

  await c.step(C.FEATURED, async () => {
    const r = await c.evaluate(`(() => {
      const name = document.querySelector('#explore-featured a')?.innerText.trim() ?? '';
      const grid = [...document.querySelectorAll('section[aria-labelledby=explore-all] ul > li > a')]
        .map((a) => a.querySelector('span.font-semibold')?.innerText.trim() ?? '');
      return { name, dup: grid.filter((n) => n === name).length, n: grid.length };
    })()`);
    characterName = r.name;
    return { ok: !!r.name && r.dup === 0, detail: r.name ? `${r.name}: ${r.dup} lần trong lưới ${r.n} thẻ` : 'không thấy tên nhân vật nổi bật' };
  });

  await c.step(C.VIBE, async () => {
    const group = '[role=group][aria-label="Lọc theo cảm xúc"]';
    const counter = `document.querySelector('section[aria-labelledby=explore-all] h2').parentElement.querySelector('span').innerText.trim()`;
    const gridNames = `[...document.querySelectorAll('section[aria-labelledby=explore-all] ul > li > a')].map((a) => a.querySelector('span.font-semibold')?.innerText.trim() ?? '')`;
    const total = await c.evaluate(counter);
    const before = await c.evaluate(gridNames);
    const chips = await c.evaluate(`__bot.all({ within: ${J(group)}, css: 'button' }).map((b) => b.innerText.trim())`);
    // Tag của từng nhân vật, đọc thẳng từ server (card: tags + vibe của mẫu đã cài; mẫu chưa cài: vibes + tags).
    const tagsByName = await c.evaluate(`Promise.all([fetch('/api/cards').then((r) => r.json()), fetch('/api/templates').then((r) => r.json())]).then(([cards, temps]) => {
      const norm = (t) => String(t).normalize('NFC').replace(/[\\p{Extended_Pictographic}\\p{So}\\uFE0F\\u200D]/gu, ' ').toLocaleLowerCase('vi-VN').replace(/\\s+/g, ' ').trim();
      const out = {};
      const add = (name, tags) => { (out[name] ??= []).push(...tags.map(norm)); };
      const installed = new Set(cards.map((c) => c.id));
      for (const c of cards) add(c.name, [...(c.tags ?? []), ...temps.filter((t) => t.installed_card_id === c.id).flatMap((t) => t.vibes ?? [])]);
      for (const t of temps) if (t.installed_card_id === null || !installed.has(t.installed_card_id)) add(t.card.name, [...(t.vibes ?? []), ...(t.card.tags ?? [])]);
      return out;
    })`);
    const norm = (t) => t.normalize('NFC').toLocaleLowerCase('vi-VN').replace(/\s+/g, ' ').trim();
    // Chip đầu tiên mà CÓ nhân vật mang tag đó nhưng KHÔNG phải mọi nhân vật đều mang (0 < x < tổng): chip không có ai
    // thì lưới rỗng, chip ai cũng có thì lọc không bỏ ai — cả hai không chứng minh được việc lọc.
    const totalN = Number(total);
    const matches = (t) => Object.values(tagsByName).filter((tags) => tags.includes(norm(t))).length;
    const pick = chips.find((t) => t !== 'Tất cả' && matches(t) > 0 && matches(t) < totalN);
    if (!pick) throw new Error(`không có chip cảm xúc nào lọc bớt được lưới (chip: ${chips.join(', ')}; tổng ${total})`);
    const tag = norm(pick);
    const expected = Object.entries(tagsByName).filter(([, tags]) => tags.includes(tag)).map(([n]) => n).sort();
    const chip = { within: group, css: 'button', text: pick };
    await c.click(chip, `chip ${pick}`);
    await c.waitFor(`${counter}.includes('/')`, 'bộ đếm lọc');
    await c.sleep(200);
    const filtered = await c.evaluate(counter);
    const shown = await c.evaluate(gridNames);
    const pressed = await c.evaluate(`__bot.find(${J(chip)}).getAttribute('aria-pressed')`);
    await c.shot('Lọc theo cảm xúc');
    await c.click(chip, `chip ${pick} (bỏ lọc)`);
    await c.waitFor(`!${counter}.includes('/')`, 'bộ đếm về tổng');
    await c.sleep(200);
    const back = await c.evaluate(counter);
    const after = await c.evaluate(gridNames);
    const [a, b] = filtered.split('/').map((x) => Number(x.trim()));
    const problems = [];
    if (pressed !== 'true') problems.push(`chip aria-pressed=${pressed}`);
    if (!(a > 0) || String(b) !== total) problems.push(`bộ đếm "${filtered}" (tổng ${total})`);
    if (!(a < b)) problems.push(`lọc không bỏ ai: ${filtered}`);
    if (shown.length !== a) problems.push(`lưới ${shown.length} thẻ, bộ đếm ${a}`);
    const without = shown.filter((n) => !(tagsByName[n] ?? []).includes(tag));
    if (without.length) problems.push(`thẻ không có tag "${tag}": ${without.join(', ')}`);
    const missing = expected.filter((n) => !shown.includes(n));
    if (missing.length) problems.push(`thiếu nhân vật có tag: ${missing.join(', ')}`);
    if (back !== total) problems.push(`bỏ lọc: bộ đếm ${back}`);
    if (J(after) !== J(before)) problems.push(`bỏ lọc: lưới khác lúc đầu (${after.length} thẻ, trước ${before.length})`);
    return { ok: problems.length === 0, detail: problems.join('; ') || `"${pick}": ${filtered}, lưới ${shown.length} thẻ đều có tag → bỏ lọc: ${back}, lưới như cũ (${after.length} thẻ)` };
  });

  await c.step(C.GRID, async () => {
    const cols = `getComputedStyle(document.querySelector('section[aria-labelledby=explore-all] ul')).gridTemplateColumns.split(' ').length`;
    const widths = `(() => { const w = [...document.querySelectorAll('section[aria-labelledby=explore-all] ul > li')].map((l) => Math.round(l.getBoundingClientRect().width)); return Math.max(...w) - Math.min(...w); })()`;
    const out = [];
    for (const [label, vp] of [['390', 'phone'], ['800', { width: 800 }], ['1280', 'desktop']]) {
      await c.viewport(vp);
      await c.sleep(400);
      out.push([label, await c.evaluate(cols), await c.evaluate(widths)]);
    }
    await c.viewport('phone');
    await c.sleep(300);
    const ok = out[0][1] === 2 && out[1][1] === 3 && out[2][1] === 5 && out.every(([, , w]) => w <= 1);
    return { ok, detail: out.map(([l, n, w]) => `${l}px: ${n} cột${w > 1 ? ` (lệch ${w}px)` : ''}`).join(', ') };
  });

  // ================================================================ hồ sơ nhân vật mẫu + sheet bắt đầu
  await c.step(C.PROFILE, async () => {
    await c.goto('#/explore');
    await c.waitFor('!!document.querySelector("#explore-featured a")', 'nhân vật nổi bật', 15000);
    await c.click('#explore-featured a', 'tên nhân vật nổi bật');
    await c.waitFor('location.hash.startsWith("#/character/")', 'mở hồ sơ nhân vật');
    await c.waitFor(`!!__bot.find({ css: 'button', text: 'Bước vào câu chuyện' })`, 'nút Bước vào câu chuyện', 15000);
    const r = await c.evaluate(`(() => ({
      fields: [...document.querySelectorAll('main input:not([type=hidden]), main textarea, main select, main [contenteditable=true]')].filter(__bot.visible).length,
      name: document.querySelector('main h2')?.innerText.trim() ?? '',
      tabs: !!document.querySelector('[role=tablist][aria-label="Thông tin nhân vật"]'),
    }))()`);
    if (r.name) characterName = r.name;
    await recordTabs('#/character/<id>');
    await scan(await hashNow(c));
    await c.shot('Hồ sơ nhân vật');
    const problems = [];
    if (r.fields) problems.push(`${r.fields} ô nhập liệu`);
    if (!r.tabs) problems.push('không có tab thông tin');
    return { ok: problems.length === 0, detail: problems.join('; ') || r.name };
  });

  await c.step(C.TEMPLATE_PROFILE, async () => {
    const r = await c.evaluate(`(() => {
      const edit = !!__bot.find({ css: 'a, button', textHas: 'Sửa nhân vật' });
      const bar = __bot.all({ css: 'button', text: 'Bước vào câu chuyện' }).map((b) => {
        for (let e = b; e; e = e.parentElement) { const s = getComputedStyle(e); if (s.position === 'fixed') return Math.round(window.innerHeight - e.getBoundingClientRect().bottom); }
        return null;
      }).filter((v) => v !== null);
      return { edit, bar };
    })()`);
    return { ok: !r.edit && r.bar.length > 0 && r.bar[0] <= 1, detail: `${r.edit ? 'CÓ nút Sửa nhân vật · ' : ''}${r.bar.length ? `thanh dính đáy (cách đáy ${r.bar[0]}px)` : 'không có thanh dính đáy'}` };
  });

  await c.step(C.START, async () => {
    await c.click({ css: 'button', text: 'Bước vào câu chuyện' }, 'nút Bước vào câu chuyện');
    await c.waitFor(dialogTitled('Chọn persona'), 'sheet Chọn persona');
    await c.waitFor(`__bot.all({ css: '[role=dialog] [role=radiogroup][aria-label=Persona] label' }).length > 0`, 'danh sách persona', 15000);
    // Mặc định: persona đang dùng (đổi ở sheet Tài khoản) đã được chọn sẵn, "Tuỳ chỉnh story" đang gập.
    const pre = await c.evaluate(`(() => {
      const on = document.querySelector('[role=dialog] [role=radiogroup][aria-label=Persona] input:checked, [role=dialog] [role=radiogroup][aria-label=Persona] [aria-checked=true]');
      const lab = on ? (on.closest('label')?.innerText ?? on.innerText ?? '') : '';
      const disc = __bot.find({ within: '[role=dialog]', css: 'button[aria-expanded]', textHas: 'Tuỳ chỉnh story' });
      return { picked: lab.trim(), folded: disc?.getAttribute('aria-expanded') ?? null };
    })()`);
    c.check(C.START_DEFAULT, !!defaultPersona && pre.picked.includes(defaultPersona) && pre.folded === 'false', `chọn sẵn: "${pre.picked.replace(/\s+/g, ' ').slice(0, 40)}" (persona đang dùng: "${defaultPersona}") · Tuỳ chỉnh story aria-expanded=${pre.folded}`);
    await c.click({ within: '[role=dialog]', css: 'button[aria-expanded]', textHas: 'Tuỳ chỉnh story' }, 'Tuỳ chỉnh story');
    thoughtSwitches.sheet = await c.waitFor(`!!__bot.find({ within: '[role=dialog]', css: '[role=switch]', textHas: 'Đọc suy nghĩ của nhân vật' })`, 'công tắc Đọc suy nghĩ trong sheet', 10000).catch(() => false);
    await c.click({ css: '[role=dialog] [role=radiogroup][aria-label=Persona] label' }, 'persona đầu tiên');
    const checked = await c.evaluate(`!!document.querySelector('[role=dialog] [role=radiogroup][aria-label=Persona] input:checked')`);
    await c.shot('Sheet chọn persona');
    await c.waitFor(`!__bot.find({ within: '[role=dialog]', css: 'button', text: 'Bước vào câu chuyện' })?.disabled`, 'nút bắt đầu bật', 15000);
    await c.click({ within: '[role=dialog]', css: 'button', text: 'Bước vào câu chuyện' }, 'nút Bước vào câu chuyện trong sheet');
    await c.waitFor('/^#\\/chat\\/\\d+$/.test(location.hash)', 'story mở', 15000);
    storyHash = await hashNow(c);
    c.setWhere(storyHash);
    await c.waitFor(`__bot.all({ css: ${J(LAST_REPLY)} }).length > 0`, 'lời chào của nhân vật', 15000);
    const greet = await c.evaluate(`document.querySelector(${J(LAST_REPLY)}).innerText.trim().length`);
    storyOpen = true;
    await scan('chat: lời chào');
    await recordTabs('#/chat/<id>');
    await measure('#/chat/<id>', true);
    await c.shot('Story mở với lời chào');
    return { ok: checked && greet > 20, detail: `persona ${checked ? 'đã chọn' : 'CHƯA chọn'}, lời chào ${greet} ký tự` };
  });
  const needStory = () => { if (!storyOpen) throw new Error('story chưa mở'); };

  // ================================================================ Story: một lượt đầy đủ
  const say = 'Chào cậu, hôm nay trời đẹp quá nhỉ';
  const act = 'mỉm cười kéo ghế ngồi xuống';
  let placeholder = null;
  await c.step(C.PLAYER, async () => {
    needStory();
    placeholder = await c.evaluate(`({ ph: __bot.find(${J(STORY_INPUT)})?.getAttribute('placeholder'), label: __bot.find(${J(STORY_INPUT)})?.getAttribute('aria-label') })`);
    await c.click(STORY_INPUT, 'ô nhập lượt');
    await c.type(`"${say}" *${act}*`);
    await c.evaluate(watchStream(LAST_REPLY));
    await c.click({ label: 'Gửi (Enter)' }, 'nút Gửi');
    await c.waitFor(`!!document.querySelector('article[aria-label="Lượt của bạn"]')`, 'lượt của bạn hiện ra');
    await c.sleep(300);
    await c.shot('Đang chờ trả lời (chấm đang gõ)');
    const r = await c.evaluate(`(() => {
      const turn = [...document.querySelectorAll('article[aria-label="Lượt của bạn"]')].pop();
      const ps = [...turn.querySelectorAll('p')];
      return { dialogue: ps.filter((p) => p.className.includes('bg-user-gradient')).map((p) => p.innerText.trim()),
               narration: ps.filter((p) => p.className.includes('italic')).map((p) => p.innerText.trim()) };
    })()`);
    const problems = [];
    if (r.dialogue.length !== 1) problems.push(`${r.dialogue.length} thẻ lời nói`);
    if (r.dialogue.some((t) => QUOTES.test(t))) problems.push(`lời nói còn ngoặc kép ngoài: ${r.dialogue[0]}`);
    if (r.dialogue[0] && r.dialogue[0] !== say) problems.push(`lời nói khác: ${r.dialogue[0]}`);
    if (!r.narration.some((t) => t.includes(act))) problems.push('không thấy hành động in nghiêng');
    if (r.narration.some((t) => t.includes('*'))) problems.push('hành động còn dấu *');
    return { ok: problems.length === 0, detail: problems.join('; ') || `“${r.dialogue[0]}” + ${r.narration.length} đoạn hành động` };
  });

  let stream = {};
  await c.step(C.STREAM, async () => {
    needStory();
    await waitReplyDone(c);
    stream = (await c.evaluate('window.__stream')) ?? {};
    await scan('chat: sau lượt trả lời');
    await c.shot('Nhân vật trả lời xong');
    const s = stream;
    const ok = s.dotsAt !== null && s.textAt !== null && s.dotsAt <= s.textAt && s.doneAt !== null;
    return { ok, detail: `chấm ${ms(s.dotsAt)} → chữ ${ms(s.textAt)} → xong ${ms(s.doneAt)}` };
  });
  {
    const s = stream;
    const stopGone = storyOpen ? await c.evaluate('!__bot.find({ label: "Dừng" })') : false;
    c.check(C.STOP, s.stopSeen === true && !s.sendWithStop && stopGone, `Dừng ${s.stopSeen ? 'có' : 'KHÔNG có'} lúc sinh${s.sendWithStop ? ', nút Gửi vẫn hiện' : ''}, sinh xong ${stopGone ? 'đã ẩn' : 'VẪN còn'}`);
    c.check(C.WAIT_DOTS, s.dotsAt !== null && (s.waitWords ?? []).length === 0, s.waitWords?.length ? `có chữ: ${s.waitWords[0]}` : `chấm ở ${ms(s.dotsAt)}`);
    c.check(C.LOCKED, (s.lockChecked ?? 0) > 0 && (s.unlocked ?? []).length === 0 && (s.noReason ?? ['?']).length === 0,
      `${s.lockChecked ?? 0} lần soát nút Sửa/Xoá từ đây lúc đang trả lời${s.unlocked?.length ? `, KHÔNG khoá: ${s.unlocked[0]}` : ', đều khoá'}${(s.noReason ?? ['?']).length ? `, KHÔNG có lý do (title): ${(s.noReason ?? ['?'])[0]}` : ` · title: "${s.reason}"`}`);
  }

  let placeInfo = null; // lượt người chơi căn phải + placeholder Story; placeholder DM thêm vào sau bước DM
  if (storyOpen) try {
    const r = await c.evaluate(`(() => {
      const turn = [...document.querySelectorAll('article[aria-label="Lượt của bạn"]')].pop();
      const list = turn.parentElement.getBoundingClientRect();
      const bubble = turn.querySelector('.bg-user-gradient').getBoundingClientRect();
      const avatar = [...turn.querySelectorAll('span[aria-hidden=true]')].find((s) => Math.round(s.getBoundingClientRect().width) === 28);
      return { right: Math.round(list.right - bubble.right), left: Math.round(bubble.left - list.left), avatar: !!avatar,
               avatarRight: avatar ? avatar.getBoundingClientRect().left >= bubble.right - 1 : false };
    })()`);
    placeInfo = r;
  } catch { /* placeInfo = null → check PLACEHOLDER đỏ */ }

  await c.step(C.REPLY_BLOCKS, async () => {
    needStory();
    const r = await c.evaluate(`(() => {
      const turn = [...document.querySelectorAll(${J(LAST_REPLY)})].pop();
      const dialogue = [...turn.querySelectorAll('p')].filter((p) => p.className.includes('text-dialogue') && p.className.includes('rounded-card'));
      const narration = [...turn.querySelectorAll('p')].filter((p) => p.className.includes('italic') && !p.closest('button'));
      const thought = [...turn.querySelectorAll('span.sr-only')].some((s) => s.textContent.startsWith('Suy nghĩ'));
      return { dialogue: dialogue.map((p) => p.innerText.trim()), thought, raw: turn.innerText.includes('[Thought'),
               narr: narration.map((p) => { const s = getComputedStyle(p); return s.fontStyle + '/' + s.borderTopWidth; }) };
    })()`);
    const problems = [];
    if (!r.dialogue.length) problems.push('không có thẻ thoại');
    if (r.dialogue.some((t) => QUOTES.test(t))) problems.push('thẻ thoại còn ngoặc kép');
    if (!r.thought) problems.push('không có thẻ suy nghĩ');
    if (r.raw) problems.push('còn chữ [Thought');
    if (!r.narr.length || r.narr.some((x) => x !== 'italic/0px')) problems.push(`dẫn truyện: ${r.narr.join(', ') || 'không có'}`);
    return { ok: problems.length === 0, detail: problems.join('; ') || `${r.dialogue.length} thẻ thoại, ${r.narr.length} đoạn dẫn truyện nghiêng không viền` };
  });

  await c.step(C.DIRECTIVE, async () => {
    needStory();
    const labelOk = placeholder?.label === 'Lượt của bạn: lời nói, *hành động* hoặc ((chỉ đạo cho AI))';
    const before = await c.evaluate(`document.querySelectorAll('article[aria-label="Lượt của bạn"]').length`);
    await c.click(STORY_INPUT, 'ô nhập lượt');
    await c.type('Chào. ((cho nhân vật đang ghen nhưng không nói ra))');
    await c.click({ label: 'Gửi (Enter)' }, 'nút Gửi');
    await c.waitFor(`document.querySelectorAll('article[aria-label="Lượt của bạn"]').length > ${before}`, 'lượt mới của bạn');
    await waitReplyDone(c);
    const r = await c.evaluate(`(() => {
      const turn = [...document.querySelectorAll('article[aria-label="Lượt của bạn"]')].pop();
      const chip = turn.querySelector('[title="Chỉ đạo cho AI (không hiện trong truyện)"]');
      const story = [...turn.querySelectorAll('p')].map((p) => p.innerText).join(' ');
      return { chip: chip ? chip.innerText.trim() : '', leak: story.includes('((') || story.includes('))') };
    })()`);
    await c.shot('Lượt có chỉ đạo');
    return { ok: labelOk && r.chip.includes('đang ghen') && !r.leak, detail: `aria-label ${labelOk ? 'đúng' : `sai: ${placeholder?.label}`} · chip: "${r.chip}"${r.leak ? ' · LỘ (( trong truyện' : ''}` };
  });

  await c.step(C.THOUGHT, async () => {
    needStory();
    const card = { ...lastReplySel, css: 'button[aria-pressed]' };
    await c.waitFor(`!!__bot.find(${J(card)})`, 'thẻ suy nghĩ trong lời trả lời');
    const blurOf = `(() => { const b = __bot.find(${J(card)}); const s = b.querySelector('span[class*=font-story]'); return getComputedStyle(s).filter; })()`;
    const before = await c.evaluate(blurOf);
    const hint = await c.exists({ ...card, textHas: 'Chạm để lắng nghe' });
    await c.shot('Thẻ suy nghĩ đang mờ');
    await c.click(card, 'thẻ suy nghĩ');
    await c.sleep(450);
    const after = await c.evaluate(blurOf);
    const pressed = await c.evaluate(`__bot.find(${J(card)}).getAttribute('aria-pressed')`);
    await c.shot('Thẻ suy nghĩ đã mở');
    const ok = before.includes('blur') && hint && !after.includes('blur') && pressed === 'true';
    return { ok, detail: `trước: ${before}, sau: ${after}, aria-pressed=${pressed}` };
  });

  const thoughtMenu = { css: 'button[aria-haspopup=dialog]', textHas: 'Suy nghĩ' };
  const thoughtPanel = '[role=dialog][aria-label="Suy nghĩ của nhân vật"]';
  await c.step(C.ALWAYS, async () => {
    needStory();
    await c.click(thoughtMenu, 'nút Suy nghĩ');
    const sw = { within: thoughtPanel, css: '[role=switch]', textHas: 'Luôn hiện suy nghĩ' };
    await c.waitFor(`!!__bot.find(${J(sw)})`, 'công tắc Luôn hiện suy nghĩ');
    await c.click(sw, 'công tắc Luôn hiện suy nghĩ');
    await c.waitFor(`__bot.find(${J(sw)})?.getAttribute('aria-checked') === 'true'`, 'công tắc bật');
    await c.sleep(400);
    const r = await c.evaluate(`({
      pressable: document.querySelectorAll('article button[aria-pressed] span[class*=font-story]').length,
      blurred: [...document.querySelectorAll('article span[class*=font-story][class*=italic]')].filter((s) => getComputedStyle(s).filter.includes('blur')).length,
      shown: [...document.querySelectorAll('article span.sr-only')].filter((s) => s.textContent.startsWith('Suy nghĩ')).length,
      saved: localStorage.getItem('lyris.revealThoughts'),
    })`);
    await c.press('Escape');
    await c.shot('Luôn hiện suy nghĩ');
    // Trả lại như cũ cho các bước sau.
    await c.click(thoughtMenu, 'nút Suy nghĩ');
    await c.click(sw, 'công tắc Luôn hiện suy nghĩ (tắt)');
    await c.waitFor(`__bot.find(${J(sw)})?.getAttribute('aria-checked') === 'false'`, 'công tắc tắt');
    await c.press('Escape');
    const ok = r.shown > 0 && r.pressable === 0 && r.blurred === 0 && (r.saved === 'true' || r.saved === '1');
    return { ok, detail: `${r.shown} thẻ, ${r.blurred} thẻ còn mờ, lyris.revealThoughts=${r.saved}` };
  });

  await c.step(C.THOUGHT_STYLE, async () => {
    needStory();
    const id = storyHash.match(/\d+/)[0];
    const style = () => c.evaluate(`fetch('/api/stories/${id}').then((r) => r.json()).then((s) => (s.story ?? s).thought_style)`);
    const before = await style();
    await c.click(thoughtMenu, 'nút Suy nghĩ');
    const radios = await c.evaluate(`__bot.all({ within: ${J(thoughtPanel)}, css: '[role=radio]' }).map((b) => [b.innerText.split('\\n')[0].trim(), b.getAttribute('aria-checked')])`);
    const other = radios.find(([, on]) => on === 'false');
    if (!other) throw new Error(`không có kiểu suy nghĩ để đổi: ${J(radios)}`);
    await c.click({ within: thoughtPanel, css: '[role=radio]', textHas: other[0] }, `kiểu ${other[0]}`);
    await c.waitFor(`__bot.find({ within: ${J(thoughtPanel)}, css: '[role=radio]', textHas: ${J(other[0])} })?.getAttribute('aria-checked') === 'true'`, 'kiểu mới được chọn', 8000);
    await c.sleep(500);
    const after = await style();
    await c.shot('Đổi kiểu suy nghĩ');
    const back = radios.find(([, on]) => on === 'true');
    if (back) await c.click({ within: thoughtPanel, css: '[role=radio]', textHas: back[0] }, `kiểu ${back[0]} (trả lại)`);
    await c.sleep(400);
    await c.press('Escape');
    const names = radios.map(([n]) => n);
    const ok = names.includes('Lồng trong truyện') && names.includes('Một đoạn ở cuối') && after !== before && !!after;
    return { ok, detail: `${names.join(' / ')} · thought_style ${before} → ${after}` };
  });

  await c.step(C.THOUGHTS_OFF, async () => {
    needStory();
    const thoughtCount = `[...document.querySelectorAll('article span.sr-only')].filter((s) => s.textContent.startsWith('Suy nghĩ')).length`;
    const before = await c.evaluate(thoughtCount);
    await c.click(thoughtMenu, 'nút Suy nghĩ');
    const sw = { within: thoughtPanel, css: '[role=switch]', textHas: 'Đọc suy nghĩ của nhân vật' };
    await c.waitFor(`!!__bot.find(${J(sw)})`, 'công tắc Đọc suy nghĩ');
    await c.shot('Menu suy nghĩ');
    await c.click(sw, 'công tắc Đọc suy nghĩ');
    await c.waitFor(`__bot.find(${J(sw)})?.getAttribute('aria-checked') === 'false'`, 'công tắc tắt');
    await c.sleep(300);
    const after = await c.evaluate(thoughtCount);
    await c.press('Escape');
    thoughtSwitches.headerLabel = await c.exists({ css: 'button[aria-haspopup=dialog]', label: 'Suy nghĩ (đang ẩn)' });
    await c.shot('Đã tắt Đọc suy nghĩ');
    await c.click({ css: 'button[aria-haspopup=dialog]', labelStarts: 'Suy nghĩ' }, 'nút Suy nghĩ (đang ẩn)');
    await c.click(sw, 'công tắc Đọc suy nghĩ');
    await c.waitFor(`__bot.find(${J(sw)})?.getAttribute('aria-checked') === 'true'`, 'công tắc bật lại');
    await c.press('Escape');
    const back = await c.evaluate(thoughtCount);
    return { ok: before > 0 && after === 0 && back > 0, detail: `thẻ suy nghĩ: ${before} → ${after} → bật lại ${back}` };
  });

  await c.step(C.SETTINGS, async () => {
    needStory();
    await c.click({ label: 'Thiết lập story' }, 'nút Thiết lập story');
    await c.waitFor(dialogTitled('Thiết lập story'), 'panel Thiết lập story');
    await c.sleep(400);
    const text = await c.evaluate(`document.querySelector('[role=dialog]').innerText`);
    const want = ['Tiêu đề', 'Bối cảnh', 'Ngôn ngữ', 'Kiểu quan hệ', 'Ngôi kể', 'Suy nghĩ của nhân vật ở Story'];
    const missing = want.filter((w) => !text.includes(w));
    thoughtSwitches.settings = await c.exists({ within: '[role=dialog]', css: '[role=switch]', textHas: 'Đọc suy nghĩ của nhân vật' });
    await scan('chat: thiết lập story');
    await c.click({ within: '[role=dialog]', css: 'button', textHas: 'Xoá story' }, 'nút Xoá story…');
    const confirm = await c.waitFor(`!!__bot.find({ within: '[role=alertdialog][aria-label="Xác nhận xoá story"]', css: 'button', text: 'Xoá vĩnh viễn' })`, 'hỏi lại trước khi xoá', 5000).catch(() => false);
    await c.shot('Xoá story hỏi lại');
    // Bấm đúng nút 'Huỷ' (không có nút này thì check đỏ), rồi hỏi server: story vẫn còn.
    await c.click({ within: '[role=alertdialog][aria-label="Xác nhận xoá story"]', css: 'button', text: 'Huỷ' }, 'nút Huỷ');
    await c.waitFor(`!document.querySelector('[role=alertdialog][aria-label="Xác nhận xoá story"]')`, 'hộp hỏi lại đóng sau Huỷ', 5000);
    await c.press('Escape');
    await c.waitFor(`!${dialogTitled('Thiết lập story')}`, 'đóng panel');
    const storyId = (await hashNow(c)).match(/^#\/chat\/(\d+)$/)?.[1];
    const status = storyId ? await c.evaluate(`fetch('/api/stories/${storyId}').then((r) => r.status)`) : 0;
    const stillThere = status === 200;
    return { ok: missing.length === 0 && thoughtSwitches.settings && !!confirm && stillThere,
      detail: `${missing.length ? `thiếu: ${missing.join(', ')} · ` : ''}${thoughtSwitches.settings ? '' : 'không có công tắc Đọc suy nghĩ · '}${confirm ? 'có hỏi lại "Xoá vĩnh viễn"' : 'KHÔNG hỏi lại'} · bấm Huỷ: GET /api/stories/${storyId ?? '?'} → ${status}` };
  });

  await c.step(C.ACTIONS, async () => {
    needStory();
    const labels = ['Thích', 'Chê', 'Sửa', 'Xoá từ đây'];
    const has = [];
    for (const l of labels) if (await c.exists({ ...lastReplySel, css: 'button', label: l })) has.push(l);
    await c.click({ ...lastReplySel, css: 'button', label: 'Xoá từ đây' }, 'nút Xoá từ đây');
    const box = '[role=alertdialog][aria-label="Xác nhận xoá"]';
    await c.waitFor(`!!__bot.find({ within: ${J(box)}, css: 'button', text: 'Xoá' })`, 'hộp Xác nhận xoá');
    const text = await c.evaluate(`document.querySelector(${J(box)}).innerText`);
    const phoneWidth = await c.evaluate('window.innerWidth');
    if (phoneWidth <= 400) {
      // Hàng thao tác dưới lượt cuối (Tạo lại, Thích, Chê, Sửa, Xoá từ đây, Báo cáo…) và Huỷ/Xoá của hộp hỏi lại.
      const inRow = await c.evaluate(`(() => { const a = [...document.querySelectorAll(${J(LAST_REPLY)})].pop(); return a ? [...a.querySelectorAll('button')].filter(__bot.visible).map((b) => [__bot.name(b), Math.round(b.getBoundingClientRect().width), Math.round(b.getBoundingClientRect().height)]) : []; })()`);
      rowMeasured += inRow.length;
      for (const [n, w, h] of inRow) if (w < 44 || h < 44) rowSizes.push(`lượt chat: ${n} ${w}×${h}px`);
      await measureButtons('hộp Xác nhận xoá', `${box} button`);
    } else rowSizes.push(`không đo được: màn rộng ${phoneWidth}px (cần 390px)`);
    await c.shot('Xoá từ đây hỏi lại');
    await c.click({ within: box, css: 'button', text: 'Huỷ' }, 'nút Huỷ');
    const ok = has.length === labels.length && text.includes('Xoá lượt này và mọi lượt sau?');
    return { ok, detail: `có: ${has.join(', ')}${ok ? '' : ` · hộp: ${text.slice(0, 60)}`}` };
  });

  await c.step(C.REGEN, async () => {
    needStory();
    const textOf = `__bot.find(${J({ css: LAST_REPLY, last: true })})?.innerText ?? ''`;
    const before = await c.evaluate(textOf);
    await c.click({ ...lastReplySel, label: 'Tạo lại câu trả lời' }, 'nút Tạo lại câu trả lời');
    await c.waitFor('!!__bot.find({ label: "Dừng" })', 'bắt đầu tạo lại', 5000).catch(() => {});
    await waitReplyDone(c);
    await c.waitFor(`!!__bot.find({ within: '[role=group][aria-label="Các phiên bản trả lời"]', css: 'span', textHas: '/' })`, 'bộ chuyển phiên bản');
    const counter = await c.evaluate(`__bot.find({ within: '[role=group][aria-label="Các phiên bản trả lời"]', css: 'span', textHas: '/' }).innerText.trim()`);
    const after = await c.evaluate(textOf);
    await c.shot('Tạo lại: phiên bản 2');
    return { ok: counter === '2/2' && after !== before, detail: `phiên bản ${counter}${after === before ? ', chữ không đổi' : ''}` };
  });

  await c.step(C.REPORT, async () => {
    needStory();
    await c.click({ ...lastReplySel, label: 'Báo cáo' }, 'nút Báo cáo');
    await c.waitFor(dialogTitled('Báo cáo câu trả lời'), 'sheet Báo cáo câu trả lời');
    const reasons = await c.evaluate(`__bot.all({ within: '[role=dialog] [role=radiogroup][aria-label="Lý do"]', css: '[role=radio]' }).length`);
    await scan('chat: sheet báo cáo');
    await c.shot('Sheet báo cáo câu trả lời');
    await c.press('Escape');
    await c.waitFor(`!${dialogTitled('Báo cáo câu trả lời')}`, 'đóng sheet báo cáo');
    return { ok: reasons > 0, detail: `${reasons} lý do` };
  });

  // ================================================================ menu "+"
  const plus = { css: 'button[aria-haspopup=menu]', label: 'Thêm' };
  await c.step(C.MENU_SIZE, async () => {
    needStory();
    const btn = await c.evaluate(`(() => { const b = __bot.find(${J(plus)}); const r = b.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height), exp: b.getAttribute('aria-expanded') }; })()`);
    await c.click(plus, 'nút +');
    await c.waitFor(`!!document.querySelector('[role=menu]')`, 'menu +');
    const phone = await c.evaluate(`(() => {
      const m = document.querySelector('[role=menu]'); const s = getComputedStyle(m); const r = m.getBoundingClientRect();
      const scrim = [...document.querySelectorAll('div[aria-hidden=true]')].some((d) => getComputedStyle(d).position === 'fixed' && d.className.includes('bg-scrim') && __bot.visible(d));
      return { pos: s.position, gap: Math.round(window.innerHeight - r.bottom), scrim, exp: __bot.find(${J(plus)}).getAttribute('aria-expanded') };
    })()`);
    await c.shot('Menu cộng ở điện thoại');
    await closeMenu(c);
    await c.viewport('desktop');
    await c.sleep(400);
    await c.click(plus, 'nút + (desktop)');
    await c.waitFor(`!!document.querySelector('[role=menu]')`, 'menu + (desktop)');
    const desk = await c.evaluate(`(() => {
      const m = document.querySelector('[role=menu]').getBoundingClientRect(); const b = __bot.find(${J(plus)}).getBoundingClientRect();
      return { pos: getComputedStyle(document.querySelector('[role=menu]')).position, above: m.bottom <= b.top + 1 };
    })()`);
    await c.shot('Menu cộng ở máy tính');
    await closeMenu(c);
    await c.viewport('phone');
    await c.sleep(300);
    const ok = btn.w >= 44 && btn.h >= 44 && btn.exp === 'false' && phone.exp === 'true' && phone.pos === 'fixed' && phone.gap <= 1 && phone.scrim && desk.pos === 'absolute' && desk.above;
    return { ok, detail: `nút ${btn.w}×${btn.h}, aria-expanded ${btn.exp}→${phone.exp} · 390: ${phone.pos}, cách đáy ${phone.gap}px, nền mờ ${phone.scrim ? 'có' : 'KHÔNG'} · 1280: ${desk.pos}${desk.above ? ', phía trên nút' : ', KHÔNG ở trên nút'}` };
  });

  await c.step(C.MENU_IMAGE, async () => {
    needStory();
    await c.click(plus, 'nút +');
    const item = { css: '[role=menu] [role=menuitem]', textHas: 'Gửi hình ảnh' };
    await c.waitFor(`!!__bot.find(${J(item)})`, 'mục Gửi hình ảnh');
    const r = await c.evaluate(`(() => { const b = __bot.find(${J(item)}); return { dis: b.getAttribute('aria-disabled') === 'true' || b.disabled, text: b.innerText }; })()`);
    await closeMenu(c);
    const ok = r.dis && r.text.includes('Sắp có') && r.text.split('\n').filter((l) => l.trim()).length >= 3;
    return { ok, detail: r.text.replace(/\n+/g, ' · ') };
  });

  await c.step(C.MENU_KEYS, async () => {
    needStory();
    await c.click(plus, 'nút +');
    await c.waitFor(`document.activeElement?.getAttribute('role') === 'menuitem'`, 'focus vào menu', 3000).catch(() => {});
    const active = () => c.evaluate(`document.activeElement?.getAttribute('role') === 'menuitem' ? document.activeElement.innerText.split('\\n')[0].trim() : '(' + (document.activeElement?.getAttribute('aria-label') || document.activeElement?.tagName) + ')'`);
    const trail = [await active()];
    for (const k of ['ArrowDown', 'ArrowDown', 'ArrowUp', 'Home', 'End']) { await c.press(k); trail.push(`${k}:${await active()}`); }
    await c.press('Escape');
    const after = await c.evaluate(`({ menu: !!document.querySelector('[role=menu]'), focus: document.activeElement?.getAttribute('aria-label') })`);
    const items = ['Nhận gợi ý', 'Xem sự kiện', 'Gửi hình ảnh'];
    const visited = items.filter((i) => trail.some((t) => t.endsWith(i)));
    const ok = visited.length === 3 && trail[4].endsWith('Nhận gợi ý') && trail[5].endsWith('Gửi hình ảnh') && !after.menu && after.focus === 'Thêm';
    return { ok, detail: `${trail.join(' → ')} · Esc: menu ${after.menu ? 'còn' : 'đóng'}, focus "${after.focus}"` };
  });

  await c.step(C.SUGGEST, async () => {
    needStory();
    await closeOverlays(c);
    await c.click(plus, 'nút +');
    await c.waitFor(`!!__bot.find({ css: '[role=menu] [role=menuitem]', textHas: 'Nhận gợi ý' })`, 'menu +');
    await c.shot('Menu cộng');
    await c.evaluate(watchLoop(
      'const log = window.__suggest = { cancel: false, dots: false };',
      `const area = document.querySelector('[role=group][aria-label="Gợi ý cho bạn"]') || document.body;
      if (__bot.find({ label: 'Huỷ gợi ý' })) log.cancel = true;
      if ([...area.querySelectorAll('.typing-bounce')].some(__bot.visible) && __bot.find({ label: 'Huỷ gợi ý' })) log.dots = true;`,
      "!!__bot.find({ labelStarts: 'Gửi: ' })", 15000));
    await c.click({ css: '[role=menu] [role=menuitem]', textHas: 'Nhận gợi ý' }, 'Nhận gợi ý');
    await c.waitFor(`__bot.all({ within: '[role=group][aria-label="Gợi ý cho bạn"]', css: 'button', labelStarts: 'Gửi: ' }).length > 0`, 'gợi ý hiện ra', 15000);
    const items = await c.evaluate(`__bot.all({ within: '[role=group][aria-label="Gợi ý cho bạn"]', css: 'button', labelStarts: 'Gửi: ' }).map((b) => b.innerText.trim())`);
    await scan('chat: gợi ý');
    await c.shot('Gợi ý cho bạn');
    return { ok: items.length === 3, detail: `${items.length} gợi ý` };
  });

  await c.step(C.SUGGEST_TAP, async () => {
    needStory();
    const waiting = await c.evaluate('window.__suggest ?? {}');
    const card = { within: '[role=group][aria-label="Gợi ý cho bạn"]', css: 'button', labelStarts: 'Gửi: ' };
    const text = await c.evaluate(`__bot.find(${J(card)}).innerText.trim()`);
    const before = await c.evaluate(`document.querySelectorAll('article[aria-label="Lượt của bạn"]').length`);
    await c.click(card, 'thẻ gợi ý đầu tiên');
    await c.waitFor(`document.querySelectorAll('article[aria-label="Lượt của bạn"]').length > ${before}`, 'lượt mới từ gợi ý');
    const gone = await c.evaluate(`!document.querySelector('[role=group][aria-label="Gợi ý cho bạn"] button[aria-label^="Gửi: "]')`);
    const sent = await c.evaluate(`[...document.querySelectorAll('article[aria-label="Lượt của bạn"]')].pop().innerText`);
    await waitReplyDone(c);
    const core = (s) => s.replace(/["“”*]/g, '').replace(/\s+/g, ' ').trim();
    const ok = waiting.cancel && waiting.dots && gone && core(sent).includes(core(text).split(' ').slice(-4).join(' '));
    return { ok, detail: `lúc chờ: ${waiting.dots ? 'ba chấm' : 'KHÔNG ba chấm'}, ${waiting.cancel ? 'có Huỷ gợi ý' : 'KHÔNG có Huỷ gợi ý'} · gửi "${core(text)}"${gone ? '' : ' · nhóm gợi ý vẫn còn'}` };
  });

  // ================================================================ sự kiện và ngăn trái tim
  await c.step(C.EVENTS, async () => {
    needStory();
    await closeOverlays(c);
    await c.click(plus, 'nút +');
    await c.click({ css: '[role=menu] [role=menuitem]', textHas: 'Xem sự kiện' }, 'Xem sự kiện');
    await c.waitFor(dialogTitled('Sự kiện'), 'sheet Sự kiện');
    const tabNames = await c.evaluate(`__bot.all({ within: '[role=tablist][aria-label="Loại sự kiện"]', css: '[role=tab]' }).map((t) => t.innerText.trim())`);
    await scan('chat: sự kiện');
    await c.shot('Sheet Sự kiện');
    return { ok: tabNames.includes('Dòng thời gian') && tabNames.includes('Khoảnh khắc'), detail: tabNames.join(' | ') };
  });

  await c.step(C.TIMELINE_JUMP, async () => {
    needStory();
    if (!(await c.evaluate(dialogTitled('Sự kiện')))) {
      await c.click(plus, 'nút +');
      await c.click({ css: '[role=menu] [role=menuitem]', textHas: 'Xem sự kiện' }, 'Xem sự kiện');
    }
    const entry = { within: '[role=dialog] [role=tabpanel]', css: 'li > button', textHas: 'Story' };
    await c.waitFor(`!!__bot.find(${J(entry)})`, 'mục Story trong dòng thời gian', 15000);
    const info = await c.evaluate(`(() => { const all = __bot.all(${J(entry)}); const b = all[all.length - 1]; return { n: all.length, text: b.innerText.replace('Đi tới lượt này.', '').split('\\n').map((l) => l.trim()).filter(Boolean).slice(0, 2).join(' · ') }; })()`);
    await c.click({ ...entry, last: true }, 'mục Story cũ nhất');
    await c.waitFor(`!${dialogTitled('Sự kiện')}`, 'sheet đóng');
    await c.waitFor(`!!document.querySelector('.turn-highlight')`, 'lượt được đánh dấu', 5000);
    // Cuộn mượt: chờ tới khi lượt đó nằm trong màn hình (tối đa 4 giây).
    await c.waitFor(`(() => { const r = document.querySelector('.turn-highlight').getBoundingClientRect(); return r.bottom > 0 && r.top < window.innerHeight; })()`, 'lượt vào màn hình', 4000).catch(() => {});
    const r = await c.evaluate(`(() => { const el = document.querySelector('.turn-highlight'); const r = el.getBoundingClientRect();
      return { inView: r.bottom > 0 && r.top < window.innerHeight, focused: document.activeElement === el, label: el.getAttribute('aria-label') }; })()`);
    await c.shot('Nhảy tới lượt từ dòng thời gian');
    const timeOk = /\d{1,2}:\d{2}/.test(info.text);
    return { ok: r.inView && r.focused && timeOk, detail: `${info.n} mục Story, chạm "${info.text}" → ${r.label}${r.inView ? ' trong màn hình' : ' NGOÀI màn hình'}${r.focused ? ', có focus' : ''}` };
  });

  await c.step(C.HEART, async () => {
    needStory();
    await closeOverlays(c);
    await c.click({ label: 'Cảm xúc & ký ức' }, 'nút trái tim');
    await c.waitFor(dialogTitled('Cảm xúc & ký ức'), 'ngăn Cảm xúc & ký ức');
    await c.sleep(800);
    const meters = await c.evaluate(`__bot.all({ within: '[role=dialog]', css: '[role=meter]' }).map((m) => m.getAttribute('aria-label'))`);
    await scan('chat: ngăn trái tim');
    await c.shot('Ngăn cảm xúc và ký ức');
    return { ok: meters.length === 6, detail: meters.join(', ') };
  });

  await c.step(C.HEART_DIRECTIVE, async () => {
    needStory();
    const r = await c.evaluate(`(() => {
      const d = document.querySelector('[role=dialog]');
      const h = [...d.querySelectorAll('h2, h3, h4')].find((x) => x.innerText.trim() === 'Chỉ dẫn diễn xuất');
      const text = h?.closest('section')?.innerText.replace('Chỉ dẫn diễn xuất', '').trim() ?? '';
      const pct = [...d.querySelectorAll('[role=meter]')].map((m) => m.getAttribute('aria-valuetext'));
      return { has: !!h, text, pct };
    })()`);
    const ok = r.has && r.text.length > 0 && r.pct.length === 6 && r.pct.every((p) => /^\d+%$/.test(p ?? ''));
    return { ok, detail: `${r.has ? `chỉ dẫn: "${r.text.slice(0, 50)}"` : 'không có Chỉ dẫn diễn xuất'} · ${r.pct.join(' ')}` };
  });

  await c.step(C.HEART_MEMORY, async () => {
    needStory();
    await c.waitFor(`__bot.all({ within: '[role=dialog]', css: 'button', labelStarts: 'Quên: ' }).length > 0`, 'ký ức có nút Quên', 15000);
    const r = await c.evaluate(`(() => {
      const d = document.querySelector('[role=dialog]');
      const forget = __bot.all({ within: '[role=dialog]', css: 'button', labelStarts: 'Quên: ' }).length;
      const kinds = [...d.querySelectorAll('li')].map((li) => li.innerText).filter((t) => /Sự kiện|Điều đã biết/.test(t)).length;
      return { forget, kinds };
    })()`);
    await c.shot('Ký ức trong ngăn trái tim');
    await c.press('Escape');
    await c.waitFor(`!${dialogTitled('Cảm xúc & ký ức')}`, 'đóng ngăn trái tim');
    const header = await c.evaluate(`document.querySelector('header').innerText`);
    const scene = header.includes('Quán trà nhỏ cuối phố') && header.includes('·') && header.includes('Chiều mưa');
    return { ok: r.forget > 0 && r.kinds > 0 && scene, detail: `${r.forget} nút Quên, ${r.kinds} ký ức có nhãn · header: ${scene ? 'có nơi chốn · thời gian' : header.replace(/\n+/g, ' | ').slice(0, 80)}` };
  });

  // ================================================================ DM
  const modeGroup = '[role=radiogroup][aria-label="Chế độ hiển thị"]';
  let dmInfo = null;
  await c.step(C.DM, async () => {
    needStory();
    await closeOverlays(c);
    await c.click({ within: modeGroup, css: '[role=radio]', text: 'DM' }, 'nút DM');
    const dmInput = { css: 'textarea', labelStarts: 'Tin nhắn cho' };
    await c.waitFor(`!!__bot.find(${J(dmInput)})`, 'ô nhắn tin DM');
    const pre = await c.evaluate(`({
      ph: __bot.find(${J(dmInput)}).getAttribute('placeholder'),
      chip: (document.body.innerText.match(/\\d+ lượt trong truyện/) || [''])[0],
      leak: /nghiêng đầu|tách trà|bật cười|kéo ghế ngồi xuống/.test(document.body.innerText),
    })`);
    await c.click(dmInput, 'ô nhắn tin');
    await c.type('Đang làm gì đấy?');
    await c.evaluate(watchStream('[aria-label^="Tin nhắn của "]:not([aria-label="Tin nhắn của bạn"])'));
    await c.click({ label: 'Gửi (Enter)' }, 'nút Gửi');
    await c.waitFor(`!!document.querySelector('[aria-label="Tin nhắn của bạn"]')`, 'tin nhắn của bạn');
    await c.sleep(300);
    await c.shot('DM: bong bóng ba chấm');
    await waitReplyDone(c);
    const w = await c.evaluate('window.__stream');
    const look = await c.evaluate(`(() => {
      const mine = [...document.querySelectorAll('article[aria-label="Tin nhắn của bạn"]')].pop();
      const theirs = [...document.querySelectorAll('article[aria-label^="Tin nhắn của "]:not([aria-label="Tin nhắn của bạn"])')];
      const foot = mine ? [...mine.querySelectorAll('p')].map((p) => p.innerText.trim()).find((t) => /Đã gửi|Đã xem/.test(t)) ?? '' : '';
      const avatar = theirs.some((a) => [...a.querySelectorAll('span[aria-hidden=true]')].some((s) => Math.round(s.getBoundingClientRect().width) === 28 && __bot.visible(s)));
      const thought = theirs.some((a) => [...a.querySelectorAll('span.sr-only')].some((s) => s.textContent.startsWith('Suy nghĩ')) && a.querySelector('[class*="text-[15px]"]'));
      return { replies: theirs.length, foot, avatar, thought };
    })()`);
    dmInfo = { pre, w, look };
    if ((await c.evaluate('window.innerWidth')) <= 400) await measure('#/chat/<id> DM', true);
    await scan('chat: DM');
    await c.shot('Chế độ DM');
    // Tắt "Đọc suy nghĩ" ngay ở DM: thẻ suy nghĩ của DM cũng biến mất.
    await c.click(thoughtMenu, 'nút Suy nghĩ (DM)');
    const sw = { within: thoughtPanel, css: '[role=switch]', textHas: 'Đọc suy nghĩ của nhân vật' };
    await c.click(sw, 'công tắc Đọc suy nghĩ (DM)');
    await c.waitFor(`__bot.find(${J(sw)})?.getAttribute('aria-checked') === 'false'`, 'công tắc tắt (DM)');
    await c.press('Escape');
    await c.sleep(300);
    thoughtSwitches.dmHidden = await c.evaluate(`[...document.querySelectorAll('article span.sr-only')].filter((s) => s.textContent.startsWith('Suy nghĩ')).length === 0`);
    await c.click({ css: 'button[aria-haspopup=dialog]', labelStarts: 'Suy nghĩ' }, 'nút Suy nghĩ (đang ẩn, DM)');
    await c.click(sw, 'công tắc Đọc suy nghĩ (bật lại)');
    await c.waitFor(`__bot.find(${J(sw)})?.getAttribute('aria-checked') === 'true'`, 'công tắc bật lại (DM)');
    await c.press('Escape');
    await c.click({ within: modeGroup, css: '[role=radio]', text: 'Story' }, 'nút Story');
    await c.waitFor(`!!__bot.find(${J(STORY_INPUT)})`, 'quay lại ô nhập Story');
    const storyTurns = await c.evaluate(`document.querySelectorAll(${J(LAST_REPLY)}).length`);
    await c.shot('Quay lại Story');
    return { ok: look.replies > 0 && storyTurns > 0, detail: `${look.replies} tin của nhân vật trong DM, ${storyTurns} lượt Story khi quay lại` };
  });
  {
    const d = dmInfo;
    c.check(C.DM_LOOK, !!d && /Đã gửi|Đã xem/.test(d.look.foot) && d.look.avatar && d.w?.dotsBubbleAvatar === true,
      d ? `chân: "${d.look.foot || '—'}" · avatar ${d.look.avatar ? 'có' : 'KHÔNG'} · ba chấm cạnh avatar ${d.w?.dotsBubbleAvatar ? 'có' : 'KHÔNG'}` : 'DM chưa chạy');
    c.check(C.DM_OTHER, !!d && !!d.pre.chip && !d.pre.leak, d ? `nhãn "${d.pre.chip || '—'}"${d.pre.leak ? ' · LỘ chữ của lượt Story' : ''}` : 'DM chưa chạy');
    c.check(C.DM_THOUGHT, !!d && d.look.thought, d ? (d.look.thought ? 'có thẻ suy nghĩ thu gọn' : 'không có thẻ suy nghĩ trong DM') : 'DM chưa chạy');
    const r = placeInfo;
    const ok = placeholder?.ph === 'Nhập lời thoại vào "…"' && d?.pre.ph === 'Nhắn tin…' && !!r && r.avatar && r.avatarRight && r.right < r.left;
    c.check(C.PLACEHOLDER, ok, `Story: ${placeholder?.ph ?? '—'} · DM: ${d?.pre.ph ?? '—'}${r ? ` · lề phải ${r.right}px, lề trái ${r.left}px · avatar ${r.avatar ? (r.avatarRight ? 'bên phải' : 'sai chỗ') : 'KHÔNG có'}` : ''}`);
  }
  c.check(C.THOUGHT_SWITCHES, thoughtSwitches.headerLabel && thoughtSwitches.dmHidden === true && !!thoughtSwitches.sheet && thoughtSwitches.settings,
    `header "Suy nghĩ (đang ẩn)": ${thoughtSwitches.headerLabel ? 'có' : 'KHÔNG'} · DM ẩn thẻ: ${thoughtSwitches.dmHidden} · sheet bắt đầu: ${thoughtSwitches.sheet ? 'có' : 'KHÔNG'} · Thiết lập story: ${thoughtSwitches.settings ? 'có' : 'KHÔNG'}`);

  // ================================================================ hub: tìm story
  await c.step(C.HUB_SEARCH, async () => {
    await c.goto('#/');
    await c.waitFor(`document.querySelectorAll('section[aria-label="Story của bạn"] a[href^="#/chat/"]').length > 1`, 'danh sách story', 15000);
    const rows = `[...document.querySelectorAll('section[aria-label="Story của bạn"] a[href^="#/chat/"]')].map((a) => a.innerText)`;
    const all = await c.evaluate(rows);
    const dirty = all.filter((t) => t.includes('[Thought') || t.includes('(('));
    const query = characterName || all[0].split('\n')[0];
    const search = { field: 'Tìm story' };
    await c.fill(search, query, 'ô Tìm story');
    await c.sleep(300);
    const hit = await c.evaluate(rows);
    await c.shot('Tìm story');
    await c.fill(search, 'zzzz khong co', 'ô Tìm story (không khớp)');
    await c.sleep(300);
    const none = await c.evaluate(rows);
    const empty = await c.evaluate(`document.body.innerText.includes('Không có story nào khớp')`);
    await c.fill(search, '', 'xoá ô Tìm story');
    const fold = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
    const ok = hit.length > 0 && hit.every((t) => fold(t).includes(fold(query))) && none.length === 0 && empty && dirty.length === 0;
    return { ok, detail: `${all.length} story · "${query}": ${hit.length} · không khớp: ${none.length}${empty ? ' (có câu báo)' : ''}${dirty.length ? ` · xem trước bẩn: ${dirty[0].slice(0, 60)}` : ''}` };
  });

  // ================================================================ thế giới mở khoá trong story của nhân vật seed
  await c.step(C.LORE_UNLOCK, async () => {
    if (!ownCard) throw new Error('chưa mở được nhân vật trong Studio');
    await c.goto(`#/character/${ownCard.id}`);
    await c.waitFor(`!!__bot.find({ css: 'button', text: 'Tiếp tục story' }) || !!__bot.find({ css: 'button', text: 'Bước vào câu chuyện' })`, 'hồ sơ nhân vật seed', 15000);
    if (await c.exists({ css: 'button', text: 'Tiếp tục story' })) await c.click({ css: 'button', text: 'Tiếp tục story' }, 'nút Tiếp tục story');
    else throw new Error('nhân vật seed không có story để tiếp tục');
    await c.waitFor('/^#\\/chat\\/\\d+$/.test(location.hash)', 'story của nhân vật seed', 15000);
    await c.waitFor(`!!__bot.find(${J(STORY_INPUT)})`, 'ô nhập Story', 15000);
    await c.click(STORY_INPUT, 'ô nhập lượt');
    await c.type(`Chiều nay mình ra ${loreKey} đi dạo nhé.`);
    await c.click({ label: 'Gửi (Enter)' }, 'nút Gửi');
    await waitReplyDone(c);
    await c.click({ label: 'Cảm xúc & ký ức' }, 'nút trái tim');
    await c.waitFor(dialogTitled('Cảm xúc & ký ức'), 'ngăn Cảm xúc & ký ức');
    const entry = { within: '[role=dialog]', css: 'button[aria-expanded]', textHas: loreTitle };
    await c.waitFor(`!!__bot.find(${J(entry)})`, `mục "${loreTitle}" trong Thế giới đã mở khoá`, 10000);
    await c.click(entry, `mục ${loreTitle}`);
    const jump = await c.waitFor(`!!__bot.find({ within: '[role=dialog]', css: 'button', text: 'Xem lúc được nhắc tới lần đầu' })`, 'nút Xem lúc được nhắc tới lần đầu', 5000).catch(() => false);
    const section = await c.evaluate(`[...document.querySelectorAll('[role=dialog] h2, [role=dialog] h3')].some((h) => h.innerText.trim() === 'Thế giới đã mở khoá')`);
    await c.shot('Thế giới đã mở khoá');
    await c.press('Escape');
    return { ok: section && !!jump, detail: `${section ? 'có' : 'KHÔNG có'} phần Thế giới đã mở khoá · ${jump ? 'có' : 'KHÔNG có'} nút Xem lúc được nhắc tới lần đầu` };
  });

  // ================================================================ quản trị
  await c.step(C.ADMIN, async () => {
    await c.goto('#/admin');
    const tabsSel = '[role=radiogroup][aria-label="Mục quản lý"]';
    await c.waitFor(`!!__bot.find({ within: ${J(tabsSel)}, css: '[role=radio]', text: 'Số liệu' })`, 'các mục quản lý', 15000);
    await c.waitFor(`!!document.querySelector('#admin-invites') && !!document.querySelector('#admin-members')`, 'mục Mã mời và Thành viên');
    await c.waitFor(`document.querySelector('section[aria-labelledby=admin-members]')?.innerText.includes('@' + ${J(c.creds.handle)})`, 'tài khoản chủ máy trong danh sách', 10000);
    const accountsTab = await c.exists({ within: tabsSel, css: '[role=radio]', text: 'Tài khoản' });
    await scan('#/admin');
    await c.shot('Quản trị: tài khoản và mã mời');
    await c.click({ within: tabsSel, css: '[role=radio]', text: 'Số liệu' }, 'mục Số liệu');
    await c.waitFor(`!!document.querySelector('#metrics-export')`, 'nội dung Số liệu', 15000);
    await c.sleep(400);
    await scan('#/admin số liệu');
    await c.shot('Quản trị: số liệu');
    return { ok: accountsTab, detail: accountsTab ? '' : 'thiếu mục Tài khoản' };
  });

  await c.step(C.ADMIN_REPORTS, async () => {
    const tabsSel = '[role=radiogroup][aria-label="Mục quản lý"]';
    await c.click({ within: tabsSel, css: '[role=radio]', text: 'Báo cáo' }, 'mục Báo cáo');
    await c.waitFor(`__bot.find({ within: ${J(tabsSel)}, css: '[role=radio]', text: 'Báo cáo' })?.getAttribute('aria-checked') === 'true'`, 'mục Báo cáo được chọn');
    await c.sleep(800);
    const text = await c.evaluate(`document.querySelector('main').innerText`);
    await scan('#/admin báo cáo');
    await c.shot('Quản trị: báo cáo');
    await c.click({ within: tabsSel, css: '[role=radio]', text: 'Tài khoản' }, 'mục Tài khoản');
    return { ok: text.includes('Báo cáo') && text.length > 80, detail: text.split('\n').filter((l) => l.trim()).slice(2, 4).join(' · ').slice(0, 90) };
  });

  await c.step(C.INVITE, async () => {
    await c.waitFor(`!!__bot.find({ css: 'button', text: 'Tạo mã mời' })`, 'nút Tạo mã mời', 10000);
    await c.click({ css: 'button', text: 'Tạo mã mời' }, 'nút Tạo mã mời');
    await c.waitFor(dialogTitled('Tạo mã mời'), 'hộp Tạo mã mời');
    const seven = { within: '[role=dialog]', css: '[role=radio]', text: '7 ngày' };
    const days = (await c.exists(seven)) ? 'có' : 'không';
    if (days === 'có') await c.click(seven, 'hết hạn sau 7 ngày');
    await c.click({ within: '[role=dialog]', css: 'button', text: 'Tạo mã' }, 'nút Tạo mã');
    await c.waitFor(dialogTitled('Mã mời mới'), 'mã mời mới', 10000);
    inviteCode = await c.evaluate(`(document.querySelector('[role=dialog]').innerText.match(/LYR-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}/) || [''])[0]`);
    const copy = await c.exists({ within: '[role=dialog]', css: 'button', text: 'Sao chép mã' });
    const link = await c.exists({ within: '[role=dialog]', css: 'button', text: 'Sao chép liên kết' });
    await c.shot('Mã mời mới');
    await c.click({ within: '[role=dialog]', css: 'button', text: 'Xong' }, 'nút Xong');
    return { ok: !!inviteCode && copy && link, detail: `${inviteCode || 'không thấy mã'} · lựa chọn 7 ngày: ${days}` };
  });

  // ================================================================ desktop
  await c.step(C.DESKTOP, async () => {
    await c.viewport('desktop');
    await c.goto('#/explore');
    await c.waitFor('document.querySelectorAll("section[aria-labelledby=explore-all] ul > li").length > 0', 'lưới nhân vật (desktop)', 15000);
    await c.sleep(500);
    const over = await overflowX(c);
    await scan('#/explore desktop');
    await c.shot('Desktop 1280 Khám phá');
    await c.viewport('phone');
    return { ok: over <= 1, detail: over > 1 ? `tràn ngang ${over}px` : '' };
  });

  // ================================================================ đường dẫn lạ
  await c.step(C.NOT_FOUND, async () => {
    expectedErrors.push('/api/cards/999999');
    await c.goto('#/character/999999');
    await c.waitFor(`document.body.innerText.includes('Không tìm thấy nhân vật này')`, 'câu không tìm thấy', 15000);
    const back = await c.exists({ css: 'button', text: 'Về Khám phá' });
    await c.shot('Nhân vật không tồn tại');
    return { ok: back, detail: back ? '' : 'thiếu nút Về Khám phá' };
  });

  // Hồ sơ của nhân vật đã có story: thanh dính đáy (điện thoại) có cả 'Tiếp tục story' và 'Bước vào câu chuyện'.
  await c.step(C.CONTINUE_BAR, async () => {
    if (!storyHash) throw new Error('chưa có story');
    await c.viewport('phone');
    await c.goto(storyHash);
    await c.waitFor(`!!document.querySelector('header a[title^="Hồ sơ của "]')`, 'link hồ sơ trên header chat', 15000);
    await c.click('header a[title^="Hồ sơ của "]', 'tên nhân vật trên header chat');
    await c.waitFor('location.hash.startsWith("#/character/")', 'hồ sơ nhân vật', 10000);
    await c.waitFor(`!!__bot.find({ css: 'button', text: 'Tiếp tục story' })`, 'nút Tiếp tục story', 15000).catch(() => {});
    const bar = await c.evaluate(`(() => {
      const inBar = (label) => __bot.all({ css: 'button', text: label }).map((b) => {
        for (let e = b; e; e = e.parentElement) { if (getComputedStyle(e).position === 'fixed') return Math.round(window.innerHeight - e.getBoundingClientRect().bottom); }
        return null;
      }).filter((v) => v !== null);
      return { cont: inBar('Tiếp tục story'), enter: inBar('Bước vào câu chuyện') };
    })()`);
    await c.shot('Hồ sơ đã có story: thanh dính đáy');
    let opened = '';
    if (bar.cont.length) {
      await c.click({ css: 'button', text: 'Tiếp tục story', last: true }, 'nút Tiếp tục story');
      opened = await c.waitFor('/^#\\/chat\\/\\d+$/.test(location.hash)', 'story mở lại', 10000).then(() => hashNow(c)).catch(() => '');
    }
    const want = storyHash.split('?')[0];
    const ok = bar.cont.length > 0 && bar.cont[0] <= 1 && bar.enter.length > 0 && bar.enter[0] <= 1 && opened === want;
    return { ok, detail: `Tiếp tục story: ${bar.cont.length ? `cách đáy ${bar.cont[0]}px` : 'KHÔNG có trong thanh dính đáy'} · Bước vào câu chuyện: ${bar.enter.length ? `cách đáy ${bar.enter[0]}px` : 'KHÔNG có'} · bấm Tiếp tục story → ${opened || 'không mở story'} (story của bot: ${want})` };
  });

  await c.step(C.LEGACY, async () => {
    if (!ownCard) throw new Error('chưa có id nhân vật');
    await c.evaluate(`location.hash = '#/new-story?card=${ownCard.id}'`);
    c.setWhere('#/new-story');
    // Link cũ → hồ sơ nhân vật với sheet bắt đầu mở ("?start=1"; app bỏ tham số này khỏi địa chỉ khi đã mở sheet).
    const want = `#/character/${ownCard.id}`;
    await c.waitFor(`location.hash.split('?')[0] === ${J(want)}`, want, 10000).catch(() => {});
    const sheet = await c.waitFor(dialogTitled('Chọn persona'), 'sheet bắt đầu', 8000).catch(() => false);
    const now = await hashNow(c);
    await c.shot('Link new-story cũ');
    await c.press('Escape');
    return { ok: now.split('?')[0] === want && !!sheet, detail: `#/new-story?card=${ownCard.id} → ${now}${sheet ? ', sheet bắt đầu mở' : ', KHÔNG mở sheet'}` };
  });

  // ================================================================ đăng xuất → link mời → thành viên thứ hai
  await c.goto('#/');
  await openAccountSheet(c).catch(() => {});
  // Lúc đăng xuất, vài request đang bay (sức khoẻ máy, persona…) nhận 401 trước khi app chuyển sang #/login.
  c.setWhere('đăng xuất');
  expectedErrors.push(/^\[đăng xuất\] Failed to load resource: the server responded with a status of 401\b/);
  await c.click({ within: '[role=dialog]', css: 'button', text: 'Đăng xuất' }, 'nút Đăng xuất').catch(() => {});
  await c.waitFor('location.hash.startsWith("#/login")', 'về trang đăng nhập', 15000).catch(() => {});

  await c.step(C.INVITE_LINK, async () => {
    if (!inviteCode) throw new Error('chưa tạo được mã mời');
    await c.goto(`#/signup?code=${inviteCode}`, { reload: true });
    const field = { field: 'Mã mời' };
    await c.waitFor(`!!__bot.find(${J(field)})`, 'ô Mã mời', 15000);
    await c.sleep(300);
    const r = await c.evaluate(`({ value: __bot.find(${J(field)}).value, hash: location.hash, href: location.href })`);
    await scan('#/signup');
    await c.shot('Trang tạo tài khoản từ link mời');
    const norm = (s) => s.replace(/[^A-Z0-9]/gi, '').toUpperCase();
    return { ok: norm(r.value) === norm(inviteCode) && !r.href.includes(norm(inviteCode).slice(3, 7)) && !r.hash.includes('code='), detail: `ô: ${r.value} · địa chỉ: ${r.hash}` };
  });

  let memberIn = false;
  await c.step(C.HUB_EMPTY, async () => {
    await c.goto('#/login', { reload: true });
    await submitLogin(c, c.member);
    await c.waitFor('!!__bot.find({ labelEnds: "Mở tài khoản" })', 'thành viên vào hub', 15000);
    memberIn = true;
    await c.waitFor(`document.body.innerText.includes('Chưa có story nào')`, 'hub rỗng', 10000);
    const r = await c.evaluate(`({ open: !!__bot.find({ css: 'button', text: 'Mở Khám phá' }),
      invite: [...document.querySelectorAll('h2')].some((h) => h.innerText.trim() === 'Đặt tên cho tài khoản của bạn') })`);
    await scan('#/ (thành viên)');
    await c.shot('Hub rỗng của thành viên');
    return { ok: r.open && r.invite, detail: `${r.open ? 'có' : 'KHÔNG có'} Mở Khám phá · ${r.invite ? 'có' : 'KHÔNG có'} khối Đặt tên cho tài khoản` };
  });

  await c.step(C.MEMBER_ADMIN, async () => {
    if (!memberIn) throw new Error('thành viên chưa đăng nhập được');
    const t0 = Date.now();
    await c.evaluate(`location.hash = '#/admin'`);
    await c.waitFor(`location.hash === '#/' || location.hash === ''`, 'về hub', 8000).catch(() => {});
    await c.sleep(800);
    const now = await hashNow(c);
    const admin = c.requests.filter((q) => q.at >= t0 && new URL(q.url).pathname.startsWith('/api/admin')).length;
    return { ok: (now === '#/' || now === '') && admin === 0, detail: `#/admin → ${now || '(trống)'} · ${admin} request /api/admin` };
  });

  await c.step(C.SHARED, async () => {
    if (!memberIn || !sharedCard) throw new Error('thiếu thành viên hoặc nhân vật công khai');
    await c.goto('#/explore');
    await c.waitFor(`!!document.querySelector('section[aria-labelledby=explore-shared]')`, 'mục Nhân vật được chia sẻ', 15000);
    const link = { within: 'section[aria-labelledby=explore-shared]', css: 'a', labelStarts: `Xem nhân vật ${sharedCard.name}` };
    await c.waitFor(`!!__bot.find(${J(link)})`, `nhân vật ${sharedCard.name} trong mục chia sẻ`, 8000);
    await c.shot('Nhân vật được chia sẻ');
    // Hồ sơ nhân vật thử GET /api/cards/{id} trước (404 vì không phải của mình) rồi mới đọc bản công khai: đúng thiết kế.
    expectedErrors.push(`(/api/cards/${sharedCard.id})`);
    await c.click(link, 'nhân vật được chia sẻ');
    await c.waitFor(`!!__bot.find({ css: 'button', text: 'Bước vào câu chuyện' })`, 'hồ sơ nhân vật chia sẻ', 15000);
    const r = await c.evaluate(`({ edit: !!__bot.find({ css: 'a, button', textHas: 'Sửa nhân vật' }),
      by: [...document.querySelectorAll('main a[href^="#/u/"]')].map((a) => [a.getAttribute('href'), a.innerText.trim()])[0] ?? null })`);
    await scan('hồ sơ nhân vật chia sẻ');
    const ok = !r.edit && !!r.by && r.by[0] === `#/u/${c.creds.handle}` && r.by[1].includes(`@${c.creds.handle}`);
    return { ok, detail: `${r.edit ? 'CÓ Sửa nhân vật · ' : ''}${r.by ? `${r.by[1]} → ${r.by[0]}` : 'không có link người tạo'}` };
  });

  await c.step(C.COPY_NOTE, async () => {
    if (!memberIn) throw new Error('thành viên chưa đăng nhập được');
    await c.click({ css: 'button', text: 'Bước vào câu chuyện' }, 'nút Bước vào câu chuyện');
    await c.waitFor(dialogTitled('Chọn persona'), 'sheet bắt đầu');
    const line = await c.evaluate(`document.querySelector('[role=dialog]').innerText.split('\\n').find((l) => l.includes('sửa nhân vật sau này')) ?? ''`);
    await c.shot('Sheet bắt đầu với nhân vật của người khác');
    await c.press('Escape');
    const ok = line.includes(`@${c.creds.handle} sửa nhân vật sau này thì story của bạn không đổi.`);
    return { ok, detail: line || 'không có dòng bản sao' };
  });

  // Đăng nhập thẳng ở #/login (không có trang nào được nhớ) bằng tài khoản ĐÃ CÓ story: phải vào Tương tác (#/),
  // không tự nhảy vào story gần nhất.
  await c.step(C.LOGIN_HUB, async () => {
    await c.goto('#/');
    await openAccountSheet(c);
    c.setWhere('đăng xuất');
    await c.click({ within: '[role=dialog]', css: 'button', text: 'Đăng xuất' }, 'nút Đăng xuất');
    await c.waitFor('location.hash.startsWith("#/login")', 'về trang đăng nhập', 15000);
    await c.goto('#/login', { reload: true });
    await submitLogin(c, c.creds);
    await c.waitFor('!location.hash.startsWith("#/login")', 'rời trang đăng nhập', 15000);
    await c.waitFor('!!__bot.find({ labelEnds: "Mở tài khoản" })', 'header hub có nút … Mở tài khoản', 15000);
    await c.sleep(1500); // nếu app tự nhảy vào story thì nhảy trong lúc này
    const r = await c.evaluate(`({ hash: location.hash, stories: document.querySelectorAll('main a[href^="#/chat/"]').length,
      account: !!__bot.find({ labelEnds: 'Mở tài khoản' }) })`);
    await c.shot('Đăng nhập xong: màn Tương tác');
    const ok = (r.hash === '#/' || r.hash === '') && r.account && r.stories > 0;
    return { ok, detail: `sau đăng nhập: ${r.hash || '(trống)'} · ${r.stories} story trong danh sách · ${r.account ? 'có' : 'KHÔNG có'} nút … Mở tài khoản` };
  });

  // ================================================================ tổng kết cả lượt chạy
  {
    const want = { '#/': 3, '#/explore': 3, '#/studio': 3, '#/chat/<id>': 0, '#/studio/<id>': 0, '#/personas': 0, '#/character/<id>': 0 };
    const bad = Object.entries(want).filter(([k, n]) => tabs[k] !== n).map(([k, n]) => `${k}: ${tabs[k] ?? '—'} (cần ${n})`);
    c.check(C.TABBAR, bad.length === 0, bad.join(', ') || Object.entries(tabs).map(([k, n]) => `${k}=${n}`).join(' '));
  }
  c.check(C.TAP_ROW, rowSizes.length === 0 && rowMeasured >= 6, rowSizes.slice(0, 6).join('; ') || `${rowMeasured} nút (hàng thao tác dưới lượt cuối, hộp Xác nhận xoá) đều ≥ 44px ở 390px`);
  c.check(C.SIZE390, sizes.length === 0, sizes.slice(0, 6).join('; ') || '#/, #/studio, #/chat: không tràn; nút header và thanh tab ≥ 44px');
  {
    const appOrigin = new URL(c.base).origin;
    const local = (u) => /^(data|blob|about|chrome|devtools):/.test(u) || u.startsWith(`${appOrigin}/`);
    const out = [...new Set(c.requests.map((q) => q.url).filter((u) => !local(u)))];
    c.check(C.NO_EXTERNAL, out.length === 0 && c.requests.length > 0, out.slice(0, 3).join(', ') || `${c.requests.length} request, đều tới ${new URL(c.base).origin}`);
  }
  // Lỗi mạng mà kịch bản CỐ Ý gây ra (AI viết nháp khi LLM giả báo lỗi, nhân vật/profile không tồn tại) không tính.
  const expected = (e) => expectedErrors.some((x) => (x instanceof RegExp ? x.test(e) : e.includes(x)));
  const errs = c.errors.filter((e) => !expected(e));
  c.check(C.CONSOLE, errs.length === 0, errs.slice(0, 3).join(' | ') || (c.errors.length ? `${c.errors.length} lỗi mạng đúng kịch bản (${expectedErrors.map(String).join(', ')})` : ''));
  const leaks = [];
  for (const [label, text] of seen) {
    const m = text.match(TECH_WORDS);
    if (m) leaks.push(`${label}: "${m[0]}"`);
  }
  c.check(C.TECH, leaks.length === 0 && seen.length > 0, leaks.slice(0, 4).join(', ') || `${seen.length} màn`);
}

/** --look: chỉ chụp các màn chính để Model tự nhìn (không chấm). */
export async function look(c) {
  await c.goto('#/login', { reload: true });
  await c.waitFor('!!document.querySelector("input[autocomplete=username]")', 'ô Tên đăng nhập', 20000);
  await c.shot('Đăng nhập');
  await submitLogin(c, c.creds);
  await c.waitFor('!!__bot.find({ labelEnds: "Mở tài khoản" })', 'vào Tương tác sau khi đăng nhập', 15000);
  await c.shot('Tương tác');
  await c.goto('#/explore');
  await c.waitFor('document.querySelectorAll("section[aria-labelledby=explore-all] ul > li").length > 0', 'lưới nhân vật', 15000);
  await c.shot('Khám phá');
  await c.click('#explore-featured a', 'nhân vật nổi bật');
  await c.waitFor(`!!__bot.find({ css: 'button', text: 'Bước vào câu chuyện' })`, 'hồ sơ nhân vật', 15000);
  await c.shot('Hồ sơ nhân vật');
  // Story seed có sẵn (lời chào của nhân vật mẫu Lạc Dương) — mở story đầu tiên ở Tương tác.
  await c.goto('#/');
  const story = await c.waitFor(`[...document.querySelectorAll('a[href^="#/chat/"]')].map((a) => a.getAttribute('href'))[0] ?? ''`, 'story trong Tương tác', 10000).catch(() => '');
  if (story) {
    await c.goto(story);
    await c.waitFor(`document.querySelectorAll('article').length > 0`, 'nội dung story', 15000).catch(() => {});
    await c.shot('Story');
  }
  await c.goto('#/');
  await c.click({ labelEnds: 'Mở tài khoản' }, 'nút tài khoản');
  await c.sleep(500);
  await c.shot('Sheet tài khoản');
  await c.press('Escape');
  await c.goto('#/admin');
  await c.waitFor(`!!document.querySelector('#admin-invites')`, 'trang quản trị', 15000).catch(() => {});
  await c.shot('Quản trị');
  await c.viewport('desktop');
  await c.goto('#/explore');
  await c.sleep(800);
  await c.shot('Desktop Khám phá');
  c.check('look: đã chụp các màn chính', true);
}
