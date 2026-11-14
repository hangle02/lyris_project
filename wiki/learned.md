# Learned Wiki: bài học từ lần sai

Harness và các agent ghi thêm bài học mới ở cuối trang; bài mới nhất nằm dưới cùng.

### 2026-11-12 Cụm sáo "bầu không khí"

- **Sai:** Tả cảnh kỳ cục: "bầu không khí xung quanh anh như hạ xuống độ lạnh của băng giá".
- **Vì sao:** Model hay dùng cụm sáo "bầu không khí".
- **Luật rút ra:** Prompt dặn tả chi tiết cụ thể, không tả "bầu không khí". Harness có forbidden_phrases cho cụm này.
- **Nguồn:** Lời người dùng, 2026-11-12 14:00 (xem [raw/](raw/)); [docs/plan.md](../docs/plan.md) §9; [docs/phase1.md](../docs/phase1.md) (luật 4)

### 2026-11-12 Train LoRA trên 12B quá sức RAM

- **Sai:** Train thử LoRA trên gemma4:12b dùng hết 24GB RAM, swap 5GB, chỉ 2-3 tok/s.
- **Vì sao:** 16 lớp LoRA với câu tới 1,168 token quá sức máy 24GB khi model 12B.
- **Luật rút ra:** Không train và serve cùng lúc. Lần sau thử: đóng hết app, 8 lớp, --max-seq-length 1024, hoặc train trên gemma4:e4b.
- **Nguồn:** [docs/plan.md](../docs/plan.md) Phase 0 (Kết quả thực tế)

### 2026-11-12 Chọn model theo quảng cáo ngôn ngữ

- **Sai:** sailor2 (model duy nhất nêu rõ hỗ trợ tiếng Việt) chấm kém hơn cả qwen.
- **Vì sao:** Danh sách ngôn ngữ trên trang model không nói lên chất lượng roleplay tiếng Việt.
- **Luật rút ra:** Chọn model bằng bake-off với câu test thật và người dùng tự chấm, không theo quảng cáo ngôn ngữ.
- **Nguồn:** Lời người dùng, 2026-11-12 06:53 (xem [raw/](raw/)); [docs/plan.md](../docs/plan.md) Phase 0

### 2026-11-13 DM kết câu lặp "ngủ sớm đi"

- **Sai:** Trong DM, lượt trả lời nào của nhân vật cũng kết bằng "ngủ sớm đi".
- **Vì sao:** Model nhỏ dễ rơi vào khuôn. Lượt trước nằm trong lịch sử nên khuôn tự củng cố (Story cũng hay mở đầu `<Tên> khẽ …`).
- **Luật rút ra:** Khối F nêu đích danh các câu kết (DM) hoặc câu mở đầu (Story) của 3 lượt gần nhất và dặn tránh (repetition.py).
- **Nguồn:** Lời người dùng, 2026-11-13 01:59 (xem [raw/](raw/)); [backend/lyris/prompt/repetition.py](../backend/lyris/prompt/repetition.py)

### 2026-11-13 CTA ghi "Bắt đầu story"

- **Sai:** Nút bắt đầu ghi "Bắt đầu story".
- **Vì sao:** Dùng thuật ngữ "story" máy móc cho cả câu CTA mà DESIGN.md đã viết sẵn.
- **Luật rút ra:** CTA luôn là "Bước vào câu chuyện". Mọi chỗ khác gọi là "story".
- **Nguồn:** Lời người dùng, 2026-11-13 05:44 (xem [raw/](raw/))

### 2026-11-13 Chạm nhân vật mở trang sửa được

- **Sai:** Bấm vào nhân vật thì nhảy sang trang tạo story mới, có ô sửa được.
- **Vì sao:** Luồng cũ coi chạm nhân vật là bắt đầu story.
- **Luật rút ra:** Chạm nhân vật chỉ mở hồ sơ chỉ đọc. Persona chọn sau khi bấm "Bước vào câu chuyện".
- **Nguồn:** Lời người dùng, 2026-11-13 05:44 (xem [raw/](raw/)); [docs/design-impl.md](../docs/design-impl.md) §16

