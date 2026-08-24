/**
 * Per-run orchestrator: ties the registry, the sidecar index, the
 * Range-fetching stream reader, and state reconstruction together into
 * "give me the state as of tick T" and "tail this run for new records."
 *
 * Byte-offset acceleration (docs/frame-log-schema.md §6): `stateAt(t)`
 * finds the nearest keyframe <= t via the sidecar's `keyframe_offsets` and
 * Range-fetches starting there, rather than scanning from byte 0 of a
 * possibly-large log — the whole point of the sidecar index existing.
 */
import type { FrameRecord, KeyframeScheduleOverlay, RunRegistryEntry, SidecarIndexFile } from "./types";
import { fetchSidecarIndex, keyframeAtOrBefore, tickAtOrBefore } from "./sidecarIndex";
import { readByteRange, runStreamUrl, LiveTailPoller, type LiveTailListener } from "./streamReader";
import {
  emptySocialState,
  fromKeyframeState,
  parseScheduleRewrite,
  replayTo,
  type SocialState,
} from "./reconstruct";

/** Merge-order for records sharing a tick: events before trace, per schema §8's writer order; then seq. */
function compareRecords(a: FrameRecord, b: FrameRecord): number {
  if (a.tick !== b.tick) return a.tick - b.tick;
  if (a.stream !== b.stream) return a.stream === "events" ? -1 : 1;
  return a.seq - b.seq;
}

export class RunReader {
  private sidecar: SidecarIndexFile | undefined;
  private readonly eventsUrl: string;
  private readonly traceUrl: string;
  private readonly keyframeCache = new Map<number, SocialState>();
  /** Byte offset one past the last complete record this reader has seen on each stream, as of the last read. */
  private lastOffsets = { events: 0, trace: 0 };

  constructor(private readonly registryEntry: RunRegistryEntry) {
    this.eventsUrl = runStreamUrl(registryEntry.run_id, registryEntry.streams.events);
    this.traceUrl = runStreamUrl(registryEntry.run_id, registryEntry.streams.trace);
  }

  async loadSidecar(): Promise<void> {
    const result = await fetchSidecarIndex(this.registryEntry.run_id);
    this.sidecar = result.index;
  }

  private async keyframeStateAtOrBefore(t: number): Promise<SocialState> {
    if (this.sidecar === undefined) await this.loadSidecar();
    const kf = this.sidecar ? keyframeAtOrBefore(this.sidecar.streams.events, t) : null;
    // -1, not 0: "no keyframe exists" must not be confused with "a
    // keyframe at tick 0 already bakes in every tick-0 record" -- the
    // deltasBetween(afterTick, ...) filter below is `tick > afterTick`,
    // and tick 0 is a perfectly ordinary first tick to have records on.
    if (kf === null) return emptySocialState(-1);

    const cached = this.keyframeCache.get(kf.tick);
    if (cached !== undefined) return cached;

    // The keyframe is one record on the events stream; we don't know its
    // exact byte length ahead of time, so read from its offset to EOF and
    // take only the first parsed record (torn-tail-safe: readByteRange
    // already drops any incomplete trailing line).
    const { records } = await readByteRange(this.eventsUrl, kf.offset);
    const first = records[0];
    const state =
      first !== undefined && first.payload.record_type === "keyframe"
        ? fromKeyframeState(first.payload.state as never, kf.tick)
        : emptySocialState(kf.tick);
    this.keyframeCache.set(kf.tick, state);
    return state;
  }

  /** Every record with `afterTick < tick <= uptoTick`, merged across both streams, in replay order. */
  private async deltasBetween(afterTick: number, uptoTick: number): Promise<FrameRecord[]> {
    if (this.sidecar === undefined) await this.loadSidecar();
    const sidecar = this.sidecar;

    const startOffset = (streamKey: "events" | "trace"): number => {
      if (sidecar === undefined) return 0;
      const streamIndex = sidecar.streams[streamKey];
      const tick = tickAtOrBefore(streamIndex, afterTick);
      return tick === null ? 0 : streamIndex.tick_offsets[String(tick)]!;
    };

    const [eventsResult, traceResult] = await Promise.all([
      readByteRange(this.eventsUrl, startOffset("events")),
      readByteRange(this.traceUrl, startOffset("trace")),
    ]);

    // readByteRange always fetches from startOffset to the current EOF
    // (no `end` is passed) regardless of uptoTick -- uptoTick only filters
    // which parsed records are returned. So consumedThrough here is always
    // "as far as this reader has currently seen this stream," which is
    // exactly what a caller resuming LIVE tailing from this point needs
    // (see `stateAtLatestKnown`/`currentOffsets` below).
    this.lastOffsets = { events: eventsResult.consumedThrough, trace: traceResult.consumedThrough };

    const all = [...eventsResult.records, ...traceResult.records].filter(
      (r) => r.tick > afterTick && r.tick <= uptoTick && r.payload.record_type !== "keyframe",
    );
    all.sort(compareRecords);
    return all;
  }

