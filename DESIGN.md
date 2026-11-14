# LYRIS — Design System & UI/UX Architecture Specification (`design.md`)

## 1. Brand Identity & Core Philosophy

* **App Name:** **Lyris**
* **Tagline:** *"Nơi những tâm hồn từ trang sách bước ra sưởi ấm thực tại"* (Where souls step off the page to warm reality).
* **Design Ethos:** **Romantic, Healing, Intimate & Subtly Mysterious** (*Lãng mạn, Chữa lành, Gần gũi nhưng Bí ẩn*).
* **Visual Metaphor:** Unlike cold sci-fi or sterile utility AI chatbots, **Lyris** feels like reading a cherished novel by candlelight in a rain-kissed attic bookstore (Dark Mode) or writing a love letter on silk parchment under morning sunlight (Light Mode).
* **Target Form Factor:** Mobile-first iOS Web App / PWA (optimized for iPhone 15/16 Pro ergonomics, Dynamic Island safe areas, and single-thumb navigation) paired with a responsive desktop companion view, connected to a local MacBook M2 server.

---

## 2. Logo & Stylized Wordmark Specification

### 2.1. App Icon Mark
* **Symbolism:** Two open book pages gracefully curving into a heart silhouette, cradling a glowing 4-point star at the center (representing the spark of life/soul awakening from ink and paper).
* **Stroke & Fill:** `1.8px` rounded vector stroke using a warm dual-stop gradient, with the central star filled in warm gold/amber.

### 2.2. Stylized Wordmark (`Lyris`)
* **Font Family:** `Cormorant Garamond` (Italic, 600/700 weight).
* **Artistic Customizations:**
  1. **Swash Capital `L`:** Rendered in `italic font-bold` with a multi-stop warm gradient (`#F3C68F -> #E5989B -> #FAF2EB` in Dark Mode; `#9E475B -> #C86D7E -> #B87D4B` in Light Mode).
  2. **Star-Dotted `ı`:** Uses a dotless lowercase `ı` (`\u0131`) topped with a custom 4-point sparkling vector star (`svg` path) that gently pulses.
  3. **Flourish Underline:** A delicate, hand-drawn curved SVG stroke (`stroke-linecap="round"`) sweeping beneath the wordmark like a silk bookmark ribbon.

---

## 3. Dual-Theme Color Architecture

**Strict Anti-Halation Rule:** Never use pure black (`#000000`) or pure stark white (`#FFFFFF`) for long-form reading surfaces. All backgrounds and typography are tinted with warm rosewood, mulberry, or vellum undertones to eliminate eye strain during multi-hour novel roleplay sessions.

### 3.1. Dark Mode — *"Velvet Nocturne"* (Đêm Nhung & Ánh Nến)
Designed for late-night immersive storytelling and intimate conversations.

| Token Role | CSS / Tailwind Hex | Name | Usage Description |
| :--- | :--- | :--- | :--- |
| `bg-primary` | `#130D14` | **Velvet Mulberry** | Main app background & canvas |
| `bg-surface` | `#1F1521` | **Plum Lounge** | Character cards, dialogue bubbles, modals |
| `bg-glass` | `rgba(31, 21, 33, 0.78)` | **Frosted Plum** | Glassmorphic cards (`backdrop-filter: blur(16px)`) |
| `border-subtle` | `#382635` | **Rosewood Rim** | Hairline card borders and dividers |
| `accent-primary` | `#E5989B` | **Dusty Rose** | Primary emotional accent, `[Thought]` border, active states |
| `accent-secondary`| `#F3C68F` | **Candlelight Gold** | Story mode highlights, star dot, M2 status pulse |
| `text-primary` | `#FAF2EB` | **Warm Silk** | Primary dialogue text, titles, active UI labels |
| `text-secondary` | `#C2AAB8` | **Muted Mauve** | Environmental narration, italicized actions, timestamps |
| `user-bubble` | `#3D2638` $\rightarrow$ `#291928` | **Deep Berry Gradient**| Player message bubble background (`border: #E5989B/35`) |

