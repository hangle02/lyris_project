<p align="center">
  <img src="docs/assets/lyris-banner.png" alt="Lyris: Nơi những tâm hồn từ trang sách bước ra sưởi ấm thực tại" width="820">
</p>

# Lyris

> *Nơi những tâm hồn từ trang sách bước ra sưởi ấm thực tại.*
> Where the souls of storybook pages step out to warm the real world.

**English** · [Tiếng Việt](#tiếng-việt)

[Demo video](#demo-video) · [Build and run](#build-run-and-access) · [Launch and deploy](#launch-and-deploy) · [Tracking plan](#tracking-plan) · [Privacy and compliance](#privacy-and-compliance) · [AI-native workflow](#ai-native-workflow-how-we-built-lyris-with-claude) · [Harness](#harness-based-on-aperos-mini-harness) · [Team](#team)

---

## English

### Pitch

Lyris is a Vietnamese-first AI roleplay app.  You pick a character, or write your own in the Studio, step into a story with them, and talk. The AI narrates and plays the character. You alone control your persona. The character remembers what happened, including what you said by text message. Their feelings toward you rise and fall with what you do, and they know only what their world allows them to know. Friends can join with an invite code and get their own private stories.

### Demo video

> **TODO (team):** add the link to the 2–3 minute demo video here before submission.
> Script with timestamps, actions and voice-over: [docs/demo-script.md](docs/demo-script.md).

**Demo video:** *link coming soon*

### The problem

- **Roleplay apps write over the player.** Hosted apps such as WHIF often ignore what the player just wrote, act and speak *for* the player's character, and drift off the scene.
- **Vietnamese is an afterthought.** English-trained roleplay models get Vietnamese forms of address wrong (anh/em, tớ/cậu, ta/ngươi), mix in English or Chinese words, and forget the relationship between two characters.

- **Memory is shallow.** Characters forget names, promises and events after a few dozen turns, and their attitude never changes, whatever the player does.

### Target users

- **Readers of Vietnamese romance web fiction** (ngôn tình, đam mỹ, cổ trang, vườn trường) who want to *live inside* a story rather than read it. Mobile-first, mostly evenings.
- **Writers and character creators** who build characters and whole worlds (side characters, places, secrets, plot hooks) and want them played faithfully.
- **Self-hosting enthusiasts** with a capable machine who value privacy over a subscription.

### Core features

| Area | What it does |
|---|---|
| **Story and DM modes** | Story mode reads like a novel: italic narration, speech in dialogue cards, and the character's inner thoughts as blurred cards you tap to read. DM mode looks like a messaging app. Both share one timeline, so a name given by text is known in the story. |
| **Player stays the author** | The AI never writes your dialogue, actions or decisions. It continues directly from what you wrote. Hidden directions to the character go in `((…))`. Your own speech is written in `"…"`, actions in `*…*`, and other people's words in `*"…"*`. |
| **Six-emotion relationship** | Affection, trust, attraction, possessiveness, fear and aversion (0–100) rise *and fall* with your actions. Jealousy lowers trust, an apology lowers aversion, and small talk barely moves anything. The numbers become acting directions for the character and never appear in the prompt as raw numbers. |
| **Memory** | Rolling scene summaries, long-term memories and facts. Search is by keyword, plus by meaning when an embedding model is present. Regenerating, editing or deleting a turn rolls the state back correctly. |
| **Lorebook** | Each character can carry a world: side characters, places and lore entries, imported from a Markdown `world.md`. Entries are triggered by Vietnamese-aware keywords, with diacritics preserved. Each entry says who knows it: everyone, only the character, or only you. Spoilers that only you know never reach the model. |
| **Character Studio** | Create and edit characters, draft one with AI from a one-line idea, set signature lines, set forms of address, upload an avatar, and import or export Character Card V2. |
| **Explore and profile** | Featured character, vibe filters ("Chữa lành", "Tình đầu"…), equal-size character cards, and a read-only profile with "Bước vào câu chuyện". |
| **On-demand helpers** | A "+" menu in the composer: reply suggestions (only when tapped), an event timeline, and image sending (shell). |
| **Accounts** | Owner and invited members, invite codes, password login with scrypt and HttpOnly sessions, an owner-only admin page, and fully private stories. Characters can be made public; others then play their own private copy. |
| **Fast on modest hardware** | Prompt-cache-aware prompt layout and a background "prefill" of the next turn cut the first-token wait on long stories from ~30–47 s to ~5 s on a 12B model. |
| **No technical noise** | No model names, tokens or server status in the UI. Waiting shows typing dots. Technical settings live behind "Nâng cao". |
| **Safety and privacy** | Safe content by default (no sexual content; romance and jealousy stay non-explicit; nothing sexual involving minors, ever). "Báo cáo" on every AI reply and on every public character's profile (the owner can hide a reported character), Terms and Privacy Policy with recorded consent, self-service data export and account deletion, and an opt-out for anonymous usage data. |
| **Usage analytics** | 40 tracked events with no user text, an owner "Số liệu" page (DAU/WAU/MAU, funnel, D1/D7) and CSV/JSONL export; optional PostHog forwarding. |

### Launch channel and business model

**Launch channel: the open web, as an installable PWA.** Lyris is served over HTTPS from one GPU machine ([docs/deploy.md](docs/deploy.md)). People open a link or add it to their home screen; no store review is needed. Sign-up uses invite codes released in waves, matching capacity (about two replies generated at once per 12B model). Wrapping it as a Google Play or App Store app is planned for later.

**Getting users** *(plan)*
- **Vietnamese roleplay and web-fiction communities:** Facebook groups, TikTok and Discord servers where WHIF and ngôn tình readers gather.
- **Showcase content:** short clips of story mode and the hand-written worlds that already ship (Lục Bắc Uyên, Yến Hoành Sinh, Cố Hoài Dã, Tần Dương).
- **Creator-led discovery:** writers publish public characters, and their followers come to play them.

**Revenue: a coin economy** *(plan, not yet built; the tracking plan already measures its inputs: messages per active user per day and compute per turn)*
- **Chat costs coins:** every chat turn spends a small number of coins.
- **Buying coins:** users top up coins with money.
- **Earning coins without paying:**
  - **Missions:** daily check-ins, finishing a story arc, unlocking story moments.
  - **Creation:** writing characters and worlds, earning when other users play your public characters.

  This rewards the creators who bring players in.
- **Self-hosting stays free:** coins apply only to the hosted version, for people without a strong enough machine.
- **Pricing follows real compute cost:** coin prices would follow measured cost per turn (prompt size, reply length).

### Build, run and access

#### Hardware for local AI

Lyris runs a ~12B-parameter instruction model locally through Ollama, with an 8,192-token context. The model and its cache take about 16 GB.

| | Minimum | Recommended |
|---|---|---|
| Memory for the model | 16 GB unified memory or VRAM, running a smaller model (e.g. `gemma4:e4b`) | 24 GB+ unified memory (Apple Silicon) or a 16 GB+ GPU (NVIDIA) for `gemma4:12b` |
| Disk | ~15 GB (model + app) | 30 GB+ if you add an embedding model or fine-tune later |
| OS | macOS on Apple Silicon (tested), Linux with Ollama (expected to work) | |

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
- **Phone or other devices on the same Wi-Fi:** open the LAN address that `dev.sh` prints (`http://<computer-ip>:5173`) and log in. Use `LYRIS_LAN=0` to keep the app on this computer only. Over plain Wi-Fi, traffic is not encrypted. Remote access over HTTPS (Tailscale) is planned.
- **Inviting someone:** go to Tài khoản → Quản lý tài khoản → Tạo mã mời.
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
| `LYRIS_POSTHOG_KEY` | unset | PostHog project key. Set it to forward usage events to PostHog as well as the local database ([tracking plan](docs/tracking-plan.md)). Unset: events stay on the machine. |
| `LYRIS_POSTHOG_HOST` | `https://us.i.posthog.com` | PostHog host (`https://eu.i.posthog.com` for EU projects). |
| `LYRIS_APP_VERSION` | package version | Version tag attached to every usage event. |
| `LYRIS_CONTACT` | `lethuhang.cv@gmail.com` (set by `scripts/dev.sh` / `scripts/serve.sh`) | The operator's support email (or an `https://` page). The login page then offers "Xin mã mời" and "Quên mật khẩu?" links, and the legal texts show it in place of the contact placeholder. |

All variables, with production values: [docs/deploy.md §6](docs/deploy.md#6-biến-môi-trường).

#### Tests

Run from the repository root (each line runs in its own subshell, so they can be pasted in order):

```bash
(cd backend && .venv/bin/pytest -q)                                  # ~1,500 tests
(cd frontend && npm test && npm run typecheck && npm run build)      # ~400 tests
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
| `docs/` | Phase designs (`plan.md`, `phase1–4.md`, `auth.md`, `design-impl.md`), [tracking plan](docs/tracking-plan.md), [compliance](docs/compliance.md), [deploy](docs/deploy.md), [demo script](docs/demo-script.md), legal texts (`legal/terms.md`, `legal/privacy.md`) |
| `scripts/` | `dev.sh` (development), `serve.sh` (production-like run), `lyris-admin.sh` (setup code, password reset), `ollama-env.sh` (macOS Ollama settings) |
| `wiki/` | Harness ①, the source of truth: original ideas (`raw/`), feature pages `features/F01…F41` with "Done when" and "Tests", screens, decisions, lessons learned |
| `DESIGN.md` | Design system and UI/UX specification |

### Launch and deploy

- **Channel:** open web, installable PWA, HTTPS. One machine with an NVIDIA GPU (≥ 16 GB VRAM) or Apple Silicon (≥ 24 GB) runs Ollama, the backend and Caddy.
- **Production setup:** [docs/deploy.md](docs/deploy.md): Ollama service and model, uvicorn as a systemd service (no `--reload`, `--no-proxy-headers`, one process), Caddy serving `frontend/dist` and proxying `/api`, `LYRIS_COOKIE_SECURE=1`, nightly SQLite backups, updates (migrations run on restart), capacity (~2 replies at once per 12B model) and monitoring.
- **Quick production-like run:** `bash scripts/serve.sh`.

### Tracking plan

Full plan: [docs/tracking-plan.md](docs/tracking-plan.md).
- **40 events** across acquisition, activation, engagement and AI quality, retention, creation, safety and account; most are recorded by the server at the moment an action succeeds. **North Star: weekly engaged stories** (stories with 3+ player turns in a week).
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
- **Tests as the contract.** About 1,500 backend and 390 frontend tests, including a route-by-route data-isolation sweep across two accounts and a check that no typed text ever reaches analytics. Large refactors such as adding login to every route stayed safe.
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
| ① Wiki | `wiki/` | One page per feature, `features/F01-…` to `F41-…`. Each page has "Done when" lines of three kinds (`Unit:`, `Bot:`, `Model thật:`) and a "Tests" list naming the tests that prove them. Also screens, decisions, `learned.md`, `log.md` and `plan-checklist.md`. `raw/` keeps the owner's original messages and is never edited. |
| ② Environment | `environment/` | `rules.md`, the AI's working rules (pulled in by `CLAUDE.md`), and `doctor.mjs`, a machine check. Also the browser bot: `bot.mjs` drives headless Chrome over the DevTools Protocol (no extra dependencies), `e2e.mjs` holds 82 named checks, and `fake-server.py` runs the real backend with a scripted fake LLM and a temporary database on ports 8066/8067. The bot never touches `data/`, Ollama or ports 8000/5173. |
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

**Tally on 2026-11-14** (full `verify.sh` run: backend 1,532 passed, frontend 401, bot 82/82): **✅ 24 · 🟡 12 · ⏳ 5 · ⛔ 0.**
- ✅ passing: F01, F02, F04, F06, F08, F11, F16, F18, F20–F35.
- 🟡 claimed, waiting for `--real-model`: F03, F05, F07, F09, F10, F12, F13, F14, F15, F17, F19, F36.
- ⏳ planned: F37–F41 (iPhone over Tailscale, sending images, community, scene director, model fine-tuning).

The bot found a real bug on its first pass. The character editor validated the card after cleaning, and cleaning keeps only 3 "Lời nói đặc trưng" lines, so a 4th line was dropped silently instead of blocking the save. It is fixed and covered by a unit test (`saveProblems`).

### Team

> **Nhóm sẽ điền / to be filled by the team** before submission: every member, their role and what they contributed.

| Tên | Vai trò | Đóng góp |
|---|---|---|
| *(Nhóm sẽ điền)* | *(e.g. Product owner)* | *(e.g. vision, DESIGN.md, character worlds, product decisions)* |
| *(Nhóm sẽ điền)* | | |
| *(Nhóm sẽ điền)* | | |
| *(Nhóm sẽ điền)* | | |

---

## Tiếng Việt

[Video demo](#video-demo) · [Cài đặt và chạy](#cài-đặt-chạy-và-truy-cập) · [Ra mắt và triển khai](#ra-mắt-và-triển-khai) · [Theo dõi sự kiện](#kế-hoạch-theo-dõi-sự-kiện) · [Quyền riêng tư](#quyền-riêng-tư-và-tuân-thủ) · [Quy trình cùng AI](#quy-trình-làm-việc-cùng-ai-nhóm-đã-xây-lyris-cùng-claude-thế-nào) · [Harness](#harness-theo-mẫu-mini-harness-của-apero) · [Nhóm](#nhóm)

### Giới thiệu

Lyris là app nhập vai với nhân vật AI, ưu tiên tiếng Việt. Bạn chọn một nhân vật (hoặc tự viết trong Studio), bước vào một story với nhân vật đó và trò chuyện. AI dẫn truyện và đóng vai nhân vật, còn persona của bạn chỉ bạn điều khiển. Nhân vật nhớ những gì đã xảy ra, kể cả điều bạn nhắn tin. Cảm xúc của họ với bạn tăng hay giảm theo việc bạn làm, và họ chỉ biết những gì thế giới của họ cho phép. Bạn bè vào bằng mã mời và có story riêng tư của mình.

### Video demo

> **TODO (nhóm):** dán link video demo 2–3 phút vào đây trước khi nộp.
> Kịch bản (thời điểm, thao tác, lời đọc): [docs/demo-script.md](docs/demo-script.md).

**Video demo:** *sắp có link*

### Vấn đề

- **App nhập vai viết đè lên người chơi.** Các app chạy trên server như WHIF hay bỏ qua điều người chơi vừa viết, nói và làm thay nhân vật của người chơi, rồi trôi khỏi cảnh.
- **Tiếng Việt bị xem nhẹ.** Model nhập vai huấn luyện bằng tiếng Anh dùng sai xưng hô (anh/em, tớ/cậu, ta/ngươi), chêm chữ Anh hay chữ Trung, và quên quan hệ giữa hai nhân vật.
- **Trí nhớ nông.** Nhân vật quên tên, lời hứa, sự kiện sau vài chục lượt, và thái độ không đổi dù người chơi làm gì.

### Người dùng mục tiêu

- **Người đọc truyện mạng tiếng Việt** (ngôn tình, đam mỹ, cổ trang, vườn trường) muốn *sống trong* câu chuyện thay vì chỉ đọc. Dùng điện thoại là chính, thường vào buổi tối.
- **Người viết và tạo nhân vật**, dựng cả thế giới (nhân vật phụ, nơi chốn, bí mật, móc sự kiện) và muốn nhân vật được đóng đúng.
- **Người thích tự chạy AI**, có máy đủ mạnh, coi trọng riêng tư hơn gói thuê bao.

### Tính năng chính

| Mảng | Làm gì |
|---|---|
| **Chế độ Story và DM** | Story đọc như tiểu thuyết: dẫn truyện chữ nghiêng, lời thoại trong ô thoại, suy nghĩ của nhân vật trong thẻ làm mờ, chạm để đọc. DM giống app nhắn tin. Hai chế độ chung một dòng thời gian: xưng tên qua tin nhắn thì trong story nhân vật vẫn biết. |
| **Người chơi là tác giả** | AI không viết lời, hành động hay quyết định thay bạn, và tiếp nối đúng từ điều bạn vừa viết. Chỉ đạo ngầm cho nhân vật viết trong `((…))`. Lời thoại của bạn viết trong `"…"`, hành động trong `*…*`, lời của người khác trong `*"…"*`. |
| **Sáu chỉ số cảm xúc** | Thương mến, tin cậy, rung động, chiếm hữu, sợ mất, chán ghét (0–100) tăng *và giảm* theo việc bạn làm. Ghen thì tin cậy giảm, xin lỗi thì chán ghét giảm, chuyện thường ngày hầu như không đổi gì. Chỉ số được đổi thành chỉ dẫn diễn xuất cho nhân vật, không bao giờ đưa con số thô vào prompt. |
| **Trí nhớ** | Tóm tắt cảnh theo đợt, ký ức dài hạn và các điều đã biết. Tìm theo từ khoá, và theo nghĩa nếu máy có model embedding. Tạo lại, sửa hay xoá một lượt thì trạng thái cũng lùi lại đúng. |
| **Sổ thế giới (lorebook)** | Mỗi nhân vật mang theo thế giới riêng: nhân vật phụ, nơi chốn, các mục lore, nhập từ file Markdown `world.md`. Mục được gợi ra bằng từ khoá, so khớp đúng tiếng Việt và giữ dấu. Mỗi mục ghi rõ ai biết: mọi người, chỉ nhân vật, hay chỉ bạn. Spoiler chỉ bạn biết không bao giờ tới model. |
| **Studio nhân vật** | Tạo và sửa nhân vật, AI viết nháp từ một dòng ý tưởng, lời nói đặc trưng, xưng hô, ảnh đại diện, nhập và xuất Character Card V2. |
| **Khám phá và hồ sơ** | Nhân vật nổi bật, lọc theo cảm xúc ("Chữa lành", "Tình đầu"…), lưới thẻ đều nhau, hồ sơ chỉ xem với nút "Bước vào câu chuyện". |
| **Trợ giúp khi cần** | Nút "+" ở ô chat: gợi ý trả lời (chỉ khi bấm), dòng thời gian sự kiện, gửi hình ảnh (mới có khung). |
| **Tài khoản** | Chủ máy và thành viên được mời, mã mời, đăng nhập bằng mật khẩu (scrypt, phiên HttpOnly), trang quản lý chỉ chủ máy thấy, story riêng tư hoàn toàn. Nhân vật có thể bật công khai; người khác chơi trên bản sao riêng của họ. |
| **Nhanh trên máy vừa phải** | Prompt được sắp theo cách giữ được cache, và lượt sau được chuẩn bị trước ("prefill") khi bạn đang gõ. Thời gian chờ chữ đầu tiên ở story dài giảm từ khoảng 30–47 giây xuống khoảng 5 giây với model 12B. |
| **Không chữ kỹ thuật** | Giao diện không có tên model, token hay trạng thái máy. Lúc chờ chỉ hiện ba chấm nhảy. Thiết lập kỹ thuật nằm trong "Nâng cao". |
| **An toàn và quyền riêng tư** | Nội dung mặc định an toàn (không nội dung tình dục; tình cảm, ghen tuông kín đáo; tuyệt đối không gì tình dục với trẻ vị thành niên). "Báo cáo" trên mọi câu trả lời của AI và trên hồ sơ mọi nhân vật công khai (chủ máy ẩn được nhân vật bị báo cáo), Điều khoản và Chính sách có lưu lần đồng ý, tự tải dữ liệu và xoá tài khoản, tắt được chia sẻ dữ liệu sử dụng ẩn danh. |
| **Số liệu sử dụng** | 40 sự kiện, không chứa chữ người dùng; trang "Số liệu" của chủ máy (DAU/WAU/MAU, phễu, D1/D7), xuất CSV/JSONL; tuỳ chọn gửi sang PostHog. |

### Kênh ra mắt và mô hình doanh thu

**Kênh ra mắt: web mở, dạng PWA cài được.** Lyris chạy qua HTTPS trên một máy có GPU ([docs/deploy.md](docs/deploy.md)). Người dùng mở link hoặc thêm vào màn hình chính, không cần chờ duyệt cửa hàng. Đăng ký bằng mã mời phát theo đợt, khớp sức chứa (khoảng 2 câu trả lời cùng lúc cho mỗi model 12B). Bọc thành app Google Play / App Store để sau.

**Thu hút người dùng** *(kế hoạch)*
- **Cộng đồng nhập vai và truyện mạng tiếng Việt:** nhóm Facebook, TikTok, máy chủ Discord, nơi người chơi WHIF và độc giả ngôn tình tụ họp.
- **Nội dung giới thiệu:** clip ngắn về chế độ Story và các thế giới viết tay đã có sẵn (Lục Bắc Uyên, Yến Hoành Sinh, Cố Hoài Dã, Tần Dương).
- **Lan toả nhờ tác giả:** tác giả đăng nhân vật công khai, người theo dõi họ tới chơi.

**Doanh thu: hệ thống coin** *(kế hoạch, chưa làm; số liệu đã đo sẵn đầu vào: số tin nhắn mỗi người mỗi ngày và chi phí tính toán mỗi lượt)*
- **Chat tốn coin:** mỗi lượt chat tiêu một lượng coin nhỏ.
- **Nạp coin:** người dùng nạp coin bằng tiền.
- **Kiếm coin không cần trả tiền:**
  - **Làm nhiệm vụ:** điểm danh hằng ngày, đi hết một chặng truyện, mở khoá khoảnh khắc.
  - **Sáng tác:** viết nhân vật và thế giới, nhận coin khi người khác chơi nhân vật công khai của mình.

  Cách này thưởng cho những người mang người chơi tới.
- **Tự chạy trên máy mình vẫn miễn phí:** coin áp dụng cho bản host sẵn, dành cho người không có máy đủ mạnh.
- **Giá theo chi phí thật:** giá coin sẽ bám theo chi phí tính toán đo được cho mỗi lượt (độ dài prompt, độ dài câu trả lời).

### Cài đặt, chạy và truy cập

#### Phần cứng để chạy AI local

Lyris chạy một model khoảng 12 tỷ tham số qua Ollama, context 8.192 token. Model và bộ nhớ đệm chiếm khoảng 16 GB.

| | Tối thiểu | Khuyên dùng |
|---|---|---|
| Bộ nhớ cho model | 16 GB (bộ nhớ hợp nhất hoặc VRAM), dùng model nhỏ hơn (vd. `gemma4:e4b`) | Từ 24 GB bộ nhớ hợp nhất (Apple Silicon) hoặc GPU NVIDIA từ 16 GB cho `gemma4:12b` |
| Ổ đĩa | ~15 GB (model + app) | Từ 30 GB nếu thêm model embedding hoặc fine-tune |
| Hệ điều hành | macOS trên Apple Silicon (đã thử), Linux có Ollama (dự kiến chạy được) | |

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
- **Điện thoại hoặc máy khác cùng Wi-Fi:** mở địa chỉ LAN mà `dev.sh` in ra (`http://<ip-máy>:5173`) rồi đăng nhập. Đặt `LYRIS_LAN=0` nếu chỉ muốn mở trên máy này. Qua Wi-Fi thường, đường truyền chưa được mã hoá; truy cập từ xa qua HTTPS (Tailscale) đang trong kế hoạch.
- **Mời người khác:** vào Tài khoản → Quản lý tài khoản → Tạo mã mời.
- **Quên mật khẩu chủ máy:** chạy `bash scripts/lyris-admin.sh reset-password <handle>`.

#### Chạy kiểu production trên một máy

```bash
bash scripts/serve.sh      # build frontend/dist, uvicorn không --reload (một tiến trình),
                           # phục vụ bản build bằng `vite preview` kèm proxy /api
```

Dùng để demo và dùng ở nhà. Ra mắt công khai (HTTPS, Caddy, systemd, sao lưu): xem [docs/deploy.md](docs/deploy.md).

Biến môi trường và sơ đồ thư mục: xem các bảng ở phần tiếng Anh phía trên (giống hệt nhau).

#### Chạy test

Chạy từ thư mục gốc của repo (mỗi dòng chạy trong subshell riêng, dán lần lượt được):

```bash
(cd backend && .venv/bin/pytest -q)
(cd frontend && npm test && npm run typecheck && npm run build)
backend/.venv/bin/python harness/run_eval.py --model gemma4:12b        # cần Ollama
bash verification/verify.sh                                           # giám khảo của harness: tất cả các dòng trên + bot trình duyệt (xem mục Harness)
```

### Ra mắt và triển khai

- **Kênh:** web mở, PWA cài được, HTTPS. Một máy có GPU NVIDIA (từ 16 GB VRAM) hoặc Apple Silicon (từ 24 GB) chạy Ollama, backend và Caddy.
- **Cài production:** [docs/deploy.md](docs/deploy.md): Ollama và model, uvicorn chạy bằng systemd (không `--reload`, `--no-proxy-headers`, một tiến trình), Caddy phục vụ `frontend/dist` và proxy `/api`, `LYRIS_COOKIE_SECURE=1`, sao lưu SQLite mỗi đêm, cập nhật (migration tự chạy khi khởi động lại), sức chứa (~2 câu trả lời cùng lúc mỗi model 12B), theo dõi.
- **Chạy nhanh kiểu production:** `bash scripts/serve.sh`.

### Kế hoạch theo dõi sự kiện

Đầy đủ: [docs/tracking-plan.md](docs/tracking-plan.md).
- **40 sự kiện** theo cả vòng đời: thu hút, kích hoạt, tương tác và chất lượng AI, giữ chân, sáng tạo, an toàn, tài khoản; phần lớn do server ghi đúng lúc thao tác thành công. **North Star: số story "sống" mỗi tuần** (story có từ 3 lượt người chơi trong tuần).
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
- **Test là hợp đồng.** Khoảng 1.500 test backend và 390 test frontend, gồm một bài quét từng route để chắc hai tài khoản không đọc được dữ liệu của nhau, và một bài kiểm không chữ nào người dùng gõ lọt vào số liệu. Nhờ vậy những thay đổi lớn như thêm đăng nhập vào mọi route vẫn an toàn.
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
| ① Wiki | `wiki/` | Mỗi tính năng một trang, từ `features/F01-…` tới `F41-…`. Mỗi trang có các dòng "Done when" thuộc ba loại (`Unit:`, `Bot:`, `Model thật:`) và danh sách "Tests" ghi tên các test chứng minh chúng. Ngoài ra có màn hình, quyết định, `learned.md`, `log.md` và `plan-checklist.md`. `raw/` giữ nguyên văn lời của chủ dự án và không bao giờ bị sửa. |
| ② Environment | `environment/` | `rules.md`, luật làm việc của AI (`CLAUDE.md` kéo file này vào), và `doctor.mjs` để kiểm máy. Thêm bot trình duyệt: `bot.mjs` điều khiển Chrome headless qua DevTools Protocol (không thêm thư viện), `e2e.mjs` có 82 check có tên, `fake-server.py` chạy backend thật với LLM giả có kịch bản và DB tạm ở cổng 8066/8067. Bot không bao giờ đụng `data/`, Ollama hay cổng 8000/5173. |
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

**Bảng đếm ngày 2026-11-14** (lần chạy `verify.sh` đầy đủ: backend 1.532 test qua, frontend 401, bot 82/82): **✅ 24 · 🟡 12 · ⏳ 5 · ⛔ 0.**
- ✅ đạt: F01, F02, F04, F06, F08, F11, F16, F18, F20–F35.
- 🟡 đã claim, chờ `--real-model`: F03, F05, F07, F09, F10, F12, F13, F14, F15, F17, F19, F36.
- ⏳ kế hoạch: F37–F41 (iPhone qua Tailscale, gửi hình ảnh, cộng đồng, đạo diễn khoảnh khắc, tự train model).

Ngay lượt chạy đầu, bot đã tìm ra một lỗi thật. Trình sửa nhân vật kiểm card sau khi làm sạch, mà bước làm sạch chỉ giữ 3 dòng "Lời nói đặc trưng", nên dòng thứ 4 bị bỏ âm thầm thay vì chặn lưu. Lỗi đã được sửa và có unit test (`saveProblems`).

### Nhóm

> **Nhóm sẽ điền / to be filled by the team** trước khi nộp: mọi thành viên, vai trò và phần đóng góp.

| Tên | Vai trò | Đóng góp |
|---|---|---|
| *(Nhóm sẽ điền)* | *(vd. Product owner)* | *(vd. tầm nhìn, DESIGN.md, thế giới nhân vật, quyết định sản phẩm)* |
| *(Nhóm sẽ điền)* | | |
| *(Nhóm sẽ điền)* | | |
| *(Nhóm sẽ điền)* | | |
