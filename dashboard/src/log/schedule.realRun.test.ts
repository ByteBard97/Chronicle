import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { applyTraceRecord, effectiveScheduleAt, emptySocialState, fromKeyframeState, replayTo } from "./reconstruct";
import type { FrameRecord, KeyframeScheduleBlock, KeyframeScheduleOverlay, KeyframeState } from "./types";

/**
 * Lane 41: `reconstruct.ts`'s schedule/overlay extension (base schedule
 * hydration, `schedule_rewrite` replay, `effectiveScheduleAt`'s total-
 * override + automatic-restoration semantics), unit-tested in isolation
 * plus against the real `runs/mourning-demo-01` demo run -- same
 * "runs/ is gitignored, skip rather than fail when absent" precedent as
 * `layer4.realRun.test.ts`.
 */

function block(npcId: string, locationId: string, startTick: number, endTick: number): KeyframeScheduleBlock {
  return { npc_id: npcId, location_id: locationId, start_tick: startTick, end_tick: endTick };
}

function overlay(
  npcId: string,
  locationId: string,
  startTick: number,
  endTick: number,
  seq: number,
): KeyframeScheduleOverlay {
  return {
    npc_id: npcId,
    location_id: locationId,
    start_tick: startTick,
    end_tick: endTick,
    cause: "mourning",
    rule: "schedule-write-back",
    trigger_event_key: { save_uuid: "s", generation: 0, seq },
  };
}

function scheduleRewritePayload(o: KeyframeScheduleOverlay): Record<string, unknown> {
  return {
    event_type: "schedule_rewrite",
    gamets: o.start_tick,
    wall_ts: 0,
    origin: null,
    npc_id: o.npc_id,
    location_id: o.location_id,
    start_tick: o.start_tick,
    end_tick: o.end_tick,
    cause: o.cause,
    rule: o.rule,
    trigger_event_key: o.trigger_event_key,
  };
}

describe("effectiveScheduleAt (mirrors chronicle/schedule.py::effective_schedule_at)", () => {
  const base = [block("sven", "sven_house", 0, 144), block("erik", "sven_house", 0, 144)];

  it("with no overlays, returns base blocks covering tick unmodified", () => {
    expect(effectiveScheduleAt(base, [], 10)).toEqual(base);
  });

  it("total override: an NPC with an active overlay shows ONLY the overlay block, not base+overlay", () => {
    const ov = overlay("sven", "temple_of_kynareth", 0, 72, 1);
    const result = effectiveScheduleAt(base, [ov], 10);
    expect(result).toContainEqual(ov);
    expect(result.find((b) => b.npc_id === "sven" && b.location_id === "sven_house")).toBeUndefined();
    // erik, uninvolved, keeps his base block.
    expect(result).toContainEqual(base[1]);
    expect(result).toHaveLength(2);
  });

  it("automatic restoration exactly at end_tick: active at end_tick-1, base again at end_tick", () => {
    const ov = overlay("sven", "temple_of_kynareth", 0, 72, 1);
    const stillActive = effectiveScheduleAt(base, [ov], 71);
    expect(stillActive).toContainEqual(ov);

    const restored = effectiveScheduleAt(base, [ov], 72);
    expect(restored).toContainEqual(base[0]);
    expect(restored.find((b) => "cause" in b)).toBeUndefined();
  });

  it("active exactly at start_tick (half-open lower bound)", () => {
    const ov = overlay("sven", "temple_of_kynareth", 10, 20, 1);
    expect(effectiveScheduleAt(base, [ov], 9)).not.toContainEqual(ov);
    expect(effectiveScheduleAt(base, [ov], 10)).toContainEqual(ov);
  });

  it("multiple overlays for different NPCs at the same tick both apply, no dedupe/last-wins", () => {
    const ovSven = overlay("sven", "temple_of_kynareth", 0, 72, 1);
    const ovErik = overlay("erik", "temple_of_kynareth", 0, 72, 2);
    const result = effectiveScheduleAt(base, [ovSven, ovErik], 10);
    expect(result).toEqual(expect.arrayContaining([ovSven, ovErik]));
    expect(result).toHaveLength(2);
  });

  it("older-run tolerance: no overlays and no base schedule produces an empty result without throwing", () => {
    expect(effectiveScheduleAt([], [], 10)).toEqual([]);
  });
});

