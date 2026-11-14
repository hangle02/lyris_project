// Pure wording of the machine status (header pill and the "Persona & Máy chủ" modal). Tested in status.test.ts.
import type { HealthLevel } from "../../hooks/useHealth.ts";
import type { SystemInfo } from "../../types.ts";

export type MachineTone = "checking" | "ok" | "power" | "warn" | "down";

export interface MachineStatus {
  tone: MachineTone;
  /** Header pill, two or three words. */
  short: string;
  /** Badge in the modal. */
  long: string;
}

type Power = Pick<SystemInfo, "on_battery" | "low_power_mode"> | null | undefined;

/**
 * Status of the local Mac from /api/health (Ollama and the chat model) and /api/system (power).
 * Power only matters while Ollama answers: a dead connection is the news.
 */
export function machineStatus(level: HealthLevel, power: Power): MachineStatus {
  switch (level) {
    case "checking":
      return { tone: "checking", short: "Đang kiểm tra", long: "Đang kiểm tra kết nối" };
    case "down":
      return { tone: "down", short: "Mất kết nối", long: "Không kết nối được Ollama" };
    case "warn":
      return { tone: "warn", short: "Thiếu model", long: "Ollama chạy nhưng thiếu model chat" };
    case "ok":
      if (power?.on_battery) return { tone: "power", short: "Đang chạy pin", long: "Đang chạy pin, sẽ chậm hơn" };
      if (power?.low_power_mode) {
        return { tone: "power", short: "Tiết kiệm pin", long: "Đang bật tiết kiệm pin, sẽ chậm hơn" };
      }
      return { tone: "ok", short: "M2 sẵn sàng", long: "Hoạt động êm ái" };
  }
}

/** "9.4 GB / 24 GB"; null when either number is unknown. */
export function memoryText(used: number | null | undefined, total: number | null | undefined): string | null {
  if (typeof used !== "number" || typeof total !== "number" || !Number.isFinite(used) || !Number.isFinite(total) || total <= 0) {
    return null;
  }
  return `${formatGb(used)} / ${formatGb(total)}`;
}

/** "9.4 GB", "24 GB" (one decimal, none for whole numbers; a decimal point, as macOS prints memory). */
export function formatGb(gb: number): string {
  const rounded = Math.round(gb * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1)} GB`;
}

/** "Bật" / "Tắt" / null (unknown) for a boolean setting. */
export function onOff(v: boolean | null | undefined): string | null {
  if (v === true) return "Bật";
  if (v === false) return "Tắt";
  return null;
}

export interface MemorySearchRow {
  /** Value of the "Ký ức" row. */
  value: string;
  /** Terminal command that turns on search by meaning; null when it is already on or cannot help. */
  pull: string | null;
}

/** "Ký ức" row of the machine block (phase3.md §8): keyword or meaning search, plus the pull hint. */
export function memorySearchRow(
  info: Pick<SystemInfo, "memory_search" | "embed_model" | "ollama_reachable">,
): MemorySearchRow {
  const model = info.embed_model?.trim() || null;
  if (info.memory_search === "hybrid") return { value: model ? `Tìm theo nghĩa, ${model}` : "Tìm theo nghĩa", pull: null };
  return { value: "Tìm theo từ khoá", pull: model && info.ollama_reachable ? `ollama pull ${model}` : null };
}

/**
 * The machine in plain words for the main Tài khoản sheet (Phase 3b): only when something is
 * wrong, without "Ollama" or "model" (the details live under Nâng cao).
 */
export function plainMachineLine(level: HealthLevel): string | null {
  if (level === "down") return "Lyris chưa kết nối được phần trả lời trên máy này, nên nhân vật tạm thời chưa trả lời được.";
  if (level === "warn") return "Máy chưa sẵn sàng để trả lời. Mở mục Nâng cao bên dưới để xem chi tiết.";
  return null;
}