### 3.2. Light Mode — *"Rosewater Parchment"* (Giấy Lụa & Nắng Sớm)
Designed for daytime reading with the tactile warmth of high-grade vellum paper and dried rose petals.

| Token Role | CSS / Tailwind Hex | Name | Usage Description |
| :--- | :--- | :--- | :--- |
| `bg-primary` | `#FAF5EE` | **Silk Parchment** | Main daytime reading background |
| `bg-surface` | `#FFFDF9` | **Warm Alabaster** | Elevated story cards, dialogue containers |
| `bg-input` | `#F4ECE4` | **Pressed Linen** | Text input field, quick-reply chips, inactive toggles |
| `bg-glass` | `rgba(255, 252, 249, 0.85)`| **Translucent Vellum**| Floating glass cards & headers (`blur(16px)`) |
| `border-subtle` | `#E8D7CE` | **Blush Border** | Soft card outlines and section dividers |
| `accent-primary` | `#C86D7E` | **Rose Berry** | Primary interactive buttons, emotional highlights |
| `accent-secondary`| `#C58B52` | **Honey Amber** | Secondary badges, character titles, DM mode toggle |
| `text-primary` | `#2D1E24` | **Espresso Ink** | High-contrast warm charcoal for crisp novel reading |
| `text-secondary` | `#7D636D` | **Earl Grey Mauve** | Scene narration, physical action text, subtitles |
| `user-bubble` | `#C86D7E` $\rightarrow$ `#B05768` | **Rosewood Gradient** | Player message bubble with `#FFFFFF` text |

### 3.3. 6-Dimension Emotional Matrix Colors (Semantic Gauges)
Used in the Slide-over Relationship Drawer and Story Card badges:
1. **Affection (Thương mến):** `#D86C86` (Warm Rose)
2. **Trust (Tin cậy):** `#C58B52` (Golden Amber)
3. **Attraction (Rung động):** `#A864A8` (Orchid Plum)
4. **Obsession (Nhung nhớ / Chiếm hữu):** `#D15B5B` (Crimson Ember)
5. **Fear (Lo sợ mất mát):** `#6E7BB8` (Twilight Indigo)
6. **Aversion (Khoảng cách):** `#9E8881` (Ash Taupe)

---

## 4. Typography System

All fonts must fully support Vietnamese diacritics with generous line height to prevent visual crowding on mobile screens.

1. **Brand & Artistic Display (`font-brand`):**
   * **Family:** `'Cormorant Garamond', serif`
   * **Usage:** Exclusively for the **Lyris** wordmark and special chapter/letter headings.
2. **UI & DM Mode Sans-Serif (`font-sans-ui`):**
   * **Family:** `'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif`
   * **Weights:** `400` (Regular), `500` (Medium), `600` (SemiBold), `700` (Bold), `800` (ExtraBold).
   * **Usage:** Navigation bars, buttons, badges, character cards, DM Mode chat bubbles, and system settings.
3. **Novel & Story Mode Narrative (`font-story`):**
   * **Family:** `'Be Vietnam Pro', sans-serif`
   * **Weights:** `300` / `400` / `400 Italic` / `500`.
   * **Line Height:** `1.65` (`leading-relaxed`) for effortless long-form reading.
   * **Usage:** Story Mode environmental descriptions (italicized), spoken character dialogue, and `[Thought]` inner monologue cards.

---

## 5. Information Architecture & Navigation (Option A: 3+1 Layout)

To prioritize the core roleplay experience at the exact center of the user's thumb reach on iPhone, **Lyris** uses a **3-Tab Floating Glass Pill** at the bottom and places **User/Server Settings** in the top header.