describe("SocialState schedule hydration + replay", () => {
  it("fromKeyframeState hydrates baseSchedule from a keyframe's schedules[]", () => {
    const state: KeyframeState = { schedules: [block("sven", "sven_house", 0, 144)] };
    const social = fromKeyframeState(state, 0);
    expect(social.baseSchedule).toEqual([block("sven", "sven_house", 0, 144)]);
    expect(social.scheduleOverlays).toEqual([]);
  });

  it("older-run tolerance: a keyframe with no schedules field produces an empty baseSchedule without throwing", () => {
    const social = fromKeyframeState({}, 0);
    expect(social.baseSchedule).toEqual([]);
  });

  it("fromKeyframeState skips a malformed schedules[] entry instead of throwing", () => {
    const state: KeyframeState = {
      schedules: [
        { npc_id: "sven", location_id: "x", start_tick: 5, end_tick: 5 }, // end_tick <= start_tick: invalid
        { npc_id: "erik", location_id: "y" }, // missing ticks
        block("hilde", "z", 0, 10),
      ],
    };
    const social = fromKeyframeState(state, 0);
    expect(social.baseSchedule).toEqual([block("hilde", "z", 0, 10)]);
  });

  it("applyTraceRecord folds a schedule_rewrite event into scheduleOverlays", () => {
    const social = emptySocialState(0);
    const ov = overlay("sven", "temple_of_kynareth", 0, 72, 1);
    applyTraceRecord(social, scheduleRewritePayload(ov), 0);
    expect(social.scheduleOverlays).toEqual([ov]);
  });

  it("a schedule_rewrite record does not fall through to the record_type switch (no record_type present)", () => {
    const social = emptySocialState(0);
    const ov = overlay("sven", "temple_of_kynareth", 0, 72, 1);
    expect(() => applyTraceRecord(social, scheduleRewritePayload(ov), 0)).not.toThrow();
    expect(social.claims.size).toBe(0);
    expect(social.beliefs.size).toBe(0);
  });

  it("older-run tolerance: a run with zero schedule_rewrite events leaves scheduleOverlays empty", () => {
    const social = emptySocialState(0);
    applyTraceRecord(social, { record_type: "threshold_crossed" }, 0);
    expect(social.scheduleOverlays).toEqual([]);
  });

  it("replayTo carries baseSchedule forward and folds in schedule_rewrite deltas", () => {
    const start = fromKeyframeState({ schedules: [block("sven", "sven_house", 0, 144)] }, 0);
    const ov = overlay("sven", "temple_of_kynareth", 0, 72, 1);
    const record: FrameRecord = {
      schema_version: 1,
      seed_id: "s",
      save_uuid: "s",
      generation: 0,
      tick: 0,
      stream: "events",
      seq: 1,
      payload: scheduleRewritePayload(ov),
    };
    const replayed = replayTo(start, [record], 10);
    expect(replayed.baseSchedule).toEqual([block("sven", "sven_house", 0, 144)]);
    expect(replayed.scheduleOverlays).toEqual([ov]);
    expect(effectiveScheduleAt(replayed.baseSchedule, replayed.scheduleOverlays, 10)).toEqual([ov]);
  });
});

const RUN_DIR = path.resolve(process.cwd(), "../runs/mourning-demo-01");
const EVENTS_FILE = path.join(RUN_DIR, "events.jsonl");
const runExists = existsSync(EVENTS_FILE);

function loadEvents(): FrameRecord[] {
  return readFileSync(EVENTS_FILE, "utf8")
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as FrameRecord);
}

describe.skipIf(!runExists)("schedule reconstruction against runs/mourning-demo-01 (real demo run)", () => {
  const allEvents = runExists ? loadEvents() : [];
  const keyframes = allEvents.filter((r) => r.payload.record_type === "keyframe");
  const rewrites = allEvents.filter((r) => r.payload.event_type === "schedule_rewrite");

  it("has real schedule_rewrite events for sven and erik, 0->72, cause mourning", () => {
    expect(rewrites.length).toBeGreaterThanOrEqual(2);
    const sven = rewrites.find((r) => r.payload.npc_id === "sven");
    expect(sven).toMatchObject({
      payload: { location_id: "temple_of_kynareth", start_tick: 0, end_tick: 72, cause: "mourning", rule: "schedule-write-back" },
    });
  });

  it("keyframe hydration recovers the immutable base schedule (7 entries, includes sven at sven_house)", () => {
    const kf = keyframes[0]!;
    const state = fromKeyframeState(kf.payload.state as never, kf.tick);
    expect(state.baseSchedule.length).toBeGreaterThan(0);
    expect(state.baseSchedule).toContainEqual(expect.objectContaining({ npc_id: "sven", location_id: "sven_house" }));
  });

  it("delta replay from tick 0 through the tick-0 rewrites shows sven overridden to temple_of_kynareth at tick 10 (before end_tick)", () => {
    const kf = keyframes[0]!;
    const base = fromKeyframeState(kf.payload.state as never, kf.tick).baseSchedule;
    const deltas = allEvents.filter((r) => r.payload.record_type !== "keyframe" && r.tick <= 10);
    const replayed = replayTo(emptySocialState(-1), deltas, 10);
    const effective = effectiveScheduleAt(base, replayed.scheduleOverlays, 10);
    const sven = effective.find((b) => b.npc_id === "sven");
    expect(sven?.location_id).toBe("temple_of_kynareth");
  });

  it("restoration: at tick 100 (past end_tick 72), sven is back on his base schedule", () => {
    const kf = keyframes[0]!;
    const base = fromKeyframeState(kf.payload.state as never, kf.tick).baseSchedule;
    const deltas = allEvents.filter((r) => r.payload.record_type !== "keyframe" && r.tick <= 100);
    const replayed = replayTo(emptySocialState(-1), deltas, 100);
    const effective = effectiveScheduleAt(base, replayed.scheduleOverlays, 100);
    const sven = effective.find((b) => b.npc_id === "sven");
    expect(sven?.location_id).toBe("sven_house");
    expect(sven && "cause" in sven).toBe(false);
  });
});
