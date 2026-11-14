# Wiki của Lyris

Đây là nguồn sự thật về Lyris: app là gì, có tính năng nào, màn hình nào, đã chọn gì và vì sao. Code làm theo wiki; wiki ghi đúng những gì code đang có. Mọi trang: [index.md](index.md).

Wiki viết bằng tiếng Việt, câu ngắn, cụ thể. Giao diện gọi là "story"; chỉ CTA là "Bước vào câu chuyện". Người chơi luôn ghi là `{{user}}`.

## Thư mục

```
wiki/
├── README.md         ← trang này: wiki vận hành thế nào
├── raw/              ← lời chủ dự án, chép nguyên văn. KHÔNG BAO GIỜ sửa.
├── overview.md       ← Lyris là gì, cho ai, tiến độ từng phase
├── features/         ← mỗi tính năng một trang, có danh sách "Done when"
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

Trạng thái trên mỗi trang tính năng chỉ là một trong ba: **Đã xong** (có trong code), **Một phần** (có code, còn thiếu phần ghi ở trang), **Chưa làm** (mới là kế hoạch). Không ghi "Đã xong" khi chưa có code và test.

## raw/ không bao giờ sửa

- Mỗi file là lời chủ dự án, chép nguyên chữ, dưới dòng `## <ngày giờ>`. Tên file: `YYYY-MM-DD-<chủ-đề-ngắn>.md`.
- Không sửa, không xoá, không "dọn" chính tả. Chủ dự án đổi ý thì thêm **file mới** có ngày mới; trang wiki theo lời mới nhất.
- Luật đầy đủ: [raw/README.md](raw/README.md).

## Thêm một tính năng

1. **Ghi ý tưởng:** chép nguyên lời chủ dự án vào `raw/YYYY-MM-DD-<chủ-đề>.md`.
2. **Kiểm đủ chưa:** đi qua [plan-checklist.md](plan-checklist.md). Phần nào thiếu thì hỏi lại chủ dự án (tối đa 3-4 câu một lượt). Câu trả lời cũng ghi vào `raw/` (file mới).
3. **Viết trang tính năng:** `features/<ten-tinh-nang>.md`, trạng thái "Chưa làm", có danh sách "Done when" (mỗi dòng kiểm được: một test, một thao tác trên màn hình, một con số đo). Có màn hình mới thì thêm trang trong `screens/`. Có lựa chọn quan trọng thì thêm trang trong `decisions/` (ngày, ai quyết, bối cảnh, lựa chọn, vì sao).
4. **Cập nhật [index.md](index.md):** thêm một dòng cho mỗi trang mới.
5. **Ghi [log.md](log.md):** thêm một dòng ở cuối: `YYYY-MM-DD · việc · trang`.

## Làm (build) một tính năng

1. **Đọc trang tính năng** và các trang nó dẫn tới (màn hình, quyết định, mục trong `docs/`, [design/](design/README.md) nếu có giao diện).
2. **Viết code** theo trang. Chỗ nào code buộc phải khác trang thì sửa trang và ghi lý do (trong trang quyết định hoặc mục "Khác với thiết kế" của docs).
3. **Kiểm theo "Done when":** chạy test (`backend/.venv/bin/pytest`, `npm test`, typecheck, build), thử tay ở 390px trước, hai theme. Đánh dấu từng dòng đã đạt.
4. **Đổi trạng thái** trên trang tính năng (Đã xong / Một phần, ghi rõ phần còn thiếu), cập nhật bảng ở [index.md](index.md) và tiến độ ở [overview.md](overview.md) nếu phase đổi.
5. **Ghi [log.md](log.md)** một dòng.

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
- Không bịa tính năng. Ý tưởng chưa có code thì ghi "Chưa làm".
- Không chép nguyên các mục dài của `docs/`; dẫn link tới mục đó.
