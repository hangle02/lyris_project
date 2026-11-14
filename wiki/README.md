# Wiki của Lyris

Đây là nguồn sự thật về Lyris: app là gì, có tính năng nào, màn hình nào, đã chọn gì và vì sao. Code làm theo wiki; wiki ghi đúng những gì code đang có. Mọi trang: [index.md](index.md).

Wiki viết bằng tiếng Việt, câu ngắn, cụ thể. Giao diện gọi là "story"; chỉ CTA là "Bước vào câu chuyện". Người chơi luôn ghi là `{{user}}`.

## Thư mục

```
wiki/
├── README.md         ← trang này: wiki vận hành thế nào
├── raw/              ← lời chủ dự án, chép nguyên văn. KHÔNG BAO GIỜ sửa.
├── overview.md       ← Lyris là gì, cho ai, tiến độ từng phase
├── features/         ← mỗi tính năng một trang F<NN>-<slug>.md, có "Done when" và "Tests"
├── screens/          ← mỗi màn hình một trang
├── decisions/        ← lựa chọn quan trọng và vì sao
├── design/           ← README (nguyên tắc), assets (nguồn miễn phí), style.md (của Lyris), credits
├── plan-checklist.md ← 8 phần một ý tưởng phải có (để hỏi lại khi còn thiếu)
├── learned.md        ← bài học từ lần sai (ghi thêm sau mỗi lần sai)
├── index.md          ← mọi trang, liệt kê
└── log.md            ← mỗi thay đổi một dòng
```

## Nguồn sự thật, theo thứ tự

1. **Lời chủ dự án trong `raw/`.** Lời mới nhất thắng lời cũ.
2. **Code đang chạy** (`backend/lyris`, `frontend/src`). Trang wiki nói khác code thì trang sai, sửa trang (hoặc sửa code nếu chủ dự án muốn theo trang).
3. **Thiết kế chi tiết trong `docs/`** ([plan.md](../docs/plan.md), [phase1.md](../docs/phase1.md) tới [phase4.md](../docs/phase4.md), [accounts.md](../docs/accounts.md), [auth.md](../docs/auth.md), [design-impl.md](../docs/design-impl.md)). Wiki không chép lại docs; wiki tóm tắt và dẫn link tới đúng mục.
4. **Trang wiki** (`features/`, `screens/`, `decisions/`, `design/`) là bản gọn, dễ đọc của ba nguồn trên.

## Trang tính năng: mã F, Done when, Tests

Wiki là nguồn sự thật cho **nội dung** tính năng. **Trạng thái** (đã chứng minh hay chưa) không nằm trong wiki mà nằm ở `memory/features.json`, và chỉ máy được đổi nó sang ✅.

- **Tên file:** `features/F<NN>-<slug>.md`, hai chữ số (F01, F02, …), không đổi số khi đã có. Tính năng mới lấy số kế tiếp.
- **Dòng đầu:** đúng dạng `# F<NN> — <Tên tính năng>`.
- **Metadata:** `- **Trạng thái:** xem memory/features.json · **Phase:** …`, rồi `- **Giai đoạn:** Đã có` hoặc `Kế hoạch`, rồi `- **Màn hình:** …`. Tính năng **Kế hoạch** luôn ⏳ pending cho tới khi có code; lúc đó đổi Giai đoạn thành Đã có.
- **`## Done when`:** mỗi dòng một điều kiện kiểm được, luôn là `- [ ]` (không bao giờ tick `[x]`: trạng thái chỉ ở `memory/features.json`). Ba loại:
  - `- [ ] Unit: …` chứng minh bằng test có tên trong `## Tests` (backend pytest, frontend `node --test`).
  - `- [ ] Bot: …` chứng minh bằng bot trình duyệt chạy trên server LLM giả: route, chữ hay aria-label nhìn thấy, bấm gì thì thấy gì, không cuộn ngang ở 390px.
  - `- [ ] Model thật: …` cần model thật (Ollama). `verification/verify.sh` bỏ qua và **nói rõ** là bỏ qua, trừ khi chạy với `--real-model`. Tính năng có dòng Model thật chỉ lên ✅ khi chạy `--real-model`.
