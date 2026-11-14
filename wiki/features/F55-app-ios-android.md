# F55 — App iOS và Android (Capacitor)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Máy chủ (sau khi nộp bài)
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Mọi màn hình hiện có, chạy trong app; mới: màn "Cập nhật Lyris" khi bản app quá cũ.

## Là gì

Bọc chính frontend React hiện có thành app iOS và Android bằng Capacitor, thêm plugin native (Keychain/Keystore, StoreKit 2,
Play Billing, push, haptics, chia sẻ, Sign in with Apple). Assets đóng gói trong app, API ở `https://api.lyris.example`.
AI chọn theo yêu cầu "tối ưu và mượt mà nhất" của PO ([quyết định](../decisions/app-di-dong-capacitor.md)).
Thiết kế: [docs/server.md §16](../../docs/server.md).

## Hoạt động thế nào

- `VITE_API_BASE` đặt địa chỉ API cho bản app; web giữ `/api` tương đối.
- Trên app: token `Bearer` lưu ở Keychain/Keystore (không `localStorage`), không cookie (F51).
- `CapacitorHttp` tắt để `fetch` stream được SSE; app quay lại foreground thì nối lại câu trả lời đang sinh.
- Story dài chỉ dựng những tin đang thấy (ảo hoá danh sách) để cuộn đạt 60 khung hình/giây.
- Universal Links / App Links cho `https://lyris.example/c/{card_uid}` → hồ sơ nhân vật.
- Push (tuỳ chọn, hỏi quyền khi có lý do): "{Tên} đã trả lời" khi app ở nền; không gửi nội dung story.
- `GET /api/app/config` trả `min_supported_version`; app cũ hơn thì chỉ hiện màn "Cập nhật Lyris".
- Không tải JavaScript từ xa để đổi tính năng (App Store 2.5.2).
- "Quảng cáo mẫu" (F45) không hiện trong app và bản host (`LYRIS_SAMPLE_ADS=off`): nội dung giữ chỗ dễ bị từ chối theo
  App Store 2.1 (tạm chọn, câu hỏi cho PO).
- Đo hiệu năng bằng mốc `performance.mark` / Event Timing gửi lên RUM, cộng Xcode Instruments và Android `FrameMetrics`
  (xem [quyết định](../decisions/app-di-dong-capacitor.md)).

## Done when

- [ ] Unit: `apiBase()` trả `/api` khi build web và `https://api.lyris.example/api` khi `VITE_API_BASE` được đặt (`frontend/src/lib/platform.test.ts`).
- [ ] Unit: khi `isNativePlatform()` đúng, `request()` gửi `Authorization: Bearer …` và `X-Lyris: 1`, không dùng `credentials: "include"`; trên web giữ cookie như cũ (`frontend/src/api/nativeAuth.test.ts`).
- [ ] Unit: `resumeReply(replyId, lastEventId)` gửi header `Last-Event-ID` và không lặp lại delta đã hiện (`frontend/src/lib/replyResume.test.ts`).
- [ ] Unit: `needsUpdate("1.2.0", { min_supported_version: "1.3.0" })` trả `true`, `needsUpdate("1.3.0", …)` trả `false` (`frontend/src/lib/appVersion.test.ts`).
- [ ] Bot: với `window.Capacitor` giả (`isNativePlatform() = true`) ở 390px: đăng nhập, gửi một lượt ở `#/chat/{id}`, câu trả lời hiện; request có header `Authorization`, không có cookie `lyris_session`.
- [ ] Bot: `min_supported_version` lớn hơn bản app → chỉ hiện màn có nút `aria-label="Cập nhật Lyris"`, không vào được `#/`.
- [ ] Bot: story 300 tin ở `#/chat/{id}` chỉ có ≤ 60 phần tử tin nhắn trong DOM khi cuộn từ đầu tới cuối.
- [ ] Unit: `perfMarks` ghi mốc `sse-delta-received` và `sse-delta-painted` cho mỗi delta, tính được khoảng cách và gửi một sự kiện RUM gom theo lượt (không có chữ chat trong sự kiện) (`frontend/src/lib/perfMarks.test.ts`).
- [ ] Bot: với `LYRIS_SAMPLE_ADS=off`, `#/missions` không có dòng "Xem quảng cáo" (chỉ còn "Trò chuyện với 3 nhân vật khác nhau" và "Gửi 20 lượt"), không mở được hộp "Quảng cáo mẫu", và `POST /api/coins/ads/start` trả 404.

## Tests

- `frontend/src/lib/platform.test.ts`
- `frontend/src/api/nativeAuth.test.ts`
- `frontend/src/lib/replyResume.test.ts`
- `frontend/src/lib/appVersion.test.ts`
- `frontend/src/lib/perfMarks.test.ts`
- bot: vỏ app native đăng nhập bằng token
- bot: buộc cập nhật app cũ
- bot: story dài chỉ dựng tin đang thấy
- bot: bản host không có quảng cáo mẫu

## Ngoài Done when

Không chặn ✅ (đo trên thiết bị thật mỗi bản phát hành; trượt 2 bản liên tiếp sau khi tối ưu thì mở lại quyết định, hướng
đổi là chuyển **cả app** sang React Native/Expo): iPhone 11 và Samsung Galaxy A15 bản 4 GB RAM (Android 14, ghi phiên bản
WebView) — mở nguội tới hub p75 ≤ 2,0 s; cuộn story 300 tin ≥ 95 % khung hình ≤ 16,7 ms; delta SSE tới lúc chữ hiện
p95 ≤ 50 ms; gõ phím tới lúc chữ hiện p95 ≤ 50 ms; bộ nhớ ≤ 300 MB; phiên không crash ≥ 99,5 %. Cách đo từng chỉ số ở
[docs/server.md §16.2](../../docs/server.md).
Duyệt App Store/Google Play: các mục ở [docs/server.md §16.4](../../docs/server.md) (4.2, 1.2, 1.2.1(a), 2.1, 3.1.1,
4.8, 5.1.1(v)); chạy thử kín Google Play 14 ngày; ra mắt chỉ ở kho Việt Nam (tạm chọn).

## Liên quan

- **Tài liệu:** [docs/server.md §10, §16](../../docs/server.md), [docs/compliance.md §5](../../docs/compliance.md), [DESIGN.md](../../DESIGN.md)
- **Code hiện tại:** [`frontend/src/api/client.ts`](../../frontend/src/api/client.ts), [`frontend/src/lib/sse.ts`](../../frontend/src/lib/sse.ts), [`frontend/src/lib/router.ts`](../../frontend/src/lib/router.ts), [`frontend/public/manifest.webmanifest`](../../frontend/public/manifest.webmanifest)
- **Tính năng:** [F37](F37-iphone-tailscale.md) (cách cũ: PWA qua Tailscale), [F51](F51-redis-api-khong-trang-thai.md), [F56](F56-iap-google-play.md), [F61](F61-dang-ky-cong-khai.md)
- **Quyết định:** [app-di-dong-capacitor](../decisions/app-di-dong-capacitor.md), [phien-token-cho-app](../decisions/phien-token-cho-app.md)
