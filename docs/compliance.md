# Tuân thủ khi ra mắt (open web / PWA)

> **English summary.** Lyris ships with a safe-by-default content policy enforced in every prompt (story, texting
> and AI character drafting), an in-app report flow for AI replies (the reported text reaches the administrator
> only with the reporter's explicit consent), self-service account deletion and full personal-data export,
> recorded consent to versioned Terms and Privacy Policy (required at sign-up and owner setup; existing accounts
> are asked once), and public legal pages served by the API. **Lyris is for users aged 16+** (stated in the Terms;
> accepting the Terms at sign-up confirms it; no birth date is collected), because Vietnam's Decree 13/2023 treats
> under-16s as children. A **"Nội dung an toàn" (safe content) toggle, on by default for everyone**, and an 18+ mode
> behind turning it off plus a "Tôi đã đủ 18 tuổi" self-confirmation are **planned only** (F48); no 18+ content
> exists today. Code: `backend/lyris/compliance/`, `backend/lyris/api/routes_compliance.py`, migration
> `0010_compliance.sql`. Tests: `backend/tests/test_compliance.py`.
>
> **Launch channel: the open web first**, as an installable PWA over HTTPS (docs/deploy.md). §5 checks Lyris
> against the policies that apply there and against the Google Play and App Store rules that would apply if the
> PWA is later wrapped as a store app; §5.3 covers Vietnam's personal-data rules (Decree 13/2023/NĐ-CP) at a
> plain, non-legal level; §5.4 lists what is done, what the team must do before launch, and what is planned.
> This page is a product checklist, not legal advice.

Trạng thái: backend và giao diện đã làm, có test (2026-11-15). Giao diện theo hợp đồng ở §7, mô tả ở
`docs/design-impl.md` §19. Đây là danh sách kiểm của nhóm sản phẩm, **không phải ý kiến pháp lý**.

## 0. Quyết định của chủ sản phẩm (đã chốt)

1. **Nội dung mặc định an toàn.** Không có nội dung tình dục. Tình cảm, ghen tuông, chiếm hữu được phép nhưng kín
   đáo. Mọi nội dung tình dục liên quan tới người dưới 18 tuổi bị từ chối tuyệt đối.
2. **Lyris dành cho người từ 16 tuổi (16+).** Ghi trong Điều khoản §1 và Chính sách §8: tạo tài khoản và đồng ý
   Điều khoản là xác nhận đã đủ 16 tuổi; người dưới 16 không được dùng; biết tài khoản của người dưới 16 thì xoá.
   **Không có ô năm sinh / ngày sinh** khi đăng ký. Lý do chọn 16: Nghị định 13/2023/NĐ-CP coi người dưới 16 tuổi là
   trẻ em (xử lý dữ liệu cần cha mẹ/người giám hộ đồng ý), nên đặt tuổi tối thiểu 16 thay cho "không đặt tuổi" (chốt
   2026-11-15, thay quyết định 2026-11-14; [wiki/decisions/tuoi-16-va-noi-dung-an-toan.md](../wiki/decisions/tuoi-16-va-noi-dung-an-toan.md)).
3. **Nút "Nội dung an toàn" bật sẵn cho mọi người** (Kế hoạch, F48; hiện chưa có nội dung 18+ nào).
   Khi có nội dung 18+: tắt nút thì hiện ô tích "Tôi đã đủ 18 tuổi" (tự xác nhận, bắt buộc tích mới tắt được); chỉ lưu thời điểm
   xác nhận; người vận hành gỡ quyền được nếu bị lạm dụng (§6).
4. **Số liệu:** lưu trong DB của app, gửi tiếp PostHog khi có khoá; không bao giờ có chữ của người dùng
   (docs/tracking-plan.md).

## 1. An toàn nội dung trong prompt

Một dòng luật ngắn (~115 token) thêm vào khối A, ngay trước dòng ngôn ngữ, ở cả bốn bộ luật:

| Prompt | Hàm | Nội dung |
|---|---|---|
| Story + nhắn tin, tiếng Việt | `lyris/prompt/templates/vi.py` `safety_rule()` | "An toàn: tình cảm, ghen tuông, chiếm hữu được phép nhưng không có cảnh tình dục hay gợi dục (dừng ở nụ hôn rồi chuyển cảnh); tuyệt đối không có gì tình dục với người dưới 18 tuổi; không tả máu me tàn bạo; ai nhắc tới tự hại thì {nhân vật} đáp lại bằng sự quan tâm, không cổ vũ. Bị kéo sang những điều này thì {nhân vật} lảng đi đúng tính cách." |
| Story + nhắn tin, tiếng Anh | `lyris/prompt/templates/en.py` `safety_rule()` | Cùng ý, bằng tiếng Anh. |
| AI viết nháp nhân vật (vi + en) | `lyris/studio/draft.py` (`_VI_SYSTEM`, `_EN_SYSTEM`, mục "Quy ước chung") | Không tình dục/gợi dục lộ liễu, không máu me, không cổ vũ tự hại, tuyệt đối không gì tình dục với người dưới 18; ý tưởng đòi điều bị cấm thì viết bản an toàn. |

- Nhân vật **lảng đi trong vai** (không giảng giải, không nhắc tới luật) để không phá trải nghiệm.
- Chat thử trong Studio dựng prompt bằng cùng `build_prompt` nên cũng có luật này. Gợi ý lượt cho người chơi
  (`lyris/state/suggest.py`) có prompt riêng: thêm một câu "gợi ý luôn an toàn" vào system (vi + en).
- Hash prompt chuẩn (`tests/test_prompt_state.py`) đổi có chủ ý; test `test_safety_rule_is_the_only_change` dựng lại
  template không có dòng này và kiểm cho lại đúng hash cũ. Ba test ngân sách token chỉnh lại có ghi lý do
  (khối A dài thêm ~115 token).
- Giới hạn: đây là luật trong prompt, không phải bộ lọc đầu ra. Model local có thể vẫn lỡ; nút báo cáo (§2) là lưới
  thứ hai. Bộ lọc đầu ra tự động là việc của Round 2 nếu số liệu `content_reported` cho thấy cần.

## 2. Báo cáo câu trả lời của AI

`POST /api/messages/{id}/report` (thành viên, chỉ tin trong story **của chính mình**; tin của người khác: 404):

```json
{"reason": "sexual | minor_safety | violent | hateful | self_harm | harassment | other",
 "note": "≤ 300 ký tự, tuỳ chọn",
 "share_text": false}
```

- Chỉ báo cáo được câu trả lời của nhân vật (`role = assistant`; tin của người chơi: 422).
- `share_text = true` ("Gửi kèm câu trả lời này để người quản lý xem xét"): lưu bản chụp phần hiển thị của câu trả
  lời (≤ 6000 ký tự). `false` (mặc định): chỉ lưu lý do và ghi chú. DB có CHECK: không chia sẻ thì không có chữ.
- Báo cáo lại cùng tin: cập nhật lý do/ghi chú/chia sẻ và mở lại (một người một tin một dòng).
- Lưu thêm: chế độ, ngôn ngữ, tên model, và nếu story chơi bằng **bản sao nhân vật công khai** thì id nhân vật
  công khai gốc (để quản trị viên xem lại nhân vật đó). Nhân vật riêng tư: không lưu.
- `reason` có thêm `minor_safety` so với danh sách ban đầu (an toàn trẻ vị thành niên phải tách riêng để theo dõi
  không khoan nhượng).
- Ghi sự kiện `content_reported {reason (đổi tên theo bảng sự kiện), target: message, mode}` **không gắn ai**: không
  tài khoản, không `anon_id`, không lượt, không story, chỉ lưu ở máy (không gửi PostHog). Nếu gắn tài khoản, chủ máy
  khớp được dòng số liệu (cùng thời điểm, cùng lý do) với báo cáo trong bản xuất CSV và biết ai báo cáo.

**Báo cáo nhân vật công khai** (nội dung người dùng tạo, App Store 1.2 / Google Play UGC): trên hồ sơ nhân vật công
khai của người khác có "Báo cáo nhân vật" → `POST /api/cards/{id}/report {"reason": ..., "note": "..."}`. Mở từ bản
sao trong story của mình thì báo cáo nhân vật gốc (còn công khai). Nhân vật của chính mình: 422; nhân vật không công
khai: 404. Một người một nhân vật một dòng (báo cáo lại thì cập nhật). Lưu `target = 'character'` (migration 0011),
`public_card_id`, lý do, ghi chú; không có tin nhắn hay story. Sự kiện `content_reported {target: character}` cũng không
gắn ai. Chủ máy thấy báo cáo trong cùng tab "Báo cáo" (dòng "Hồ sơ nhân vật") và bấm **"Ẩn nhân vật"**
(`POST /api/admin/cards/{id}/unpublish`): nhân vật về Riêng tư, biến khỏi Khám phá và hồ sơ công khai; người tạo vẫn
giữ và sửa được.

Quản trị viên (chủ máy): `GET /api/admin/reports?status=open|reviewed|dismissed` (mới nhất trước, tối đa 200) và
`PATCH /api/admin/reports/{id} {"status": ...}`. Mỗi dòng có: lý do, ghi chú, chế độ, ngôn ngữ, model, bản chụp (chỉ khi
được đồng ý), trạng thái, và nhân vật công khai liên quan (tên + người tạo, chỉ khi nhân vật đó vẫn đang công khai).
**Không có** người báo cáo, id story hay id tin nhắn: quản trị viên không lần ra được story riêng tư của ai.

Bảng `content_reports` (migration 0010, cột `target` ở 0011). Ghi chú do người báo cáo tự viết để gửi đi nên quản trị viên đọc được.

## 3. Điều khoản, Chính sách quyền riêng tư và lần đồng ý

- Văn bản: `docs/legal/terms.md`, `docs/legal/privacy.md` (tiếng Việt trước, bản tiếng Anh ở mục "English"). Email
  liên hệ trong file là chỗ trống **[ĐIỀN EMAIL LIÊN HỆ]** và **cố ý giữ nguyên**: backend điền liên hệ của đơn vị
  vận hành vào lúc phục vụ (`GET /api/legal/*`, `with_contact` trong `lyris/compliance/legal.py`) từ biến
  `LYRIS_CONTACT`, và bỏ luôn ghi chú "sẽ điền trước khi ra mắt". Hiện `scripts/dev.sh` và `scripts/serve.sh` đặt sẵn
  `LYRIS_CONTACT=lethuhang.cv@gmail.com`, nên người dùng trong app thấy email này (giống §5.2, dòng "Liên hệ hỗ trợ,
  đơn vị vận hành"). Giữ chỗ trống trong file để khi Apero (hay đơn vị vận hành khác) nhận sản phẩm, chỉ cần đổi
  `LYRIS_CONTACT`, không phải sửa văn bản. Test giữ hành vi này: `test_legal_files_state_the_current_version` (file
  còn chỗ trống), `test_contact_reaches_login_page_and_legal_texts` (có `LYRIS_CONTACT` thì văn bản trả về không còn
  chỗ trống và không còn ghi chú), `test_without_contact_the_placeholder_stays` (chưa đặt thì giữ nguyên). Người đọc
  file trên GitHub sẽ thấy chỗ trống: đó là chỗ điền lúc chạy, không phải văn bản chưa xong.
- **Phục vụ qua backend:** `GET /api/legal/{terms|privacy}` → `{doc, version, markdown}`; mở hoàn toàn (không cần
  đăng nhập, chạy cả khi chủ máy chưa thiết lập). Chọn cách này thay vì tài sản tĩnh của frontend vì: một nguồn duy
  nhất (file trong `docs/legal/`), phiên bản nằm cùng chỗ với nơi ghi lần đồng ý (`lyris/compliance/legal.py`
  `LEGAL_VERSION`), sửa văn bản không cần build lại frontend. Test kiểm cả hai file ghi đúng `LEGAL_VERSION`.
  Dòng đầu mỗi văn bản ghi "Phiên bản" và "Hiệu lực từ" (Version / Effective from), cả hai bằng `LEGAL_VERSION`
  (hiện `2026-11-16`); đổi `LEGAL_VERSION` thì sửa cả hai dòng này ở hai bản ngôn ngữ.
- **Lưu lần đồng ý:** `accounts.terms_accepted_at`, `accounts.privacy_version` (migration 0010).
- **Bắt buộc khi tạo tài khoản và thiết lập chủ máy:** body của `POST /api/auth/signup` và
  `POST /api/auth/setup-owner` có `accept_terms: true` (và tuỳ chọn `terms_version`). Thiếu/false: 400
  `code = terms_required`, không ghi gì (mã mời và mã thiết lập vẫn dùng được). Phiên bản cũ: 409 `terms_outdated`.
- **Tài khoản có từ trước** (gồm tài khoản chủ máy hiện tại): `GET /api/auth/me` trả `account.terms_required = true`
  và `legal_version`. Giao diện hỏi **một lần**; đồng ý bằng `POST /api/account/terms {"accept_terms": true,
  "version": "<legal_version>"}` (sai phiên bản: 409; false: 422). Tăng `LEGAL_VERSION` thì mọi người được hỏi lại.
  API không chặn tài khoản chưa đồng ý (giao diện chặn bằng màn đồng ý), để không khoá nhầm chủ máy khỏi máy của mình.
- `GET /api/account` có thêm `terms_required`, `terms_accepted_at`, `privacy_version`, `legal_version`.

## 4. Xoá tài khoản và xuất dữ liệu

`DELETE /api/account {"password": "..."}` (thành viên và chủ máy, chỉ tài khoản của chính mình):

- Cần mật khẩu hiện tại, cùng luật thử sai với đổi mật khẩu (5 lần / 15 phút theo tài khoản → 429). Sai: 400
  `code = bad_password`. Story đang sinh câu trả lời: 409.
- **Chủ máy còn tài khoản khác: 409** kèm lời giải thích. Lý do: chủ máy là người duy nhất tạo mã mời, đặt lại mật
  khẩu và mở khoá cho thành viên; xoá chủ máy khi còn thành viên sẽ để họ không còn ai quản lý (và DB chỉ có đúng một
  chủ máy). Thành viên tự xoá tài khoản của họ trước. Chủ máy là tài khoản cuối cùng: xoá được; Lyris tạo lại một
  chủ máy trống và in mã thiết lập mới ra Terminal, như máy vừa cài (`setup_required: true` trong kết quả).
- Xoá trong **một transaction** (`lyris/compliance/account_data.py`): story (tin nhắn, biến thể, đánh giá, lịch sử
  sửa, state, ký ức, job, lore đã mở theo CASCADE), mọi nhân vật của tài khoản (kể cả công khai và bản sao đang dùng,
  kèm sổ thế giới), persona, phiên, lần thử đăng nhập (theo @handle và theo khoá tài khoản), mã mời đã tạo, rồi dòng
  tài khoản. File ảnh (avatar, ảnh bìa, ảnh persona, ảnh nhân vật) xoá sau khi commit.
- Còn lại, không gắn với ai: sự kiện sử dụng (`account_id → NULL`, cả sự kiện lúc chưa đăng nhập trên các thiết bị
  của tài khoản; `anon_id` đổi thành một bí danh ngẫu nhiên mới và mỗi `session_id` thành một mã mới, vì PostHog đã nối
  `anon_id` cũ với tài khoản lúc đăng nhập; cookie `lyris_anon` của trình duyệt đang xoá bị xoá cùng response; sự kiện
  chưa gửi PostHog thì không gửi nữa), lý do
  của các báo cáo đã gửi (ghi chú, bản chụp, id story/tin nhắn bị xoá), và bản sao nhân vật công khai của người này
  mà **người khác** đã dùng để bắt đầu story (dữ liệu của họ; `origin_account_id → NULL`, không còn "bởi @handle").
- Sự kiện `account_deleted` ghi không gắn tài khoản, thiết bị hay lượt, chỉ lưu ở máy (bỏ qua nếu tài khoản đã tắt
  chia sẻ dữ liệu sử dụng).
- Nhật ký máy chủ (dòng "Tài khoản @handle đã tự xoá", các dòng đăng nhập có IP) không xoá được từ app: chúng tự hết
  hạn sau tối đa 30 ngày theo cấu hình journald ở docs/deploy.md §5.3; Chính sách §2, §6, §7 nói rõ điều này.
- Sự kiện đã gửi sang PostHog trước đó: xoá trên PostHog theo yêu cầu (thủ công, ghi trong Chính sách).
- Lưu ý: SQLite có thể cấp lại id số của tài khoản đã xoá cho tài khoản mới; không còn dòng nào trỏ tới id cũ
  (test quét mọi cột tài khoản), `uid` luôn mới.

`GET /api/account/export` → tệp `lyris-<handle>-<YYYYMMDD>.json` (`Content-Disposition: attachment`), ghi sự kiện
`data_exported`. Nội dung: hồ sơ (không hash mật khẩu), persona, nhân vật của mình kèm sổ thế giới, nhân vật đang
chơi bằng bản sao (chỉ phần công khai, như giao diện cho xem: không bí mật, không sổ thế giới của người tạo), story
kèm **mọi** tin nhắn (cả biến thể, đánh giá, ghi chú) và ký ức, báo cáo đã gửi, thiết bị đăng nhập, sự kiện sử dụng.
Ảnh ghi bằng tên file. Không có prompt snapshot (chứa phần riêng tư của nhân vật người khác).

## 5. Đối chiếu chính sách kênh phát hành

### 5.1 Kênh ra mắt: open web (PWA) trước

- **Lần đầu ra mắt trên web mở**: một tên miền HTTPS, người dùng mở trong trình duyệt hoặc "Thêm vào màn hình chính"
  (manifest `frontend/public/manifest.webmanifest`, `display: standalone`, icon). Cách chạy: docs/deploy.md.
- Vì sao web trước: không phải chờ duyệt cửa hàng; người dùng mục tiêu (độc giả truyện mạng) đến từ link trong nhóm
  Facebook, TikTok, Discord; AI chạy trên máy chủ nên điện thoại nào cũng dùng được.
- **Đăng ký bằng mã mời** (theo đợt): khớp sức chứa (~2 lượt sinh cùng lúc mỗi model, docs/deploy.md §9) và cho đội
  vận hành xem báo cáo, số liệu trước khi mở rộng.
- Bọc thành app Google Play / App Store (TWA, WebView) là **kế hoạch**; các dòng "Cửa hàng" ở §5.2 là việc phải làm
  thêm lúc đó.

### 5.2 Danh sách kiểm

Trạng thái: **Đã có** (có code và test), **Nhóm làm** (việc của nhóm trước khi ra mắt, không cần code),
**Kế hoạch** (chưa làm).

| Yêu cầu | Áp dụng cho | Lyris | Trạng thái |
|---|---|---|---|
| Chính sách quyền riêng tư công khai, đọc được không cần đăng nhập | Web, Google Play (User Data), App Store 5.1.1 | `#/privacy`, `GET /api/legal/privacy`, `docs/legal/privacy.md` (vi + en); liên kết ở trang đăng nhập, đăng ký và Tài khoản | Đã có |
| Điều khoản sử dụng, quy tắc nội dung | Web, cửa hàng | `#/terms`, `docs/legal/terms.md` §3 | Đã có |
| Đồng ý trước khi tạo tài khoản, lưu bằng chứng, hỏi lại khi văn bản đổi | Web; Nghị định 13 (§5.3) | Ô đồng ý bắt buộc, `accounts.terms_accepted_at`, `privacy_version`, màn đồng ý một lần (§3) | Đã có |
| Công khai nội dung do AI tạo; không giả làm người thật | Web, Google Play (AI-Generated Content), App Store | Điều khoản §2 "Nhân vật là AI, không phải người thật"; một dòng nhắc dưới "Bước vào câu chuyện" | Đã có |
| Ngăn AI tạo nội dung bị cấm (tình dục với trẻ vị thành niên, nội dung tình dục, bạo lực máu me, cổ vũ tự hại) | Google Play (AI-Generated Content, Inappropriate Content, Child Safety Standards), App Store 1.1 | Luật an toàn trong mọi prompt (§1); mặc định không có nội dung tình dục; nhân vật lảng đi trong vai | Đã có (luật trong prompt; chưa có bộ lọc đầu ra) |
| Báo cáo nội dung xúc phạm ngay trong app, không phải rời app | Google Play (AI-Generated Content, UGC), App Store 1.2 | "Báo cáo" trên mọi câu trả lời của nhân vật và "Báo cáo nhân vật" trên hồ sơ nhân vật công khai, 7 lý do gồm "Liên quan trẻ vị thành niên"; chủ máy xử lý ở tab "Báo cáo" (§2) | Đã có |
| Xử lý báo cáo kịp thời | App Store 1.2, Google Play | Tab "Báo cáo" (mở / đã xem / bỏ qua); quy trình: xem mỗi ngày, `minor_safety` trong 24 giờ (docs/deploy.md §11) | Đã có (công cụ) + Nhóm làm (trực) |
| Chặn người dùng lạm dụng; gỡ nội dung do người dùng đăng | App Store 1.2, Google Play (UGC) | Story luôn riêng tư (không ai thấy story của người khác). Nhân vật công khai: báo cáo từ hồ sơ; chủ máy "Ẩn nhân vật" (về Riêng tư) và tạm khoá được tài khoản của người tạo | Đã có |
| Xoá tài khoản ngay trong app, kèm dữ liệu | Google Play (Account deletion), App Store 5.1.1(v) | "Xoá tài khoản" trong Tài khoản (§4) | Đã có |
| Xoá tài khoản từ một đường link web (không cần cài app) | Google Play (Data deletion) | App chính là trang web: đăng nhập rồi "Xoá tài khoản"; hoặc gửi email liên hệ | Đã có khi chạy web; Cửa hàng: khai link trong Data safety |
| Xuất dữ liệu cá nhân | Nghị định 13 (quyền của chủ thể dữ liệu), thông lệ chung | "Tải dữ liệu của tôi" → JSON (§4) | Đã có |
| Thu thập tối thiểu; số liệu không chứa nội dung; tắt được | Google Play (User Data), App Store 5.1.1, 5.1.2 | docs/tracking-plan.md: không chữ, không IP; công tắc "Chia sẻ dữ liệu sử dụng ẩn danh" (tắt thì cả trình duyệt đó không bị ghi nữa); tôn trọng `Sec-GPC: 1` (không cả cookie); báo cáo và xoá tài khoản ghi không gắn ai; chưa đồng ý chính sách thì không gửi PostHog | Đã có |
| Không theo dõi chéo app, không quảng cáo, không bán dữ liệu | App Store 5.1.2 (ATT), Google Play | Không SDK quảng cáo, không cookie bên thứ ba; PostHog chỉ khi người vận hành bật, không gửi IP | Đã có |
| Kê khai cookie | Web; EU ePrivacy nếu phục vụ người dùng EU | Chính sách §5 kê đủ bốn cookie: `lyris_session` (đăng nhập), `lyris_device` (nhận ra thiết bị đã đăng nhập, chống khoá nhầm), `lyris_anon` (số liệu), `lyris_noshare` (trình duyệt đã tắt chia sẻ) và localStorage | Đã có. Nếu nhắm người dùng EU: cần hỏi đồng ý trước khi đặt `lyris_anon` lúc chưa đăng nhập (Kế hoạch) |
| HTTPS, cookie `Secure` | Web | Caddy + `LYRIS_COOKIE_SECURE=1` (docs/deploy.md §5) | Nhóm làm (khi dựng máy chủ) |
| Trẻ em, tuổi tối thiểu | COPPA (Mỹ, dưới 13), Google Play Families, App Store 1.3; Nghị định 13 (trẻ em dưới 16) | **16+**: Điều khoản §1 và Chính sách §8 ghi "dành cho người từ đủ 16 tuổi"; đồng ý Điều khoản lúc tạo tài khoản là xác nhận 16+ (tự xác nhận, không hỏi năm sinh); dưới 16 không được dùng, biết thì xoá tài khoản; không nhắm tới trẻ em; nội dung mặc định an toàn; cha mẹ yêu cầu xoá qua email | Đã có (văn bản). Ô đồng ý ghi rõ "đã đủ 16 tuổi": Kế hoạch (F48). Không đăng ký chương trình Families |
| Nội dung 18+ chỉ cho người đã xác nhận 18 tuổi | App Store 1.2.1(a), Google Play (Inappropriate Content) | Hiện không có nội dung 18+. Nút "Nội dung an toàn" bật sẵn cho mọi tài khoản; tắt nút cần tích "Tôi đã đủ 18 tuổi" (chỉ lưu thời điểm); bật lại thì lần sau phải xác nhận lại; người vận hành gỡ quyền được (§0.3, §6) | Kế hoạch (F48) |
| Xếp hạng tuổi của cửa hàng | Google Play (IARC), App Store | Khai đúng: chat AI, nội dung do người dùng tạo, chủ đề tình cảm, không nội dung tình dục. Với nội dung an toàn bật sẵn và không có nội dung 18+, cân nhắc **12+ hoặc 17+** của App Store (chat AI không lọc hết, nội dung người dùng tạo thường đẩy lên 17+); điều khoản vẫn là 16+ dù xếp hạng cửa hàng thấp hơn. Khi có chế độ 18+ (F48) phải trả lời lại bảng hỏi tuổi và xem lại xếp hạng (17+ / 18+, IARC 18) | Kế hoạch (khi bọc app) |
| Thanh toán trong app | Google Play Billing, App Store 3.1.1 | Chưa có thanh toán. Coin (kế hoạch) bán trong app cửa hàng phải qua hệ thống thanh toán của cửa hàng; trên web cần nhà cung cấp thanh toán hợp pháp tại Việt Nam, hoá đơn, chính sách hoàn tiền | Kế hoạch |
| Liên hệ hỗ trợ, đơn vị vận hành | Web, Google Play, App Store 1.5 | Đặt `LYRIS_CONTACT` (email hoặc `https://`): trang đăng nhập hiện "Chưa có mã mời? Xin mã mời" và "Quên mật khẩu? Nhờ người quản lý đặt lại", và backend điền vào chỗ **[ĐIỀN EMAIL LIÊN HỆ]** của `docs/legal/*.md` khi phục vụ. Chưa đặt: trang nói chung chung, văn bản còn chỗ trống | Đã đặt: `lethuhang.cv@gmail.com` (mặc định trong `scripts/dev.sh`, `scripts/serve.sh`; production đặt trong env, docs/deploy.md) |
| Nhật ký máy chủ (handle, IP) được kê khai và có hạn giữ | Nghị định 13 (thông báo, thời hạn lưu) | Chính sách §2, §6, §7 kê nhật ký máy chủ, giữ tối đa 30 ngày; docs/deploy.md §5.3 đặt journald `MaxRetentionSec=30day` | Đã có (văn bản + cấu hình mẫu) |

### 5.3 Dữ liệu cá nhân ở Việt Nam (Nghị định 13/2023/NĐ-CP), mức cơ bản

Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân là khung chính khi Lyris được thiết kế. Từ 01/01/2026 Luật Bảo vệ
dữ liệu cá nhân có hiệu lực; trước khi ra mắt chính thức, đơn vị phát hành cần người có chuyên môn pháp lý kiểm lại
theo văn bản đang có hiệu lực. Trang này chỉ đối chiếu những nguyên tắc chung:

| Nguyên tắc chung | Lyris làm gì |
|---|---|
| **Thông báo** cho người dùng dữ liệu nào được xử lý, để làm gì, ai xử lý, giữ bao lâu | Chính sách quyền riêng tư §2-6, đọc được trước khi tạo tài khoản |
| **Đồng ý** rõ ràng, tự nguyện, rút lại được | Ô đồng ý không đánh sẵn; số liệu tắt được bất cứ lúc nào; xoá tài khoản là rút đồng ý toàn bộ |
| **Quyền** được biết, truy cập, xoá, nhận lại dữ liệu | Xem trong app, "Tải dữ liệu của tôi", "Xoá tài khoản", email liên hệ cho yêu cầu khác |
| **Thu thập tối thiểu, đúng mục đích** | Không hỏi tên thật, ngày sinh, số điện thoại, email; số liệu không có chữ, không IP |
| **Dữ liệu nhạy cảm** | Lyris không hỏi. Story có thể chứa điều người dùng tự kể (tình cảm, sức khoẻ...): chỉ lưu trên máy chủ, không vào số liệu, không dùng để huấn luyện AI (Chính sách §1), xoá được |
| **Trẻ em** (dưới 16 tuổi: cần đồng ý của cha mẹ/người giám hộ) | Lyris không phục vụ người dưới 16: Điều khoản đặt tuổi tối thiểu 16, đồng ý Điều khoản là tự xác nhận 16+, biết tài khoản của người dưới 16 thì xoá. Không hỏi năm sinh (thu thập tối thiểu). Không có xác minh tuổi bằng giấy tờ: đây là tự xác nhận |
| **Bảo mật** | scrypt, phiên HttpOnly, giới hạn thử sai, tách dữ liệu theo tài khoản (test quét mọi route), HTTPS khi ra mắt |
| **Chuyển dữ liệu ra nước ngoài** | Mặc định không có. Bật PostHog (máy chủ Mỹ hoặc EU) là chuyển dữ liệu sử dụng (đã ẩn danh hoá một phần, không chữ, không IP) ra nước ngoài: đơn vị phát hành kiểm hồ sơ cần có trước khi bật |
| **Hồ sơ đánh giá tác động, thông báo khi có sự cố** | Việc của đơn vị phát hành (Apero sau khi nhận sản phẩm); docs này và docs/tracking-plan.md là đầu vào cho hồ sơ |

### 5.4 Đã làm, nhóm phải làm, kế hoạch

**Đã làm (có code và test):** luật an toàn trong prompt; báo cáo câu trả lời AI kèm đồng ý gửi bản chụp; báo cáo
nhân vật công khai và "Ẩn nhân vật" của chủ máy; Điều khoản,
Chính sách (vi + en) công khai; đồng ý có phiên bản; xoá tài khoản và xuất dữ liệu tự phục vụ; số liệu không chữ,
tắt được, GPC, giữ 180 ngày; trang "Báo cáo" và "Số liệu" của chủ máy; cookie kê khai.

**Nhóm phải làm trước khi ra mắt (không cần code):** email liên hệ đã có (`LYRIS_CONTACT=lethuhang.cv@gmail.com`, đặt sẵn
trong script chạy app; production đặt trong env), và nếu muốn ghi tên đơn vị vận hành vào `docs/legal/*.md` thì sửa thêm
`test_legal_files_state_the_current_version`; dựng HTTPS và `LYRIS_COOKIE_SECURE=1`; người
trực xem báo cáo mỗi ngày; nếu bật PostHog: chọn vùng (EU/US), bật "Discard client IP data", kiểm quy định chuyển dữ
liệu ra nước ngoài.

**Kế hoạch (Round 2 trở đi):**
- **Nút "Nội dung an toàn" và xác nhận 18+** (F48, §6): làm khi có nội dung 18+, chỉ nếu kênh phát hành cho phép.
- **Thanh toán coin:** cần nhà cung cấp thanh toán tuân thủ (ở Việt Nam: cổng thanh toán được cấp phép; trong app cửa
  hàng: Google Play Billing / Apple In-App Purchase), điều khoản bán hàng, hoàn tiền, hoá đơn, và xem lại Điều khoản
  (đổi `LEGAL_VERSION`). Kế hoạch coin chi tiết (chế độ thử chưa thu tiền, mục "Coin" trong Điều khoản, quảng cáo mẫu,
  không phần thưởng ngẫu nhiên): [coins.md §12](coins.md).
- Bộ lọc đầu ra tự động nếu `content_reported` cho thấy cần; chặn một người dùng cụ thể (hiện chỉ tạm khoá được cả
  tài khoản); khoá không cho đăng lại nhân vật đã bị ẩn (hiện người tạo bật Công khai lại được, và sẽ bị báo cáo lại).
- Nếu phục vụ người dùng EU: hỏi đồng ý cookie số liệu trước khi đăng nhập.
- Nếu Lyris mở thành mạng xã hội (bình luận, đăng bài công khai): xem lại nghĩa vụ của dịch vụ mạng xã hội theo quy
  định Việt Nam về dịch vụ internet (xác thực tài khoản, gỡ nội dung theo yêu cầu).
- Bọc app cửa hàng: Data safety (Google Play), App Privacy (App Store), xếp hạng tuổi, link xoá tài khoản.

## 6. Kế hoạch: nút "Nội dung an toàn" và chế độ 18+ (CHƯA LÀM, F48)

Không có trong code. Chủ sản phẩm chốt 2026-11-15 ([wiki/decisions/tuoi-16-va-noi-dung-an-toan.md](../wiki/decisions/tuoi-16-va-noi-dung-an-toan.md),
trang tính năng [F48](../wiki/features/F48-noi-dung-an-toan.md)):

1. **Nút "Nội dung an toàn"** theo từng tài khoản, **bật sẵn cho mọi người** (kể cả tài khoản có từ trước), bật lại
   được bất cứ lúc nào.
2. **Tắt nút = tự xác nhận 18+:** khi tắt, hiện ô tích "Tôi đã đủ 18 tuổi"; chưa tích thì không tắt được (API trả
   lỗi). Không hỏi năm sinh, không giấy tờ, không nhà cung cấp xác minh. Chỉ lưu thời điểm xác nhận
   (`adult_confirmed_at`); bật lại nút thì lần tắt sau phải tích lại.
3. **Bộ luật prompt riêng** cho tài khoản đã tắt nút, chỉ khi đã có nội dung 18+ (vẫn giữ tuyệt đối: không gì tình
   dục với người dưới 18, không nhân vật có tuổi/dáng vẻ trẻ em trong nội dung 18+). Khi nút bật: luôn `safety_rule()`.
4. Nhân vật công khai 18+ (nếu có) chỉ hiện cho tài khoản đã tắt nút.
5. **Người vận hành gỡ quyền được** khi bị lạm dụng hoặc xác nhận sai: đặt lại nút về bật và khoá không cho tắt.
6. Điều khoản §3 đã ghi sẵn ý này (16+, nút bật sẵn, xác nhận 18+). Khi thật sự mở nội dung 18+: đổi `LEGAL_VERSION`
   cho mọi người đồng ý lại; sự kiện số liệu chỉ dạng boolean (`safe_content_changed {on}`), không có chữ.
7. Kiểm lại chính sách từng kênh (nhiều kênh cấm hẳn nội dung người lớn do AI tạo) và **xếp hạng tuổi**: bản hiện
   tại (an toàn bật sẵn, không nội dung 18+) cân nhắc 12+ hoặc 17+ trên App Store; có chế độ 18+ thì phải xem lại
   (17+ / 18+, IARC 18), và trên một số kho có thể phải tắt hẳn chế độ này.

## 7. Hợp đồng cho frontend

| Màn | Gọi | Ghi chú câu chữ (tiếng Việt, ngắn) |
|---|---|---|
| Tạo tài khoản, thiết lập chủ máy | thêm `accept_terms: true`, `terms_version` vào body | Ô đánh dấu: "Tôi đồng ý với Điều khoản sử dụng và Chính sách quyền riêng tư" (hai liên kết mở trang pháp lý). Nút tạo tài khoản tắt khi chưa đánh dấu. Lỗi `terms_required` / `terms_outdated` hiện `detail`. |
| Đồng ý lại (một lần) | `GET /api/auth/me` → `account.terms_required`; `POST /api/account/terms` | Màn chặn sau đăng nhập, hai liên kết, nút "Đồng ý và tiếp tục". |
| Trang pháp lý | `GET /api/legal/terms`, `/api/legal/privacy` (không cần đăng nhập) | Hiện markdown; có thêm liên kết ở trang Đăng nhập và Tài khoản. |
| Báo cáo | `POST /api/messages/{id}/report` | Trên câu trả lời của nhân vật: "Báo cáo". Lý do: Tình dục · An toàn trẻ em · Bạo lực · Thù ghét · Tự làm hại · Quấy rối · Khác. Ô ghi chú (≤ 300). Công tắc mặc định tắt: "Gửi kèm câu trả lời này để người quản lý xem xét". Không gửi thêm sự kiện `content_reported` từ client. |
| Quản lý báo cáo (chủ máy) | `GET /api/admin/reports`, `PATCH /api/admin/reports/{id}` | Trong trang Quản lý tài khoản. |
| Tải dữ liệu | `GET /api/account/export` | "Tải dữ liệu của bạn". |
| Xoá tài khoản | `DELETE /api/account {password}` | Hộp xác nhận nhập mật khẩu, nói rõ không hoàn tác. Chủ máy còn thành viên: hiện `detail` (409). Xong: về trang đăng nhập (hoặc màn thiết lập khi `setup_required`). |
