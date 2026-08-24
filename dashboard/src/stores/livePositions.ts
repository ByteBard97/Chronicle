import { defineStore } from "pinia";
import type { LivePositionSnapshot } from "../derived/livePositions";

/**
 * Polls ChronicleBridge's listener snapshot (served by
 * vite-plugins/serveLive.ts at /live/whiterun-positions.json) on a plain
 * interval -- not RunReader's byte-offset tailing, since this file isn't
 * an append-only frame log, just a rolling "latest snapshot" the listener
 * overwrites in place (adapters/skyrim/listener/listener.py).
 *
 * Never throws: a 404 (listener never started, or hasn't POSTed yet) or a
 * network error just leaves `snapshot` at its previous value (or null on
 * the very first attempt) -- there is no game/listener running in most
 * dev/CI contexts, and that must render as "no live markers," not an
 * error state.
 */
export const useLivePositionsStore = defineStore("livePositions", {
  state: () => ({
    snapshot: null as LivePositionSnapshot | null,
    enabled: false,
    intervalId: null as ReturnType<typeof setInterval> | null,
  }),
  actions: {
    async poll() {
      try {
        const res = await fetch("/live/whiterun-positions.json", { cache: "no-store" });
        if (!res.ok) return;
        this.snapshot = (await res.json()) as LivePositionSnapshot;
      } catch {
        // Listener unreachable -- leave the last-known snapshot in place.
      }
    },
    start(intervalMs = 1000) {
      if (this.intervalId !== null) return;
      this.enabled = true;
      void this.poll();
      this.intervalId = setInterval(() => void this.poll(), intervalMs);
    },
    stop() {
      this.enabled = false;
      if (this.intervalId !== null) {
        clearInterval(this.intervalId);
        this.intervalId = null;
      }
    },
  },
});