### 2026-11-13 Thẻ Khám phá quá to

- **Sai:** Thẻ nhân vật ở Khám phá quá to, phải cuộn nhiều, thông tin dễ bị che.
- **Vì sao:** Làm theo thẻ dọc 3:4 của DESIGN.md mà không xem trên điện thoại.
- **Luật rút ra:** Thẻ chỉ vừa đủ để đọc thông tin (ảnh 4:3). Luôn xem lưới ở 390px trước.
- **Nguồn:** Lời người dùng, 2026-11-13 05:26 (xem [raw/](raw/))

### 2026-11-13 Thẻ thoại còn dấu ngoặc

- **Sai:** Lời nói đã thành thẻ thoại mà vẫn còn dấu "".
- **Vì sao:** Làm theo DESIGN.md (lời thoại nằm trong ngoặc).
- **Luật rút ra:** Thẻ thoại bỏ cặp ngoặc ngoài cùng lúc hiển thị; chữ đã lưu giữ nguyên.
- **Nguồn:** Lời người dùng, 2026-11-13 10:35 (xem [raw/](raw/)); [docs/design-impl.md](../docs/design-impl.md) §6.2

### 2026-11-13 Câu thoại ngắn của người chơi không thành thẻ

- **Sai:** Người chơi nhập hai câu thoại trong một lượt, chỉ một câu thành ô thoại, câu kia vẫn để "".
- **Vì sao:** Lượt người chơi dùng ngưỡng của lượt nhân vật (đoạn trong ngoặc phải từ 3 từ mới thành thẻ), và ngoặc ” mở của bàn phím điện thoại chưa được nhận.
- **Luật rút ra:** Ở lượt người chơi, mọi "…" là một ô thoại dù ngắn (paragraphBlocks(para, 1)). Nhận cả ” dùng làm ngoặc mở. `*"…"*` là trích dẫn, ở lại trong dòng.
- **Nguồn:** Lời người dùng, 2026-11-13 16:02, 16:13 (xem [raw/](raw/)); [frontend/src/lib/storyBlocks.ts](../frontend/src/lib/storyBlocks.ts) (`paragraphBlocks`, ngoặc mở); [frontend/src/lib/text.ts](../frontend/src/lib/text.ts); [frontend/src/lib/playerBlocks.ts](../frontend/src/lib/playerBlocks.ts)

### 2026-11-13 Placeholder dài bị cắt trên điện thoại

- **Sai:** Gợi ý trong ô nhập dài quá, bị cắt trên điện thoại.
- **Vì sao:** Viết gợi ý cho màn hình rộng.
- **Luật rút ra:** Placeholder phải vừa một dòng ở 390px (`Nhập lời thoại vào "…"`). Nhãn đầy đủ để ở aria-label.
- **Nguồn:** Lời người dùng, 2026-11-13 16:15 (xem [raw/](raw/))

### 2026-11-13 Giao diện lộ chữ kỹ thuật

- **Sai:** Giao diện lộ chữ kỹ thuật: pill "M2 sẵn sàng", model, nguồn ảnh, câu "đang ngập ngừng tìm lời hồi đáp".
- **Vì sao:** Đưa thông tin máy và trạng thái nội bộ ra màn hình thường.
- **Luật rút ra:** Chữ kỹ thuật chỉ nằm trong "Nâng cao" gập sẵn. Chờ trả lời là ba chấm nhảy. Lỗi là câu dễ hiểu kèm "Chi tiết".
- **Nguồn:** Lời người dùng, 2026-11-12 18:04, 2026-11-13 03:22 (xem [raw/](raw/)); [docs/phase3.md](../docs/phase3.md) §10.3

### 2026-11-13 Chỉ số cảm xúc chỉ tăng

