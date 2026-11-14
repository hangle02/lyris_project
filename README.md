<p align="center">
  <img src="docs/assets/lyris-banner.png" alt="Lyris: Nơi những tâm hồn từ trang sách bước ra sưởi ấm thực tại" width="820">
</p>

# Lyris

> *Nơi những tâm hồn từ trang sách bước ra sưởi ấm thực tại.*
> Where the souls of storybook pages step out to warm the real world.

**English** · [Tiếng Việt](#tiếng-việt)

[Demo video](#demo-video) · [Problem](#the-problem) · [Jobs to be done](#jobs-to-be-done) · [Target users](#target-users) · [Core features](#core-features) · [Launch and revenue](#launch-channel-and-business-model) · [Build and run](#build-run-and-access) · [Launch and deploy](#launch-and-deploy) · [Roadmap](#roadmap-hosted-lyris) · [Limitations](#limitations-and-future-evaluation) · [Tracking plan](#tracking-plan) · [Privacy and compliance](#privacy-and-compliance) · [AI-native workflow](#ai-native-workflow-how-we-built-lyris-with-claude) · [Harness](#harness-based-on-aperos-mini-harness) · [Team](#team)

**Labels used in this README:** **Built** = code and tests in this repository today. **Planned** = what we expect Lyris to have; not built yet. Exact per-feature status (✅ passing `verify.sh`, 🟡 built and waiting for verification, ⏳ planned) is in the [Harness tally](#harness-based-on-aperos-mini-harness).

---

## English

### Pitch

Lyris is a Vietnamese-first AI roleplay app. You pick a character, or write your own in the Studio, step into a story with them, and talk. The AI narrates and plays the character. You alone control your persona. The character remembers what happened, including what you said by text message. Their feelings toward you rise and fall with what you do, and they know only what their world allows them to know. Friends can join with an invite code and get their own private stories.

**Where it is going.** The submitted version (built) runs on one machine with a local open model and invite-only accounts. After the course, Lyris becomes a public hosted app on the web, the App Store and Google Play, with coins sold through the stores and Vietnamese payment gateways (planned, designed in [docs/server.md](docs/server.md); see [Roadmap](#roadmap-hosted-lyris)).

### Demo video

**Demo video (2–3 minutes, core flow):** [watch on Google Drive](https://drive.google.com/file/d/1ew4_fgywsVmjGFwK4U-7Vl9aLGexrYvS/view?usp=drive_link)

Script with timestamps, actions and voice-over: [docs/demo-script.md](docs/demo-script.md).

### The problem

**Market context.** AI roleplay is an established paid consumer category. According to Appfigures data reported by TechCrunch (Perez, 2025), 337 active, revenue-generating AI companion apps had reached 220 million lifetime downloads and $221 million in lifetime consumer spending by July 2025. This shows commercial activity in the global category; it does not prove demand or willingness to pay among Vietnamese users specifically.

Immersive roleplay needs more than a coherent next reply. The AI has to keep each character's identity, remember what happened, react consistently to the relationship, and leave the player's own persona to the player. Vietnamese makes this harder: forms of address (anh/em, tớ/cậu, ta/ngươi…) carry age, status, intimacy and context, and a wrong pronoun breaks the character.

| Problem | What goes wrong | Supporting research |
|---|---|---|
| **1. Player agency** | Roleplay models drift from standing instructions such as "never write for the player" within a few turns. In the team's own use, hosted apps such as WHIF sometimes ignored what the player just wrote, spoke and acted *for* the player's character, and drifted off the scene. | Li et al. (2024) measured significant instruction drift within eight rounds of conversation. |
| **2. Vietnamese adaptation** | Models are neither evaluated nor tuned for relationship-dependent forms of address. English-trained roleplay models get them wrong, mix in English or Chinese words, and forget how two characters address each other. | Truong et al. (2024) evaluate Vietnamese LLMs on 10 tasks and 31 metrics; none targets forms of address in dialogue. |
| **3. Memory and continuity** | Characters lose names, promises, facts and personality over long sessions, even with long context or retrieval, and their attitude never changes whatever the player does. | Maharana et al. (2024). |

Together, these make roleplay feel like a series of disconnected chats rather than an ongoing story.

#### Jobs to be done

The same problems seen from the user's side: what progress people "hire" Lyris to make, independent of any feature. This analysis follows the research above and the [personas](#customer-personas-hypotheses-to-validate) below. Every part of it is a **hypothesis to validate** with interviews and tracking data after launch.

**Job statements**

| Who | Job statement |
|---|---|
| **Core job: the story reader** (Vietnamese romance web-fiction reader) | *When* I finish a chapter in the evening and want more time with a kind of character I love, *I want to* step into a story with that character and speak and act as my own persona in natural Vietnamese, *so I can* live the relationship myself and pick it up again tomorrow where we left off. |
| **Related job: the character writer** (Wattpad / Facebook writer) | *When* I have created a character and their world, *I want to* turn them into someone my readers can talk to, played faithfully (voice, forms of address, secrets), *so I can* deepen my readers' attachment and grow my audience. |

**Dimensions of each job**

| | Story reader | Character writer |
|---|---|---|
| **Functional** | A character who answers exactly what I wrote, uses the right anh/em, remembers names and promises across days, and never writes my lines | Set personality, forms of address, signature lines, a world and who knows which secret once; have it played the same way for every reader |
| **Emotional** | Immersion and romance tension, comfort and healing, feeling in control of my own persona; no jolt from broken Vietnamese | Pride that the character comes alive; trust that it will not be distorted |
| **Social** | Talk about favourite characters and moments in reading groups; bring a friend along | Standing in writing communities; readers bringing more readers; recognition through the ranking |

**Job map: where today's alternatives fail**

| Job step | Where current alternatives fail | What Lyris does (built) |
|---|---|---|
| **1. Discover a character** that fits today's mood | Generic AI chat apps are English-first; reading platforms such as Wattpad have the characters, but you can only read them | Explore with vibe filters, "Tìm nhân vật" search, the "Nhân vật hot" ranking, read-only profiles |
| **2. Set up persona and story** | Few apps let the player set their own persona plus per-story forms of address and language | "Bước vào câu chuyện" sheet: persona, Story or DM, language, forms of address per character and per story |
| **3. Play turns** | Generic apps write for the player, ignore the last turn and drift off the scene; wrong forms of address and stray English or Chinese words | Input conventions, a closing instruction to continue from the player's exact turn, Vietnamese-first prompts |
| **4. Keep continuity over days** | Characters forget names, promises and facts; their attitude never changes; human roleplay partners are not always available or drop out | Scene summaries, memories and facts with correct rollback, six emotion dimensions, one timeline for Story and DM, available any time |
| **5. Share and create** | Reading-only platforms give readers no way to interact; nothing rewards a writer for bringing readers | Character Studio, Lorebook with "who knows this", public characters, invite codes, ranking-based creator coins |

**Forces of progress** (why someone would switch, or not)
- **Push of the current situation:** AI apps that take over the player's role, wrong Vietnamese, characters that forget; reading is passive; human partners keep their own schedules.
- **Pull of Lyris:** a Vietnamese-first character who remembers and lets the player stay the author; hand-written worlds; private stories; there whenever the player is.
- **Anxieties:** is a 12B model good enough; are intimate stories private; will coins run out; is the content safe. Lyris answers with 300 free coins plus 60 a day and missions, fully private stories, no user text in analytics, data export and account deletion, and safe content by default.
- **Habits:** reading apps, Wattpad and Facebook groups; AI chat apps people already know; human roleplay in Discord or Facebook groups. Launch channels go to these places (see [Launch channels](#launch-channels)).

**Desired outcomes and how we will measure them**

| Desired outcome (user's view) | Measure | Status |
|---|---|---|
| Minimise the times the AI writes my lines or decisions | Harness: the judge's `godmodding` verdict on model scenarios such as `03-hanh-dong-cho-ai`; in use: dissatisfaction rate (`regenerate_used` + `message_edited` + `reply_rated` down, per `reply_completed`) | Scenario check built and run internally; real-user rate is a hypothesis |
| Minimise wrong forms of address and mixed-in foreign words | Harness machine checks on scenarios `06-viet-hien-dai`, `07-co-trang`, `08-tieng-anh` | Internal only; to be evaluated with readers |
| Minimise the effort to pick up an old story where it stopped | `story_resumed` per week; memory scenario `f10-ky-uc` | Hypothesis |
| Keep a story going | Turns per story (`message_sent`); first target ≥ 40 % of started stories reach 5 turns; North Star: weekly engaged stories | Hypothesis ([tracking plan §5.3](docs/tracking-plan.md#53-first-targets-for-round-2)) |
| Come back to the character | D1 ≥ 35 %, D7 ≥ 15 % (first targets) | Hypothesis |
| Minimise waiting for a reply | First token under 10 s for ≥ 90 % of replies after warm-up (`reply_completed` `ttft_bucket`) | About 5 s measured on a 12B model at home; real use is a hypothesis |
| Creator: maximise how many readers play my character | Players per public character, `story_started` from public characters, `character_published`, `creator_rank_reached` | Hypothesis |

**How Lyris answers each problem.** The approaches below are built; how well they work with real users is **still to be evaluated** (see [Limitations](#limitations-and-future-evaluation)).

| Problem | Lyris approach (built) | Expected outcome |
|---|---|---|
| Limited player agency | A strict split: the AI plays the characters and the world, the player alone writes their persona; [input conventions](#core-features) and a closing instruction to continue from the player's exact turn | Fewer AI-written lines, actions or decisions for the player |
| Inconsistent Vietnamese | Vietnamese-first prompts, forms of address set per character and per story, diacritic-preserving lore matching | More natural, context-appropriate Vietnamese (to be evaluated) |
| Weak long-term memory | Rolling scene summaries, long-term memories, stored facts, correct rollback on regenerate, edit and delete | Better continuity (intended; to be evaluated) |
| Static relationships | Six emotion dimensions that rise and fall with the player's actions | Relationships that respond and evolve |
| Inconsistent worlds | A Lorebook per character, with "who knows this" on every entry | Consistent worlds and controlled reveals |

References: see [References](#references) at the end of this README.

### Target users

- **Readers of Vietnamese romance web fiction** (ngôn tình, đam mỹ, cổ trang, vườn trường) who want to *live inside* a story rather than read it. Mobile-first, mostly evenings.
- **Writers and character creators** who build characters and whole worlds (side characters, places, secrets, plot hooks) and want them played faithfully.
- **Self-hosting enthusiasts** with a capable machine who value privacy over a subscription.

#### Customer personas (hypotheses to validate)

Two personas drawn from the [launch-channel](#launch-channel-and-business-model) audiences. They are **hypotheses, not research findings**: we will check them against the tracking data (activation funnel, D1/D7 retention, creation events) and short user interviews after launch.

| | **Linh, the story reader** | **Minh, the character writer** |
|---|---|---|
| **Who** | 18–25, student or young office worker; reads ngôn tình and đam mỹ on her phone every evening (reading apps, Wattpad, Facebook groups) | 20–30; writes web fiction or original-character posts on Wattpad and Facebook writing groups; has a small following |
| **Wants** | To be *inside* the story with a favourite kind of character (slow-burn romance, jealousy, healing) without the AI taking over her role | Characters played faithfully (voice, forms of address, secrets) and a reason for readers to keep coming back |
| **Pain today** | English-first apps, wrong anh/em, characters that forget, an AI that writes her lines for her | No easy way to turn a character and its world into something readers can talk to; nothing rewards bringing readers in |
| **What Lyris gives** | Story mode, a six-emotion relationship, memory, and "Bước vào câu chuyện" in two taps | Character Studio, a Lorebook with "who knows this", public characters, the "Nhân vật hot" ranking and creator coin rewards |
| **Where to reach** | Facebook reading groups, TikTok book communities, Wattpad reading communities | Wattpad writing communities, Facebook writing groups, TikTok creators |
| **Likely to pay for** | Coins to keep chatting; personalization and early access to new features (planned) | Mostly earns coins through creator rewards; may top up for Studio test chats |
| **Signal to validate** | First story with 3+ turns, D7 retention, turns per day | Characters published, players per public character |

### Core features

Everything in this table is **built** and covered by tests that `verification/verify.sh` runs. Planned features are under [Roadmap](#roadmap-hosted-lyris) and [Limitations](#limitations-and-future-evaluation).

**How you write a turn** (the player-agency mechanism):

| You type | It means | What the AI does |
|---|---|---|
| `"…"` | Your persona's own words | Shown as your dialogue card; the character answers it |
| `*…*` | Your persona's action | Treated as something you did; the AI may describe its visible effect but never adds new actions for you |
| `*"…"*` | A quotation or another person's words | Stays inside the narration, not as your dialogue |
| `((…))` | A hidden direction to the AI, e.g. `((he is jealous but hides it))` | The character follows it in its own voice and never repeats it; in the chat it shows as a small chip |

| Area | What it does |
|---|---|
| **Story and DM modes** | Story mode reads like a novel: italic narration, speech in dialogue cards, and the character's inner thoughts as blurred cards you tap to read. DM mode looks like a messaging app. Both share one timeline, so a name given by text is known in the story. |
| **Player stays the author** | The AI plays the characters and the world and never writes your dialogue, actions or decisions. A closing instruction in every prompt makes it continue directly from what you just wrote, without jumping scenes. |
| **Six-emotion relationship** | Affection, trust, attraction, possessiveness, fear and aversion (0–100) rise *and fall* with your actions. Jealousy lowers trust, an apology lowers aversion, and small talk barely moves anything. The numbers become acting directions for the character and never appear in the prompt as raw numbers. |
| **Memory** | Rolling scene summaries, long-term memories and facts. Search is by keyword, plus by meaning when an embedding model is present. Regenerating, editing or deleting a turn rolls the state back correctly. |
| **Lorebook** | Each character can carry a world: side characters, places and lore entries, imported from a Markdown `world.md`. Entries are triggered by Vietnamese-aware keywords, with diacritics preserved. Each entry says who knows it: everyone, only certain characters, or only you. Spoilers that only you know never reach the model. |
| **Character Studio** | Create and edit characters, draft one with AI from a one-line idea, set signature lines, set forms of address, upload an avatar, and import or export Character Card V2. |
| **Explore and profile** | A "Tìm nhân vật" character search box and a "Nhân vật hot" ranking strip in place of the old featured character, with the full top-100 board at `#/explore/hot` (F46/F47); vibe filters ("Chữa lành", "Tình đầu"…), equal-size character cards, and a read-only profile with "Bước vào câu chuyện". |
| **On-demand helpers** | A "+" menu in the composer: reply suggestions (only when tapped), an event timeline, and image sending (shell). |
| **Accounts** | Owner and invited members, invite codes, password login with scrypt and HttpOnly sessions, an owner-only admin page, and fully private stories. Characters can be made public; others then play their own private copy. |
| **Fast on modest hardware** | Prompt-cache-aware prompt layout and a background "prefill" of the next turn cut the first-token wait on long stories from ~30–47 s to ~5 s on a 12B model. |
| **No technical noise** | No model names, tokens or server status in the UI. Waiting shows typing dots. Technical settings live behind "Nâng cao". |
| **Safety and privacy** | Safe content by default (no sexual content; romance and jealousy stay non-explicit; nothing sexual involving minors, ever). "Báo cáo" on every AI reply and on every public character's profile (the owner can hide a reported character), Terms and Privacy Policy with recorded consent, self-service data export and account deletion, and an opt-out for anonymous usage data. |
| **Coins** | A coin wallet with a chip in the header, 6 coins per character reply, a "Nạp coin" top-up screen (test mode), daily missions and creator rewards from the "Nhân vật hot" ranking. Details under [Revenue](#revenue-model). |
| **Usage analytics** | 57 tracked events with no user text, an owner "Số liệu" page (DAU/WAU/MAU, funnel, D1/D7) and CSV/JSONL export; optional PostHog forwarding. |

### Launch channel and business model

#### Launch channels

| Channel | Audience | Where | How we execute | Why it should work |
|---|---|---|---|---|
| **1. Community discovery** | Readers of Vietnamese romance web fiction (ngôn tình, đam mỹ, cổ trang, vườn trường) | Vietnamese Facebook groups, TikTok book and roleplay communities, Discord servers, Wattpad reading communities | Introduce Lyris as Vietnamese-first; short clips of story mode with the hand-written worlds that already ship (Lục Bắc Uyên, Yến Hoành Sinh, Cố Hoài Dã, Tần Dương): stepping into a story, talking, keeping control of your own persona. For Wattpad readers: another way to live character-driven fiction. | These communities already love fictional characters and relationship-driven stories. |
| **2. Creator-led discovery** | Writers and character creators | Wattpad writing communities, Vietnamese Facebook writing groups, TikTok creators, roleplay communities | Character Studio and the Lorebook for writers; publish public characters and share them with followers; the "Nhân vật hot" ranking and creator coin rewards (built) give a reason to promote. Later: collaborations with Vietnamese web-fiction authors, including Wattpad writers, only with the rights holders' permission. | Every writer brings characters, worlds and their own readers. |
| **3. Referral and sharing** | Existing users | Inside the app | Invite codes (built): every invited member gets their own private stories. Referral coin rewards are planned (see Revenue). | A natural reason to bring friends along. |

#### Distribution

- **Submitted version (built):** a web app, installable as a PWA, served from one machine on the home LAN (a single-server HTTPS setup is documented in [docs/deploy.md](docs/deploy.md), not yet run on a real server). Sign-up is by invite code, released in waves to match capacity (about two replies generated at once per 12B model).
- **Public launch (planned, after the course):** hosted Lyris on the web, the **App Store** and **Google Play**, with open sign-up (email, Sign in with Apple, Google) and real coin payments (Apple IAP, Google Play Billing, VNPay/MoMo). Design: [Roadmap](#roadmap-hosted-lyris) and [docs/server.md](docs/server.md).

#### Revenue model

**Freemium + in-app purchases + subscription + advertising + creator economy.** Chatting costs coins. Every account gets free coins and can earn more; paying buys more coins and, later, extras. Inputs are already measured by the [tracking plan](#tracking-plan): messages per active user per day, compute per turn and every coin event.

**Built now** (design: [docs/coins.md](docs/coins.md); features F42–F47; test mode, no real money changes hands yet):
- **An account is required to chat.** A new account gets **300 coins**; every day you open the app adds **60** (a daily check-in; 360 on day one).
- **Pay per reply:** every character reply costs **6 coins**: a sent turn, "Tạo lại câu trả lời" (regenerate), DM and Studio test chat. Reply suggestions and AI character drafting are free. A reply that fails or never starts costs nothing. Out of coins, the message box locks and offers "Nạp coin" (top up) and "Nhiệm vụ" (missions).
- **Coin packs with tiered bonuses:** 100 coins for 10.000đ · 550 (500 + 50 bonus) for 50.000đ · 1.200 (1.000 + 200 bonus) for 100.000đ · 2.500 (2.000 + 500 bonus) for 200.000đ. Until launch the "Nạp coin" screen runs in test mode: prices are expected launch prices and nothing is sold; the operator gives away one-time top-up codes or adds coins by hand, with a reason. Test-mode coins reset to 0 at launch.
- **Earning coins without paying:**
  - **Missions:** up to 30 coins a day: watch a 15-second sample ad (+5, three times; a placeholder for rewarded ads, no ad network yet), chat with 3 different characters (+10), send 20 turns (+5).
  - **Creation:** when your public character enters the top 100, top 50 or top 10 of the "Nhân vật hot" (hot characters) ranking, you get +100, +200 or +300 coins, once per tier per character (jumping straight into the top 10 pays all three, 600). The ranking counts all-time players (other accounts who really played it) and refreshes every hour. Your first public character earns +50 once, after it has been public for 24 hours and someone else has played it. A player counts after 3 paid replies on 2 different days; ranking rewards are capped at 600 coins per creator per 7 days (the rest waits, it is not lost), and the machine owner earns none.

  This rewards the creators who bring players in.
- **Self-hosting stays free:** the machine owner never spends coins, and a self-hoster can switch coins off entirely (`LYRIS_COINS=0`).
- **Coins are not money:** no cash-out, no transfers between users, lost when an account is deleted.

**Planned** (what we expect Lyris to have; not built):

| Stream | What we expect |
|---|---|
| **First conversion** | A discount on the first coin pack bought within a new account's first 24 hours. Referral rewards: both the inviter and the invited friend get bonus coins once the friend has chatted for a few turns, with a monthly cap per inviter. |
| **In-app purchases** | A low-balance notice before coins run out; auto top-up with a threshold, a spending limit and confirmation settings; paying coins to be among the first to try new features, starting with **phone calls** with a character (part of the "Tender Moment" ideas: the character's emotional voice, ambient sounds, and the player's own voice input). A call is charged per turn: each time {{user}} speaks and the character answers costs coins, like a chat turn; each answer is length-capped to a few short spoken sentences so the call feels like a real conversation and the cost stays predictable. |
| **Premium personalization** | Chat themes, text and chat-bubble colours, and couple profile frames (matching avatar frames for {{user}} and the AI character), bought with coins; the subscription includes a starter set. |
| **Multilingual characters** | Characters who understand and speak two or more languages and switch naturally between them (e.g. a half-Vietnamese character). Today each story can already be set to Vietnamese or English (built). |
| **Advertising** | In-app ads for free users through an ad network; rewarded ads for coins (today the sample ad in missions); ad-free use through a subscription or a premium pack. |
| **Subscription** | A monthly plan: ad-free, a monthly coin allowance, and the starter personalization set. |
| **Creator economy** | On top of the built ranking rewards: performance-based incentives by how much players engage with public characters; creators promoting their characters and inviting readers. |
| **Retention** | On top of the built daily coins and missions: 7-day chat-streak rewards and rewards for finishing story arcs and milestones. |

**Store rules.** In the iOS and Android apps, every digital purchase (coins, subscriptions, personalization, early access) must go through Apple In-App Purchase or Google Play Billing, and every receipt is verified on the server into the same coin ledger ([docs/server.md §11](docs/server.md#11-thanh-toán-po-5a)). Auto top-up and subscriptions therefore follow the stores' purchase-confirmation and auto-renewal rules; VNPay/MoMo are used on the web only. Real ads in the apps need App Tracking Transparency and privacy labels.

### Build, run and access

#### Hardware for local AI

Lyris runs a ~12B-parameter instruction model locally through Ollama, with an 8,192-token context. The model and its cache take about 16 GB.

| | Minimum | Recommended |
|---|---|---|
| Memory for the model | 16 GB unified memory or VRAM, running a smaller model (e.g. `gemma4:e4b`) | 24 GB+ unified memory (Apple Silicon) or a 16 GB+ GPU (NVIDIA) for `gemma4:12b` |
| Disk | ~15 GB (model + app) | 30 GB+ if you add an embedding model or fine-tune later |
| OS | macOS on Apple Silicon (tested), Linux with Ollama (expected to work) | macOS on Apple Silicon or Linux with an NVIDIA GPU |

Most phones and ordinary laptops cannot run the model, which is why the public version will be hosted ([Roadmap](#roadmap-hosted-lyris)).

Speed scales with memory bandwidth. The first reply after starting the app reads the whole story (tens of seconds). Later turns start in about 5 s thanks to prefill.

#### Software

- [Ollama](https://ollama.com) 0.40+
- Python 3.12 with [`uv`](https://docs.astral.sh/uv/)
- Node.js 22 with npm

#### Steps

```bash
# 1. Model
ollama pull gemma4:12b          # chat model (default)
ollama pull bge-m3              # optional: memory search by meaning

# Recommended Ollama settings (set them for the Ollama server, then restart it):
#   OLLAMA_FLASH_ATTENTION=1  OLLAMA_KV_CACHE_TYPE=q8_0  OLLAMA_NUM_PARALLEL=2
#   On macOS, scripts/ollama-env.sh installs these as a LaunchAgent.

# 2. Backend dependencies
cd backend && uv sync && cd ..

# 3. Run backend (127.0.0.1:8000) and frontend (port 5173) together
bash scripts/dev.sh
```

- **First run:** the terminal prints a one-time **setup code** in a box ("Lyris: đặt mật khẩu cho tài khoản chủ máy"). Open http://localhost:5173, paste the code and choose the owner password. If the box is gone, run `bash scripts/lyris-admin.sh setup-code`.
- **Phone or other devices on the same Wi-Fi:** open the LAN address that `dev.sh` prints (`http://<computer-ip>:5173`) and log in. Use `LYRIS_LAN=0` to keep the app on this computer only.
- **Security note:** over plain Wi-Fi the connection is **not encrypted**, so use it only on a network you trust. Remote access over HTTPS (Tailscale, F37) is planned; a public server must run behind HTTPS with `LYRIS_COOKIE_SECURE=1` ([docs/deploy.md](docs/deploy.md)).
- **Inviting someone:** go to Tài khoản → Quản lý tài khoản → Tạo mã mời, and send the code. The invited member signs up with it and gets their own private stories and coin wallet.
- **Forgot the owner password:** run `bash scripts/lyris-admin.sh reset-password <handle>`.

#### Production-like run on one machine

```bash
bash scripts/serve.sh      # builds frontend/dist, runs uvicorn without --reload (one process),
                           # serves the build with `vite preview` and its /api proxy
LYRIS_API_PORT=8064 LYRIS_WEB_PORT=8065 LYRIS_DB_PATH=/tmp/lyris-demo/lyris.db bash scripts/serve.sh   # other ports and DB
```

Use it for demos and home use. For the public launch (HTTPS, Caddy, systemd, backups), follow [docs/deploy.md](docs/deploy.md).

#### Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `LYRIS_CHAT_MODEL` | `gemma4:12b` | Chat model, also used for background extraction and summaries. |
| `LYRIS_NUM_CTX` | `8192` | Context window. Keep one value for all calls, because a change makes Ollama reload the model. |
| `LYRIS_EMBED_MODEL` | `bge-m3` if installed | Memory search by meaning. |
| `LYRIS_CHAT_SLOTS` | `2` | Replies generated at once across all accounts. |
| `LYRIS_DB_PATH` | `data/lyris.db` | SQLite database (one file; back it up). |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama server. |
| `LYRIS_COOKIE_SECURE` | `0` | Set `1` when served over HTTPS: the sign-in cookie always gets `Secure`. |
| `LYRIS_COINS` | `1` | Set `0` to switch coins off (no charges, no wallet chip or missions). |
| `LYRIS_POSTHOG_KEY` | unset | PostHog project key. Set it to forward usage events to PostHog as well as the local database ([tracking plan](docs/tracking-plan.md)). Unset: events stay on the machine. |
| `LYRIS_POSTHOG_HOST` | `https://us.i.posthog.com` | PostHog host (`https://eu.i.posthog.com` for EU projects). |
| `LYRIS_APP_VERSION` | package version | Version tag attached to every usage event. |
| `LYRIS_CONTACT` | `lethuhang.cv@gmail.com` (set by `scripts/dev.sh` / `scripts/serve.sh`) | The operator's support email (or an `https://` page). The login page then offers "Xin mã mời" and "Quên mật khẩu?" links, and the legal texts show it in place of the contact placeholder. |

All variables, with production values: [docs/deploy.md §6](docs/deploy.md#6-biến-môi-trường).

#### Tests

Run from the repository root (each line runs in its own subshell, so they can be pasted in order):

```bash
(cd backend && .venv/bin/pytest -q)                                  # ~1,650 tests
(cd frontend && npm test && npm run typecheck && npm run build)      # ~465 tests
backend/.venv/bin/python harness/run_eval.py --model gemma4:12b        # model-behaviour scenarios (needs Ollama)
bash verification/verify.sh                                           # the harness judge: all of the above + the browser bot (see Harness below)
```

#### Repository map

| Path | Contents |
|---|---|
| `backend/lyris/` | FastAPI app: `api/`, `prompt/` (prompt builder, vi/en templates), `state/` (emotions, extraction), `memory/`, `lore/`, `jobs/` (background worker, prefill), `auth/`, `analytics/` (event tracking), `compliance/` (terms consent, reports, account deletion and export), `db/` (SQLite and migrations) |
| `frontend/src/` | React app: `pages/` (explore, character, chat, studio, auth, admin), `components/`, `lib/` |
| `worlds/` | Hand-written character worlds (`card.json` and `world.md`) |
| `harness/` | Model bake-off and behaviour checks on the real model (`run_eval.py`; `verify.sh --real-model` calls it) |
| `environment/` | Harness ②: rules for the AI, machine check, the browser bot (`bot.mjs`, `e2e.mjs`, `fake-server.py`) |
| `verification/` | Harness ③: `verify.sh` (the judge) and `plan-check.sh` |
| `memory/` | Harness ④: `features.json` (feature state), `features.mjs`, `progress.md`, `po-questions.md` |
| `training/` | LoRA fine-tuning experiments (planned phase) |
| `docs/` | Phase designs (`plan.md`, `phase1–4.md`, `auth.md`, `design-impl.md`), [coins](docs/coins.md), [hosted server and App Store plan](docs/server.md), [tracking plan](docs/tracking-plan.md), [compliance](docs/compliance.md), [deploy](docs/deploy.md), [demo script](docs/demo-script.md), legal texts (`legal/terms.md`, `legal/privacy.md`) |
| `scripts/` | `dev.sh` (development), `serve.sh` (production-like run), `lyris-admin.sh` (setup code, password reset), `ollama-env.sh` (macOS Ollama settings) |
| `wiki/` | Harness ①, the source of truth: original ideas (`raw/`), feature pages `features/F01…F47` (app) and `F50…F62` (hosted plan) with "Done when" and "Tests", screens, decisions, lessons learned |
| `DESIGN.md` | Design system and UI/UX specification |

### Launch and deploy

- **Submitted version (built):** web app, installable PWA, running on one machine at home over LAN; a single-server HTTPS deployment (Caddy, systemd) is documented in [docs/deploy.md](docs/deploy.md) but not yet run on a real server. One machine with an NVIDIA GPU (≥ 16 GB VRAM) or Apple Silicon (≥ 24 GB) runs Ollama and the backend.
- **Public launch (planned):** the hosted app on the web, App Store and Google Play described in the [Roadmap](#roadmap-hosted-lyris).
- **Production setup:** [docs/deploy.md](docs/deploy.md): Ollama service and model, uvicorn as a systemd service (no `--reload`, `--no-proxy-headers`, one process), Caddy serving `frontend/dist` and proxying `/api`, `LYRIS_COOKIE_SECURE=1`, nightly SQLite backups, updates (migrations run on restart), capacity (~2 replies at once per 12B model) and monitoring.
- **Quick production-like run:** `bash scripts/serve.sh`.

### Roadmap: hosted Lyris

The submitted version runs on one machine (SQLite + Ollama) and stays supported as the self-host mode. After the course submission, Lyris becomes a public hosted app on the web, the App Store and Google Play. The full design is in [docs/server.md](docs/server.md) (planned features F50–F62, nothing coded yet):
- **Scale target:** ~10k monthly users, a few hundred people chatting at once.
- **Backend:** stateless FastAPI pods behind Cloudflare and a load balancer; Postgres (append-only coin ledger kept by triggers and row locks); Redis (session cache, distributed generation gate, resumable SSE); a Postgres-backed job queue; images on S3-compatible storage.
- **AI:** own GPU servers running the same open model (`gemma4:12b`, later our own LoRA fine-tunes) on vLLM, with an 8192-token context, prefix caching and story-sticky routing.
- **Mobile:** the existing React app wrapped with Capacitor plus native plugins (StoreKit 2, Play Billing, Sign in with Apple, push).
- **Payments:** Apple IAP and Google Play Billing in the apps, VNPay/MoMo on the web; every receipt is verified on the server and recorded in the same coin ledger.
- **Reviewed:** the design went through an architecture and App Store/Play review (23 points, accepted or rejected with reasons in [docs/server.md §21](docs/server.md#21-phản-biện-đã-áp-dụng-2026-11-14)): coin holds are fenced in Postgres, the Redis gate cannot leak capacity when a server dies, unsafe text is filtered before it is streamed, and the model keeps its voice when moving from Ollama to vLLM.
- **Rollout after submission:** phases G0–G8 (prepare → interfaces → Postgres → Redis + stateless API → vLLM → S3 + observability + web beta → open sign-up + VNPay/MoMo → iOS/Android apps → import + own LoRA). Every phase must keep `verification/verify.sh` green in the self-host mode.

**Other planned product features** (not built):

| Feature | Notes |
|---|---|
| Own LoRA fine-tune for Vietnamese roleplay (F41) | A 12B training trial did not fit in 24 GB, so it waits for GPU servers |
| Remote HTTPS access for self-hosters via Tailscale (F37) | The hosted version gets HTTPS behind Cloudflare |
| Image interaction: sending images in chat (F38) | The "+" menu item is a locked shell today |
| Hosted coin economy with real payments (F56 Apple IAP / Google Play Billing, F57 VNPay/MoMo) | Same coin rules as the built test mode |
| Community: comments, follows, sharing (F39) | Needs its own moderation and privacy plan |
| Story director and "Khoảnh khắc" moments (F40) | The banner and tab exist; the backend does not generate them yet |
| Tender Moment: phone calls with the character, emotional character voices, ambient sounds, voice input | Idea stage, no design yet; also the first early-access feature in the [revenue model](#revenue-model) |
| Premium personalization, multilingual characters, subscription, real ads, streaks | See [Revenue model](#revenue-model) |

### Limitations and future evaluation

**Limitations today**
- **Hardware barrier:** self-hosting needs about 16 GB of memory just for the model, which rules out most phones and ordinary laptops.
- **Model dependence:** a 12B open model still hallucinates, sometimes contradicts the lore, forgets plans made by text and repeats phrases. Prompt rules and validation reduce this but do not remove it.
- **Internal evaluation only:** unit tests, the browser bot and model-behaviour scenarios show that the app does what its specification says. They do not establish real-world quality, user satisfaction or product-market fit, and the expected outcomes in [The problem](#the-problem) are not yet measured with real users.

**What we will evaluate next**
- Compare local and open models for Vietnamese roleplay (forms of address, player agency, character voice).
- Memory retrieval accuracy over long conversations.
- Character consistency over long sessions.
- Usability studies with Vietnamese interactive-fiction readers, starting with the two [personas](#customer-personas-hypotheses-to-validate).
- Lightweight fine-tuning (LoRA) and whether it beats prompting alone.

### Tracking plan

Full plan: [docs/tracking-plan.md](docs/tracking-plan.md).
- **57 events** across acquisition, activation, engagement and AI quality, retention, creation, safety, account and coins; most are recorded by the server at the moment an action succeeds. **North Star: weekly engaged stories** (stories with 3+ player turns in a week).
- **No user text ever** goes into analytics (only fixed codes, booleans and bounded numbers; no IP). Events stay in the app database for 180 days and are forwarded to PostHog when `LYRIS_POSTHOG_KEY` is set. Users can opt out in Account settings.
- The owner sees DAU/WAU/MAU, the activation funnel and D1/D7 retention in Quản lý tài khoản → "Số liệu", and exports every event as CSV/JSONL for Round 2 analysis.

### Privacy and compliance

- **Legal texts:** [Terms](docs/legal/terms.md) and [Privacy Policy](docs/legal/privacy.md) (Vietnamese and English), public in the app at `#/terms` and `#/privacy`; consent is required at sign-up and recorded with its version. The contact email comes from `LYRIS_CONTACT`; the run scripts set it to lethuhang.cv@gmail.com.
- **Safe by default:** no sexual content; romance, jealousy and possessiveness stay non-explicit; sexual content involving minors is refused absolutely. The rule is in every story, texting and character-draft prompt.
- **User controls:** "Báo cáo" on every AI reply (the reply text reaches the operator only if the reporter allows it) and "Báo cáo nhân vật" on public characters, never linked to the reporter; "Tải dữ liệu của tôi" (JSON export), "Xoá tài khoản", and the usage-data opt-out (which also stops recording on that browser after sign-out).
- **A way in for open-web visitors:** sign-up is by invite code; the login page tells visitors without a code how to get one, and members who forgot their password how to reach the operator (`LYRIS_CONTACT`).
- **Planned, not built:** a "mature mode" behind real age verification, and coin payments through a compliant payment provider.
- **Checklist** against open-web, Google Play, App Store and Vietnam personal-data rules: [docs/compliance.md](docs/compliance.md).

### AI-native workflow: how we built Lyris with Claude

Our team built Lyris in about four days with **Claude Code** (Claude Opus). We wrote the vision, the design spec (`DESIGN.md`), the character worlds and every product decision. Claude wrote almost all of the code, tests and design docs. We directed and corrected it in plain Vietnamese.

#### How the work was organised

1. **Plan first, as files.** Claude reviewed and rewrote the original plan into `docs/plan.md`. Each phase starts with a design doc (`docs/phase3.md`, `docs/phase4.md`, `docs/auth.md`) that fixes contracts before any code: tables, API payloads, UI copy and test plan.
2. **Multi-agent workflows for every substantial phase.** One phase is a scripted pipeline of sub-agents:
   - design;
   - an *adversarial critique* that edits the design;
   - backend and frontend implementation;
   - review along 3–4 independent lenses (security, data isolation, cache and performance, UX);
   - an *adversarial verifier* for each finding, which tries to refute it before anyone fixes it;
   - a fix stage with regression tests;
   - an end-to-end smoke test on a copy of real data.

   Phase 4 (lorebook) used 22 agents and Phase 4b (accounts) 23, about two hours each.
3. **Measure on the real model, not in theory.** Claims about speed and model behaviour were tested on the local model with timing tables and Ollama cache logs. Before/after scenario tables covered cases such as forgetting a birthday, jealousy and apologies.
4. **Persistent memory of preferences.** Claude keeps short memory notes of standing rules (reply in Vietnamese, say "story" not "câu chuyện", hide technical UI, no quotes in dialogue cards, equal-size grid cards). Corrections then stick across sessions.
5. **A wiki as the source of truth.** `wiki/` keeps our original messages verbatim (`raw/`), a page per feature with a *Done when* checklist checked against the code, a page per decision with its reason, and `learned.md` for mistakes not to repeat.
6. **A launch-readiness pass against the brief.** Before submission we gave Claude the Apero assignment brief and asked whether Lyris would pass. The gap analysis found what was missing for a public launch: no event tracking, no Terms or Privacy Policy, no consent, no in-app reporting, no account deletion or data export, and no deploy guide, demo script or team section. We made the product decisions (store events locally and in PostHog with no user text; safe content by default with no age gate yet; mature mode only as a plan), then ran one scripted workflow: backend tracking → backend compliance → frontend → documentation → review and fixes, each stage with the same hard rules and the full test suites green at the end.

#### What worked

- **Adversarial review caught real bugs before the user did.** Examples:
  - parallel wrong-password requests that bypassed the login rate limit;
  - a session surviving a password change;
  - side characters' secrets leaking into the lorebook;
  - the background prefill sending a prompt 6 tokens different from the real one, which made it useless.

  Adversarial verifiers filtered out false alarms, so fix stages worked only on confirmed defects.
- **Measuring beat guessing.** Reading Ollama's prefix-cache logs showed exactly why long stories were slow, and led to the "raw prefill" fix: first-token time on window shifts dropped from 26–30 s to about 5 s. A suspected slow-prompt regression (68 s per extraction) turned out to be the machine running at half speed; the fix that followed still cut extraction to about 15 s.
- **Tests as the contract.** About 1,650 backend and 465 frontend tests, including a route-by-route data-isolation sweep across two accounts and a check that no typed text ever reaches analytics. Large refactors such as adding login to every route stayed safe.
- **Checking ourselves against the brief.** Reading the assignment as a checklist, rather than only building features, surfaced launch work (tracking, consent, deletion, reporting) that a feature-by-feature plan had left for "later".
- **Design docs before code.** Contracts written first let backend and frontend agents work without stepping on each other. A "critique" pass on the design was much cheaper than fixing code later.

#### What didn't work (and what changed)

- **Taste needs the human.** Claude's defaults were often reasonable but not what we wanted:
  - the "Bắt đầu story" wording;
  - Explore cards too large;
  - quotes kept inside dialogue cards;
  - a stretched last card in the grid;
  - a placeholder too long for a phone;
  - the featured character listed twice.

  Each correction became a rule in memory or in `wiki/learned.md`.
- **Prompting can't fix everything in a 12B model.** DM replies kept ending with "ngủ sớm đi", and the character sometimes contradicted the lore or forgot a text-message plan. Prompt changes and validation rules reduced these but did not remove them. That is the case for the planned LoRA fine-tune.
- **Shared hardware got in the way.** Real-model tests share one local GPU with our own chatting. We had to stop the app during measurements, and long workflows were paused and resumed several times. One measurement was wrong because the machine was under memory pressure.
- **Agents slip on the rules.** Agents occasionally broke house rules, such as calling the system Python instead of the project's virtual environment, or echoing a temporary secret into a log. Explicit hard rules in every agent prompt, plus a review stage, contained this.
- **Cost.** Thorough multi-agent phases are token-heavy (millions of tokens per phase). They pay off for security-sensitive or cross-cutting work; small UI fixes are faster done directly.
- **Some things cannot be verified by an agent.** The production Caddy setup was written from documentation, not run on a server; the demo video and the parallel-generation speed on a GPU need a person and real hardware. These are marked as such in the docs instead of being claimed as done.

### Harness (based on Apero's mini-harness)

Lyris is built and checked with a harness adapted from Apero's teaching *mini-harness*, with the same rules: the model may only **claim** a feature (🟡); only the verification script can mark it passing (✅); after 3 red runs on one feature the model stops (⛔) and writes a lesson in `wiki/learned.md`; open product questions go to `memory/po-questions.md`; and the wiki is the source of truth.

| Part | Folder | What it holds |
|---|---|---|
| ① Wiki | `wiki/` | One page per feature: `features/F01-…` to `F47-…` for the app and `F50-…` to `F62-…` for the hosted plan. Each page has "Done when" lines of three kinds (`Unit:`, `Bot:`, `Model thật:`) and a "Tests" list naming the tests that prove them. Also screens, decisions, `learned.md`, `log.md` and `plan-checklist.md`. `raw/` keeps the owner's original messages and is never edited. |
| ② Environment | `environment/` | `rules.md`, the AI's working rules (pulled in by `CLAUDE.md`), and `doctor.mjs`, a machine check. Also the browser bot: `bot.mjs` drives headless Chrome over the DevTools Protocol (no extra dependencies), `e2e.mjs` holds 112 named checks, and `fake-server.py` runs the real backend with a scripted fake LLM and a temporary database on ports 8066/8067. The bot never touches `data/`, Ollama or ports 8000/5173. |
| ③ Verification | `verification/` | `verify.sh`, the judge, and `plan-check.sh`, which checks that the wiki is complete enough to build. |
| ④ Memory | `memory/` | `features.json` holds only the state of each feature and is written by `features.mjs`, never by hand. Also `progress.md` and `po-questions.md`. |

`harness/` is separate: it holds the model bake-off and the behaviour scenarios on the real model (`run_eval.py`). `verify.sh --real-model` calls it.

**Claude Code commands** (`.claude/commands/`):
- `/plan`: a new idea becomes wiki pages and a feature plan. The raw message is saved with `environment/raw.mjs`, then the command runs `plan-check`.
- `/build`: the model builds features until verification is green (claim, then `verify.sh`).
- `/play`: runs the bot and shows the report with screenshots.

**By hand:**

```bash
node environment/doctor.mjs                    # is the machine ready?
bash verification/plan-check.sh                # is the wiki complete enough to build?
node memory/features.mjs sync                  # read wiki/features/F*.md into memory/features.json
node memory/features.mjs claim F07             # the model says "built, not proven yet" (🟡)
bash verification/verify.sh                    # judge every claimed feature (full suites + bot)
bash verification/verify.sh --quick F07        # fast loop; never marks ✅
bash verification/verify.sh --real-model F07   # also run harness/run_eval.py on Ollama, only when nobody is using the app
node environment/bot.mjs                       # the bot alone; report in reports/latest/report.html
node memory/features.mjs list                  # the tally
```

`verify.sh` runs five steps:
1. Every referenced test exists.
2. The tests each feature names pass.
3. The full suites pass: backend pytest, frontend tests, typecheck and build.
4. The bot is green and every `bot: …` check a feature names is green.
5. The real model: skipped without `--real-model`, and a feature with `Model thật` lines then stays 🟡.

Exit codes: 0 green, 1 red, 3 green with features still 🟡.

**Tally on 2026-11-14** (latest runs: backend 1,646 passed, frontend 465, bot 112/112): **✅ 37 · 🟡 5 · ⏳ 18 · ⛔ 0.**
- ✅ passing (including the real-model scenarios): F01–F21, F24–F36, F42, F43, F45.
- 🟡 built, waiting for the next full `verify.sh`: F22, F23, F44, F46, F47 (Explore search, the "Nhân vật hot" ranking and the reworked creator rewards).
- ⏳ planned: F37–F41 (iPhone over Tailscale, sending images, community, story director, model fine-tuning) and F50–F62 (hosted server and App Store, after the course).

The bot found a real bug on its first pass. The character editor validated the card after cleaning, and cleaning keeps only 3 "Lời nói đặc trưng" lines, so a 4th line was dropped silently instead of blocking the save. It is fixed and covered by a unit test (`saveProblems`).

### Team

| Name | Student ID | Role | Contributions |
|---|---|---|---|
| **Le Thu Hang** | 240116 | Product owner, lead builder | Product vision and every product decision; built the app with Claude Code (wiki as source of truth, harness, verification); hands-on QA; demo video |
| Nguyen Ngoc Anh Thu | 240065 | Research, tester | Problem statement, market data and research review, Jobs to be done, personas; app testing and bug reports |
| Nguyen Thi Hai An | 240032 | Content and design, tester | Sample characters and worlds, character art, UI feedback; app testing and bug reports |
| Nguyen Anh Hong | 240169 | Business | Revenue model and coin pricing, launch channels |
| Huynh Quoc Toi | 240193 | Tracking and QA | Tracking plan, privacy and terms review, app testing |

---

## Tiếng Việt

[Video demo](#video-demo) · [Vấn đề](#vấn-đề) · [Công việc cần làm](#công-việc-cần-làm-jobs-to-be-done) · [Người dùng mục tiêu](#người-dùng-mục-tiêu) · [Tính năng chính](#tính-năng-chính) · [Ra mắt và doanh thu](#kênh-ra-mắt-và-mô-hình-doanh-thu) · [Cài đặt và chạy](#cài-đặt-chạy-và-truy-cập) · [Ra mắt và triển khai](#ra-mắt-và-triển-khai) · [Lộ trình](#lộ-trình-lyris-trên-máy-chủ) · [Giới hạn](#giới-hạn-và-đánh-giá-tiếp-theo) · [Theo dõi sự kiện](#kế-hoạch-theo-dõi-sự-kiện) · [Quyền riêng tư](#quyền-riêng-tư-và-tuân-thủ) · [Quy trình cùng AI](#quy-trình-làm-việc-cùng-ai-nhóm-đã-xây-lyris-cùng-claude-thế-nào) · [Harness](#harness-theo-mẫu-mini-harness-của-apero) · [Nhóm](#nhóm)

**Nhãn dùng trong README:** **Đã có** = code và test có trong repo này. **Kế hoạch** = điều nhóm muốn Lyris sẽ có, chưa làm. Trạng thái chính xác của từng tính năng (✅ qua `verify.sh`, 🟡 đã làm và chờ chấm, ⏳ kế hoạch) ở [bảng đếm Harness](#harness-theo-mẫu-mini-harness-của-apero).

### Giới thiệu

Lyris là app nhập vai với nhân vật AI, ưu tiên tiếng Việt. Bạn chọn một nhân vật (hoặc tự viết trong Studio), bước vào một story với nhân vật đó và trò chuyện. AI dẫn truyện và đóng vai nhân vật, còn persona của bạn chỉ bạn điều khiển. Nhân vật nhớ những gì đã xảy ra, kể cả điều bạn nhắn tin. Cảm xúc của họ với bạn tăng hay giảm theo việc bạn làm, và họ chỉ biết những gì thế giới của họ cho phép. Bạn bè vào bằng mã mời và có story riêng tư của mình.

**Hướng đi.** Bản nộp bài (đã có) chạy trên một máy với model mở chạy local và tài khoản theo lời mời. Sau môn học, Lyris thành app công khai trên web, App Store và Google Play, coin bán qua cửa hàng và cổng thanh toán Việt Nam (kế hoạch, thiết kế ở [docs/server.md](docs/server.md); xem [Lộ trình](#lộ-trình-lyris-trên-máy-chủ)).

### Video demo

**Video demo (2–3 phút, luồng chính):** [xem trên Google Drive](https://drive.google.com/file/d/1ew4_fgywsVmjGFwK4U-7Vl9aLGexrYvS/view?usp=drive_link)

Kịch bản (thời điểm, thao tác, lời đọc): [docs/demo-script.md](docs/demo-script.md).

### Vấn đề

**Bối cảnh thị trường.** Nhập vai với AI đã là một mảng ứng dụng tiêu dùng có người trả tiền. Theo số liệu Appfigures do TechCrunch đưa tin (Perez, 2025), tới tháng 7/2025 có 337 app bạn đồng hành AI đang hoạt động và có doanh thu, tổng cộng 220 triệu lượt tải và 221 triệu USD người dùng chi trả. Con số này cho thấy mảng này có hoạt động thương mại trên thế giới; nó chưa chứng minh người dùng Việt Nam cần hay sẵn sàng trả tiền.

Nhập vai cuốn hút cần nhiều hơn một câu trả lời trôi chảy. AI phải giữ đúng bản sắc từng nhân vật, nhớ chuyện đã xảy ra, phản ứng nhất quán với mối quan hệ, và để persona của người chơi cho người chơi. Tiếng Việt khó hơn: xưng hô (anh/em, tớ/cậu, ta/ngươi…) mang theo tuổi, vai vế, độ thân và hoàn cảnh, và một đại từ sai là nhân vật vỡ.

| Vấn đề | Sai ở đâu | Nghiên cứu liên quan |
|---|---|---|
| **1. Quyền của người chơi** | Model nhập vai trôi khỏi chỉ dẫn cố định như "không bao giờ viết thay người chơi" chỉ sau vài lượt. Theo trải nghiệm của chính nhóm, các app chạy trên server như WHIF đôi khi bỏ qua điều người chơi vừa viết, nói và làm thay nhân vật của người chơi, rồi trôi khỏi cảnh. | Li và cộng sự (2024) đo được độ trôi chỉ dẫn đáng kể trong vòng tám lượt hội thoại. |
| **2. Thích ứng tiếng Việt** | Model không được đánh giá hay tinh chỉnh cho xưng hô theo quan hệ. Model nhập vai huấn luyện bằng tiếng Anh dùng sai xưng hô, chêm chữ Anh hay chữ Trung, và quên hai nhân vật gọi nhau thế nào. | Truong và cộng sự (2024) đánh giá LLM tiếng Việt trên 10 tác vụ và 31 chỉ số; không chỉ số nào nhắm vào xưng hô trong hội thoại. |
| **3. Trí nhớ và mạch truyện** | Nhân vật quên tên, lời hứa, sự kiện và tính cách qua các phiên dài, kể cả khi có context dài hay truy xuất, và thái độ không đổi dù người chơi làm gì. | Maharana và cộng sự (2024). |

Gộp lại, các vấn đề này khiến nhập vai giống một chuỗi cuộc chat rời rạc hơn là một câu chuyện đang tiếp diễn.

#### Công việc cần làm (Jobs to be done)

Cùng các vấn đề trên, nhìn từ phía người dùng: họ "thuê" Lyris để tiến tới điều gì, không phụ thuộc tính năng nào. Phân tích này dựa trên nghiên cứu ở trên và [chân dung khách hàng](#chân-dung-khách-hàng-giả-thuyết-cần-kiểm-chứng) bên dưới. Mọi phần đều là **giả thuyết cần kiểm chứng** bằng phỏng vấn và số liệu theo dõi sau khi ra mắt.

**Câu phát biểu công việc**

| Ai | Câu phát biểu |
|---|---|
| **Công việc chính: người đọc truyện** (độc giả truyện mạng ngôn tình tiếng Việt) | *Khi* đọc xong một chương vào buổi tối và còn muốn ở cạnh kiểu nhân vật mình thích, *tôi muốn* bước vào một story với nhân vật đó, nói và làm bằng persona của chính mình bằng tiếng Việt tự nhiên, *để* tự mình sống mối quan hệ ấy và hôm sau quay lại đúng chỗ đang dừng. |
| **Công việc liên quan: người viết nhân vật** (tác giả trên Wattpad / Facebook) | *Khi* đã tạo một nhân vật và thế giới của họ, *tôi muốn* biến nhân vật thành người mà độc giả trò chuyện được, được đóng đúng (giọng, xưng hô, bí mật), *để* độc giả gắn bó hơn và cộng đồng của tôi lớn lên. |

**Ba khía cạnh của mỗi công việc**

| | Người đọc truyện | Người viết nhân vật |
|---|---|---|
| **Chức năng** | Nhân vật trả lời đúng điều mình vừa viết, xưng anh/em đúng, nhớ tên và lời hứa qua nhiều ngày, và không bao giờ viết lời thay mình | Đặt một lần tính cách, xưng hô, lời nói đặc trưng, thế giới và ai biết bí mật nào; mọi độc giả đều gặp đúng nhân vật ấy |
| **Cảm xúc** | Đắm chìm, hồi hộp lãng mạn, được an ủi và chữa lành, thấy mình làm chủ persona; không bị khựng vì tiếng Việt lủng củng | Tự hào khi nhân vật "sống"; yên tâm nhân vật không bị bóp méo |
| **Xã hội** | Kể về nhân vật và khoảnh khắc yêu thích trong nhóm đọc truyện; rủ bạn cùng chơi | Có chỗ đứng trong cộng đồng viết; độc giả kéo thêm độc giả; được ghi nhận qua bảng xếp hạng |

**Các bước của công việc: cách làm hiện nay hỏng ở đâu**

| Bước | Cách làm hiện nay hỏng ở đâu | Lyris làm gì (đã có) |
|---|---|---|
| **1. Tìm nhân vật** hợp tâm trạng hôm nay | App chat AI phổ thông ưu tiên tiếng Anh; nền tảng đọc như Wattpad có nhân vật nhưng chỉ đọc được | Khám phá có lọc theo cảm xúc, ô "Tìm nhân vật", bảng "Nhân vật hot", hồ sơ chỉ xem |
| **2. Thiết lập persona và story** | Ít app cho người chơi đặt persona riêng cùng xưng hô và ngôn ngữ cho từng story | Sheet "Bước vào câu chuyện": persona, Story hay DM, ngôn ngữ, xưng hô theo nhân vật và theo story |
| **3. Chơi từng lượt** | App phổ thông viết thay người chơi, bỏ qua lượt vừa rồi, trôi khỏi cảnh; xưng hô sai, lẫn chữ Anh hay chữ Trung | Quy ước nhập lượt, chỉ dẫn cuối prompt bảo tiếp nối đúng lượt người chơi, prompt ưu tiên tiếng Việt |
| **4. Giữ mạch truyện qua nhiều ngày** | Nhân vật quên tên, lời hứa, sự kiện; thái độ không đổi; bạn nhập vai là người thật thì không phải lúc nào cũng rảnh, hoặc bỏ dở | Tóm tắt cảnh, ký ức và điều đã biết, lùi lại đúng khi sửa; sáu chỉ số cảm xúc; Story và DM chung một dòng thời gian; lúc nào cũng có mặt |
| **5. Chia sẻ và sáng tác** | Nền tảng chỉ đọc không cho độc giả tương tác; không gì thưởng cho tác giả mang độc giả tới | Studio nhân vật, sổ thế giới có "ai biết", nhân vật công khai, mã mời, coin thưởng sáng tác theo bảng xếp hạng |

**Các lực khi đổi sang Lyris** (vì sao người ta đổi, hay không đổi)
- **Lực đẩy từ hiện tại:** app AI chiếm vai người chơi, tiếng Việt sai, nhân vật hay quên; đọc truyện thì thụ động; bạn nhập vai người thật có lịch riêng.
- **Lực hút của Lyris:** nhân vật ưu tiên tiếng Việt, biết nhớ, để người chơi làm tác giả; các thế giới viết tay; story riêng tư; có mặt bất cứ lúc nào.
- **Lo lắng:** model 12B có đủ hay không; story riêng tư có thật riêng tư; hết coin thì sao; nội dung có an toàn. Lyris trả lời bằng 300 coin miễn phí, thêm 60 mỗi ngày và nhiệm vụ; story riêng tư hoàn toàn; không ghi chữ người dùng vào số liệu; tự tải dữ liệu và xoá tài khoản; nội dung mặc định an toàn.
- **Thói quen:** app đọc truyện, Wattpad, nhóm Facebook; app chat AI đã quen; nhập vai với người thật trên Discord hay Facebook. Kênh ra mắt đi thẳng tới những nơi này (xem [Kênh ra mắt](#kênh-ra-mắt)).

**Kết quả mong muốn và cách đo**

| Kết quả mong muốn (theo lời người dùng) | Cách đo | Trạng thái |
|---|---|---|
| Ít lần AI viết lời hay quyết định thay mình nhất | Harness: kết luận `godmodding` của model chấm trên các kịch bản như `03-hanh-dong-cho-ai`; khi dùng thật: tỉ lệ không hài lòng (`regenerate_used` + `message_edited` + `reply_rated` chê, trên mỗi `reply_completed`) | Kịch bản đã có và chạy nội bộ; tỉ lệ với người dùng thật là giả thuyết |
| Ít xưng hô sai và ít chữ nước ngoài chêm vào nhất | Kiểm tra máy của harness trên các kịch bản `06-viet-hien-dai`, `07-co-trang`, `08-tieng-anh` | Chỉ nội bộ; cần đánh giá với độc giả |
| Ít công sức nhất để quay lại story cũ đúng chỗ đang dừng | `story_resumed` mỗi tuần; kịch bản ký ức `f10-ky-uc` | Giả thuyết |
| Giữ story tiếp diễn | Số lượt mỗi story (`message_sent`); mục tiêu đầu ≥ 40 % story đã bắt đầu đạt 5 lượt; North Star: số story "sống" mỗi tuần | Giả thuyết ([tracking plan §5.3](docs/tracking-plan.md#53-first-targets-for-round-2)) |
| Quay lại với nhân vật | D1 ≥ 35 %, D7 ≥ 15 % (mục tiêu đầu) | Giả thuyết |
| Chờ câu trả lời ít nhất | Chữ đầu tiên dưới 10 giây cho ≥ 90 % câu trả lời sau khi máy đã nóng (`ttft_bucket` của `reply_completed`) | Đo nội bộ khoảng 5 giây với model 12B ở nhà; dùng thật là giả thuyết |
| Người viết: nhiều độc giả chơi nhân vật của mình nhất | Số người chơi mỗi nhân vật công khai, `story_started` từ nhân vật công khai, `character_published`, `creator_rank_reached` | Giả thuyết |

**Lyris trả lời từng vấn đề thế nào.** Các cách dưới đây đã có; hiệu quả với người dùng thật **vẫn cần đánh giá** (xem [Giới hạn](#giới-hạn-và-đánh-giá-tiếp-theo)).

| Vấn đề | Cách của Lyris (đã có) | Kết quả mong đợi |
|---|---|---|
| Người chơi bị lấn quyền | Tách bạch: AI đóng nhân vật và thế giới, chỉ người chơi viết persona của mình; [quy ước nhập lượt](#tính-năng-chính) và chỉ dẫn cuối prompt bảo tiếp nối đúng lượt người chơi | Ít lời, hành động hay quyết định do AI viết thay người chơi hơn |
| Tiếng Việt không nhất quán | Prompt ưu tiên tiếng Việt, xưng hô đặt theo nhân vật và theo story, so khớp lore giữ dấu | Tiếng Việt tự nhiên, đúng hoàn cảnh hơn (cần đánh giá) |
| Trí nhớ dài hạn yếu | Tóm tắt cảnh theo đợt, ký ức dài hạn, điều đã biết, lùi lại đúng khi tạo lại, sửa, xoá | Mạch truyện liền hơn (dự định; cần đánh giá) |
| Quan hệ đứng yên | Sáu chỉ số cảm xúc tăng giảm theo việc người chơi làm | Quan hệ có phản ứng và thay đổi |
| Thế giới không nhất quán | Sổ thế giới riêng cho từng nhân vật, mỗi mục ghi "ai biết" | Thế giới nhất quán, tiết lộ có kiểm soát |

**Tài liệu tham khảo:** xem [References](#references) ở cuối README.

### Người dùng mục tiêu

- **Người đọc truyện mạng tiếng Việt** (ngôn tình, đam mỹ, cổ trang, vườn trường) muốn *sống trong* câu chuyện thay vì chỉ đọc. Dùng điện thoại là chính, thường vào buổi tối.
- **Người viết và tạo nhân vật**, dựng cả thế giới (nhân vật phụ, nơi chốn, bí mật, móc sự kiện) và muốn nhân vật được đóng đúng.
- **Người thích tự chạy AI**, có máy đủ mạnh, coi trọng riêng tư hơn gói thuê bao.

#### Chân dung khách hàng (giả thuyết cần kiểm chứng)

Hai chân dung rút từ đối tượng của các [kênh ra mắt](#kênh-ra-mắt-và-mô-hình-doanh-thu). Đây là **giả thuyết, không phải kết quả nghiên cứu**: nhóm sẽ đối chiếu với số liệu theo dõi (phễu kích hoạt, D1/D7, sự kiện sáng tác) và phỏng vấn ngắn sau khi ra mắt.

| | **Linh, người đọc truyện** | **Minh, người viết nhân vật** |
|---|---|---|
| **Là ai** | 18–25 tuổi, sinh viên hoặc mới đi làm; tối nào cũng đọc ngôn tình, đam mỹ trên điện thoại (app đọc truyện, Wattpad, nhóm Facebook) | 20–30 tuổi; viết truyện mạng hoặc bài về nhân vật tự tạo trên Wattpad và nhóm viết trên Facebook; có một nhóm độc giả nhỏ |
| **Muốn** | Được ở *trong* câu chuyện với kiểu nhân vật mình thích (yêu chậm, ghen, chữa lành) mà AI không giành vai của mình | Nhân vật được đóng đúng (giọng, xưng hô, bí mật) và có lý do để độc giả quay lại |
| **Khó khăn hôm nay** | App ưu tiên tiếng Anh, xưng anh/em sai, nhân vật hay quên, AI viết lời thay mình | Không có cách dễ để biến nhân vật và thế giới thành thứ độc giả trò chuyện được; không gì thưởng cho việc mang độc giả tới |
| **Lyris cho gì** | Chế độ Story, quan hệ sáu chỉ số cảm xúc, trí nhớ, và "Bước vào câu chuyện" sau hai lần chạm | Studio nhân vật, sổ thế giới có "ai biết", nhân vật công khai, bảng "Nhân vật hot" và coin thưởng sáng tác |
| **Gặp ở đâu** | Nhóm đọc truyện trên Facebook, cộng đồng sách trên TikTok, cộng đồng đọc trên Wattpad | Cộng đồng viết trên Wattpad, nhóm viết trên Facebook, nhà sáng tạo TikTok |
| **Có thể trả tiền cho** | Coin để chat tiếp; cá nhân hoá và quyền thử sớm tính năng mới (kế hoạch) | Chủ yếu kiếm coin qua thưởng sáng tác; có thể nạp để chat thử ở Studio |
| **Tín hiệu cần kiểm** | Story đầu tiên có từ 3 lượt, D7, số lượt mỗi ngày | Số nhân vật đăng công khai, số người chơi mỗi nhân vật công khai |

### Tính năng chính

Mọi thứ trong bảng này **đã có** và có test do `verification/verify.sh` chạy. Tính năng kế hoạch nằm ở [Lộ trình](#lộ-trình-lyris-trên-máy-chủ) và [Giới hạn](#giới-hạn-và-đánh-giá-tiếp-theo).

**Cách viết một lượt** (cơ chế giữ quyền người chơi):

| Bạn gõ | Nghĩa là | AI làm gì |
|---|---|---|
| `"…"` | Lời của chính persona bạn | Hiện thành ô thoại của bạn; nhân vật đáp lại |
| `*…*` | Hành động của persona bạn | Xem như việc bạn đã làm; AI có thể tả hệ quả nhìn thấy được nhưng không thêm hành động mới cho bạn |
| `*"…"*` | Trích dẫn hoặc lời của người khác | Ở lại trong dẫn truyện, không thành lời thoại của bạn |
| `((…))` | Chỉ đạo ngầm cho AI, vd. `((anh ấy ghen nhưng giấu))` | Nhân vật làm theo bằng giọng của mình và không nhắc lại; trong chat hiện thành một chip nhỏ |

| Mảng | Làm gì |
|---|---|
| **Chế độ Story và DM** | Story đọc như tiểu thuyết: dẫn truyện chữ nghiêng, lời thoại trong ô thoại, suy nghĩ của nhân vật trong thẻ làm mờ, chạm để đọc. DM giống app nhắn tin. Hai chế độ chung một dòng thời gian: xưng tên qua tin nhắn thì trong story nhân vật vẫn biết. |
| **Người chơi là tác giả** | AI đóng nhân vật và thế giới, không bao giờ viết lời, hành động hay quyết định thay bạn. Chỉ dẫn cuối mọi prompt bảo AI tiếp nối đúng từ điều bạn vừa viết, không nhảy cảnh. |
| **Sáu chỉ số cảm xúc** | Thương mến, tin cậy, rung động, chiếm hữu, sợ mất, chán ghét (0–100) tăng *và giảm* theo việc bạn làm. Ghen thì tin cậy giảm, xin lỗi thì chán ghét giảm, chuyện thường ngày hầu như không đổi gì. Chỉ số được đổi thành chỉ dẫn diễn xuất cho nhân vật, không bao giờ đưa con số thô vào prompt. |
| **Trí nhớ** | Tóm tắt cảnh theo đợt, ký ức dài hạn và các điều đã biết. Tìm theo từ khoá, và theo nghĩa nếu máy có model embedding. Tạo lại, sửa hay xoá một lượt thì trạng thái cũng lùi lại đúng. |
| **Sổ thế giới (lorebook)** | Mỗi nhân vật mang theo thế giới riêng: nhân vật phụ, nơi chốn, các mục lore, nhập từ file Markdown `world.md`. Mục được gợi ra bằng từ khoá, so khớp đúng tiếng Việt và giữ dấu. Mỗi mục ghi rõ ai biết: mọi người, chỉ một số nhân vật, hay chỉ bạn. Spoiler chỉ bạn biết không bao giờ tới model. |
| **Studio nhân vật** | Tạo và sửa nhân vật, AI viết nháp từ một dòng ý tưởng, lời nói đặc trưng, xưng hô, ảnh đại diện, nhập và xuất Character Card V2. |
| **Khám phá và hồ sơ** | Ô "Tìm nhân vật" và dải "Nhân vật hot" thay cho nhân vật nổi bật trước đây, bảng đầy đủ top 100 ở `#/explore/hot` (F46/F47); lọc theo cảm xúc ("Chữa lành", "Tình đầu"…), lưới thẻ đều nhau, hồ sơ chỉ xem với nút "Bước vào câu chuyện". |
| **Trợ giúp khi cần** | Nút "+" ở ô chat: gợi ý trả lời (chỉ khi bấm), dòng thời gian sự kiện, gửi hình ảnh (mới có khung). |
| **Tài khoản** | Chủ máy và thành viên được mời, mã mời, đăng nhập bằng mật khẩu (scrypt, phiên HttpOnly), trang quản lý chỉ chủ máy thấy, story riêng tư hoàn toàn. Nhân vật có thể bật công khai; người khác chơi trên bản sao riêng của họ. |
| **Nhanh trên máy vừa phải** | Prompt được sắp theo cách giữ được cache, và lượt sau được chuẩn bị trước ("prefill") khi bạn đang gõ. Thời gian chờ chữ đầu tiên ở story dài giảm từ khoảng 30–47 giây xuống khoảng 5 giây với model 12B. |
| **Không chữ kỹ thuật** | Giao diện không có tên model, token hay trạng thái máy. Lúc chờ chỉ hiện ba chấm nhảy. Thiết lập kỹ thuật nằm trong "Nâng cao". |
| **An toàn và quyền riêng tư** | Nội dung mặc định an toàn (không nội dung tình dục; tình cảm, ghen tuông kín đáo; tuyệt đối không gì tình dục với trẻ vị thành niên). "Báo cáo" trên mọi câu trả lời của AI và trên hồ sơ mọi nhân vật công khai (chủ máy ẩn được nhân vật bị báo cáo), Điều khoản và Chính sách có lưu lần đồng ý, tự tải dữ liệu và xoá tài khoản, tắt được chia sẻ dữ liệu sử dụng ẩn danh. |
| **Coin** | Ví coin có chip trên đầu trang, 6 coin mỗi câu trả lời của nhân vật, màn "Nạp coin" (chế độ thử), nhiệm vụ hằng ngày và thưởng sáng tác theo bảng "Nhân vật hot". Chi tiết ở [Mô hình doanh thu](#mô-hình-doanh-thu). |
| **Số liệu sử dụng** | 57 sự kiện, không chứa chữ người dùng; trang "Số liệu" của chủ máy (DAU/WAU/MAU, phễu, D1/D7), xuất CSV/JSONL; tuỳ chọn gửi sang PostHog. |

### Kênh ra mắt và mô hình doanh thu

#### Kênh ra mắt

| Kênh | Đối tượng | Ở đâu | Làm thế nào | Vì sao hợp |
|---|---|---|---|---|
| **1. Khám phá qua cộng đồng** | Độc giả truyện mạng lãng mạn tiếng Việt (ngôn tình, đam mỹ, cổ trang, vườn trường) | Nhóm Facebook Việt Nam, cộng đồng sách và nhập vai trên TikTok, máy chủ Discord, cộng đồng đọc trên Wattpad | Giới thiệu Lyris là app ưu tiên tiếng Việt; clip ngắn về chế độ Story với các thế giới viết tay đã có (Lục Bắc Uyên, Yến Hoành Sinh, Cố Hoài Dã, Tần Dương): bước vào story, trò chuyện, tự làm chủ persona. Với độc giả Wattpad: một cách khác để sống trong truyện xoay quanh nhân vật. | Các cộng đồng này vốn mê nhân vật hư cấu và truyện xoay quanh quan hệ. |
| **2. Khám phá nhờ tác giả** | Người viết và tạo nhân vật | Cộng đồng viết trên Wattpad, nhóm viết trên Facebook, nhà sáng tạo TikTok, cộng đồng nhập vai | Studio nhân vật và sổ thế giới cho người viết; đăng nhân vật công khai và chia sẻ với người theo dõi; bảng "Nhân vật hot" và coin thưởng sáng tác (đã có) cho tác giả lý do để quảng bá. Về sau: hợp tác với tác giả truyện mạng Việt Nam, kể cả tác giả Wattpad, chỉ khi có phép của người giữ bản quyền. | Mỗi tác giả mang theo nhân vật, thế giới và độc giả của mình. |
| **3. Giới thiệu và chia sẻ** | Người dùng hiện có | Trong app | Mã mời (đã có): mỗi thành viên được mời có story riêng tư của mình. Thưởng coin khi giới thiệu bạn bè là kế hoạch (xem Doanh thu). | Lý do tự nhiên để rủ bạn bè. |

#### Phân phối

- **Bản nộp bài (đã có):** web app, cài được dạng PWA, chạy từ một máy trong mạng LAN ở nhà (cách chạy HTTPS trên một máy chủ đã viết ở [docs/deploy.md](docs/deploy.md), chưa chạy trên máy chủ thật). Đăng ký bằng mã mời phát theo đợt, khớp sức chứa (khoảng hai câu trả lời cùng lúc cho mỗi model 12B).
- **Ra mắt công khai (kế hoạch, sau môn học):** Lyris trên máy chủ, có trên web, **App Store** và **Google Play**, đăng ký mở (email, Sign in with Apple, Google) và thanh toán coin thật (Apple IAP, Google Play Billing, VNPay/MoMo). Thiết kế: [Lộ trình](#lộ-trình-lyris-trên-máy-chủ) và [docs/server.md](docs/server.md).

#### Mô hình doanh thu

**Freemium + mua trong app + gói tháng + quảng cáo + kinh tế người sáng tạo.** Chat tốn coin. Tài khoản nào cũng được coin miễn phí và kiếm thêm được; trả tiền thì mua thêm coin và, về sau, các tiện ích khác. Đầu vào đã được [kế hoạch theo dõi sự kiện](#kế-hoạch-theo-dõi-sự-kiện) đo sẵn: số tin nhắn mỗi người mỗi ngày, chi phí tính toán mỗi lượt và mọi sự kiện coin.

**Đã có** (thiết kế: [docs/coins.md](docs/coins.md); tính năng F42–F47; chế độ thử, chưa có tiền thật):
- **Phải có tài khoản mới chat được.** Tài khoản mới được **300 coin**; mỗi ngày mở app được thêm **60** (điểm danh hằng ngày; ngày đầu là 360).
- **Trả theo câu trả lời:** mỗi câu trả lời của nhân vật tốn **6 coin**: lượt gửi, "Tạo lại câu trả lời", DM và chat thử ở Studio. Gợi ý trả lời và AI viết nháp nhân vật thì miễn phí. Câu trả lời lỗi hay chưa kịp bắt đầu thì không mất coin. Hết coin thì ô nhập khoá, có nút "Nạp coin" và "Nhiệm vụ".
- **Gói coin có thưởng theo bậc:** 100 coin giá 10.000đ · 550 (500 + 50 thưởng) giá 50.000đ · 1.200 (1.000 + 200 thưởng) giá 100.000đ · 2.500 (2.000 + 500 thưởng) giá 200.000đ. Trước khi ra mắt, màn "Nạp coin" chạy chế độ thử: giá là giá dự kiến khi ra mắt, chưa bán gì; người quản lý tặng mã nạp dùng một lần hoặc cộng coin tay kèm lý do. Coin của chế độ thử về 0 khi ra mắt.
- **Kiếm coin không cần trả tiền:**
  - **Làm nhiệm vụ:** tối đa 30 coin mỗi ngày: xem quảng cáo mẫu 15 giây (+5, ba lần; chỗ giữ cho quảng cáo có thưởng, chưa nối mạng quảng cáo), trò chuyện với 3 nhân vật khác nhau (+10), gửi 20 lượt (+5).
  - **Sáng tác:** nhân vật công khai của bạn vào top 100, top 50, top 10 của bảng "Nhân vật hot" thì bạn được +100, +200, +300 coin, mỗi bậc một lần cho mỗi nhân vật (lên thẳng top 10 nhận đủ 600). Bảng xếp theo tổng số người chơi từ trước tới nay (tài khoản khác đã thật sự chơi), cập nhật mỗi giờ. Nhân vật công khai đầu tiên được +50 một lần, sau khi đã công khai đủ 24 giờ và có người khác chơi. Người chơi được đếm khi có 3 câu trả lời đã trả coin ở 2 ngày khác nhau; thưởng xếp hạng tối đa 600 coin mỗi người tạo trong 7 ngày (phần dư chờ, không mất); chủ máy không nhận.

  Cách này thưởng cho những người mang người chơi tới.
- **Tự chạy trên máy mình vẫn miễn phí:** chủ máy không bao giờ tốn coin, và người tự chạy có thể tắt hẳn coin (`LYRIS_COINS=0`).
- **Coin không phải tiền:** không đổi ra tiền, không chuyển cho người khác, mất khi xoá tài khoản.

**Kế hoạch** (điều nhóm muốn Lyris sẽ có; chưa làm):

| Nguồn | Nhóm muốn có |
|---|---|
| **Chuyển đổi lần đầu** | Giảm giá gói coin đầu tiên mua trong 24 giờ đầu của tài khoản mới. Thưởng giới thiệu: người mời và người được mời cùng được thêm coin khi người được mời đã chat vài lượt, có trần mỗi tháng cho mỗi người mời. |
| **Mua trong app** | Báo trước khi sắp hết coin; tự động nạp theo ngưỡng, có hạn mức chi tiêu và cài đặt xác nhận; trả coin để được thử trước tính năng mới, bắt đầu với **gọi điện** với nhân vật (thuộc nhóm ý tưởng "Tender Moment": giọng nói có cảm xúc của nhân vật, âm thanh nền, và người chơi nói bằng giọng của mình). Cuộc gọi tính coin theo lượt: mỗi lần {{user}} nói và nhân vật đáp lại tốn coin như một lượt chat; mỗi câu đáp bị giới hạn độ dài (vài câu nói ngắn) để giống cuộc gọi thật và chi phí dễ đoán. |
| **Cá nhân hoá cao cấp** | Theme khung chat, màu chữ và màu bong bóng chat, khung avatar đôi (khung avatar cặp cho {{user}} và nhân vật AI), mua bằng coin; gói tháng có sẵn một bộ cơ bản. |
| **Nhân vật đa ngôn ngữ** | Nhân vật hiểu và nói hai thứ tiếng trở lên, chuyển qua lại tự nhiên (vd. nhân vật lai Việt). Hiện mỗi story đã đặt được tiếng Việt hoặc tiếng Anh (đã có). |
| **Quảng cáo** | Quảng cáo trong app cho người dùng miễn phí qua mạng quảng cáo; quảng cáo có thưởng để nhận coin (hiện là quảng cáo mẫu trong nhiệm vụ); bỏ quảng cáo bằng gói tháng hoặc gói cao cấp. |
| **Gói tháng** | Gói theo tháng: không quảng cáo, một lượng coin mỗi tháng, và bộ cá nhân hoá cơ bản. |
| **Kinh tế người sáng tạo** | Thêm vào thưởng bảng xếp hạng đã có: thưởng theo hiệu quả, tức mức người chơi tương tác với nhân vật công khai; tác giả quảng bá nhân vật và mời độc giả. |
| **Giữ chân** | Thêm vào coin hằng ngày và nhiệm vụ đã có: thưởng chuỗi 7 ngày chat liên tiếp và thưởng khi đi hết mạch truyện hay đạt cột mốc. |

**Luật cửa hàng.** Trong app iOS và Android, mọi giao dịch số (coin, gói tháng, cá nhân hoá, thử sớm) phải đi qua Apple In-App Purchase hoặc Google Play Billing, và mọi biên nhận được server xác minh rồi ghi vào cùng một sổ coin ([docs/server.md §11](docs/server.md#11-thanh-toán-po-5a)). Vì vậy tự động nạp và gói tháng theo đúng luật xác nhận mua và tự gia hạn của cửa hàng; VNPay/MoMo chỉ dùng trên web. Quảng cáo thật trong app cần App Tracking Transparency và nhãn quyền riêng tư.

### Cài đặt, chạy và truy cập

#### Phần cứng để chạy AI local

Lyris chạy một model khoảng 12 tỷ tham số qua Ollama, context 8.192 token. Model và bộ nhớ đệm chiếm khoảng 16 GB.

| | Tối thiểu | Khuyên dùng |
|---|---|---|
| Bộ nhớ cho model | 16 GB (bộ nhớ hợp nhất hoặc VRAM), dùng model nhỏ hơn (vd. `gemma4:e4b`) | Từ 24 GB bộ nhớ hợp nhất (Apple Silicon) hoặc GPU NVIDIA từ 16 GB cho `gemma4:12b` |
| Ổ đĩa | ~15 GB (model + app) | Từ 30 GB nếu thêm model embedding hoặc fine-tune |
| Hệ điều hành | macOS trên Apple Silicon (đã thử), Linux có Ollama (dự kiến chạy được) | macOS trên Apple Silicon hoặc Linux có GPU NVIDIA |

Phần lớn điện thoại và laptop thường không chạy nổi model, nên bản công khai sẽ chạy trên máy chủ ([Lộ trình](#lộ-trình-lyris-trên-máy-chủ)).

Tốc độ tăng theo băng thông bộ nhớ. Lượt trả lời đầu tiên sau khi mở app phải đọc cả story (vài chục giây). Các lượt sau bắt đầu trong khoảng 5 giây nhờ prefill.

#### Phần mềm

- [Ollama](https://ollama.com) 0.40 trở lên
- Python 3.12 và [`uv`](https://docs.astral.sh/uv/)
- Node.js 22 và npm

#### Các bước

```bash
# 1. Model
ollama pull gemma4:12b          # model chat (mặc định)
ollama pull bge-m3              # tuỳ chọn: tìm ký ức theo nghĩa

# Thiết lập Ollama nên dùng (đặt cho server Ollama rồi khởi động lại):
#   OLLAMA_FLASH_ATTENTION=1  OLLAMA_KV_CACHE_TYPE=q8_0  OLLAMA_NUM_PARALLEL=2
#   Trên macOS, scripts/ollama-env.sh cài sẵn các biến này qua LaunchAgent.

# 2. Thư viện backend
cd backend && uv sync && cd ..

# 3. Chạy backend (127.0.0.1:8000) và frontend (cổng 5173) cùng lúc
bash scripts/dev.sh
```

- **Lần đầu chạy:** Terminal in một **mã thiết lập** trong khung "Lyris: đặt mật khẩu cho tài khoản chủ máy". Mở http://localhost:5173, dán mã và đặt mật khẩu chủ máy. Không thấy khung thì chạy `bash scripts/lyris-admin.sh setup-code`.
- **Điện thoại hoặc máy khác cùng Wi-Fi:** mở địa chỉ LAN mà `dev.sh` in ra (`http://<ip-máy>:5173`) rồi đăng nhập. Đặt `LYRIS_LAN=0` nếu chỉ muốn mở trên máy này.
- **Lưu ý bảo mật:** qua Wi-Fi thường, đường truyền **chưa được mã hoá**, nên chỉ dùng trong mạng mình tin. Truy cập từ xa qua HTTPS (Tailscale, F37) đang trong kế hoạch; máy chủ công khai phải chạy sau HTTPS với `LYRIS_COOKIE_SECURE=1` ([docs/deploy.md](docs/deploy.md)).
- **Mời người khác:** vào Tài khoản → Quản lý tài khoản → Tạo mã mời, rồi gửi mã. Người được mời đăng ký bằng mã đó và có story riêng tư cùng ví coin của mình.
- **Quên mật khẩu chủ máy:** chạy `bash scripts/lyris-admin.sh reset-password <handle>`.

#### Chạy kiểu production trên một máy

```bash
bash scripts/serve.sh      # build frontend/dist, uvicorn không --reload (một tiến trình),
                           # phục vụ bản build bằng `vite preview` kèm proxy /api
LYRIS_API_PORT=8064 LYRIS_WEB_PORT=8065 LYRIS_DB_PATH=/tmp/lyris-demo/lyris.db bash scripts/serve.sh   # cổng và DB khác
```

Dùng để demo và dùng ở nhà. Ra mắt công khai (HTTPS, Caddy, systemd, sao lưu): xem [docs/deploy.md](docs/deploy.md).

Biến môi trường và sơ đồ thư mục: xem [Configuration](#configuration-environment-variables) và [Repository map](#repository-map) ở phần tiếng Anh (dùng chung cho cả hai bản).

#### Chạy test

Chạy từ thư mục gốc của repo (mỗi dòng chạy trong subshell riêng, dán lần lượt được):

```bash
(cd backend && .venv/bin/pytest -q)                                  # ~1.650 test
(cd frontend && npm test && npm run typecheck && npm run build)      # ~465 test
backend/.venv/bin/python harness/run_eval.py --model gemma4:12b        # kịch bản hành vi model (cần Ollama)
bash verification/verify.sh                                           # giám khảo của harness: tất cả các dòng trên + bot trình duyệt (xem mục Harness)
```

### Ra mắt và triển khai

- **Bản nộp bài (đã có):** web app, cài được dạng PWA, chạy trên một máy ở nhà qua LAN; triển khai HTTPS trên một máy chủ (Caddy, systemd) đã viết ở [docs/deploy.md](docs/deploy.md) nhưng chưa chạy trên máy chủ thật. Một máy có GPU NVIDIA (từ 16 GB VRAM) hoặc Apple Silicon (từ 24 GB) chạy Ollama và backend.
- **Ra mắt công khai (kế hoạch):** app trên máy chủ, có trên web, App Store và Google Play, như mô tả ở [Lộ trình](#lộ-trình-lyris-trên-máy-chủ).
- **Cài production:** [docs/deploy.md](docs/deploy.md): Ollama và model, uvicorn chạy bằng systemd (không `--reload`, `--no-proxy-headers`, một tiến trình), Caddy phục vụ `frontend/dist` và proxy `/api`, `LYRIS_COOKIE_SECURE=1`, sao lưu SQLite mỗi đêm, cập nhật (migration tự chạy khi khởi động lại), sức chứa (~2 câu trả lời cùng lúc mỗi model 12B), theo dõi.
- **Chạy nhanh kiểu production:** `bash scripts/serve.sh`.

### Lộ trình: Lyris trên máy chủ

Bản nộp bài chạy trên một máy (SQLite + Ollama) và vẫn được giữ làm chế độ tự chạy. Sau khi nộp bài, Lyris thành app công khai trên web, App Store và Google Play. Thiết kế đầy đủ: [docs/server.md](docs/server.md) (tính năng kế hoạch F50–F62, chưa có code):
- **Quy mô:** khoảng 10 nghìn người dùng mỗi tháng, vài trăm người chat cùng lúc.
- **Backend:** nhiều máy chủ FastAPI không trạng thái sau Cloudflare và load balancer; Postgres (sổ coin chỉ thêm, giữ bằng trigger và khoá dòng); Redis (cache phiên, cổng sinh chung, SSE nối lại được); hàng đợi việc nền trên Postgres; ảnh trên kho S3.
- **AI:** máy chủ GPU riêng chạy đúng model mở hiện tại (`gemma4:12b`, sau này bản LoRA tự train) bằng vLLM, context 8192 token, prefix caching, định tuyến mỗi story về cùng một máy.
- **Di động:** bọc app React hiện có bằng Capacitor, thêm plugin native (StoreKit 2, Play Billing, Sign in with Apple, push).
- **Thanh toán:** Apple IAP và Google Play Billing trong app, VNPay/MoMo trên web; mọi giao dịch được server xác minh và ghi vào cùng một sổ coin.
- **Đã phản biện:** thiết kế đã qua một vòng phản biện kiến trúc và duyệt App Store/Play (23 điểm, nhận hay bác kèm lý do ở [docs/server.md §21](docs/server.md#21-phản-biện-đã-áp-dụng-2026-11-14)): giữ chỗ coin có fence ở Postgres, cổng sinh trên Redis không rò chỗ khi một máy chủ chết, chữ không an toàn bị lọc trước khi tới người chơi, model giữ giọng văn khi chuyển từ Ollama sang vLLM.
- **Lộ trình sau khi nộp bài:** các giai đoạn G0–G8 (chuẩn bị → tách giao diện → Postgres → Redis + API không trạng thái → vLLM → S3, quan sát, beta web → đăng ký mở + VNPay/MoMo → app iOS/Android → nhập dữ liệu + LoRA tự train). Giai đoạn nào cũng phải giữ `verification/verify.sh` xanh ở chế độ tự chạy.

**Các tính năng sản phẩm khác trong kế hoạch** (chưa làm):

| Tính năng | Ghi chú |
|---|---|
| Tự fine-tune LoRA cho nhập vai tiếng Việt (F41) | Thử train model 12B không vừa 24 GB, nên chờ máy chủ GPU |
| Truy cập từ xa qua HTTPS cho người tự chạy, dùng Tailscale (F37) | Bản trên máy chủ có HTTPS sau Cloudflare |
| Tương tác bằng hình ảnh: gửi ảnh trong chat (F38) | Mục trong menu "+" hiện mới là khung khoá |
| Kinh tế coin trên máy chủ với thanh toán thật (F56 Apple IAP / Google Play Billing, F57 VNPay/MoMo) | Cùng luật coin với chế độ thử đã có |
| Cộng đồng: bình luận, theo dõi, chia sẻ (F39) | Cần kế hoạch kiểm duyệt và quyền riêng tư riêng |
| Đạo diễn story và "Khoảnh khắc" (F40) | Đã có banner và tab; backend chưa sinh ra |
| Tender Moment: gọi điện với nhân vật, giọng nhân vật có cảm xúc, âm thanh nền, nói bằng giọng mình | Mới là ý tưởng, chưa thiết kế; cũng là tính năng thử sớm đầu tiên trong [mô hình doanh thu](#mô-hình-doanh-thu) |
| Cá nhân hoá cao cấp, nhân vật đa ngôn ngữ, gói tháng, quảng cáo thật, chuỗi ngày | Xem [Mô hình doanh thu](#mô-hình-doanh-thu) |

### Giới hạn và đánh giá tiếp theo

**Giới hạn hiện nay**
- **Rào cản phần cứng:** tự chạy cần khoảng 16 GB bộ nhớ chỉ riêng cho model, nên phần lớn điện thoại và laptop thường không chạy được.
- **Phụ thuộc model:** model mở 12B vẫn bịa, thỉnh thoảng nói trái lore, quên hẹn đã nhắn và lặp cụm từ. Luật trong prompt và bước kiểm tra giảm được nhưng không hết.
- **Mới đánh giá nội bộ:** unit test, bot trình duyệt và kịch bản hành vi model cho thấy app làm đúng đặc tả. Chúng chưa chứng minh chất lượng thực tế, mức hài lòng hay độ phù hợp thị trường, và các kết quả mong đợi ở [Vấn đề](#vấn-đề) chưa được đo với người dùng thật.

**Sẽ đánh giá tiếp**
- So các model local và model mở cho nhập vai tiếng Việt (xưng hô, quyền người chơi, giọng nhân vật).
- Độ chính xác khi truy xuất ký ức qua hội thoại dài.
- Độ nhất quán của nhân vật qua các phiên dài.
- Thử nghiệm khả dụng với độc giả truyện tương tác tiếng Việt, bắt đầu từ hai [chân dung khách hàng](#chân-dung-khách-hàng-giả-thuyết-cần-kiểm-chứng).
- Fine-tune nhẹ (LoRA) và liệu nó có hơn chỉ dùng prompt hay không.

### Kế hoạch theo dõi sự kiện

Đầy đủ: [docs/tracking-plan.md](docs/tracking-plan.md).
- **57 sự kiện** theo cả vòng đời: thu hút, kích hoạt, tương tác và chất lượng AI, giữ chân, sáng tạo, an toàn, tài khoản và coin; phần lớn do server ghi đúng lúc thao tác thành công. **North Star: số story "sống" mỗi tuần** (story có từ 3 lượt người chơi trong tuần).
- **Không bao giờ ghi chữ người dùng** (chỉ mã cố định, true/false, số trong khoảng; không IP). Lưu trong DB của app 180 ngày, gửi thêm sang PostHog khi có `LYRIS_POSTHOG_KEY`. Người dùng tắt được trong Tài khoản.
- Chủ máy xem DAU/WAU/MAU, phễu kích hoạt, D1/D7 ở Quản lý tài khoản → "Số liệu", và xuất mọi sự kiện ra CSV/JSONL để phân tích ở Round 2.

### Quyền riêng tư và tuân thủ

- **Văn bản:** [Điều khoản](docs/legal/terms.md) và [Chính sách quyền riêng tư](docs/legal/privacy.md) (tiếng Việt và tiếng Anh), mở công khai trong app ở `#/terms`, `#/privacy`; phải đồng ý khi tạo tài khoản, lưu kèm phiên bản. Email liên hệ lấy từ `LYRIS_CONTACT`; script chạy app đặt sẵn lethuhang.cv@gmail.com.
- **Mặc định an toàn:** không nội dung tình dục; tình cảm, ghen tuông, chiếm hữu ở mức kín đáo; tuyệt đối từ chối mọi nội dung tình dục liên quan tới trẻ vị thành niên. Luật này có trong mọi prompt story, nhắn tin và AI viết nháp nhân vật.
- **Người dùng tự quản:** "Báo cáo" trên mọi câu trả lời của AI (chữ của câu trả lời chỉ tới người quản lý nếu người báo cáo cho phép) và "Báo cáo nhân vật" trên nhân vật công khai, không bao giờ gắn với người báo cáo; "Tải dữ liệu của tôi", "Xoá tài khoản", tắt chia sẻ dữ liệu sử dụng (tắt rồi thì trình duyệt đó cũng không bị ghi sau khi đăng xuất).
- **Lối vào cho người lạ trên web:** đăng ký bằng mã mời; trang đăng nhập chỉ cách xin mã, và cách liên hệ người quản lý khi quên mật khẩu (`LYRIS_CONTACT`).
- **Kế hoạch, chưa làm:** "chế độ người lớn" có xác minh tuổi thật; thanh toán coin qua nhà cung cấp thanh toán tuân thủ quy định.
- **Danh sách kiểm** theo web mở, Google Play, App Store và quy định dữ liệu cá nhân của Việt Nam: [docs/compliance.md](docs/compliance.md).

### Quy trình làm việc cùng AI: nhóm đã xây Lyris cùng Claude thế nào

Nhóm làm Lyris trong khoảng bốn ngày cùng **Claude Code** (Claude Opus). Nhóm viết tầm nhìn, đặc tả thiết kế (`DESIGN.md`), các thế giới nhân vật và mọi quyết định sản phẩm. Claude viết gần như toàn bộ code, test và tài liệu thiết kế. Nhóm chỉ đạo và sửa bằng tiếng Việt thông thường.

#### Cách tổ chức công việc

1. **Lên kế hoạch trước, bằng file.** Claude rà và viết lại plan gốc thành `docs/plan.md`. Mỗi phase bắt đầu bằng một tài liệu thiết kế (`docs/phase3.md`, `docs/phase4.md`, `docs/auth.md`) chốt hợp đồng trước khi viết code: bảng dữ liệu, dữ liệu API, chữ trên giao diện, kế hoạch test.
2. **Workflow nhiều agent cho mỗi phase lớn.** Một phase là một chuỗi agent phụ được viết sẵn:
   - thiết kế;
   - *phản biện* sửa thẳng vào thiết kế;
   - làm backend và frontend;
   - soát lỗi theo 3–4 góc nhìn độc lập (bảo mật, tách dữ liệu, cache và tốc độ, trải nghiệm);
   - mỗi lỗi tìm được có một *người kiểm chứng* cố bác bỏ trước khi sửa;
   - bước sửa kèm test chống lặp lỗi;
   - chạy thử từ đầu đến cuối trên bản sao dữ liệu thật.

   Phase 4 (sổ thế giới) dùng 22 agent, Phase 4b (tài khoản) dùng 23, mỗi phase khoảng hai tiếng.
3. **Đo trên model thật, không đoán.** Mọi nhận định về tốc độ và hành vi model đều được thử trên model local, kèm bảng thời gian và log cache của Ollama. Bảng so trước/sau có các tình huống như quên sinh nhật, ghen, xin lỗi.
4. **Ghi nhớ sở thích lâu dài.** Claude giữ các ghi chú ngắn về quy tắc cố định (trả lời tiếng Việt, gọi "story" thay vì "câu chuyện", giấu chữ kỹ thuật, không để ngoặc trong ô thoại, thẻ lưới đều nhau). Nhờ vậy lời sửa được giữ qua các buổi làm việc.
5. **Wiki là nguồn sự thật.** `wiki/` giữ nguyên văn tin nhắn gốc của nhóm (`raw/`), mỗi tính năng một trang kèm danh sách *Done when* đã đối chiếu với code, mỗi quyết định một trang kèm lý do, và `learned.md` ghi những lỗi không được lặp lại.
6. **Rà soát sẵn sàng ra mắt theo đề bài.** Trước khi nộp, nhóm đưa đề bài của Apero cho Claude và hỏi Lyris có qua được không. Bản phân tích thiếu hụt chỉ ra những gì còn thiếu để ra mắt công khai: chưa theo dõi sự kiện, chưa có Điều khoản và Chính sách, chưa hỏi đồng ý, chưa báo cáo nội dung trong app, chưa xoá tài khoản hay xuất dữ liệu, chưa có hướng dẫn triển khai, kịch bản demo và mục nhóm. Nhóm chốt quyết định sản phẩm (lưu sự kiện trong app và gửi PostHog, không có chữ người dùng; nội dung mặc định an toàn, chưa có cổng tuổi; chế độ người lớn chỉ là kế hoạch), rồi chạy một workflow: theo dõi sự kiện ở backend → tuân thủ ở backend → frontend → tài liệu → soát và sửa; bước nào cũng theo cùng luật cứng và kết thúc khi mọi bộ test đều qua.

#### Điều làm tốt

- **Soát lỗi phản biện bắt được lỗi thật trước khi người dùng gặp.** Ví dụ:
  - gửi song song nhiều lần đoán mật khẩu là vượt được giới hạn đăng nhập;
  - phiên đăng nhập vẫn sống sau khi đổi mật khẩu;
  - bí mật của nhân vật phụ lọt vào sổ thế giới;
  - phần chuẩn bị trước lượt sau gửi prompt lệch 6 token so với prompt thật, nên vô dụng.

  Người kiểm chứng loại bỏ các báo động giả, nên bước sửa chỉ làm trên lỗi đã xác nhận.
- **Đo tốt hơn đoán.** Đọc log cache của Ollama cho thấy chính xác vì sao story dài bị chậm, dẫn tới cách sửa "raw prefill": thời gian chờ chữ đầu tiên ở lượt cắt bớt story giảm từ 26–30 giây xuống khoảng 5 giây. Một nghi ngờ prompt chậm đi (68 giây mỗi lần chấm cảm xúc) hoá ra là do máy đang chạy nửa tốc độ; dù vậy, bản sửa sau đó vẫn rút lần chấm xuống khoảng 15 giây.
- **Test là hợp đồng.** Khoảng 1.650 test backend và 465 test frontend, gồm một bài quét từng route để chắc hai tài khoản không đọc được dữ liệu của nhau, và một bài kiểm không chữ nào người dùng gõ lọt vào số liệu. Nhờ vậy những thay đổi lớn như thêm đăng nhập vào mọi route vẫn an toàn.
- **Tự soát theo đề bài.** Đọc đề bài như một danh sách kiểm, thay vì chỉ làm từng tính năng, giúp lộ ra phần việc ra mắt (số liệu, đồng ý, xoá tài khoản, báo cáo) mà kế hoạch theo tính năng đã để "làm sau".
- **Viết thiết kế trước code.** Hợp đồng viết trước giúp agent backend và frontend làm song song mà không giẫm chân nhau. Phản biện trên giấy rẻ hơn nhiều so với sửa code về sau.

#### Điều chưa tốt (và đã đổi gì)

- **Gu thẩm mỹ cần con người.** Mặc định của Claude thường hợp lý nhưng không đúng ý nhóm:
  - chữ "Bắt đầu story";
  - thẻ Khám phá quá to;
  - ô thoại còn dấu ngoặc;
  - thẻ cuối trong lưới bị kéo giãn;
  - dòng gợi ý quá dài trên điện thoại;
  - nhân vật nổi bật hiện hai lần.

  Mỗi lần sửa trở thành một quy tắc trong bộ nhớ hoặc trong `wiki/learned.md`.
- **Prompt không sửa được hết cho model 12B.** Tin nhắn DM cứ kết bằng "ngủ sớm đi", và nhân vật thỉnh thoảng nói trái lore hoặc quên hẹn đã nhắn. Sửa prompt và thêm luật kiểm tra giảm được nhưng không hết. Đó là lý do cho kế hoạch fine-tune LoRA.
- **Dùng chung phần cứng gây vướng.** Test trên model thật dùng chung một GPU với lúc nhóm đang chat. Nhóm phải tắt app khi đo, và các workflow dài phải tạm dừng rồi chạy tiếp nhiều lần. Có một lần số đo sai vì máy đang thiếu RAM.
- **Agent đôi khi trượt quy tắc.** Agent thỉnh thoảng phạm quy tắc chung, như gọi Python hệ thống thay vì môi trường riêng của project, hoặc in lại một mã bí mật tạm thời vào log. Ghi luật cứng trong prompt của mọi agent cộng với bước soát lỗi đã kiềm chế được.
- **Chi phí.** Các phase nhiều agent rất tốn token (hàng triệu token mỗi phase). Đáng làm với phần nhạy cảm về bảo mật hoặc đụng nhiều nơi; sửa giao diện nhỏ thì làm trực tiếp nhanh hơn.
- **Có việc agent không tự kiểm được.** Cấu hình Caddy cho production được viết theo tài liệu, chưa chạy trên máy chủ thật; video demo và tốc độ sinh song song trên GPU cần người và phần cứng thật. Tài liệu ghi rõ những phần này thay vì nhận là đã xong.

### Harness (theo mẫu mini-harness của Apero)

Lyris được làm và kiểm bằng một harness chuyển từ *mini-harness* dạy học của Apero, giữ nguyên các luật: Model chỉ được **báo đã làm** (🟡); chỉ script kiểm tra mới được đánh dấu đạt (✅); một tính năng đỏ 3 lần thì Model dừng (⛔) và ghi một bài học vào `wiki/learned.md`; câu hỏi sản phẩm còn mở ghi vào `memory/po-questions.md`; Wiki là nguồn sự thật.

| Phần | Thư mục | Chứa gì |
|---|---|---|
| ① Wiki | `wiki/` | Mỗi tính năng một trang: `features/F01-…` tới `F47-…` cho app và `F50-…` tới `F62-…` cho kế hoạch máy chủ. Mỗi trang có các dòng "Done when" thuộc ba loại (`Unit:`, `Bot:`, `Model thật:`) và danh sách "Tests" ghi tên các test chứng minh chúng. Ngoài ra có màn hình, quyết định, `learned.md`, `log.md` và `plan-checklist.md`. `raw/` giữ nguyên văn lời của chủ dự án và không bao giờ bị sửa. |
| ② Environment | `environment/` | `rules.md`, luật làm việc của AI (`CLAUDE.md` kéo file này vào), và `doctor.mjs` để kiểm máy. Thêm bot trình duyệt: `bot.mjs` điều khiển Chrome headless qua DevTools Protocol (không thêm thư viện), `e2e.mjs` có 112 check có tên, `fake-server.py` chạy backend thật với LLM giả có kịch bản và DB tạm ở cổng 8066/8067. Bot không bao giờ đụng `data/`, Ollama hay cổng 8000/5173. |
| ③ Verification | `verification/` | `verify.sh` là giám khảo; `plan-check.sh` kiểm wiki đã đủ để build chưa. |
| ④ Memory | `memory/` | `features.json` chỉ giữ trạng thái của từng tính năng, do `features.mjs` ghi, không sửa tay. Thêm `progress.md` và `po-questions.md`. |

`harness/` là chuyện khác: thư mục này chứa phần so model và các kịch bản hành vi trên model thật (`run_eval.py`). `verify.sh --real-model` gọi tới nó.

**Lệnh của Claude Code** (`.claude/commands/`):
- `/plan`: biến một ý tưởng mới thành trang wiki và kế hoạch tính năng. Lời gốc được lưu bằng `environment/raw.mjs`, rồi lệnh chạy `plan-check`.
- `/build`: Model tự làm tính năng tới khi kiểm tra xanh (claim, rồi `verify.sh`).
- `/play`: chạy bot và cho xem báo cáo có ảnh.

**Chạy tay:**

```bash
node environment/doctor.mjs                    # máy đủ đồ nghề chưa
bash verification/plan-check.sh                # wiki đủ để build chưa
node memory/features.mjs sync                  # đọc wiki/features/F*.md vào memory/features.json
node memory/features.mjs claim F07             # Model báo "đã làm, chưa chứng minh" (🟡)
bash verification/verify.sh                    # chấm mọi tính năng đang 🟡 (bộ test đầy đủ + bot)
bash verification/verify.sh --quick F07        # vòng sửa nhanh, không bao giờ đánh ✅
bash verification/verify.sh --real-model F07   # chạy thêm harness/run_eval.py trên Ollama, chỉ khi không ai đang dùng app
node environment/bot.mjs                       # chỉ chạy bot; báo cáo ở reports/latest/report.html
node memory/features.mjs list                  # bảng đếm
```

`verify.sh` chạy năm bước:
1. Mọi test được tham chiếu đều có thật.
2. Các test mà từng tính năng ghi tên đều qua.
3. Bộ test đầy đủ qua: pytest backend, test frontend, typecheck và build.
4. Bot xanh, và mọi check `bot: …` mà tính năng ghi tên đều xanh.
5. Model thật: không có `--real-model` thì bỏ qua, và tính năng có dòng `Model thật` vẫn 🟡.

Mã thoát: 0 là xanh, 1 là đỏ, 3 là xanh nhưng còn tính năng 🟡.

**Bảng đếm ngày 2026-11-14** (các lần chạy gần nhất: backend 1.646 test qua, frontend 465, bot 112/112): **✅ 37 · 🟡 5 · ⏳ 18 · ⛔ 0.**
- ✅ đạt (kể cả kịch bản trên model thật): F01–F21, F24–F36, F42, F43, F45.
- 🟡 đã làm, chờ lần `verify.sh` đầy đủ tiếp theo: F22, F23, F44, F46, F47 (tìm nhân vật ở Khám phá, bảng "Nhân vật hot" và thưởng sáng tác làm lại).
- ⏳ kế hoạch: F37–F41 (iPhone qua Tailscale, gửi hình ảnh, cộng đồng, đạo diễn khoảnh khắc, tự train model) và F50–F62 (máy chủ và App Store, sau môn học).

Ngay lượt chạy đầu, bot đã tìm ra một lỗi thật. Trình sửa nhân vật kiểm card sau khi làm sạch, mà bước làm sạch chỉ giữ 3 dòng "Lời nói đặc trưng", nên dòng thứ 4 bị bỏ âm thầm thay vì chặn lưu. Lỗi đã được sửa và có unit test (`saveProblems`).

### Nhóm

| Tên | MSSV | Vai trò | Đóng góp |
|---|---|---|---|
| **Lê Thu Hằng** | 240116 | Product owner, người làm chính | Tầm nhìn và mọi quyết định sản phẩm; xây app cùng Claude Code (wiki làm nguồn sự thật, harness, chấm tự động); dùng thử và báo lỗi; video demo |
| Nguyễn Ngọc Anh Thư | 240065 | Nghiên cứu, kiểm thử | Phát biểu vấn đề, số liệu thị trường và nghiên cứu, Jobs to be done, chân dung khách hàng; dùng thử app và báo lỗi |
| Nguyễn Thị Hải An | 240032 | Nội dung và thiết kế, kiểm thử | Nhân vật mẫu và thế giới, ảnh nhân vật, góp ý giao diện; dùng thử app và báo lỗi |
| Nguyễn Anh Hồng | 240169 | Kinh doanh | Mô hình doanh thu và giá coin, kênh ra mắt |
| Huỳnh Quốc Tới | 240193 | Số liệu và kiểm thử | Kế hoạch tracking, rà soát quyền riêng tư và điều khoản, kiểm thử app |

---

## References

- Perez, S. (2025, August). AI companion apps on track to pull in $120M in 2025. *TechCrunch* (Appfigures data).
- Li, K., et al. (2024). Measuring and controlling instruction (in)stability in language model dialogs. *Conference on Language Modeling (COLM 2024)*. arXiv:2402.10962.
- Truong, S. T., et al. (2024). Crossing linguistic horizons: Finetuning and comprehensive evaluation of Vietnamese large language models. *Findings of NAACL 2024*.
- Maharana, A., et al. (2024). Evaluating very long-term conversational memory of LLM agents. *ACL 2024*.