  /**
   * Every `schedule_rewrite` event up to `uptoTick`, scanned from byte 0
   * of the events stream every time -- deliberately NOT keyframe-windowed
   * (lane 41's finding, reconstruct.ts's module header): a keyframe's own
   * `state.schedules[]` is the run's immutable BASE schedule, not a
   * rolled-up "overlays active as of this keyframe" snapshot, so an
   * overlay that started before a keyframe but whose `end_tick` reaches
   * past it would otherwise never be seen by a keyframe-relative delta
   * read. `chronicle/framelog.py`'s own reader has the identical shape
   * (`self.records(EVENTS_STREAM, upto_tick=tick)`, no keyframe floor,
   * every single `state_at` call) -- this mirrors that, not a regression
   * against the byte-offset acceleration this class otherwise relies on
   * for everything else (claims/beliefs/grudges/etc. via `deltasBetween`
   * stay keyframe-windowed; only this one record family needs the full
   * history, because it's the only one whose "currently active" answer
   * depends on total override rather than accumulation).
   */
  private async scheduleOverlaysUpTo(uptoTick: number): Promise<KeyframeScheduleOverlay[]> {
    const { records } = await readByteRange(this.eventsUrl, 0);
    const overlays: KeyframeScheduleOverlay[] = [];
    for (const record of records) {
      if (record.tick > uptoTick) continue;
      const overlay = parseScheduleRewrite(record.payload);
      if (overlay !== null) overlays.push(overlay);
    }
    return overlays;
  }

  /** State as of tick T: nearest keyframe <= T, replayed forward with every intervening delta. */
  async stateAt(t: number): Promise<SocialState> {
    const keyframeState = await this.keyframeStateAtOrBefore(t);
    const deltas = await this.deltasBetween(keyframeState.tick, t);
    const state = replayTo(keyframeState, deltas, t);
    state.scheduleOverlays = await this.scheduleOverlaysUpTo(t);
    return state;
  }

  /**
   * State as of the newest record currently in the log (no target tick
   * known in advance — used when docking to LIVE). Also leaves
   * `currentOffsets()` at EOF, so a caller can hand those straight to
   * `startLiveTail` and never re-see what it just read as "new."
   */
  async stateAtLatestKnown(): Promise<SocialState> {
    const unbounded = Number.MAX_SAFE_INTEGER;
    const keyframeState = await this.keyframeStateAtOrBefore(unbounded);
    const deltas = await this.deltasBetween(keyframeState.tick, unbounded);
    const latestTick = deltas.length > 0 ? deltas[deltas.length - 1]!.tick : Math.max(keyframeState.tick, 0);
    const state = replayTo(keyframeState, deltas, latestTick);
    state.scheduleOverlays = await this.scheduleOverlaysUpTo(latestTick);
    return state;
  }

  /** Byte offsets this reader has read through, as of its last `stateAt`/`stateAtLatestKnown` call. */
  currentOffsets(): { events: number; trace: number } {
    return { ...this.lastOffsets };
  }

  /**
   * One poller per stream, sharing the ~1s cadence ui-spec §1.3 names for
   * LIVE tailing. `fromByteOffsets` lets a caller that already read up to
   * some position (e.g. the historical view it was just docked at) resume
   * tailing from there instead of re-reading the whole file as "new."
   */
  startLiveTail(
    onRecords: LiveTailListener,
    intervalMs = 1000,
    fromByteOffsets: { events: number; trace: number } = { events: 0, trace: 0 },
  ): () => void {
    const eventsPoller = new LiveTailPoller(this.eventsUrl, fromByteOffsets.events, intervalMs);
    const tracePoller = new LiveTailPoller(this.traceUrl, fromByteOffsets.trace, intervalMs);
    const stopEvents = eventsPoller.start(onRecords);
    const stopTrace = tracePoller.start(onRecords);
    return () => {
      stopEvents();
      stopTrace();
    };
  }
}