- **Sai:** Chỉ số cảm xúc cứ nhích lên: 11/12 lượt thường đổi 2 chỉ số, hầu như luôn +1/+2; lượt ghen không làm giảm tin cậy.
- **Vì sao:** Prompt không nói khi nào giảm. Phần kiểm tra giữ 2 thay đổi lớn nhất bất kể tình huống.
- **Luật rút ra:** Model viết reason và tone trước khi chấm số. Mỗi chỉ số có dòng tăng khi / giảm khi. Lượt thường ngày (everyday) không đổi gì; warm toàn ±1 chỉ giữ 1.
- **Nguồn:** Lời người dùng, 2026-11-13 03:47 (xem [raw/](raw/)); [docs/phase3.md](../docs/phase3.md) §10.5

### 2026-11-13 Xét cảm xúc theo dấu số học

- **Sai:** pick_changes xét theo dấu số học: khoảng cách -1 bị coi là chiều ngược lại.
- **Vì sao:** Với nhung nhớ, lo sợ, khoảng cách, giảm mới là ấm lòng.
- **Luật rút ra:** Xét theo ấm lòng / tổn thương (WARM_SIGN), không theo dấu cộng trừ.
- **Nguồn:** [docs/phase3.md](../docs/phase3.md) §10.5 (Vòng sửa thứ hai)

### 2026-11-13 Luật chung trong prompt trái với ví dụ

- **Sai:** Câu chung trong prompt ("làm đau thì giảm") trái với ví dụ ghen (obsession 2, fear 2).
- **Vì sao:** Luật chung viết theo dấu số học, ví dụ viết theo nghĩa.
- **Luật rút ra:** Luật chung và ví dụ trong prompt phải cùng một quy ước. Đọc lại cả hai khi sửa một bên.
- **Nguồn:** [docs/phase3.md](../docs/phase3.md) §10.5

### 2026-11-13 Quên sinh nhật vẫn được cộng điểm

- **Sai:** Quên sinh nhật mà thương mến vẫn +1 (4/4 lần).
- **Vì sao:** Câu trả lời bao dung ("tớ quen rồi") nên model thưởng; luật "giảm khi" chưa có chuyện quên, lỡ hẹn.
- **Luật rút ra:** Chấm theo điều người chơi đã làm, không theo việc nhân vật ngoài mặt bỏ qua. Chọn tone theo hành động của người chơi, không theo việc nhân vật vui hay rung động.
- **Nguồn:** [docs/phase3.md](../docs/phase3.md) §10.5

### 2026-11-13 Tưởng prompt dài, thật ra máy chậm

- **Sai:** Một lời gọi trích xuất mất 68 giây, tưởng do prompt dài.
- **Vì sao:** Máy chậm: log Ollama cho thấy tốc độ đọc prompt chỉ 54 token/s (bình thường 107), swap 7.8/9.2GB. Cùng prompt chạy lại lúc máy rảnh mất 39 giây.
- **Luật rút ra:** Trước khi sửa prompt vì chậm, đọc ~/.ollama/logs/server.log: so tốc độ đọc và tốc độ sinh. Chỉ đo tốc độ khi máy rảnh.
- **Nguồn:** [docs/phase3.md](../docs/phase3.md) §10.7

### 2026-11-13 Prefill qua /api/chat lệch điểm chụp cache

- **Sai:** Mỗi khúc lịch sử vẫn có hai lượt chậm (lượt dịch và lượt ngay sau), lượt thường ~12 giây chứ không ~4 giây.
- **Vì sao:** Model sliding window: Ollama chỉ khôi phục cache ở điểm chụp (chỗ request bắt đầu đọc, cuối prompt trừ 4 token). Prefill qua /api/chat kết thúc bằng generation prompt nên rẽ trước điểm chụp cuối.
- **Luật rút ra:** Prefill bằng /api/generate raw, kết thúc đúng chỗ prompt thật rẽ ra. Renderer mới phải đối chiếu từng token với /api/chat thật; lệch một token là mất trắng.
- **Nguồn:** [docs/phase3.md](../docs/phase3.md) §10.6

