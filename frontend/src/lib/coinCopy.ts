// Every word of the member's coin screens (F42, docs/coins.md §10.5): header chip, "Ví coin", the
// out-of-coins block of the composers, the account sheet row, the daily gift notice, and the first
// lines of "Nạp coin" / "Nhiệm vụ". One module so coins.test.ts can check that none of it says
// "chủ máy", "token", "credits", "model" or "Ollama" (members see "người quản lý"). The owner-only
// "#/admin" words are not here.

export const PRICE_PER_REPLY = 6;

export const COIN_COPY = {
  unit: "coin",
  chipLabel: (n: string) => `Coin: ${n}. Mở ví coin`,
  walletTitle: "Ví coin",
  walletBack: "Về Tương tác",
  balanceCaption: "Số dư",
  pricePerReply: "Mỗi câu trả lời của nhân vật tốn 6 coin.",
  walletOut: "Bạn đã hết coin. Nạp coin hoặc làm nhiệm vụ để trò chuyện tiếp.",
  topUp: "Nạp coin",
  missions: "Nhiệm vụ",
  history: "Lịch sử",
  historyEmpty: "Chưa có gì trong lịch sử.",
  more: "Xem thêm",
  yesterday: "Hôm qua",
  loadError: "Chưa tải được ví coin.",
  retry: "Thử lại",
  dailyGift: (n: number) => `+${n} coin cho hôm nay`,
  outTitle: "Bạn đã hết coin",
  outText: "Mỗi câu trả lời cần 6 coin.",
  regenerateLock: "Cần 6 coin để tạo lại.",
  sendLock: "Cần 6 coin để gửi.",
  accountRow: "Coin",
  openWallet: "Mở ví coin",
  ownerNote: "Tài khoản quản lý không tốn coin.",
  groupedReplies: (k: number, name: string) => `${k} câu trả lời của ${name}`,
  replyOf: (name: string) => `Câu trả lời của ${name}`,
  someone: "nhân vật",
  topUpTitle: "Nạp coin",
  topUpBack: "Về Ví coin",
  topUpTestMode: "Chế độ thử: Lyris chưa bán coin. Nhập mã nạp người quản lý tặng bạn.",
  // F43 "Nạp coin" (docs/coins.md §10.5)
  codeLabel: "Mã nạp",
  codePlaceholder: "Nhập mã",
  redeem: "Dùng mã",
  redeemed: (n: string) => `Đã nạp ${n} coin.`,
  codeInvalid: "Mã nạp không đúng hoặc đã hết hạn.",
  codeRateLimited: "Bạn đã thử sai nhiều lần. Hãy đợi một lúc rồi thử lại.",
  packsHeading: "Giá dự kiến",
  packPrice: "Giá dự kiến",
  packBonus: (k: string) => `Tặng thêm ${k}`,
  packDialogTitle: (coins: string, price: string) => `Gói ${coins} · Giá dự kiến ${price}`,
  packDialogText:
    "Giá dự kiến khi Lyris ra mắt. Ở chế độ thử chưa bán coin; người quản lý có thể tặng bạn mã nạp để thử.",
  close: "Đóng",
  packsError: "Chưa tải được bảng giá.",
  ownerTopUpLink: "Về Quản lý tài khoản",
  // F45 "Nhiệm vụ hôm nay" and the "Quảng cáo mẫu" dialog (docs/coins.md §6, §10.5)
  missionsTitle: "Nhiệm vụ hôm nay",
  missionsBack: "Về Ví coin",
  missionsEarned: (x: number) => `Đã nhận ${x}/30 coin hôm nay`,
  missionsFull: "Đã nhận đủ 30 coin hôm nay. Quay lại sau 0:00 nhé.",
  missionsReset: "Làm mới lúc 0:00",
  missionsMeter: "Coin từ nhiệm vụ hôm nay",
  missionAd: "Xem quảng cáo",
  missionCharacters: "Trò chuyện với 3 nhân vật khác nhau",
  missionTurns: "Gửi 20 lượt",
  turnsNote: "Không tính 'Tạo lại câu trả lời'.",
  rewardEach: (n: number) => `+${n} coin mỗi lần`,
  reward: (n: number) => `+${n} coin`,
  watch: "Xem",
  claim: "Nhận",
  claimed: "Đã nhận",
  adsDone: "Đã xem đủ",
  adLimit: "Hôm nay bạn đã xem đủ 3 quảng cáo.",
  missionsError: "Chưa tải được nhiệm vụ.",
  ownerMissions: "Tài khoản quản lý không tốn coin nên không có nhiệm vụ.",
  gained: (n: number) => `+${n} coin`,
  adTitle: "Quảng cáo mẫu",
  adHonest: "Đây là quảng cáo mẫu của Lyris, chưa phải quảng cáo thật.",
  adLeft: (s: number) => `Còn ${s} giây`,
  adReady: "Đã xem xong. Bấm để nhận coin.",
  adClaim: "Nhận 5 coin",
  adClaimed: "Đã nhận 5 coin.",
  adNotFinished: "Quảng cáo chưa xem xong.",
  adExpired: "Lượt xem này đã hết hạn. Hãy xem lại.",
  adStarting: "Đang mở quảng cáo",
  adPromoName: "Hạ Vy",
  adPromoNarration: "Cô khẽ cười, xoay ly trà trong tay.",
  adPromoLine: "Hôm nay cậu đến muộn đấy.",
  adPromoThought: "Mình đã đợi cả buổi chiều, nhưng không cần nói ra.",
  adPromoTitle: "Đọc suy nghĩ của nhân vật",
  adPromoText: "Mỗi nhân vật trong Lyris có suy nghĩ riêng. Trong story, bạn có thể xem điều họ nghĩ mà không nói ra.",
  // F44 (làm lại): players and "Nhân vật hot" rank of a saved public character in the Studio editor (docs/coins.md §5.7)
  creatorPlayers: (n: string) => `${n} người chơi`,
  creatorRank: (r: string) => `Hạng ${r} Nhân vật hot`,
  creatorUnranked: "Chưa có trên bảng Nhân vật hot",
  creatorNextReward: (tier: string, c: string) => `Bậc thưởng tiếp theo: top ${tier} (+${c} coin)`,
  creatorNextTier: (tier: string) => `Bậc tiếp theo: top ${tier}`,
  creatorDone: "Đã nhận đủ thưởng xếp hạng",
  creatorTierRule: (tier: string, k: string) =>
    `Thưởng top ${tier} chỉ có khi bảng có nhân vật của ít nhất ${tier} người tạo khác nhau (hiện có ${k}).`,
  creatorWaiting: (w: string) => `Thưởng đang chờ: +${w} coin (tối đa 600 coin mỗi 7 ngày)`,
  creatorHint:
    "Người chơi là tài khoản khác đã trò chuyện với nhân vật này ít nhất 3 câu trả lời, ở 2 ngày khác nhau. Bảng xếp hạng cập nhật mỗi giờ.",
} as const;

/** Every plain string of COIN_COPY, and the templates filled with a sample (for the word check). */
export function allCoinStrings(): string[] {
  return Object.values(COIN_COPY).map((v) => {
    if (typeof v === "string") return v;
    if (typeof v === "number") return String(v);
    return (v as (...a: unknown[]) => string)(2, "Hạ Vy");
  });
}
