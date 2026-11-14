// Pure logic of "Xem trước prompt" (Studio): message labels.

/**
 * Label of message `i` of `count`. Phase 4: block D (triggered world entries) sits at the head of the
 * last user message, before the player's turn; `hasWorld` = the preview's estimate has a D block.
 */
export function roleLabel(i: number, count: number, role: string, hasWorld = false): string {
  if (i === 0 && role === "system") return "System · khối A + B + C";
  if (i === count - 1 && role === "user") return hasWorld ? "Khối D + lượt người chơi + khối F" : "Lượt người chơi + khối F";
  if (role === "user") return "Người chơi";
  if (role === "assistant") return "Nhân vật";
  return role;
}

/** The estimate has a D block (an entry was triggered by the sample history). */
export function hasWorldBlock(estimate: Record<string, number> | null | undefined): boolean {
  return (estimate?.D ?? 0) > 0;
}

/** Note under the estimate: what the sample player turn is there for. */
export function sampleTurnNote(hasWorld: boolean): string {
  return hasWorld
    ? "Có một lượt mẫu của người chơi để thấy khối D và khối F. Không gửi gì cho model."
    : "Có một lượt mẫu của người chơi để thấy khối F. Không gửi gì cho model.";
}