### 2026-11-13 num_ctx khác làm nạp lại model

- **Sai:** Một lời gọi dùng num_ctx khác làm Ollama nạp lại model.
- **Vì sao:** Ollama coi num_ctx khác là cấu hình khác, mất 10-20 giây.
- **Luật rút ra:** Mọi lời gọi tới model chat dùng đúng num_ctx của PromptBudget (8192).
- **Nguồn:** [docs/phase3.md](../docs/phase3.md) §0

### 2026-11-13 Cắt từng lượt cũ làm mất cache

- **Sai:** Cắt từng lượt cũ khi đầy cửa sổ làm TTFT khoảng 60 giây thay vì 4 giây.
- **Vì sao:** Điểm bắt đầu lịch sử đổi mỗi lượt nên Ollama đọc lại cả prompt.
- **Luật rút ra:** Phần đầu prompt phải đứng yên giữa các lượt: cắt theo khúc ở mốc cố định, dùng phần dự phòng cố định cho F, C, D.
- **Nguồn:** [docs/phase3.md](../docs/phase3.md) §10.1

### 2026-11-13 Tóm tắt sai thời điểm

- **Sai:** Tóm tắt ngay sau mỗi lần cửa sổ dịch làm thêm một lượt chậm ~50 giây mỗi khúc.
- **Vì sao:** Gọi model tóm tắt đẩy prompt chat ra khỏi cache.
- **Luật rút ra:** Chỉ tóm tắt ngay trước lượt vốn đã phải đọc lại cả prompt.
- **Nguồn:** [docs/phase3.md](../docs/phase3.md) §10.1

### 2026-11-13 Prefill đoán sai độ dài lượt người chơi

- **Sai:** Prefill đoán độ dài lượt người chơi bằng "dài nhất trong 3 lượt + 120" thì lệch ở lượt 24 và 30 trong test.
- **Vì sao:** Đoán dư hợp cho tóm tắt nhưng với prefill thì đoán sai cửa sổ là lệch ngay ở system.
- **Luật rút ra:** Prefill dùng trung vị 5 lượt người chơi gần đây.
- **Nguồn:** [docs/phase3.md](../docs/phase3.md) §10.6

### 2026-11-13 Lượt DM không có nhãn trong Story

- **Sai:** Tần Dương nói tên qua DM, sang Story thì Thought lại nói chưa nói tên với ai.
- **Vì sao:** Lượt DM nằm trong lịch sử nhưng không có gì đánh dấu đó là tin nhắn điện thoại.
- **Luật rút ra:** Ở Story Mode gắn nhãn "[Tin nhắn điện thoại]" cho lượt DM và nhắc ở F. Không gắn nhãn ở DM Mode vì model sẽ bắt chước.
- **Nguồn:** Lời người dùng, 2026-11-13 16:02 (xem [raw/](raw/)); [docs/phase3.md](../docs/phase3.md) §10.8

### 2026-11-13 Tên nhân vật làm nhiễu tìm ký ức

- **Sai:** Tìm ký ức theo từ khoá: tên nhân vật khớp gần như mọi ký ức, độ quan trọng quyết định thứ hạng thay cho độ liên quan.
- **Vì sao:** Âm tiết của tên được dùng làm từ khoá; lượt trả lời dài chiếm hết 32 cụm từ khoá.
- **Luật rút ra:** Bỏ âm tiết của tên khỏi từ khoá. Cụm từ khoá của tin người chơi đứng trước cụm của lượt trả lời.
- **Nguồn:** [docs/phase3.md](../docs/phase3.md) §9 (Ghi chú khi chạy thử)

### 2026-11-13 Schema không giới hạn số fact