- **`## Tests`:** mỗi dòng một tham chiếu test **có thật**:
  - backend: `backend/tests/test_x.py::test_ten` (node id của pytest) hoặc cả file `backend/tests/test_x.py`;
  - frontend: `frontend/src/…/x.test.ts`;
  - bot: `bot: <tên check>`, đúng từng chữ tên check trong danh sách `CHECKS` của `environment/e2e.mjs` (hiện có 82 check). Mỗi dòng Bot của tính năng Đã có có đúng một dòng `bot:`, cùng thứ tự. Đổi tên check thì đổi cả trang wiki.
  - Tính năng Kế hoạch có thể chưa có test nào; khi làm thì viết test trước rồi thêm vào đây.
- **`## Ngoài Done when`** (tuỳ chọn): việc không chặn ✅, như thử tay trên iPhone, dịch vụ thật (PostHog), hay phần còn là kế hoạch. Khi phần kế hoạch được làm thì chuyển nó thành dòng Done when.
- **Vòng trạng thái** (giống mini-harness của Apero): ⏳ pending → Model làm xong thì chỉ được **claim** 🟡 → chỉ `verification/verify.sh` xanh mới chuyển 🟡 → ✅ passing. Đỏ 3 lần liền thì ⛔ blocked, kèm lý do và một mục mới ở [learned.md](learned.md). Câu hỏi cho chủ dự án khi wiki chưa rõ: `memory/po-questions.md`.

## Harness: wiki là phần ① trong bốn phần

Lyris dùng harness theo mẫu mini-harness của Apero. Bốn phần, mỗi phần một thư mục ở gốc repo:

| Phần | Thư mục | Vai trò |
|---|---|---|
| ① Wiki | `wiki/` | Nguồn sự thật: tính năng, Done when, Tests, màn hình, quyết định, bài học. |
| ② Environment | `environment/` | Luật cho AI (`rules.md`), kiểm máy (`doctor.mjs`), bot trình duyệt (`bot.mjs` + `e2e.mjs` + `fake-server.py`, cổng 8066/8067, DB tạm, LLM giả). |
| ③ Verification | `verification/` | `verify.sh` chấm đậu/rớt; `plan-check.sh` kiểm wiki đủ để build. |
| ④ Memory | `memory/` | `features.json` (chỉ trạng thái), `progress.md`, `po-questions.md`. |

