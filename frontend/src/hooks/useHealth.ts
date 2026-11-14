import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage, errorTechnical, isAbortError } from "../api/client";
import { plainMessage } from "../lib/text";
import type { HealthResponse, SystemInfo } from "../types";

export type HealthLevel = "checking" | "ok" | "warn" | "down";

export interface HealthStatus {
  level: HealthLevel;
  /** Plain words for the player (no "Ollama", no model names). */
  label: string;
  /** What actually happened, for a "Chi tiết" disclosure; null when all is well. */
  technical: string | null;
}

const POLL_MS = 15_000;

function hasModel(models: string[], wanted: string): boolean {
  if (models.includes(wanted)) return true;
  // Ollama lists "name:latest" for untagged names.
  return !wanted.includes(":") && models.includes(`${wanted}:latest`);
}

export function describeHealth(h: HealthResponse | null, err: string | null): HealthStatus {
  if (err) return { level: "down", label: "Không kết nối được Lyris. Hãy kiểm tra mạng rồi thử lại sau giây lát.", technical: err };
  if (!h) return { level: "checking", label: "Đang kiểm tra…", technical: null };
  if (!h.ollama.reachable) {
    return {
      level: "down",
      label: "Lyris chưa kết nối được phần trả lời trên máy, nên nhân vật tạm thời chưa trả lời được.",
      technical: h.ollama.error ? plainMessage(h.ollama.error) : "Ollama không chạy. Hãy mở app Ollama.",
    };
  }
  // Phase 4b: a member gets no model names (chat_model ""); the machine is then ready when it answers.
  if (h.chat_model && !hasModel(h.ollama.models, h.chat_model)) {
    return {
      level: "warn",
      label: "Máy chưa sẵn sàng để trả lời. Xem mục Nâng cao trong Tài khoản.",
      technical: `Ollama đang chạy nhưng chưa có model ${h.chat_model} (ollama pull ${h.chat_model}).`,
    };
  }
  return { level: "ok", label: "Sẵn sàng", technical: null };
}

/** Calls `tick` now, every `ms` while the tab is visible, and when the tab becomes visible again. */
function usePolling(tick: () => void, ms: number | null): void {
  useEffect(() => {
    if (ms === null) return;
    tick();
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") tick();
    }, ms);
    const onVis = () => {
      if (document.visibilityState === "visible") tick();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [tick, ms]);
}

/** Polls GET /api/health; refreshes immediately when the tab becomes visible again. */
export function useHealth(): HealthStatus & { refresh: () => void } {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(() => {
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => ctrl.abort(), 8000);
    api
      .health(ctrl.signal)
      .then((h) => {
        setHealth(h);
        setErr(null);
      })
      .catch((e: unknown) => {
        setErr(ctrl.signal.aborted ? "Hết thời gian chờ (/api/health)." : errorTechnical(e) ?? errorMessage(e));
      })
      .finally(() => window.clearTimeout(timer));
  }, []);

  usePolling(refresh, POLL_MS);

  return { ...describeHealth(health, err), refresh };
}

export interface SystemInfoState {
  /** Last good answer (kept while a refresh is running or after a failed refresh). */
  info: SystemInfo | null;
  /** Error of the last request, null when it succeeded. */
  error: string | null;
  /** Epoch ms of the last good answer. */
  updatedAt: number | null;
  refresh: () => void;
}

/**
 * Polls GET /api/system every `intervalMs` while the tab is visible (null = stopped, e.g. while a
 * modal is closed). The backend caches it for 5 seconds and never fails on a missing sensor.
 */
export function useSystemInfo(intervalMs: number | null): SystemInfoState {
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const inflight = useRef<AbortController | null>(null);

  const refresh = useCallback(() => {
    if (inflight.current) return;
    const ctrl = new AbortController();
    inflight.current = ctrl;
    const timer = window.setTimeout(() => ctrl.abort(), 10_000);
    api
      .getSystem(ctrl.signal)
      .then((s) => {
        setInfo(s);
        setError(null);
        setUpdatedAt(Date.now());
      })
      .catch((e: unknown) => {
        setError(isAbortError(e) ? "Máy chủ không trả lời kịp." : errorMessage(e));
      })
      .finally(() => {
        window.clearTimeout(timer);
        if (inflight.current === ctrl) inflight.current = null;
      });
  }, []);

  useEffect(
    () => () => {
      inflight.current?.abort();
      inflight.current = null;
    },
    [],
  );

  usePolling(refresh, intervalMs);

  return { info, error, updatedAt, refresh };
}
