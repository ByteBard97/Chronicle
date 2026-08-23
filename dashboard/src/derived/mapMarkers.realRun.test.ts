import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import mapJson from "../../map/whiterun_map.json";
import { claimStageBreakdown, deriveMapMarkers, enumerateCast, firstClaimId, locationAt } from "./mapMarkers";
import { emptySocialState, fromKeyframeState, replayTo, type SocialState } from "../log/reconstruct";
import type { FrameRecord } from "../log/types";

/**
 * Verifies the cast enumeration and jarl_balgruuf's rendering against the
 * real demo run (see mapMarkers.ts's header for the coordinator-corrected
 * cast recipe this test exists to pin). `runs/` is gitignored — degrades to
 * skipped rather than failing when absent, matching
 * `feedReader.realRun.test.ts`'s precedent.
 */
const RUN_DIR = path.resolve(process.cwd(), "../runs/whiterun-jarl-01");
const EVENTS_FILE = path.join(RUN_DIR, "events.jsonl");
const TRACE_FILE = path.join(RUN_DIR, "trace.jsonl");
const runExists = existsSync(EVENTS_FILE) && existsSync(TRACE_FILE);

function loadRecords(file: string): FrameRecord[] {
  return readFileSync(file, "utf8")
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as FrameRecord);
}

/** Reconstruct SocialState at T from the whole log (no sidecar acceleration needed for a test-sized run). */
function stateAt(allEvents: FrameRecord[], allTrace: FrameRecord[], atTick: number): SocialState {
  const keyframes = allEvents.filter((r) => r.payload.record_type === "keyframe" && r.tick <= atTick);
  const latestKeyframe = keyframes.length > 0 ? keyframes[keyframes.length - 1]! : null;
  const start = latestKeyframe ? fromKeyframeState(latestKeyframe.payload.state as never, latestKeyframe.tick) : emptySocialState(-1);
  const deltas = [...allEvents, ...allTrace].filter((r) => r.payload.record_type !== "keyframe" && r.tick > start.tick && r.tick <= atTick);
  return replayTo(start, deltas, atTick);
}

describe.skipIf(!runExists)("map markers against runs/whiterun-jarl-01 (real demo run)", () => {
  const allEvents = runExists ? loadRecords(EVENTS_FILE) : [];
  const allTrace = runExists ? loadRecords(TRACE_FILE) : [];
  const nonKeyframeEvents = allEvents.filter((r) => r.payload.record_type !== "keyframe");

  it("enumerates exactly the run's 6 NPCs, including jarl_balgruuf", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const cast = enumerateCast(state, allTrace, nonKeyframeEvents);
    expect(new Set(cast)).toEqual(
      new Set(["hulda", "irileth", "proventus", "whiterun_guard_1", "ysolda", "jarl_balgruuf"]),
    );
  });

  it("the literal packet recipe (belief holders + trace participants only) drops jarl_balgruuf -- the bug this lane corrects", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const literalCast = new Set<string>();
    for (const b of state.beliefs.values()) literalCast.add(b.holder_id);
    for (const r of allTrace) {
      const p = r.payload;
      for (const key of ["teller_id", "hearer_id", "npc_a", "npc_b"]) {
        if (typeof p[key] === "string") literalCast.add(p[key] as string);
      }
    }
    expect(literalCast.has("jarl_balgruuf")).toBe(false);
    expect(literalCast.size).toBe(5);
  });

  it("the active claim is claim-jarl-death (the run's first claim)", () => {
    const state = stateAt(allEvents, allTrace, 0);
    expect(firstClaimId(state)).toBe("claim-jarl-death");
  });

  it("jarl_balgruuf renders as unheard at dragonsreach at t=0 and t=200", () => {
    for (const atTick of [0, 200]) {
      const state = stateAt(allEvents, allTrace, atTick);
      const markers = deriveMapMarkers({
        state,
        traceRecords: allTrace,
        eventRecords: nonKeyframeEvents,
        mapJson,
        claimId: "claim-jarl-death",
        atTick,
        isSelected: () => false,
      });
      const jarl = markers.find((m) => m.id === "jarl_balgruuf");
      expect(jarl, `jarl_balgruuf marker missing at t=${atTick}`).toBeDefined();
      expect(jarl!.stage).toBe("unheard");
      expect(jarl!.glyph).toBeNull();
      // The literal location, not just a pixel-position proxy.
      expect(locationAt("jarl_balgruuf", allTrace, nonKeyframeEvents, atTick)).toBe("dragonsreach");
      // dragonsreach's baked pixel [2970, 285] -> a percent position near the map's top-right (see fixtures/whiterunMock.ts CROP/toPct).
      expect(jarl!.left).toBeGreaterThan(80);
      expect(jarl!.top).toBeLessThan(10);
    }
  });

  it("all 6 NPCs are placeable (a resolvable location) by t=200", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const markers = deriveMapMarkers({
      state,
      traceRecords: allTrace,
      eventRecords: nonKeyframeEvents,
      mapJson,
      claimId: "claim-jarl-death",
      atTick: 200,
      isSelected: () => false,
    });
    expect(markers).toHaveLength(6);
  });

  it("at t=0, only the NPCs already observed (or dead) by then are placeable: irileth, proventus, jarl_balgruuf", () => {
    const state = stateAt(allEvents, allTrace, 0);
    const markers = deriveMapMarkers({
      state,
      traceRecords: allTrace,
      eventRecords: nonKeyframeEvents,
      mapJson,
      claimId: "claim-jarl-death",
      atTick: 0,
      isSelected: () => false,
    });
    expect(new Set(markers.map((m) => m.id))).toEqual(new Set(["irileth", "proventus", "jarl_balgruuf"]));
  });

  it("stage/glyph rollup at t=200 matches the hand-traced belief/rumor timeline", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const markers = deriveMapMarkers({
      state,
      traceRecords: allTrace,
      eventRecords: nonKeyframeEvents,
      mapJson,
      claimId: "claim-jarl-death",
      atTick: 200,
      isSelected: () => false,
    });
    const byId = Object.fromEntries(markers.map((m) => [m.id, m]));
    expect(byId.irileth).toMatchObject({ stage: "repeated", glyph: null });
    expect(byId.proventus).toMatchObject({ stage: "repeated", glyph: "S" });
    expect(byId.whiterun_guard_1).toMatchObject({ stage: "heard", glyph: null });
    expect(byId.ysolda).toMatchObject({ stage: "heard", glyph: "N" });
  });

  it("coverage/counts reconcile to the full 6-NPC cast at t=200", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const cast = enumerateCast(state, allTrace, nonKeyframeEvents);
    const { counts, coverage } = claimStageBreakdown(state, cast, "claim-jarl-death", 200);
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    expect(total).toBe(6);
    expect(coverage.startsWith("coverage ")).toBe(true);
  });
});
