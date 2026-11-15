# Real-model evaluation (evidence)

Results of Lyris running on the real model (`gemma4:12b` through Ollama, on the team's Mac), copied from
`harness/results/` (git-ignored) so the evidence stays in the repo. Every number below is taken from the
`report.md` / `raw.json` of the run named in each section; nothing is re-measured or rounded differently.

**Read this first: the judge was off.** Both `verify.sh --real-model` runs used `run_eval.py --no-judge`
(`"no_judge": true` in `raw.json`, "Judge: tắt" in `report.md`). That means only **machine rules** were checked:
thought count and position, forbidden pronouns in narration, leaked `((directives))`, forbidden phrases, language,
word limits, required world details, JSON shape, TTFT thresholds and so on. Softer qualities ("stays in character",
"follows the directive well") were **not** scored by a model in these runs; the scenario split between machine rules
and judge-only parts is recorded in `wiki/decisions/kich-ban-model-that.md`.

"Pass" below means: no generation error and no machine-rule problem for that scenario (`error = null`,
`problems = []` in `raw.json`).

## Summary

| Run (folder in `harness/results/`) | What it was | Scenarios | Machine-rule problems | Generation errors | Mean TTFT | Mean generation speed |
|---|---|---|---|---|---|---|
| `eval-20261114-161948` | `verify.sh --real-model`, run 1 | 12 | 0/12 | 0 | 18.00 s | 11.1 tok/s |
| `eval-20261114-215908` | `verify.sh --real-model`, run 2 | 10 | 0/10 | 0 | 25.11 s | 12.0 tok/s |
| `eval-20261114-220600` | nested `run_eval.py` started by scenario `f36-chay-long` | 3 | 0/3 | 0 | 16.34 s | 10.5 tok/s |
| `20261114-220516` | `bakeoff.py` started by scenario `f36-bakeoff` (`--limit 2`) | 2 prompts | 0/2 | n/a | 6.06 s | 11.0 tok/s |

Both verify runs are logged in `memory/progress.md` ("verify --real-model: … → xanh"), with the same folder names.
Model settings for all runs: `gemma4:12b`, `num_ctx` 8192, judge off.

## Run 1: `eval-20261114-161948`

Started `2026-11-14T16:19:48`, finished `2026-11-14T16:38:14` (times as recorded in `raw.json`).

| Scenario | Feature page that cites it | Kind | What it checks (scenario title) | Result | TTFT (s) |
|---|---|---|---|---|---|
| `01-mo-dau` | F03 | reply | Mở đầu đơn giản | pass | 24.29 |
| `06-viet-hien-dai` | F03 | reply | Việt Nam hiện đại, xưng anh/em | pass | 28.74 |
| `07-co-trang` | F03 | reply | Cổ trang tiên hiệp, xưng ta/sư đệ | pass | 29.84 |
| `08-tieng-anh` | F03 | reply | Story tiếng Anh, Lạc Dương | pass | 18.88 |
| `f07-thought-long` | F07 | reply | Thought lồng trong truyện (inline) | pass | 3.18 |
| `f07-thought-cuoi` | F07 | reply | Thought một đoạn ở cuối (end) | pass | 23.11 |
| `f09-cam-xuc` | F09 | extract | Cảm xúc tăng giảm đúng chiều theo tình huống | pass | not measured |
| `f12-dm-xung-ten` | F12 | reply | Xưng tên qua DM, sang Story không nói "chưa nói tên với ai" | pass | 27.25 |
| `f13-dm-10-luot` | F13 | dm_session | 10 lượt DM không kết bằng cùng một lời dặn | pass | 5.95 |
| `f14-ttft` | F14 | app_ttft | TTFT các lượt sau lượt đầu, kể cả lượt cửa sổ dịch | pass | 4.10 |
| `f17-the-gioi` | F17 | reply | Mục thế giới được dùng đúng, mục Chỉ bạn biết không lộ | pass | 14.63 |
| `f19-viet-nhap` | F19 | draft | Viết nháp card từ một dòng ý tưởng | pass | not measured |

### F14: time to first token through the real app

`f14-ttft` drives the real app over HTTP and measures, on the player's side, from sending a turn to the first
token, after the background jobs and prefill of the previous turn have finished. Per-turn timings recorded in
`raw.json`:

| Turn | TTFT (s) | Prompt tokens | History window shifted? |
|---|---|---|---|
| 1 | 51.87 | 5476 | no (first turn, nothing cached) |
| 2 | 4.05 | 5764 | no |
| 3 | 4.15 | 6026 | no |
| 4 | 4.13 | 4860 | **yes** |
| 5 | 4.08 | 5215 | no |

Turns 2–5 all stay under the 6-second ceiling set in `wiki/decisions/nguong-ttft-f14.md` (marked "tạm chọn",
a provisional choice awaiting the PO), including the turn where the history window moved. The first turn
(51.87 s) is outside the F14 rule, which covers the turns after the first.

## Run 2: `eval-20261114-215908`

Started `2026-11-14T21:59:08`, finished `2026-11-14T22:07:11` (times as recorded in `raw.json`).

| Scenario | Feature page that cites it | Kind | What it checks (scenario title) | Result | TTFT (s) |
|---|---|---|---|---|---|
| `01-mo-dau` | F03 | reply | Mở đầu đơn giản | pass | 24.29 |
| `06-viet-hien-dai` | F03 | reply | Việt Nam hiện đại, xưng anh/em | pass | 27.95 |
| `07-co-trang` | F03 | reply | Cổ trang tiên hiệp, xưng ta/sư đệ | pass | 29.81 |
| `08-tieng-anh` | F03 | reply | Story tiếng Anh, Lạc Dương | pass | 19.23 |
| `f05-chi-dao` | F05 | reply | Chỉ đạo ẩn không lọt, không bị chép, không nói thẳng | pass | 24.26 |
| `f10-ky-uc` | F10 | extract | Ký ức và điều đã biết được trích đúng ý lượt chơi | pass | not measured |
| `f10-tom-tat` | F10 | summarize | Tóm tắt những lượt cũ đúng nội dung | pass | not measured |
| `f15-goi-y` | F15 | suggest | Nhận gợi ý và Gợi ý khác | pass | not measured |
| `f36-bakeoff` | F36 | bakeoff | bakeoff.py in bảng so sánh model | pass | not measured |
| `f36-chay-long` | F36 | nested_eval | run_eval chạy trọn và lưu báo cáo | pass | not measured |

The two F36 scenarios start real tools and check that they finish: `f36-chay-long` ran `run_eval.py` on three
scenarios (`eval-20261114-220600`: `05-dm`, `f10-tom-tat`, `f15-goi-y`, all pass, `05-dm` TTFT 16.34 s), and
`f36-bakeoff` ran `bakeoff.py --models gemma4:12b --limit 2`:

| Model | RAM loaded (GB) | First load (s) | Mean TTFT (s) | Mean generation (tok/s) | Mean prompt reading (tok/s) | Prompts with machine errors |
|---|---|---|---|---|---|---|
| gemma4:12b | 14.8 | 0.7 | 6.06 | 11.0 | 110.0 | 0/2 |

## How to read the TTFT numbers

- The one-shot `reply` scenarios each send one complete prompt (1,733–3,202 prompt tokens in these runs) and
  measure a single reply, so most of their TTFTs (14.63–29.84 s) include reading that whole prompt; at the
  110 tok/s prompt-reading speed of the bake-off, 2,000–3,200 tokens alone take about 18–29 s. One of them,
  `f07-thought-long`, recorded 3.18 s; it is reported as recorded. These one-shot numbers are not what a player
  waits for in a running story: in the app, F14 prefills the next prompt between turns, and `f14-ttft` measures
  that path end to end (about 4.1 s per turn after the first).
- TTFT is measured on the client side. The first scenario of each run loads the model before timing starts
  (warm-up), so load time is not counted (`report.md` header).
- All runs are on one Mac with 24 GB RAM, the same machine that runs the app; they were started only while the
  app was not in use (see `environment/rules.md`).

## Stability and earlier runs

- Before the verify runs, an exploratory real-model run of 22 scenarios (not a verify run) is logged in
  `memory/progress.md` on 2026-11-14: 20/22 passed on the first try; `04-chi-dao` (two Thoughts in a row) and
  `f10-ky-uc` (a missing fact about the character) failed once each and then passed 3/3 on re-runs. The team
  reads this as a random failure rate of roughly 1 in 4 for those two scenarios, so a single green run is not
  proof that every reply will pass.
- Earlier runs on 2026-11-12 had the **judge on** (`gemma4:e4b`, a smaller model that can misjudge; the report
  says to re-read the replies before concluding). On 5 scenarios it flagged godmodding (the AI writing the
  player's actions) in 1/5 (`eval-20261112-155050`, `eval-20261112-162104`) and 2/5 (`eval-20261112-210438`,
  which also flagged 1/5 as not following the player's turn). No judge-on run was repeated for the 2026-11-14
  verify runs.

## Where to find more

- Full replies, prompts and per-scenario details: `harness/results/<folder>/report.md` and `raw.json`
  (git-ignored; available on the team's machine).
- Scenarios: `harness/scenarios/*.yaml`; machine rules: `harness/kinds.py`.
- How to run: `backend/.venv/bin/python harness/run_eval.py` (needs Ollama with `gemma4:12b`).
- The automated suite and bot run of the same day: [verify-2026-11-14.json](verify-2026-11-14.json),
  [bot-checks.md](bot-checks.md).
