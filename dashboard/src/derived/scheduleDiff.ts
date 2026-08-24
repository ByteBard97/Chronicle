/**
 * Schedule diff (lane 41, ui-spec §3.8): per-NPC before/after schedule
 * lanes at the playhead's tick, inserted blocks highlighted, overlaid-away
 * base spans marked, each inserted block carrying the causal link
 * (`trigger_event_key`, `rule`) the spec names ("causing rule and event
 * linked"). Lives in the inspector's Schedule tab and as the standalone
 * `/scheddiff` multi-NPC comparison -- both hosts call this same module,
 * per the packet's "two hosts, one component" pin (this pure module is
 * the shared computation both `ScheduleLanes.vue`-based hosts render).
 *
 * Semantics (chronicle/schedule.py::effective_schedule_at, mirrored
 * exactly by `log/reconstruct.ts`'s `effectiveScheduleAt` -- this module
 * calls that ONE function rather than re-deriving presence itself, per
 * the packet's "do NOT invent a second presence computation in the view
 * layer"): total override, not merge -- an NPC with an active overlay at
 * tick T shows ONLY the overlay block; their base blocks return
 * automatically once `tick >= overlay.end_tick`, no separate "restore"
 * record involved.
 *
 * Overlay input source (see `log/reconstruct.ts`'s header FINDING): this
 * module deliberately does NOT read `SocialState.scheduleOverlays` as its
 * only overlay source. `RunReader.deltasBetween` windows the events
 * stream from the nearest keyframe's tick, so `socialState.scheduleOverlays`
 * under-populates for any T that falls after a keyframe but still inside
 * an overlay recorded before that keyframe (confirmed against
 * `runs/mourning-demo-01`: tick-0 `schedule_rewrite`s, end_tick 72, first
 * keyframe at tick 23 -- `stateAt(t)` for `t` in `[23, 72)` never replays
 * the tick-0 records). `stores/mapData.ts`'s `eventRecords` is loaded in
 * full from tick 0 regardless of keyframe placement (same reason
 * `DiffScreen.vue`/`RuleLogScreen.vue` read `eventRecords`/`traceRecords`
 * directly instead of `socialState`), so `computeScheduleDiff` takes raw
 * event records and extracts every `schedule_rewrite` from them via
 * `log/reconstruct.ts`'s exported `parseScheduleRewrite` -- one shared
 * parser, not a second one invented here. This is still "the one place
 * presence is computed" (`effectiveScheduleAt`); only the overlay *input*
 * comes from the more complete stream.
 */
import type { FrameRecord, KeyframeScheduleBlock, KeyframeScheduleOverlay } from "../log/types";
import { effectiveScheduleAt, parseScheduleRewrite } from "../log/reconstruct";

/**
 * A parsed overlay plus the `schedule_rewrite` record's own envelope
 * `tick` -- distinct from `start_tick`/`end_tick` (the overlay's effective
 * window) and from `trigger_event_key` (the canonical upstream event this
 * rewrite is causally downstream of, which carries no `tick` field of its
 * own, schema §2). `recordTick` is what a "jump to the event that did
 * this" deep link needs (mirrors `DiffRow`'s `event.tick`, lane 30).
 */
export interface ExtractedOverlay extends KeyframeScheduleOverlay {
  record_tick: number;
}

/** Every well-formed `schedule_rewrite` overlay found in `eventRecords`, in stream order. */
export function extractOverlays(eventRecords: FrameRecord[]): ExtractedOverlay[] {
  const overlays: ExtractedOverlay[] = [];
  for (const record of eventRecords) {
    const overlay = parseScheduleRewrite(record.payload);
    if (overlay !== null) overlays.push({ ...overlay, record_tick: record.tick });
  }
  return overlays;
}

export interface ScheduleDiffBlock {
  npcId: string;
  locationId: string;
  startTick: number;
  endTick: number;
}