### 5.1. Top Application Header (Visible on Main Hub Tabs)
* **Left:** Stylized `Lyris` wordmark + Live Local Server status pill (`● M2 Local` pulsing indicator).
* **Right:**
  * Quick Theme Toggle button (`Sun` / `Moon` icon) for instant switching between *Rosewater Parchment* and *Velvet Nocturne*.
  * Circular User Persona Avatar button (opens **Page 4: User & M2 Server Control Modal**).

### 5.2. Bottom Floating Glass Pill (3 Tabs)
* **Position:** Floating `16px` above the bottom safe area, `90%` width, `rounded-full`, `backdrop-filter: blur(20px)`.
* **Tab Left — `Khám Phá` (Explore):** Compass icon (`Compass`). Browse featured healing worlds, mood tags, and character templates.
* **Tab Center (Elevated Orb) — `TƯƠNG TÁC` (Active Chats):**
  * Elevated `-12px` above the pill (`-top-3`), circular/pill gradient orb (`#C86D7E -> #D98A6C -> #F3C68F`), glowing drop shadow, filled `Heart` icon.
* **Tab Right — `Studio` (Creation & Wiki):** Sparkles icon (`Sparkles`). Create characters, tune initial emotion sliders, and sync `world_wiki/*.md` files.

---

## 6. Page-by-Page UI & Component Specifications

### Page 1: Tương Tác (Center Hub — 2-Layer Architecture)

#### Layer 1: Active Story Threads List
* **Time-Aware Greeting Banner:** Displays a contextual healing message based on theme/time (e.g., *"☀️ Nắng lên rồi, hôm nay trò chuyện cùng ai?"* or *"🕯️ Đêm muộn rồi, ai đang thức đợi bạn?"*).
* **Search Bar:** Rounded `16px` input filtering by character name, title, or location.
* **Active Story Cards:**
  * Left: `48x48px` rounded-2xl character portrait with a corner mode badge (`STORY` or `DM`).
  * Center/Right: Character Name, In-world Timestamp (`23:15`), Character Role/Title in warm gold/amber, 1-line italicized preview of the latest dialogue/action, and bottom micro-chips showing the dominant emotion (`♥ Thương mến 91%`) + current location (`✨ Gác Xép Mùi Gỗ Thông`).

#### Layer 2: Full-Screen Roleplay Workspace (Hides Bottom Bar)
When a user taps a character card, the view transitions into a dedicated 100% height roleplay screen:
1. **Sticky Glass Header:**
   * Back chevron button (`ChevronLeft`), Character Avatar (`32x32px`), Name, and scrolling Location/Time subtitle.
   * **Mode Switcher Pill (`STORY ⇄ DM`):** Instant toggle that switches rendering styles and backend prompt templates without losing conversation context.
   * **Inner Heart Drawer Button:** Opens the Slide-over Relationship & Memory Drawer.
2. **Situational Moment Banner (WHIF-style In-Chat Mission):**
   * Slim sub-header banner displaying the current emotional beat or subtle goal (e.g., *"Khoảnh khắc: Đón nhận sự quan tâm dịu dàng từ Hạ Vy • +Thương mến"*).
3. **Message Stream Area:**
   * **Story Mode Rendering (3 Distinct Sub-blocks per AI Turn):**
     * *Narrative / Action Block:* Italicized `text-secondary` paragraph without a rigid box, blending naturally into the page like a novel.
     * *Spoken Dialogue Block:* Elevated `bg-surface` rounded-2xl card with warm `text-primary` medium-weight typography wrapped in quotation marks `“...”`.
     * *Inner Monologue Card (`Tiếng Lòng Giấu Kín [Thought]`):* Signature left-bordered (`3px solid #E5989B` / `#C86D7E`) gradient card. **Default state:** Text is blurred (`filter: blur(3px)`, `user-select: none`) with a prompt *"Chạm để lắng nghe"*. **Tapped state:** Smoothly unblurs to reveal the character's hidden subtext and true feelings.
   * **DM Mode Rendering:**
     * Compact chat bubbles (`max-w-[80%]`), avatar beside the message, natural conversational phrasing, and delivery status footer (`00:40 • Đã gửi bằng cả nỗi nhớ`).
