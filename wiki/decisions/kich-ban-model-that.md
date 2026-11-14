# Kịch bản model thật cho mọi dòng "Model thật"

- **Ngày:** 2026-11-14 · **Ai quyết:** AI đề xuất, chủ dự án đồng ý cùng ngày ([raw](../raw/2026-11-14-po-quyet-harness.md)).
- **Cập nhật sau khi chủ dự án trả lời:** F05 "làm theo chỉ đạo, giữ giọng", F15 "'Gợi ý khác' cho hướng khác về ý" và F36 "chạy
  hết kịch bản" chuyển sang "Ngoài Done when" (kiểm bằng tay); F10 "story dài có '<details> Tóm tắt những lượt cũ'" được chứng minh
  bằng check bot (xem trang F10). Ngưỡng F13, F15 giữ như dưới; mỗi ca chấm **một mẫu**, và trước `verify.sh --real-model` nên chạy
  thử `run_eval.py --no-judge --only …` (không tốn lượt đỏ). Phần "Lựa chọn" dưới đây là bản trước khi chủ dự án trả lời.

## Bối cảnh

Bộ chấm mới (`verify.sh --real-model`) chỉ cho ✅ khi mỗi dòng `Model thật:` nhắc `id` một kịch bản trong `harness/scenarios/`
và kịch bản đó chạy `run_eval.py --no-judge` không lỗi sinh, không lỗi máy. Trước ngày này chỉ F03 có kịch bản; 11 tính năng
(F05, F07, F09, F10, F12, F13, F14, F15, F17, F19, F36) có dòng Model thật mà không có gì chứng minh. Nhiều dòng nói về việc nền
(trích xuất, tóm tắt, gợi ý, viết nháp), nhiều lượt liền, hay tốc độ, không phải một lượt trả lời.

## Lựa chọn

- `harness/run_eval.py` có khoá `kind` cho kịch bản; các loại mới ở `harness/kinds.py` gọi **đúng code app dùng** (`extract_turn`,
  `summarize`, `suggest_replies`, `draft_card`, `build_prompt` + `lore_for_history`, và app thật `create_app` cho TTFT), num_ctx 8192,
  model gemma4:12b. Mọi kiểm tra là luật máy; mỗi luật có test hai chiều (kết quả sai phải ra lỗi, kết quả đúng thì không) trong
  `backend/tests/test_run_eval_kinds.py`.
- Một kịch bản riêng cho mỗi dòng (id bắt đầu bằng mã tính năng: `f05-chi-dao`, `f07-thought-long`, `f07-thought-cuoi`,
  `f09-cam-xuc`, `f10-ky-uc`, `f10-tom-tat`, `f12-dm-xung-ten`, `f13-dm-10-luot`, `f14-ttft`, `f15-goi-y`, `f17-the-gioi`,
  `f19-viet-nhap`, `f36-bakeoff`, `f36-chay-long`). Kịch bản chỉ kiểm điều dòng đó nói, để một lỗi khác (vd số Thought) không làm
  đỏ tính năng không liên quan.
- Dòng Model thật gốc **giữ nguyên lời** trong Done when (rà soát 2026-11-14: tách sang "Ngoài Done when" trước khi PO đồng ý là
  thu hẹp Done when, sai luật 3). Phần máy chấm được thành một dòng Model thật **riêng**, nhắc id kịch bản. Dòng gốc nào chưa có gì
  chứng minh đủ thì để **không** nhắc id: `realCoverage` coi là chưa có kịch bản, tính năng ở 🟡, không ✅ được, tới khi PO trả lời:
  - F05: "làm theo chỉ đạo, giữ giọng nhân vật" (judge có chấm "bám sát" ở `04-chi-dao`, nhưng verify chạy `--no-judge`). Dòng máy:
    không lọt '((', không chép 5 chữ liền nhau của chỉ đạo, không có chữ 'chỉ đạo', không nói thẳng 'ghen' (`f05-chi-dao`).
  - F10: "story dài có '<details> Tóm tắt những lượt cũ'" là giao diện của story đủ dài để cửa sổ dịch; bot chưa có story như vậy.
    Dòng máy: ký ức, điều đã biết (đúng người) và tóm tắt đúng chi tiết (`f10-ky-uc`, `f10-tom-tat`).
  - F15: "'Gợi ý khác' cho hướng khác" về *ý*: máy chỉ đo trùng chữ. "Bấm thẻ thì gửi nguyên văn" có check bot. Dòng máy: đủ 3 gợi ý,
    gửi đi nguyên văn, lần hai trùng < 60% từ (tính trên gợi ý ngắn hơn) (`f15-goi-y`).
  - F36: "chạy hết kịch bản": cả bộ một lượt ~40 phút trở lên, mà verify cho `run_eval` tối đa 60 phút cho **mọi** kịch bản được
    tham chiếu cộng lại. Dòng máy: `run_eval` chạy trọn và lưu `report.md`, `raw.json` (`f36-chay-long`, chạy lồng ba kịch bản).
- F19: dòng gốc ("… trình sửa mở với card đó, chưa lưu") nhắc `f19-viet-nhap` vì phần giao diện nay có dòng Bot riêng (LLM giả viết
  được card nháp → `#/studio/new`, 'chưa lưu', chưa có trong `/api/cards`). F36 `bakeoff.py`: kịch bản chạy đúng `main()` của lệnh.
- Các dòng khác giữ ý, chỉ ghi rõ luật máy: F13 "không còn lượt nào cũng kết bằng cùng một lời dặn" = không câu kết nào lặp ở quá
  2/10 lượt, 3 chữ cuối không trùng ở quá 3/10 lượt, và câu kết không chứa cùng một lời dặn (nhóm cụm như "ngủ sớm / thức khuya /
  đi ngủ") ở quá 2/10 lượt; F14 trung vị ≤ 5 giây và mọi lượt ≤ 6 giây, đo phía người chơi, xem [nguong-ttft-f14](nguong-ttft-f14.md).
- Bộ 8 kịch bản gốc (01-08) giữ nguyên; test cũ ghim đúng 8 kịch bản đó (`CORE_IDS`), không bỏ assert nào.

## Vì sao

Luật 3 của `environment/rules.md`: kịch bản phải thật sự kiểm điều dòng ấy nói, và `--no-judge` không chấm được "giữ giọng",
"làm theo". Thu hẹp dòng cho dễ đậu là sai luật, kể cả "tách" một phần sang chỗ khác: dòng gốc ở lại, tính năng chờ ở 🟡, chủ dự án quyết.

## Đã cân nhắc

- Dùng judge trong verify cho F05: verify chủ ý chạy `--no-judge` (judge nhỏ, hay chấm sai) — không lách.
- F36 liệt kê mọi kịch bản làm `model:`: làm F36 đỏ mỗi khi một tính năng khác đỏ, và cùng lượt verify sẽ quá 60 phút.
- Chạy F09/F10 qua app thật như F14: chậm gấp nhiều lần và lượt trả lời do model sinh làm kết quả trích xuất khó lường; trích xuất
  là đúng hàm worker gọi, nên lượt chơi được viết sẵn trong kịch bản.

## Nguồn

- Yêu cầu bổ sung kịch bản model thật, 2026-11-14 (bộ verify mới, `memory/po-questions.md`)
- [docs/phase3.md](../../docs/phase3.md) §10.5, §10.6, §10.8; [docs/phase4.md](../../docs/phase4.md) §14.4