- **Sai:** Lượt dày fact làm model viết 14+ fact, chạm num_predict 500 và mất cả lượt trích xuất.
- **Vì sao:** Schema không giới hạn số fact, trong khi validate chỉ giữ 3.
- **Luật rút ra:** Giới hạn trong schema (maxItems) khớp với phần kiểm tra. Không dùng maxLength trong schema của Ollama (làm hỏng escape).
- **Nguồn:** [docs/phase3.md](../docs/phase3.md) §5, §10.7

### 2026-11-13 Ngân sách lore chưa đo trên card thật

- **Sai:** Thiết kế ban đầu để khối lore 700 token; với yen-hoanh-sinh chỉ còn ~740 token lịch sử sau lần dịch.
- **Vì sao:** Ngân sách đặt theo plan.md, chưa đo trên card thật.
- **Luật rút ra:** Đo ngân sách token trên các card thật lớn nhất trước khi chốt. Lore còn 520 token.
- **Nguồn:** [docs/phase4.md](../docs/phase4.md) (Thay đổi sau phản biện mục 2)

### 2026-11-13 Sổ thế giới lộ điều chỉ người chơi biết

- **Sai:** Mục người và nơi chốn của luc-bac-uyen vẫn lộ điều chỉ người chơi biết ("nữ chính của nguyên tác", "nguyên chủ").
- **Vì sao:** Chỉ bỏ dòng "Bí mật"/"Chức năng" là chưa đủ.
- **Luật rút ra:** Bỏ từng câu chứa từ meta hoặc khoá của mục {{user}}; mục trùng khoá {{user}} thành "Chỉ bạn". Có test lộ chạy qua mọi khoá.
- **Nguồn:** [docs/phase4.md](../docs/phase4.md) (Thay đổi sau phản biện mục 3)

### 2026-11-13 Quét lượt nhân vật bằng từ thường

- **Sai:** Quét lượt nhân vật bằng từ thường làm khối thế giới không bao giờ rỗng và tự nuôi mình.
- **Vì sao:** Lời mở đầu đã gợi "nhịp tim", "căn hộ", "nhẫn"; "nhẫn" còn khớp trong "kiên nhẫn".
- **Luật rút ra:** Lượt nhân vật chỉ được quét bằng khoá dạng tên riêng. Cảnh báo khoá một chữ viết thường.
- **Nguồn:** [docs/phase4.md](../docs/phase4.md) (Thay đổi sau phản biện mục 4)

### 2026-11-13 Code chạy trước migration

- **Sai:** Code đọc cột mới tới trước migration thì mọi route story của app đang chạy trả 500.
- **Vì sao:** uvicorn --reload không theo dõi file .sql, nên migration chưa áp khi code .py đã tải lại.
- **Luật rút ra:** Với app đang chạy: viết và test trong bản sao ở thư mục nháp; chép .sql trước, rồi một .py vô hại để tải lại, rồi mới sửa repo; đọc cột mới phòng thủ. Không tắt app, không đụng data/.
- **Nguồn:** [docs/phase4.md](../docs/phase4.md) (Thay đổi sau phản biện mục 7, Khác với thiết kế mục 1); [docs/phase2.md](../docs/phase2.md) (Môi trường và luật an toàn)

### 2026-11-14 "câu chuyện" lọt ra ngoài CTA

- **Sai:** Câu "Tạo một persona để bước vào câu chuyện." dùng "câu chuyện" ngoài CTA.
- **Vì sao:** Không có kiểm tra tự động cho thuật ngữ.
- **Luật rút ra:** Test copyWords.test.ts quét mọi .tsx: "câu chuyện" chỉ được có trong "Bước vào câu chuyện".
- **Nguồn:** [docs/auth.md](../docs/auth.md) §13 mục 60

### 2026-11-14 Ô lẻ trong lưới bị kéo giãn