4. **Bottom Composer & Quick-Reply Bar:**
   * **Horizontal Swipeable Quick-Reply Chips:** 3 AI-generated contextual response suggestions above the input bar (e.g., `[Khẽ nắm lấy bàn tay đang cầm khăn của cô ấy]`, `“Vì biết Vy vẫn đang thức đợi mình mà.”`). Tapping a chip sends it immediately.
   * **Input Field & Send Button:** Rounded-2xl input with mode-specific placeholder text and a gradient send button (`Send` icon).

### Slide-Over Drawer: 6-Emotion Matrix & Wiki Lorebook
Triggered from the top-right heart icon inside Layer 2:
* **Acting Directive Card (State-to-Directive Output):** Displays the natural-language emotional summary translated from the 6 scores (e.g., *"Dịu dàng, ân cần chăm sóc từng thói quen nhỏ của bạn, nhưng ánh mắt luôn ẩn chứa một nỗi niềm riêng chưa dám thổ lộ."*).
* **6 Progress Bars:** Visualizes `Affection`, `Trust`, `Attraction`, `Obsession`, `Fear`, and `Aversion` (0–100%) with smooth width transitions (`duration-500`).
* **Unlocked Wiki / Memory Tags:** Displays `lorebook_entries` triggered during the session (`✨ Tiệm Sách Mùa Thu`, `✨ Bức Thư Kẹp Trong Sách`).

### Page 2: Khám Phá (Explore)
* **Featured World Hero Card:** Soft gradient banner highlighting a curated setting with a primary CTA button (`Bước Vào Câu Chuyện`).
* **Soul Vibe Filter Chips:** Pill tags (`✨ Chữa Lành`, `✨ Dịu Dàng`, `✨ Bí Ẩn Nội Tâm`, `✨ Tình Đầu`).
* **2-Column Character Grid:** Vertical cards (`aspect-ratio: 3/4` portrait, Name, Role subtitle, and direct `Trò Chuyện` CTA).

### Page 3: Studio (Xưởng Dệt Tâm Hồn)
* **Character Creator Form:** Clean inputs for Character Name, Role, Personality & Secrets, and initial relationship sliders.
* **Lorebook Markdown Sync Status:** Displays live sync status with the local `world_wiki/*.md` directory and SQLite `lorebook_entries` table.
* **Import Support:** Supports importing `.json` / `.png` Character Cards.

### Page 4: User Persona & MacBook M2 Local Server Modal
Triggered by tapping the top-right User Avatar:
* **Active Player Persona Card:** Allows switching the player's own roleplay identity (e.g., *"Vị Khách Chiều Thu"*).
* **MacBook M2 Hardware Telemetry:**
  * Connection badge (`Hoạt động êm ái`).
  * Unified Memory progress bar (`9.4 GB / 24 GB`).
  * Ollama Model Selector dropdown (`qwen2.5:7b`, `mistral-nemo:12b`, `stheno-v3.4-gguf`).
  * KV Cache Quantization (`q8_0`) & Flash Attention status indicators.

---

## 7. Micro-Interactions & Animation Guidelines
* **Theme Transition:** `transition-colors duration-500` across background and surface containers so switching between *Rosewater Parchment* and *Velvet Nocturne* feels like dimming or brightening a warm lamp.
* **Thought Unblur Effect:** `transition-all duration-300` when toggling `blur-[3px]` off the `[Thought]` text.
* **Streaming Indicator:** Gentle spinning `RefreshCw` or pulsing star icon accompanied by italicized character-specific waiting text (`"{Character Name} đang ngập ngừng tìm lời hồi đáp..."`).
* **iOS Safe Areas:** Respect `env(safe-area-inset-top)` for the Dynamic Island and `env(safe-area-inset-bottom)` for the Home Indicator bar when installed as an iOS Home Screen Web App (`apple-mobile-web-app-capable`).