/** An inserted (overlay) block, carrying the causal link ui-spec §3.8 names. */
export interface ScheduleDiffOverlayBlock extends ScheduleDiffBlock {
  cause: string;
  rule: string;
  triggerEventKey: { save_uuid: string; generation: number; seq: number };
  /** The `schedule_rewrite` record's own tick -- the "event" half of "causing rule and event linked" (feed deep link). */
  recordTick: number;
}

export interface NpcScheduleDiff {
  npcId: string;
  /** This NPC's base blocks covering `tick` -- the "before" lane, always the immutable base schedule. */
  before: ScheduleDiffBlock[];
  /** The effective blocks at `tick` -- the "after" lane: overlay(s) if active, else the same as `before`. */
  after: (ScheduleDiffBlock | ScheduleDiffOverlayBlock)[];
  /** Overlay blocks active at `tick` (a subset of `after`) -- render these highlighted as inserted. */
  inserted: ScheduleDiffOverlayBlock[];
  /** Base blocks overridden away at `tick` (present in `before`, absent from `after`) -- render these highlighted as removed. */
  removed: ScheduleDiffBlock[];
  /** True while any overlay is active for this NPC at `tick`. */
  overridden: boolean;
}

function toDiffBlock(b: KeyframeScheduleBlock): ScheduleDiffBlock {
  return { npcId: b.npc_id, locationId: b.location_id, startTick: b.start_tick, endTick: b.end_tick };
}

function toDiffOverlayBlock(o: ExtractedOverlay): ScheduleDiffOverlayBlock {
  return {
    ...toDiffBlock(o),
    cause: o.cause,
    rule: o.rule,
    triggerEventKey: { ...o.trigger_event_key },
    recordTick: o.record_tick,
  };
}

/**
 * Per-NPC before/after schedule lanes at `tick`, from the run's immutable
 * `baseSchedule` (a keyframe's `state.schedules[]`, via
 * `log/reconstruct.ts`'s `fromKeyframeState`) and the run's full
 * `eventRecords` (from which every `schedule_rewrite` overlay is
 * extracted -- see this module's header). `npcIds` defaults to the union
 * of every NPC named in either input; pass an explicit list to restrict
 * the standalone multi-NPC view's comparison (e.g. a filter bar
 * selection).
 */
export function computeScheduleDiff(
  baseSchedule: KeyframeScheduleBlock[],
  eventRecords: FrameRecord[],
  tick: number,
  npcIds?: string[],
): NpcScheduleDiff[] {
  const overlays = extractOverlays(eventRecords);
  const ids =
    npcIds ??
    [...new Set([...baseSchedule.map((b) => b.npc_id), ...overlays.map((o) => o.npc_id)])].sort();

  return ids.map((npcId) => {
    const npcBase = baseSchedule.filter((b) => b.npc_id === npcId);
    const npcOverlays = overlays.filter((o) => o.npc_id === npcId);

    const effective = effectiveScheduleAt(npcBase, npcOverlays, tick);
    // effectiveScheduleAt is the ONE presence computation (its return items
    // are reference-equal to the ExtractedOverlay objects passed in, just
    // typed generically by that shared function's signature) -- this cast
    // recovers `record_tick` for the deep link, it does not recompute
    // which overlays are active.
    const activeOverlays = effective.filter((b): b is KeyframeScheduleOverlay => "cause" in b) as ExtractedOverlay[];
    const overridden = activeOverlays.length > 0;

    const before = npcBase.filter((b) => b.start_tick <= tick && tick < b.end_tick).map(toDiffBlock);
    const inserted = activeOverlays.map(toDiffOverlayBlock);
    const removed = overridden ? before : [];
    const after: (ScheduleDiffBlock | ScheduleDiffOverlayBlock)[] = overridden ? inserted : before;

    return { npcId, before, after, inserted, removed, overridden };
  });
}

export interface ScheduleDiffFilters {
  npc?: string;
}

export function filterScheduleDiffs(diffs: NpcScheduleDiff[], filters: ScheduleDiffFilters): NpcScheduleDiff[] {
  return diffs.filter((d) => !filters.npc || d.npcId === filters.npc);
}