- **Sai:** Ô cuối của lưới Khám phá (Trần Minh Khang) bị kéo giãn sang hai cột trên điện thoại.
- **Vì sao:** Lưới có kiểu ô "wide" cho ô lẻ và đổi số cột theo số nhân vật (desktopColumns).
- **Luật rút ra:** Số cột cố định theo độ rộng; mọi ô cùng kích thước; hàng cuối thiếu ô thì để trống.
- **Nguồn:** Lời người dùng, 2026-11-14 01:18 (xem [raw/](raw/)); [docs/design-impl.md](../docs/design-impl.md) §18

### 2026-11-14 Hạ Vy hiện hai lần ở Khám phá

- **Sai:** Khám phá hiện hai Hạ Vy, và cái ở trên chưa đổi ảnh.
- **Vì sao:** Nhân vật ở khung nổi bật cũng nằm trong lưới, và khung nổi bật dùng ảnh bối cảnh của mẫu thay vì ảnh của nhân vật đã thêm.
- **Luật rút ra:** Nhân vật ở khung nổi bật không lặp trong lưới (trừ khi đang lọc). Khung nổi bật dùng ảnh của card đã cài (heroImageUrl, withoutHero).
- **Nguồn:** Lời người dùng, 2026-11-14 01:14 (xem [raw/](raw/)); [docs/design-impl.md](../docs/design-impl.md) §18

### 2026-11-14 Model chép giá trị mẫu trong prompt

- **Sai:** Prompt cảnh cho DM có nơi mẫu (ví dụ "Nhà {p}"); gemma4:12b chép nguyên mẫu 3/3 lần.
- **Vì sao:** Model nhỏ chép giá trị ví dụ trong prompt trích xuất.
- **Luật rút ra:** Không đặt giá trị mẫu cụ thể trong prompt trích xuất. Chỉ ghi khi lượt nói rõ, không đoán.
- **Nguồn:** [docs/phase3.md](../docs/phase3.md) §9 (Ghi chú khi chạy thử)

### 2026-11-14 Đoán về cache mà chưa đo

- **Sai:** Dự đoán về điểm chụp cache khi gửi trước lore chỉ đúng một phần.
- **Vì sao:** Lập luận từ §10.6 mà chưa đo đúng chuỗi lượt T, T+1, T+2.
- **Luật rút ra:** Tối ưu cache chỉ bật sau khi đo trên Ollama thật, đọc prompt_eval_count trong log, không chỉ TTFT.
- **Nguồn:** [docs/phase4.md](../docs/phase4.md) §6.5

### 2026-11-14 Tin proxy_headers của uvicorn

- **Sai:** Thiết kế dùng proxy_headers của uvicorn để lấy IP thật.
- **Vì sao:** uvicorn lấy phần tử không tin cậy đầu tiên từ phải, nên request từ 127.0.0.1 tự đặt được IP bất kỳ.
- **Luật rút ra:** Chạy uvicorn --no-proxy-headers; peer 127.0.0.1 thì lấy phần tử cuối của X-Forwarded-For (phần Vite vừa nối).
- **Nguồn:** [docs/auth.md](../docs/auth.md) §3.7, §12 mục 1

### 2026-11-14 Ngưỡng chung để huỷ mã thiết lập

- **Sai:** Luật "sai mã thiết lập 20 lần thì huỷ mã" cho phép bất kỳ ai trên Wi-Fi chặn chủ máy thiết lập mãi.
- **Vì sao:** Ngưỡng chung cho cả máy là công cụ phá hoại.
- **Luật rút ra:** Chỉ giới hạn theo IP; mã 60 bit với 5 lần thử mỗi 15 phút thì không đoán được.
- **Nguồn:** [docs/auth.md](../docs/auth.md) §2.4, §12 mục 2

### 2026-11-14 Người khác khoá được chủ máy ra ngoài