Lệnh Claude Code: `/plan` (ý tưởng → wiki), `/build` (claim rồi verify tới khi xanh), `/play` (bot chạy thử, báo cáo có ảnh). Lệnh tay và cách đọc kết quả: [README gốc, mục Harness](../README.md#harness-theo-mẫu-mini-harness-của-apero).

Bảng đếm ngày 2026-11-14 (`verify.sh` đầy đủ, bot 82/82): **✅ 24 · 🟡 12 · ⏳ 5 · ⛔ 0**. 12 tính năng 🟡 có dòng Model thật và chờ `verify.sh --real-model` (F03, F05, F07, F09, F10, F12, F13, F14, F15, F17, F19, F36). 5 tính năng ⏳ là Kế hoạch (F37–F41). Bảng đếm mới nhất luôn lấy từ `node memory/features.mjs list`.

## raw/ không bao giờ sửa

- Mỗi file là lời chủ dự án, chép nguyên chữ, dưới dòng `## <ngày giờ>`. Tên file: `YYYY-MM-DD-<chủ-đề-ngắn>.md`.
- Không sửa, không xoá, không "dọn" chính tả. Chủ dự án đổi ý thì thêm **file mới** có ngày mới; trang wiki theo lời mới nhất.
- Luật đầy đủ: [raw/README.md](raw/README.md).

## Thêm một tính năng

1. **Ghi ý tưởng:** chép nguyên lời chủ dự án vào `raw/YYYY-MM-DD-<chủ-đề>.md`.
2. **Kiểm đủ chưa:** đi qua [plan-checklist.md](plan-checklist.md). Phần nào thiếu thì hỏi lại chủ dự án (tối đa 3-4 câu một lượt), hoặc ghi vào `memory/po-questions.md` khi chủ dự án không có mặt. Câu trả lời cũng ghi vào `raw/` (file mới).
3. **Viết trang tính năng:** `features/F<NN>-<slug>.md` theo mục trên: Giai đoạn "Kế hoạch", "Done when" với các dòng Unit / Bot / Model thật cụ thể, "Tests" (có thể còn trống). Có màn hình mới thì thêm trang trong `screens/`. Có lựa chọn quan trọng thì thêm trang trong `decisions/` (ngày, ai quyết, bối cảnh, lựa chọn, vì sao).
4. **Cập nhật [index.md](index.md):** thêm một dòng (cột ID) cho mỗi trang mới. Chạy `bash verification/plan-check.sh` để kiểm trang mới đúng định dạng và đủ 8 phần của [plan-checklist.md](plan-checklist.md).
5. **Ghi [log.md](log.md):** thêm một dòng ở cuối: `YYYY-MM-DD · việc · trang`.

## Làm (build) một tính năng

1. **Đọc trang tính năng** và các trang nó dẫn tới (màn hình, quyết định, mục trong `docs/`, [design/](design/README.md) nếu có giao diện).
2. **Viết code** theo trang. Chỗ nào code buộc phải khác trang thì sửa trang và ghi lý do (trong trang quyết định hoặc mục "Khác với thiết kế" của docs).
3. **Viết test trước** cho từng dòng Unit (đỏ), rồi code (xanh). Dòng Bot thì thêm check cùng tên vào `environment/e2e.mjs`. Ghi mọi tham chiếu vào `## Tests`.
4. **Claim, không tự chấm:** `node memory/features.mjs claim F<NN>` (🟡). Không sửa `memory/features.json` bằng tay, không tick `[x]` trong wiki.
5. **Chấm:** `bash verification/verify.sh F<NN>` chạy test trong `## Tests`, typecheck, build và bot; xanh thì chính script chuyển sang ✅ và ghi [log.md](log.md). Đỏ thì sửa rồi chạy lại; đỏ 3 lần liền thì ⛔ và ghi [learned.md](learned.md).
6. Tính năng Kế hoạch vừa làm xong: đổi `Giai đoạn` thành Đã có, cập nhật bảng ở [index.md](index.md) và tiến độ ở [overview.md](overview.md) nếu phase đổi.

## Sau mỗi lần sai: ghi learned.md

Khi chủ dự án báo lỗi, test bắt được lỗi, hay một lần đo cho thấy đoán sai: thêm một mục ở **cuối** [learned.md](learned.md):

```
### YYYY-MM-DD <tên ngắn của lỗi>

- **Sai:** chuyện gì đã xảy ra.
- **Vì sao:** nguyên nhân thật.
- **Luật rút ra:** làm gì từ nay để không lặp lại.
- **Nguồn:** lời chủ dự án (file raw/), mục docs, hoặc test.
```

Không sửa mục cũ. Luật mới trái luật cũ thì ghi mục mới, nói rõ thay luật nào. Thêm một dòng ở [log.md](log.md).

## Không làm trong wiki

- Không ghi tên tài khoản hay email thật của chủ dự án; người chơi là `{{user}}`.
- Không bịa tính năng. Ý tưởng chưa có code thì ghi Giai đoạn "Kế hoạch".
- Không ghi trạng thái (✅, "Đã xong", `[x]`) vào trang tính năng; trạng thái chỉ ở `memory/features.json`.
- Không ghi tham chiếu test chưa có thật vào `## Tests`.
- Không chép nguyên các mục dài của `docs/`; dẫn link tới mục đó.
