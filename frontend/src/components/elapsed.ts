import { useEffect, useState } from "react";

/** Seconds since `startedAt`, refreshed every second. */
export function useElapsed(startedAt: number): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);
  return Math.max(0, Math.floor((now - startedAt) / 1000));
}

export function formatElapsed(sec: number): string {
  if (sec < 60) return `${sec} giây`;
  const m = Math.floor(sec / 60);
  const r = sec % 60;
  return r ? `${m} phút ${r} giây` : `${m} phút`;
}