- **Sai:** Người khác gõ sai 50 lần mỗi giờ là khoá được chủ máy ra ngoài, reset-password xong vẫn bị khoá lại.
- **Vì sao:** Khoá theo handle không phân biệt trình duyệt quen.
- **Luật rút ra:** Cookie thiết bị lyris_device: trình duyệt từng đăng nhập đúng thì không bị khoá theo IP hay handle.
- **Nguồn:** [docs/auth.md](../docs/auth.md) §3.4, §12 mục 3

### 2026-11-14 Đoán mật khẩu song song lọt giới hạn

- **Sai:** 40 lần đoán mật khẩu song song từ một IP đều được so.
- **Vì sao:** Kiểm giới hạn, nhả khoá, băm ~0.27 giây rồi mới ghi lần sai; request tới trong lúc băm lọt qua.
- **Luật rút ra:** Ghi giữ chỗ lần thử (ok = 0) trong cùng transaction BEGIN IMMEDIATE với bước kiểm giới hạn, rồi mới băm.
- **Nguồn:** [docs/auth.md](../docs/auth.md) §13 mục 49

### 2026-11-14 Băm mật khẩu khi giữ khoá Repo

- **Sai:** Nguy cơ băm scrypt khi đang giữ khoá chung của Repo làm mọi stream chat đứng chờ.
- **Vì sao:** Repo dùng một kết nối SQLite và một khoá cho cả app.
- **Luật rút ra:** Không bao giờ băm khi giữ khoá Repo hay đang mở transaction; hàng chờ băm có trần, quá trần trả 503.
- **Nguồn:** [docs/auth.md](../docs/auth.md) §3.1, §12 mục 6, §13 mục 51

### 2026-11-14 Bản sao nhân vật mồ côi và lộ sổ thế giới

- **Sai:** Bản sao nhân vật công khai mồ côi khi xoá persona kèm story; chat thử với card.id của bản sao đọc được cả sổ thế giới của người tạo.
- **Vì sao:** Chỉ dọn bản sao ở DELETE /stories/{id}; `_lore_for` nạp sổ cho mọi card thuộc tài khoản.
- **Luật rút ra:** Dọn bản sao cuối mọi transaction xoá story; chặn bản sao ở mọi đường đọc sổ thế giới và mọi hàm ghi.
- **Nguồn:** [docs/auth.md](../docs/auth.md) §4.3, §12 mục 10

### 2026-11-14 Hai tiến trình cùng chạy migration

- **Sai:** Hai tiến trình khởi động cùng lúc thì tiến trình thứ hai chạy lại migration và chết vì "duplicate column name".
- **Vì sao:** migrate() đọc user_version trước khi giữ khoá ghi.
- **Luật rút ra:** Đọc lại user_version sau BEGIN IMMEDIATE; file đã áp thì bỏ qua.
- **Nguồn:** [docs/auth.md](../docs/auth.md) §13 mục 54

### 2026-11-14 Bản nháp Studio lưu nhầm tài khoản

- **Sai:** Đổi tài khoản ở tab khác khi Studio chưa lưu, chọn "Ở lại" thì bản nháp của tài khoản X được lưu vào tài khoản Y.
- **Vì sao:** Hộp "Rời trang?" chặn việc tải lại trang khi cookie đã đổi sang người khác.
- **Luật rút ra:** Khi đổi tài khoản, bật cờ allowForcedLeave trước location.reload(); trang có beforeunload riêng phải kiểm cờ này.
- **Nguồn:** [docs/auth.md](../docs/auth.md) §13 mục 59

### 2026-11-14 Route tài liệu của FastAPI không qua đăng nhập

- **Sai:** FastAPI tự thêm /openapi.json, /docs, /redoc ngoài /api, không qua auth.
- **Vì sao:** Route tự sinh không nằm trong router có dependency đăng nhập.
- **Luật rút ra:** Tạo app với openapi_url, docs_url, redoc_url = None; test quét mọi route qua app.openapi().
- **Nguồn:** [docs/auth.md](../docs/auth.md) §2.5, §12 mục 9
