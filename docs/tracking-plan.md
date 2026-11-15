# Lyris tracking plan

> **Status: built and tested (2026-11-15).** Every event below is in the registry
> (`backend/lyris/analytics/events.py`) and is recorded in the running app. Server events are written by the
> backend at the moment the action succeeds; client events are sent by `frontend/src/lib/track.ts`. The owner sees
> the numbers in Tài khoản → "Quản lý tài khoản" → "Số liệu" and can download every event as CSV/JSONL.
> Code: `backend/lyris/analytics/`, `backend/lyris/api/routes_analytics.py`, migration `0009_analytics.sql`,
> `frontend/src/lib/track.ts`. Tests: `backend/tests/test_analytics.py`, `backend/tests/test_analytics_api.py`,
> `backend/tests/test_compliance.py`, `backend/tests/test_launch_fixes.py`, `frontend/src/lib/track.test.ts`,
> `frontend/src/launchWiring.test.ts`.

*Tóm tắt tiếng Việt ở [cuối trang](#tóm-tắt-tiếng-việt).*

Contents: [1 Goals and North Star](#1-goals-and-north-star) · [2 Principles](#2-principles) ·
[3 Identity and sessions](#3-identity-sessions-and-common-fields) · [4 Event catalog](#4-event-catalog) ·
[5 KPIs and funnels](#5-kpis-and-funnels) · [6 Where events are recorded](#6-where-server-events-are-recorded) ·
[7 Client contract](#7-client-contract-post-apievents) · [8 Storage, viewing and export](#8-storage-viewing-and-export) ·
[9 PostHog](#9-posthog) · [10 Privacy rules](#10-privacy-rules) · [11 QA checklist](#11-qa-checklist)

## 1. Goals and North Star

Lyris is an AI roleplay app: its value is created only when a player keeps a story going with a character. The
tracking plan answers six product questions, one per stage of the funnel in §5:

1. **Acquisition.** How many people open Lyris, from an invite or not, as an installed PWA or in a browser?
2. **Activation.** Do new users find a character and start a story? Where do they drop off?
3. **Engagement and AI quality.** Once in a story, do people keep writing? Is the AI fast and good enough, or do
   they regenerate, edit and rate replies down? Which signature features (thoughts, heart drawer, DM, lore) do they use?
4. **Retention.** Do people come back the next day and the next week, and do they pick up old stories?
5. **Creation.** Do people create, import and publish characters and worlds that others play?
6. **Monetisation readiness.** How many turns does an active user write per day, and what does a turn cost in
   compute? These are the inputs for the coin system (built in test mode: 6 coin per reply, see [coins.md](coins.md); README "Revenue model").

Safety (reports, `minor_safety`) and privacy (opt-out, deletion, export) are tracked as guardrails.

### North Star metric: weekly engaged stories

> **Weekly engaged stories (WES)** = the number of distinct stories (`story_id`) that received **at least 3
> `message_sent`** in a calendar week (Monday–Sunday, Vietnam time).

Why this metric:

- It counts the moment Lyris delivers value: a player and a character in an ongoing story, not a page view.
- It grows with every healthy lever: more users (acquisition), more of them starting stories (activation), longer
  sessions (engagement), coming back to old stories (retention), and more characters to play (creation).
- It cannot be gamed by a single long session alone: one story counts once per week, whatever its length.
- It maps directly to revenue later: every `message_sent` is a turn that would spend coins.

How to compute it: from the CSV/JSONL export or PostHog, `name = message_sent`, group by ISO week (UTC+7) and
`story_id`, keep groups with count ≥ 3, count the groups. The owner page shows the related daily numbers (active
users, funnel, D1/D7); WES itself is computed from the export (one SQL or spreadsheet pivot).

Supporting input metrics: weekly active users (WAU), activation rate, turns per story, D7 retention, AI first-token
time, and stories started on public (community) characters.

## 2. Principles

- **No text, ever.** No message, character, persona, lore, title, handle, name, email, invite code or any other
  free text goes into analytics. Every property is one of four types: an enum string from a fixed list, a
  boolean, a bounded integer (durations, token counts, item counts), or an integer from a fixed set. Numbers that
  could say something about content (message length, days away, turn number) are **bucketed on the server**
  before they are stored. The registry rejects anything else: unknown events, unknown properties, wrong types,
  values outside the enum or range, more than 10 properties, or properties over 1 KB. Tests check that no text from
  a full two-account session leaks into stored events or into the PostHog payload.
- **Server-side first.** Anything the backend knows (story created, message sent, reply finished or failed,
  sign-in, character created...) is recorded on the server, at the point where the action succeeds, so ad
  blockers and closed tabs do not lose it. Failed requests record nothing. The client only reports what happens
  only in the UI (opening a page, tapping a filter, revealing a thought).
- **Never in the way.** Recording an event is one small local insert. It never raises and never blocks a request.
  Sending to PostHog runs in a background task.
- **Local by default, PostHog when configured.** Events live in the app's own SQLite database (`analytics_events`)
  for 180 days. PostHog forwarding is on only when `LYRIS_POSTHOG_KEY` is set.
- **User control.** Usage sharing is on by default (product-owner decision; the privacy policy explains it, and
  people accept it at sign-up). Each person can turn it off in Tài khoản → "Dữ liệu & quyền riêng tư" (switch
  "Chia sẻ dữ liệu sử dụng ẩn danh"). Turning it off deletes the events already stored for that account, including
  the signed-out events of its devices, and stops recording, also after signing out on that device. Browsers that
  send Global Privacy Control (`Sec-GPC: 1`) are never tracked and never get the `lyris_anon` cookie.
- **Consent before forwarding.** An account that has not accepted the current Terms and Privacy Policy (accounts
  created before them are asked once) keeps its events in the app database only; nothing of it goes to PostHog
  until it accepts.

## 3. Identity, sessions and common fields

| Field | Meaning |
|---|---|
| `distinct_id` | The account's random `uid` (32 hex characters, not the handle). Before sign-in: the device's `anon_id`. |
| `anon_id` | Random per device: the `lyris_anon` cookie (HttpOnly, SameSite=Lax, 1 year), set by the server the first time an event is recorded (never for `Sec-GPC: 1` browsers or devices where sharing was turned off). It is stored on every event of that device, signed in or not, to group a device's visits, and it links pre-sign-in events to the account: PostHog `$identify` is sent on `signup_completed`, `login_succeeded` and `owner_setup_completed`, and the owner summary counts a device's signed-out events as the account that later used the same `anon_id` (one person, not two). Several accounts used on one browser share one `anon_id`. |
| `session_id` | One visit. The server starts a new session (and records `session_started`) when a device has been idle for 30 minutes. |
| `story_id` | Internal numeric story id, for per-story funnels (turns per story, WES). Never the title. |
| `ts` | Server time, UTC, millisecond precision. Reports use Vietnam time (UTC+7) for "day". |
| `app_version` | Backend version (`LYRIS_APP_VERSION`, or the package version). |
| `source` | `server` or `client`. |

The client keeps **no identifier of its own**: no localStorage id, no fingerprint. The server owns identity
through the HttpOnly cookie, and `POST /api/events` refuses any extra field.

## 4. Event catalog

**57 events.** "S" = recorded by the server, "C" = sent by the client through `POST /api/events`.

Property types: `enum(a|b)`, `bool`, `int[lo..hi]`, `int{a,b}`. Shared buckets:
`length_bucket` = `1_20|21_80|81_200|201_500|501_plus` characters of visible text;
`user_turn` = `1|2_4|5_9|10_19|20_plus`; `ttft_bucket` = `lt_1s|1_3s|3_10s|10_30s|30s_plus|none`;
`days_since_last` = `1|2_3|4_7|8_30|31_plus`; `mode` = `story|dm`.
For client story events, `mode` is filled by the server from the story; the client does not send it.

### 4.1 Acquisition and account activation

| Event | Src | Trigger | Properties | What it measures | Why it matters | KPI / funnel |
|---|---|---|---|---|---|---|
| `app_opened` | C | App shell loads (cold start or new tab), once per load. Allowed before sign-in. | `display_mode: enum(standalone\|browser)`, `authed: bool` | Visits; how many open Lyris as an installed PWA | Top of every funnel; installed-PWA share shows "app-like" retention | Visitors, PWA install share |
| `session_started` | S | First event from a device after 30 min idle (automatic) | none | Visits per user, session count | Session frequency is the main engagement health signal | Sessions/user/day |
| `signup_viewed` | C | Sign-up page shown. Allowed before sign-in. | `has_invite_code: bool` (code came from an invite link) | Invite link click-through | Invite links are the way in today; tells whether shared links get opened | Invite funnel step 2 |
| `signup_completed` | S | Account created with an invite code | none | New accounts | The activation denominator | Signups/day, invite funnel step 3 |
| `invite_redeemed` | S | Same moment as `signup_completed` | `invite_age: enum(lt_1h\|lt_1d\|lt_7d\|7d_plus)` | How fast invites convert | Viral loop speed; tunes default invite expiry | Invite conversion, K-factor |
| `owner_setup_completed` | S | The owner sets the first password | none | Installs that got past setup | Deployments that actually start | Installs |
| `login_succeeded` | S | Successful sign-in | none | Returning sign-ins | Return visits on new devices | Sign-ins/day |
| `login_failed` | S | Failed sign-in | `reason: enum(bad_credentials\|rate_limited\|account_disabled\|temporary_expired\|setup_required\|busy\|other)` | Sign-in friction (never the handle typed) | Spikes mean confusing UX or an attack | Sign-in success rate |
| `invite_created` | S | Owner creates an invite code | `expires_days: int{1,7,30}` | Invites sent | Supply side of the viral loop | Invites/week, K-factor |

### 4.2 Discovery

| Event | Src | Trigger | Properties | What it measures | Why it matters | KPI / funnel |
|---|---|---|---|---|---|---|
| `explore_viewed` | C | Khám phá page shown | none | Reach of the catalog | Activation funnel step 1 | Activation funnel |
| `explore_searched` | C | The "Tìm nhân vật" box on Khám phá settled after the 250 ms debounce, at most once per distinct search ([F47](../wiki/features/F47-tim-nhan-vat.md)). The typed words are **never** sent | `has_results: bool` | How often people search, and how often a search finds nothing | Searches that find nothing show which characters people look for and do not find | % of Khám phá visits with a search; empty-result rate |
| `hot_board_viewed` | C | The "Nhân vật hot" leaderboard (`#/explore/hot`) opened ([F46](../wiki/features/F46-bang-xep-hang-nhan-vat-hot.md)) | `from: enum(explore\|link)` (`explore` = the "Xem bảng xếp hạng" button) | Reach of the leaderboard | Whether the ranking (and its creator rewards) draws people to public characters | Leaderboard views/week |
| `vibe_filter_used` | C | A vibe chip is tapped | `vibe: enum(chua_lanh\|diu_dang\|bi_an_noi_tam\|tinh_dau\|other_template\|other_tag)`, `position: int[1..20]` | Which moods people browse by (a fixed code, never the tag text) | Shapes which characters and vibes to make next | Content strategy |
| `character_profile_viewed` | C | Character profile opened | `source: enum(own\|template\|public)`, `from: enum(explore\|library\|profile\|story\|link)` | Interest in a character | Funnel step 2; template vs community characters | Activation funnel |

### 4.3 Story start (activation)

| Event | Src | Trigger | Properties | What it measures | Why it matters | KPI / funnel |
|---|---|---|---|---|---|---|
| `story_start_clicked` | C | "Bước vào câu chuyện" tapped (profile or Explore hero) | `source: enum(own\|template\|public)` | Intent to start | Gap between click and `story_started` shows setup friction (persona sheet) | Activation funnel |
| `story_started` | S | A story is created | `mode`, `source: enum(own\|template\|public\|default)`, `language: enum(vi\|en)` | Stories started (`default` = the seed story) | **Activation event.** Template vs public vs own characters; `public` = plays of community characters | Activation rate, stories/user |

### 4.4 Engagement and AI quality

| Event | Src | Trigger | Properties | What it measures | Why it matters | KPI / funnel |
|---|---|---|---|---|---|---|
| `message_sent` | S | Player turn saved (before the reply streams) | `mode`, `length_bucket`, `has_action: bool` (`*…*`), `has_directive: bool` (`((…))`), `user_turn` | Turns written and how people write | **Core engagement and North Star input.** First message and 5+ messages per story are funnel steps; future coin spend | Messages/user/day, turns/story, WES |
| `reply_completed` | S | AI reply finished or was stopped | `mode`, `kind: enum(send\|retry\|regenerate)`, `ttft_bucket`, `duration_ms: int[0..3600000]`, `output_tokens: int[0..100000]`, `aborted: bool`, `waited: bool` (queued behind another user) | Speed, length and completion of the AI | Slow first tokens kill chat apps; `aborted` shows frustration; tokens and duration = compute cost per turn | TTFT, abort rate, cost/turn |
| `reply_failed` | S | Reply ended with an error | `mode`, `kind`, `reason: enum(connect\|timeout\|missing_model\|empty_reply\|save_failed\|queue_timeout\|other)`, `waited: bool` | Reliability | Launch-blocking if high; reason codes point at the fix | Reply failure rate |
| `regenerate_used` | S | Player asks for another version | `mode` | Dissatisfaction with a reply | Leading indicator of AI quality | Regenerate rate |
| `message_edited` | S | A turn is edited | `role: enum(user\|assistant)`, `mode` | Players fixing the AI (assistant) or themselves (user) | Editing AI text means the model got something wrong | Edit rate |
| `message_deleted` | S | Turns deleted from a point | `count_bucket: enum(1\|2_5\|6_plus)`, `mode` | Rewinds | Large rewinds mean the story went off track | Rewind rate |
| `variant_switched` | S | Player flips between reply versions | `mode` | Comparing versions | Shows regenerate is useful, not just noise | Variant use |
| `reply_rated` | S | Thumbs up/down set or cleared | `rating: enum(up\|down\|cleared)`, `mode` | Explicit reply quality | Direct quality signal and fine-tuning priority | Up/down ratio |
| `suggestions_requested` | S | "Nhận gợi ý" answered | `ok: bool`, `items: int[0..3]`, `mode` | Use and reliability of reply suggestions | Helps new players who do not know what to write | Suggestion use |
| `suggestion_used` | C | A suggestion is tapped | `position: int[1..3]` (+ `mode` from server) | Whether suggestions help | Suggestion acceptance | Acceptance rate |
| `thought_revealed` | C | A blurred thought card is tapped in a story | (`mode` from server) | Interest in the character's inner voice | Signature feature; decides how prominent thoughts should be | Feature adoption |
| `show_thoughts_toggled` | S | "Đọc suy nghĩ của nhân vật" turned on/off for a story | `enabled: bool` | Opt-out of the signature feature | High off-rate means thoughts annoy people | Feature adoption |
| `mode_switched` | S | Story ↔ DM mode changed | `to: enum(story\|dm)` | Use of the two modes | Validates the "one timeline, two modes" bet | Mode mix |
| `heart_drawer_opened` | C | "Cảm xúc & ký ức" drawer opened | (`mode` from server) | Interest in relationship state | Validates the six-emotion system | Feature adoption |
| `lore_unlocked` | S | A reply reveals world entries for the first time in a story | `count: int[1..100]`, `mode` | Players discovering the world | Lorebooks are the creators' value; unlocks show they pay off | Lore discovery/story |
| `memory_forgotten` | S | Player deletes a memory or fact ("Quên") | none | Memory corrections | Bad extractions to fix | Memory correction rate |
| `events_timeline_opened` | C | "Xem sự kiện" sheet opened | (`mode` from server) | Use of the timeline | Decides whether to keep investing in it | Feature adoption |

### 4.5 Creation

| Event | Src | Trigger | Properties | What it measures | Why it matters | KPI / funnel |
|---|---|---|---|---|---|---|
| `character_created` | S | A character is saved for the first time | `via: enum(form\|ai_draft\|import\|duplicate)`, `visibility: enum(private\|public)`, `has_avatar: bool` (true also when the editor uploads the picture right after: `POST /api/cards?with_avatar=true`) | Creation volume and path | Creators supply the catalog; AI-draft share is an AI-native KPI | Creators/week, AI-draft share |
| `character_published` | S | A character becomes public (on create or later) | none | Community supply | Explore needs fresh public characters | Public characters/week |
| `lore_imported` | S | A `world.md` or card book import is applied (not a dry run) | `format: enum(world_md\|card_book)`, `entries: int[0..10000]` (created + updated) | World-building depth | Deep worlds correlate with long stories | Lore adoption |
| `persona_created` | S | A persona is created | none | Player self-expression | Personas personalise the story | Personas/user |

### 4.6 Retention, safety, account

| Event | Src | Trigger | Properties | What it measures | Why it matters | KPI / funnel |
|---|---|---|---|---|---|---|
| `story_resumed` | S | A player writes in a story after at least 1 day without activity in it | `days_since_last`, `mode` | Coming back to old stories | Story continuity is the retention engine | Resumed stories/week |
| `content_reported` | S | An AI reply (`POST /api/messages/{id}/report`, `target: message`) or a public character's profile (`POST /api/cards/{id}/report`, `target: character`) is reported. Stored **detached**: no account, device, session or story, never forwarded | `reason: enum(sexual_content\|minor_safety\|violence\|hate\|self_harm\|harassment\|other)`, `target: enum(message\|character)`, `mode` | Safety problems (never the reported text) | Channel-policy compliance; `minor_safety` is zero-tolerance | Reports per 1,000 messages |
| `account_deleted` | S | Account deleted (`DELETE /api/account`) | none (stored without account) | Churn by deletion | Required to measure and to honour deletion | Deletions/week |
| `data_exported` | S | Personal data export downloaded (`GET /api/account/export`) | none | Use of data portability | Privacy-compliance evidence | Exports |
| `analytics_opt_out` | S | Usage sharing turned off | none (stored without account or device, never forwarded) | Opt-out rate | Trust signal; a high rate means the policy text needs work | Opt-out rate |

### 4.7 Coins ([F42](../wiki/features/F42-vi-coin.md), [F43](../wiki/features/F43-nap-coin.md), [F44](../wiki/features/F44-thuong-sang-tac.md), [F45](../wiki/features/F45-nhiem-vu-ngay.md), [docs/coins.md §11](coins.md))

Coin amounts are bounded integers; never a character name, an adjustment reason or a top-up code. The one-time
wallet opening of existing members (`backfill_grant`) is written by the migration SQL and records no event.

| Event | Src | Trigger | Properties | What it measures | Why it matters | KPI / funnel |
|---|---|---|---|---|---|---|
| `coins_spent` | S | A reply with text was saved and its 6-coin hold was charged | `mode: enum(story\|dm\|test)`, `kind: enum(send\|retry\|regenerate)` | Coins spent per reply type (`test` = Studio test chat) | Coin sink; regenerate share shows how much spend is re-rolls | Coins spent/day |
| `coins_released` | S | A hold was released without charging (no text) | `kind`, `reason: enum(error\|empty\|cancelled\|queue_timeout\|save_failed\|invalid\|restart)` | Replies that cost nothing because they failed | Players never pay for errors; a high rate is a reliability problem | Release rate |
| `coins_insufficient` | S | A reply was refused with 402 `coins_required` | `mode: enum(story\|dm\|test)`, `kind` | Players hitting zero | Top of the top-up funnel; too frequent means prices are too high | % members at 0 coins/7 days |
| `coins_granted` | S | Coins were added: account created, first app open of the day, top-up code redeemed, daily mission claimed, creator ranking reward or first public character bonus paid ([F44](../wiki/features/F44-thuong-sang-tac.md), recorded detached) | `source: enum(signup\|daily\|mission_ad\|mission_characters\|mission_turns\|creator_rank\|creator_first_public\|topup_code)`, `amount: int[1..10000]` | Coins issued by source | Balance between coins issued and spent | Coins issued/day |
| `wallet_viewed` | C | "Ví coin" (`#/coins`) opened | `from: enum(header\|account\|composer\|link)` | Interest in the wallet | Shows whether the header chip or the out-of-coins block lead people there | Wallet reach |
| `coins_adjusted` | S | The owner added or removed coins by hand ("Cộng/trừ coin", with a reason; [F43](../wiki/features/F43-nap-coin.md)) | `direction: enum(up\|down)`, `amount_bucket: enum(1_50\|51_300\|301_plus)` | Manual corrections (never the reason or the exact amount) | Many corrections mean a bug, a price problem or abuse | Adjustments/week |
| `topup_viewed` | C | "Nạp coin" (`#/coins/top-up`) opened | `from: enum(wallet\|composer\|link)` | Interest in topping up | Second step of the top-up funnel (`coins_insufficient` → `topup_viewed` → `topup_code_redeemed`) | Top-up funnel |
| `topup_pack_selected` | C | A pack card on "Nạp coin" tapped (opens the "Giá dự kiến" explanation; nothing is sold in test mode) | `pack: enum(p100\|p550\|p1200\|p2500)` | Which planned pack people look at | Checks the planned prices before real payments exist | Pack interest share |
| `topup_code_redeemed` | S | A member redeemed a top-up code (also `coins_granted{source: topup_code}`) | `pack: enum(p100\|p550\|p1200\|p2500\|custom)` | Codes used (never the code) | Last step of the top-up funnel | Codes redeemed/week |
| `topup_code_failed` | S | A top-up code was refused (the member always sees the same sentence) | `reason: enum(invalid\|expired\|used\|revoked\|rate_limited)` | Typos, stale codes, guessing | A high `invalid` or `rate_limited` rate means guessing or a confusing code format | Failure rate |
| `topup_code_created` | S | The owner created a top-up code | `pack: enum(p100\|p550\|p1200\|p2500\|custom)`, `expires_days: int{1,7,30}` | Codes handed out | Supply side of test-mode top-ups | Codes created/week |
| `missions_viewed` | C | "Nhiệm vụ hôm nay" (`#/missions`) opened ([F45](../wiki/features/F45-nhiem-vu-ngay.md)) | `from: enum(wallet\|composer\|link)` | Interest in daily missions | Shows whether the out-of-coins block leads people to missions instead of leaving | Missions reach |
| `ad_started` | S | A member started the 15-second sample ad (`POST /api/coins/ads/start`). The sample ad sends nothing to any ad network | none | Sample ads started | With `mission_claimed{mission: ad}`, the share of ads watched to the end | Ad completion rate |
| `mission_claimed` | S | A daily mission reward was claimed (also `coins_granted{source: mission_*}`); a repeated tap records nothing | `mission: enum(ad\|characters\|turns)` | Completion of each daily mission | Whether missions are reachable and worth it; checks the 30-coin daily cap is not too low or too high | Mission completion rate |
| `creator_rank_reached` | S | A public character entered the top 100, top 50 or top 10 of the "Nhân vật hot" leaderboard for the first time and the tier was recorded once ([F44](../wiki/features/F44-thuong-sang-tac.md); also `coins_granted{source: creator_rank}` when paid). Recorded **detached** (no account, device or story; local only), since it happens when the board is computed during someone else's request | `tier: int{100,50,10}`, `paid: bool` (false: the creator is the owner, coins are off, or the reward waits under the 600-coin weekly cap) | Characters reaching each ranking tier | Whether public characters find real players; a burst of tiers from one creator is a sign of friend-group farming (the owner checks "Nhật ký") | Characters reaching tiers/week |

Notes on the safety and account events:
- `content_reported` is recorded by the server with the report, **detached** (`account_id` NULL, empty `anon_id`
  and `session_id`, no `story_id`, local only): the owner promises reporters that nobody knows who reported, and
  an export row with the reporter's id, time and reason would break that. It still respects opt-out and GPC. API
  reasons map to event reasons: `sexual → sexual_content`, `violent → violence`, `hateful → hate`; `minor_safety`,
  `self_harm`, `harassment` and `other` are unchanged. The client cannot send it.
- `account_deleted` is skipped if the account had turned usage sharing off, and is stored detached like
  `content_reported` (no device, no session, local only).

### 4.8 Planned for Round 2 (not built, not recorded)

None of these events is in the registry or in `track.ts` today, so the app does not record them and the "57 events"
count above does not include them. They exist so Round 2 can measure real revenue as soon as real payments or a real
ad network are switched on. Adding any of them follows the rule in §10 (registry, client whitelist and a row in the
tables above, in the same change, with enum/boolean/bounded-integer properties only).

| Planned event | Status | Trigger | Properties (proposed) | Source of the plan |
|---|---|---|---|---|
| `purchase_started` | Planned | A member starts a real coin purchase (store sheet or web payment page opened) | `pack: enum(p100\|p550\|p1200\|p2500)`, `store: enum(google_play\|app_store\|web)` | [docs/server.md §12.1](server.md) |
| `purchase_completed` | Planned | The payment is verified on the server and the coins are credited | `pack`, `store`, `provider: enum(google_play\|app_store\|vnpay\|momo)` | [docs/server.md §12.1](server.md) (`purchase_completed{provider, pack_id}`) |
| `purchase_refunded` | Planned | A store or payment provider reports a refund | `pack`, `provider` | [docs/server.md §12.1](server.md) |
| `purchase_failed` | Proposed | The purchase was cancelled, declined or could not be verified | `pack`, `store`, `reason: enum(cancelled\|declined\|unverified\|error)` | This plan (to confirm with the PO and Apero) |
| `ad_impression` | Proposed | A real rewarded ad is shown (replaces the sample ad of [F45](../wiki/features/F45-nhiem-vu-ngay.md)) | `network: enum(…)`, the networks Apero chooses | This plan; real ads are a separate PO decision ([docs/coins.md](coins.md), [docs/server.md §12.1](server.md)) |
| `ad_rewarded` | Proposed | The ad network's server-side callback confirms the ad was watched | `network` | This plan; same condition as above |

Notes:
- `price_vnd` is deliberately not a property: the price is fixed by the pack code (`p100` = 10.000đ … `p2500` =
  200.000đ, [docs/coins.md §4.1](coins.md)), so revenue is derived from `pack` without sending money amounts.
- No transaction id, receipt, order id or payment detail ever goes into analytics; those stay in the payment tables
  planned in docs/server.md.
- Real ads would also need ad consent, a privacy-policy update and (on iOS) ATT; see docs/server.md §12.1.

## 5. KPIs and funnels

### 5.1 The lifecycle funnel

| Stage | Question | Events | KPI (definition) |
|---|---|---|---|
| **Acquisition** | Do people arrive? | `app_opened`, `signup_viewed`, `signup_completed`, `invite_created`, `invite_redeemed` | Visitors/day (distinct `anon_id` with `app_opened`); PWA share (`display_mode = standalone`); invite conversion = `signup_completed` / `invite_created`; K-factor = invites redeemed per active user per week |
| **Activation** | Do they start a story and write? | `explore_viewed` → `character_profile_viewed` → `story_start_clicked` → `story_started` → `message_sent` → 5+ `message_sent` in one story | **Activation rate** = new accounts (`signup_completed`) with a `message_sent` within 24 h; step conversion of the funnel |
| **Engagement** | Do they keep going, and is the AI good? | `message_sent`, `reply_completed`, `reply_failed`, `regenerate_used`, `message_edited`, `reply_rated`, feature events | **WES** (North Star); messages per active user per day; turns per story; TTFT distribution (`ttft_bucket` where `aborted = false`); failure rate = `reply_failed` / (`reply_completed` + `reply_failed`); dissatisfaction = (`regenerate_used` + assistant `message_edited` + `reply_rated{down}`) / `reply_completed`; feature adoption = share of active users with `thought_revealed`, `heart_drawer_opened`, `mode_switched`, `suggestions_requested` |
| **Retention** | Do they come back? | any event except `session_started`; `story_resumed` | DAU / WAU / MAU; **D1 / D7 retention** (users whose first event was on day d0 and who are active on d0+1 / d0+7; a device's signed-out events count as the account later seen on it); stories resumed per week; sessions per user per week |
| **Creation** | Do they build for others? | `character_created`, `character_published`, `lore_imported`, `persona_created`, `story_started{source: public}` | Creators/week; AI-draft share = `character_created{via: ai_draft}` / all; public characters/week; **community plays** = `story_started{source: public}` per week |
| **Monetisation readiness** (coin system, built in test mode) | What would people spend, and what does it cost? | `message_sent`, `reply_completed` (`kind`, `output_tokens`, `duration_ms`), `story_started{source: public}`, and the coin events of §4.7: `coins_spent`, `coins_insufficient`, `coins_granted`, `wallet_viewed`, `topup_viewed`, `topup_pack_selected`, `topup_code_redeemed`, `missions_viewed`, `ad_started`, `mission_claimed`, `creator_rank_reached` | **Messages per active user per day** = future coin spend per user; generations per message = (`reply_completed`) / `message_sent` (regenerate and retry cost compute too); **compute per turn** = mean `output_tokens` and `duration_ms` per `reply_completed` → coin price per turn; share of heavy users (≥ 50 messages/day) = candidates for top-ups; creator payout base = community plays per creator (from public-character stories); **coin balance** = coins issued (`coins_granted.amount` by `source`) vs coins spent (6 × `coins_spent`) per day; **% of members hitting 0 coins in 7 days** (`coins_insufficient`); the top-up and rewarded-ad funnels of §5.4 |

Guardrails: **Safety** = `content_reported` per 1,000 `message_sent`, by `reason` (`minor_safety` must stay at
zero and every one is reviewed); **Privacy** = opt-out rate (`analytics_opt_out` / active accounts), deletions,
exports; **Sign-in health** = `login_failed` / (`login_failed` + `login_succeeded`), by `reason`.

### 5.2 What the owner page computes

`GET /api/admin/analytics/summary?days=N` (1–180, default 30) and the "Số liệu" tab show: event counts, DAU / WAU
/ MAU, active users per day, the activation funnel (Xem Khám phá → Xem hồ sơ nhân vật → Bắt đầu story → Gửi lượt
đầu → Gửi từ 5 lượt trong một story; each step alone (`users`) and nested in order (`converted`)), D1 / D7
retention (cohort, retained, rate), and whether PostHog forwarding is on. Everything else in §5.1 (WES, activation
rate, monetisation inputs) is computed from the export or in PostHog.

### 5.3 First targets for Round 2

There is no live traffic yet, so these are starting hypotheses to check against the first two weeks of data, not
commitments: activation rate ≥ 50 % of invited signups; ≥ 40 % of started stories reach 5 turns; D1 ≥ 35 %, D7 ≥
15 %; reply failure rate < 2 %; first token under 10 s for ≥ 90 % of replies after warm-up; `minor_safety` reports = 0
unreviewed.

### 5.4 Coin funnels (top-up and rewarded ad)

Both funnels run on events that are recorded today (§4.7). Nothing is sold in test mode: a "top-up" is a code the
owner hands out, and the ad is a 15-second sample ad that talks to no ad network. The funnels are defined now so
the same steps carry over when real payments and ads arrive (§4.8).

**Top-up funnel** (per account, steps in order within 24 h):

| Step | Event | Src | Note |
|---|---|---|---|
| 1. Runs out of coins | `coins_insufficient` | S | A reply was refused with 402 `coins_required` |
| 2. Opens "Nạp coin" | `topup_viewed` | C | `from: composer` = straight from the out-of-coins block |
| 3. Looks at a pack | `topup_pack_selected` | C | `pack`; opens the "Giá dự kiến" explanation |
| 4. Gets coins | `topup_code_redeemed` | S | Test mode; in Round 2 this step becomes `purchase_completed` (§4.8) |

KPIs: step-to-step conversion; **top-up rate** = accounts with step 4 / accounts with step 1; pack mix from step 3
vs step 4; failure share = `topup_code_failed` / (`topup_code_redeemed` + `topup_code_failed`), by `reason`.

**Rewarded-ad funnel** (per account and day):

| Step | Event | Src | Note |
|---|---|---|---|
| 1. Opens "Nhiệm vụ hôm nay" | `missions_viewed` | C | `from: wallet\|composer\|link` |
| 2. Starts the ad | `ad_started` | S | Sample ad today; `ad_impression` in Round 2 (§4.8) |
| 3. Claims the reward | `mission_claimed{mission: ad}` | S | Also `coins_granted{source: mission_ad}`; `ad_rewarded` in Round 2 |

KPIs: **ad completion rate** = `mission_claimed{mission: ad}` / `ad_started`; ads per active member per day (at most
3 per day, [docs/coins.md](coins.md)); share of out-of-coins members who choose missions instead of leaving =
accounts with `coins_insufficient` followed by `missions_viewed{from: composer}` the same day.

## 6. Where server events are recorded

| Event | Code (`backend/lyris/`) |
|---|---|
| `owner_setup_completed`, `login_succeeded`, `login_failed`, `signup_completed`, `invite_redeemed` | `api/routes_auth.py` |
| `invite_created` | `api/routes_admin.py` |
| `story_started`, `mode_switched`, `show_thoughts_toggled`, `message_sent`, `story_resumed`, `regenerate_used`, `variant_switched`, `message_edited`, `message_deleted`, `reply_rated` | `api/routes.py` |
| `reply_completed`, `reply_failed`, `lore_unlocked` | `analytics/replies.py` (wraps the SSE stream of send / retry / regenerate) |
| `suggestions_requested`, `memory_forgotten` | `api/routes_state.py` |
| `character_created`, `character_published`, `persona_created` | `api/routes_studio.py` (`POST /api/cards?via=form\|ai_draft\|import`; duplicate is `via=duplicate`) |
| `lore_imported` | `api/routes_lore.py` |
| `session_started` | `analytics/tracker.py` (automatic) |
| `analytics_opt_out` | `api/routes_accounts.py` (`PATCH /api/account`) |
| `content_reported`, `account_deleted`, `data_exported` | `api/routes_compliance.py` |
| `coins_granted{source: signup}` | `api/routes_auth.py` (with `signup_completed`) |
| `coins_spent`, `coins_released`, `coins_insufficient` | `coins/wallet.py` (`CoinService.hold` / `charge` / `release`, called by `chat/service.py` around every reply and by `api/routes_studio.py` for the Studio test chat; holds released at start-up go through `emit_restart_releases`, called from `api/app.py`) |
| `coins_granted` (daily, top-up code, missions), `coins_adjusted`, `topup_code_redeemed`, `topup_code_failed`, `topup_code_created`, `ad_started`, `mission_claimed` | `coins/wallet.py` (`CoinService`, called by `api/routes_coins.py`; the daily check-in is also called from `api/routes_auth.py`) |
| `creator_rank_reached`, `coins_granted{source: creator_rank\|creator_first_public}` | `coins/wallet.py` (`_emit_refresh`, detached, when the "Nhân vật hot" board of `coins/hot.py` is recomputed) |

## 7. Client contract (`POST /api/events`)

```http
POST /api/events
X-Lyris: 1
Content-Type: application/json

{"events": [
  {"name": "explore_viewed"},
  {"name": "vibe_filter_used", "props": {"vibe": "tinh_dau", "position": 4}},
  {"name": "thought_revealed", "story_id": 12}
]}
```

- 1 to 20 events per request; the CSRF header `X-Lyris: 1` is required, like every write (without it: 403).
- Response `202 {"accepted": n, "dropped": m}`. Events are dropped silently when: the name is not a client
  event, a property is unknown or invalid, the user is not signed in (or must still change a temporary password)
  and the event is not a pre-sign-in event (`app_opened`, `signup_viewed`), the account has turned sharing off,
  or the browser sends `Sec-GPC: 1`.
- `story_id` is kept only for story events (`suggestion_used`, `thought_revealed`, `heart_drawer_opened`,
  `events_timeline_opened`) and only if the story belongs to the sender; otherwise it is removed. The server fills
  `mode` from the story.
- Rate limit: 30 requests per minute per account; then `429` with `Retry-After`.
- Before sign-in (anti-flooding): each pre-sign-in event counts **once per request** (duplicates dropped), at most
  **10 requests per minute per IP** (then `429`), and at most **30 new devices per IP per hour** (a request without
  a `lyris_anon` cookie): past that the batch is dropped and no new device id is minted, so a script cannot inflate
  visitors or fill the PostHog quota.

### 7.1 Frontend client

`frontend/src/lib/track.ts` (pure core `createTracker`, tested in `track.test.ts`):

- **Whitelist.** A copy of the registry's client events with the same property rules; a test reads
  `backend/lyris/analytics/events.py` and fails if the two lists (names, pre-sign-in, story events) differ. Any
  property that is not a listed enum code, a boolean or an integer in range drops the whole event, so no text
  can leave the browser (tested with chat text, names, handles, emails, invite codes and vibe words).
- **Consent.** Signed out (or on a temporary password): only `app_opened` / `signup_viewed`. Signed in: events
  wait until `GET /api/account` says whether usage sharing is on; off drops everything waiting and stops
  sending. Browsers with Global Privacy Control send nothing.
- **Batching.** One request 4 s after the first event, at once at 20 events, and on `pagehide` /
  `visibilitychange: hidden` with `fetch(..., {keepalive: true})` (not `sendBeacon`: a beacon cannot carry the
  `X-Lyris` CSRF header). The same event twice within 1 s counts once. Errors and 429 are ignored; tracking never
  blocks the UI.
- **Where each event is sent:** `app_opened` (App, once per load, after `/auth/me`), `signup_viewed`
  (SignupPage), `explore_viewed` and `vibe_filter_used` (ExplorePage; the vibe's code via `vibeCode`, never the
  tag), `character_profile_viewed` (CharacterPage; `from` = the screen shown before), `story_start_clicked`
  ("Bước vào câu chuyện" on the profile and the Explore hero), `suggestion_used` (QuickReplies),
  `thought_revealed` (ThoughtCard, in a story only), `heart_drawer_opened` and `events_timeline_opened`
  (ChatPage). Story events carry the open story's id.
- The card editor passes `POST /api/cards?via=form|ai_draft|import` (AI draft and import come from the Studio's
  pending draft).

## 8. Storage, viewing and export

- Table `analytics_events` (migration `0009_analytics.sql`): `id, ts, name, account_id, anon_id, session_id,
  story_id, props_json (≤ 1 KB, valid JSON), source, app_version, posthog_state (local|pending|sent|failed),
  posthog_attempts, posthog_next_at`. Column `accounts.analytics_opt_out` (0 = sharing on).
- **Retention: 180 days.** Older events are deleted at start-up and every hour (with the sign-in cleanup).
- Deleting an account sets `account_id` to NULL on its events and on the signed-out events of its devices, and
  replaces their `anon_id` with a new random alias and each `session_id` with a new random id (PostHog had linked
  the old `anon_id` to the account at sign-in). The `lyris_anon` cookie is cleared in the same response. Aggregates
  stay; nothing links them back to the person, locally or in PostHog.
- **How to view and export** (owner only):
  1. **In the app:** Tài khoản → "Quản lý tài khoản" → tab **"Số liệu"**: tiles for today / 7 days / 30 days /
     busiest day, the funnel, D1/D7 return, top actions in plain Vietnamese, and a CSV download button.
  2. **API:** `GET /api/admin/analytics/summary?days=30` (JSON, §5.2).
  3. **Raw export:** `GET /api/admin/analytics/export.csv?since=YYYY-MM-DD&until=YYYY-MM-DD` and
     `.../export.jsonl` (streamed). One row per event: `event_id, ts, name, distinct_id, anon_id, session_id,
     story_id, source, app_version, props`. Dates are Vietnam time, both ends included; accounts that turned
     sharing off are excluded. **This is the file to hand to Apero for Round 2.** The "Số liệu" tab has a CSV
     button; for JSONL or a date range, open the URL in the browser where the owner is signed in.
  4. **PostHog** (when configured, §9): live dashboards, funnels and retention in the PostHog project.

## 9. PostHog

- Set `LYRIS_POSTHOG_KEY` (project API key, `phc_…`) and optionally `LYRIS_POSTHOG_HOST`
  (default `https://us.i.posthog.com`; EU projects use `https://eu.i.posthog.com`; must start with `https://`).
  No key = nothing leaves the machine. The key is never logged or shown in the UI.
- A background task sends pending events in batches of 50 to `{host}/batch/` with `httpx` (no extra dependency),
  shortly after new events arrive and every 10 seconds. Failures (network, 429, 5xx, 401/403) are retried with
  backoff (30 s, 1 min, 2 min, … up to 6 h), up to 8 attempts; `400`/`413` are dropped at once. Each event
  carries a stable `uuid`, so retries do not create duplicates.
- Payload: event name, `distinct_id` (account uid or `anon_id`), timestamp, the validated properties, plus
  `$session_id`, `app_version`, `source`, `story_id`, `$lib: "lyris"`, `$ip: null`, `$geoip_disable: true`, and
  `$process_person_profile` (false before sign-in). The user's IP is never forwarded. Recommended project
  settings: turn on "Discard client IP data"; pick the EU region if the team wants data stored in the EU.
- Opted-out accounts are never sent (nor the signed-out events of their devices); `analytics_opt_out`,
  `content_reported` and `account_deleted` stay local; events of a deleted account that were not yet sent stay
  local; events of an account that has not accepted the current Privacy Policy stay local.
- `LYRIS_POSTHOG_HOST` must start with `https://`; anything else (including `http://`) stops the server at start-up
  with a clear message, so events never travel unencrypted.
- **Round 2 handover:** set `LYRIS_POSTHOG_KEY` (and `LYRIS_POSTHOG_HOST`) to Apero's own PostHog project on the
  server Apero evaluates, or, if Apero prefers its own tools, hand over the CSV/JSONL export of §8 for the
  evaluation period. Either way the event names and properties are the ones in §4.

### 9.1 Mapping to GA4 / Firebase and AppsFlyer (if Apero uses them)

Lyris sends to PostHog only. If Round 2 runs on Google Analytics 4 / Firebase or AppsFlyer, the catalog maps over
without renaming: every name is lowercase `snake_case` starting with a letter, the longest is 24 characters
(`character_profile_viewed`), the longest property name is 15 characters, no event has more than 7 properties, and
every property value is a short code, a boolean or a number. Suggested mapping (proposal; check each tool's current
reserved names and limits with Apero before wiring it):

| Lyris event | GA4 / Firebase | AppsFlyer |
|---|---|---|
| `signup_completed` | `sign_up` (recommended event) | `af_complete_registration` |
| `login_succeeded` | `login` (recommended event) | `af_login` |
| `topup_viewed` | `view_item_list` | custom event, same name |
| `topup_pack_selected` | `select_item` (`item_id` = `pack`) | custom event, same name |
| `purchase_started` (§4.8) | `begin_checkout` | `af_initiated_checkout` |
| `purchase_completed` (§4.8) | `purchase` (`currency: VND`, `value` from the pack price) | `af_purchase` (`af_revenue`, `af_currency: VND`, `af_content_id` = `pack`) |
| every other event | custom event with the same name and properties | custom event with the same name and properties |

The privacy rules of §10 still apply on any tool: no user text, no IP, the opt-out and `Sec-GPC` respected, and no
advertising identifiers unless the PO decides on real ads (§4.8).

## 10. Privacy rules

- No free text, no IP address, no device fingerprint beyond a random HttpOnly cookie, no age or other sensitive
  personal data. Enforced twice (client whitelist and server registry) and tested.
- On by default, explained in the privacy policy (`docs/legal/privacy.md`), accepted at sign-up; opt-out in
  Account settings deletes stored events (also the signed-out ones of that account's devices) and stops recording,
  also when signed out on that device (`lyris_noshare` cookie); `Sec-GPC: 1` is honoured and gets no cookie.
- 180-day retention in the app database. Events already sent to PostHog are deleted there on request
  (docs/compliance.md §4).
- Default content is safe: no sexual content; romance, jealousy and possessiveness only non-explicitly; sexual
  content involving minors is refused absolutely. `content_reported{reason: minor_safety}` is monitored with zero
  tolerance.
- Lyris is for users aged 16+ (Terms; no birth date is collected, so no age property exists).
- **Planned, not built (F48):** a "Nội dung an toàn" (safe content) toggle, on by default; turning it off (only once
  18+ content exists) needs an "I am 18 or older" confirmation. If it ships, add `safe_content_changed {on}`
  (boolean only) and keep the same no-text rule.
- Any new event or property must be added to the registry (`events.py`) and the client whitelist (`track.ts`) in
  the same change, with an enum/boolean/bounded integer type and a row in §4. The sync test fails otherwise.

## 11. QA checklist

Run against a scratch database (never the real one), e.g.
`LYRIS_DB_PATH=/tmp/lyris-qa/lyris.db LYRIS_API_PORT=8064 LYRIS_WEB_PORT=8065 bash scripts/serve.sh`.

**Automated (must pass before each release)**
- [ ] `(cd backend && .venv/bin/pytest -q tests/test_analytics.py tests/test_analytics_api.py tests/test_compliance.py tests/test_launch_fixes.py)`
- [ ] `(cd frontend && npm test)` (includes `track.test.ts` registry sync and `launchWiring.test.ts`)

**Manual, in the browser (DevTools → Network, filter `events`)**
- [ ] Open the app signed out: one `POST /api/events` with `app_opened` (`authed: false`); response 202.
- [ ] Open an invite link: `signup_viewed{has_invite_code: true}`. Sign up: `signup_completed` and `invite_redeemed`
      appear in the database (server events never show in the Network tab).
- [ ] Khám phá → tap a vibe chip → open a profile → "Bước vào câu chuyện" → choose persona → start: client events
      `explore_viewed`, `vibe_filter_used`, `character_profile_viewed`, `story_start_clicked`; server `story_started`.
- [ ] Send a turn, wait for the reply: `message_sent`, then `reply_completed` with a `ttft_bucket`. Stop a reply
      half-way: `reply_completed{aborted: true}`.
- [ ] Regenerate, flip versions, thumbs up, edit, delete from a turn: `regenerate_used`, `variant_switched`,
      `reply_rated`, `message_edited`, `message_deleted`.
- [ ] Tap a thought, open the heart drawer, "+" → "Nhận gợi ý" → tap a suggestion, "+" → "Xem sự kiện", switch to
      DM: `thought_revealed`, `heart_drawer_opened`, `suggestions_requested`, `suggestion_used`,
      `events_timeline_opened`, `mode_switched` (client ones carry `story_id`; the server adds `mode`).
- [ ] Report a reply ("Báo cáo") and a public character (profile → "Báo cáo nhân vật"): `content_reported`
      recorded by the server with `account_id` NULL, empty `anon_id`/`session_id` and no `story_id`; **no** client
      `content_reported` in the Network tab.
- [ ] Inspect the rows: `sqlite3 -readonly <db> "SELECT name, source, props_json FROM analytics_events ORDER BY id
      DESC LIMIT 30"`. Every `props_json` holds only codes, booleans and numbers; no word you typed appears
      anywhere (`SELECT COUNT(*) FROM analytics_events WHERE props_json LIKE '%<a word you typed>%'` → 0).
- [ ] Turn off "Chia sẻ dữ liệu sử dụng ẩn danh": the account's rows (and the signed-out rows of this browser) are
      gone, one anonymous `analytics_opt_out` row exists, no further `POST /api/events` is sent, and after signing
      out the browser's `app_opened` is dropped (`accepted: 0`).
- [ ] Owner: "Số liệu" tab shows non-zero numbers and the CSV downloads with the header
      `event_id,ts,name,distinct_id,anon_id,session_id,story_id,source,app_version,props`.
- [ ] With `LYRIS_POSTHOG_KEY` set to a test project: events appear in PostHog → Activity within ~1 minute;
      `posthog_state` moves from `pending` to `sent`; no person has an IP or location.

## Tóm tắt tiếng Việt

- **Mục tiêu:** đo cả vòng đời người dùng: thu hút → kích hoạt → tương tác → giữ chân → sáng tạo → sẵn sàng
  kiếm tiền (hệ thống coin, đã có ở chế độ thử). **Chỉ số North Star: số story "sống" mỗi tuần** (story có từ 3 lượt
  `message_sent` trong một tuần, giờ Việt Nam).
- **57 sự kiện** (§4), chia theo nhóm: thu hút và tài khoản, khám phá, bắt đầu story, tương tác và chất lượng AI,
  sáng tạo, giữ chân, an toàn nội dung, tài khoản, coin. §4.8 liệt kê các sự kiện **dự kiến cho Round 2**
  (`purchase_*`, `ad_impression`, `ad_rewarded`): chưa có trong code, chưa được ghi.
- **Phễu coin** (§5.4): phễu nạp coin `coins_insufficient` → `topup_viewed` → `topup_pack_selected` →
  `topup_code_redeemed` (Round 2: `purchase_completed`), và phễu quảng cáo có thưởng `missions_viewed` →
  `ad_started` → `mission_claimed{mission: ad}`. Sự kiện server biết thì server ghi; giao diện chỉ gửi những gì
  chỉ giao diện biết qua `POST /api/events` (tối đa 20 sự kiện, cần `X-Lyris: 1`, 30 lần/phút; chưa đăng nhập: mỗi
  sự kiện một lần mỗi request, 10 lần/phút mỗi IP, tối đa 30 thiết bị mới mỗi giờ mỗi IP).
- **KPI chính** (§5): tỉ lệ kích hoạt, số lượt mỗi story, DAU/WAU/MAU, D1/D7, thời gian chờ chữ đầu, tỉ lệ lỗi, tỉ
  lệ tạo lại; **số tin nhắn mỗi người mỗi ngày** = lượng coin sẽ tiêu, **token và thời gian mỗi lượt** = chi phí để
  định giá coin.
- **Không bao giờ ghi chữ của người dùng.** Thuộc tính chỉ là enum, true/false hoặc số trong khoảng; độ dài tin
  nhắn, số ngày vắng, số lượt được chia khoảng trên server. Không gửi IP.
- Lưu trong DB của app **180 ngày**. Có `LYRIS_POSTHOG_KEY` thì gửi thêm sang PostHog (máy chủ Mỹ mặc định, đặt
  `LYRIS_POSTHOG_HOST=https://eu.i.posthog.com` cho EU), chạy nền, thử lại khi lỗi.
- Mặc định đang chia sẻ; người dùng tắt được ở Tài khoản (công tắc "Chia sẻ dữ liệu sử dụng ẩn danh"), tắt thì xoá
  sự kiện đã lưu (cả sự kiện lúc chưa đăng nhập trên thiết bị của họ) và ngừng ghi, kể cả sau khi đăng xuất trên
  thiết bị đó. Trình duyệt gửi `Sec-GPC: 1` không bị ghi và không nhận cookie nào. Tài khoản chưa đồng ý chính sách
  hiện tại: sự kiện chỉ ở máy, không gửi PostHog. Báo cáo nội dung và xoá tài khoản được ghi không gắn ai.
- **Xem số liệu:** chủ máy vào Tài khoản → "Quản lý tài khoản" → tab "Số liệu", hoặc tải CSV/JSONL
  (`/api/admin/analytics/export.csv`, `.jsonl`) để gửi Apero cho Round 2.
- **Round 2:** đặt `LYRIS_POSTHOG_KEY` của dự án PostHog do Apero cấp, hoặc bàn giao file export CSV/JSONL. Nếu
  Apero dùng GA4/Firebase hay AppsFlyer, bảng ánh xạ ở §9.1 (đề xuất, cần kiểm lại với Apero).
- **Kiểm tra (QA):** danh sách ở §11, chạy trên DB tạm, không bao giờ trên DB thật.
