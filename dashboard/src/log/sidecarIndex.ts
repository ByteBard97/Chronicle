/**
 * The per-run sidecar index reader (docs/frame-log-schema.md §6):
 * `runs/<run_id>/index.json` — tick -> byte offset per stream, plus
 * keyframe offsets on the events stream. Pure acceleration (schema §1):
 * rebuildable by scanning both streams, so a missing or malformed sidecar
 * degrades to "read from byte 0 / no known keyframes" rather than an error
 * — slower, never wrong.
 */
import type { SidecarIndexFile, SidecarStreamIndex } from "./types";
import { fetchJson } from "./rangeFetch";

const EMPTY_STREAM_INDEX: SidecarStreamIndex = { tick_offsets: {}, keyframe_offsets: [] };

export type SidecarStatus = "missing" | "loaded" | "malformed";

export interface SidecarResult {
  status: SidecarStatus;
  index: SidecarIndexFile;
}

function isValidStreamIndex(candidate: unknown): candidate is SidecarStreamIndex {
  if (typeof candidate !== "object" || candidate === null) return false;
  const c = candidate as Record<string, unknown>;
  return typeof c.tick_offsets === "object" && c.tick_offsets !== null;
}

export async function fetchSidecarIndex(runId: string): Promise<SidecarResult> {
  const url = `/runs/${encodeURIComponent(runId)}/index.json`;
  const result = await fetchJson<unknown>(url);
  const fallback: SidecarIndexFile = {
    schema_version: 1,
    streams: { events: EMPTY_STREAM_INDEX, trace: EMPTY_STREAM_INDEX },
  };

  if (!result.ok) {
    return { status: result.status === 404 ? "missing" : "malformed", index: fallback };
  }

  const body = result.body as Partial<SidecarIndexFile> | null;
  if (typeof body !== "object" || body === null || typeof body.streams !== "object" || body.streams === null) {
    return { status: "malformed", index: fallback };
  }
  const streamsIn = body.streams as Record<string, unknown>;
  const events = isValidStreamIndex(streamsIn.events) ? streamsIn.events : EMPTY_STREAM_INDEX;
  const trace = isValidStreamIndex(streamsIn.trace) ? streamsIn.trace : EMPTY_STREAM_INDEX;

  return {
    status: "loaded",
    index: { schema_version: Number(body.schema_version) || 1, streams: { events, trace } },
  };
}

/** The largest recorded tick <= T with a known byte offset, or null if none is known that low. */
export function tickAtOrBefore(streamIndex: SidecarStreamIndex, t: number): number | null {
  let best: number | null = null;
  for (const key of Object.keys(streamIndex.tick_offsets)) {
    const tick = Number(key);
    if (Number.isFinite(tick) && tick <= t && (best === null || tick > best)) {
      best = tick;
    }
  }
  return best;
}

/** The latest keyframe at or before T, or null if none exists (must replay from the start). */
export function keyframeAtOrBefore(
  streamIndex: SidecarStreamIndex,
  t: number,
): { tick: number; offset: number } | null {
  const offsets = streamIndex.keyframe_offsets ?? [];
  let best: { tick: number; offset: number } | null = null;
  for (const kf of offsets) {
    if (kf.tick <= t && (best === null || kf.tick > best.tick)) {
      best = kf;
    }
  }
  return best;
}
