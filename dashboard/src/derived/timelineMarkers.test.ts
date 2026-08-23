import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import type { FrameRecord } from "../log/types";
import {
  MARKER_TYPE_REGISTRY,
  computeDayTicks,
  computeHeatStripe,
  computeMaxTick,
  deriveTimelineMarkers,
  groupCoincidentMarkers,
  tickToPercent,
  type TimelineMarker,
} from "./timelineMarkers";

function rec(overrides: Partial<FrameRecord> & { payload: FrameRecord["payload"] }): FrameRecord {
  return {
    schema_version: 1,
    seed_id: "s",
    save_uuid: "u",
    generation: 0,
    tick: 0,
    stream: "trace",
    seq: 0,
    ...overrides,
  };
}

describe("tickToPercent", () => {
  it("maps tick 0 to 0% and maxTick to 100%", () => {
    expect(tickToPercent(0, 200)).toBe(0);
    expect(tickToPercent(200, 200)).toBe(100);
    expect(tickToPercent(100, 200)).toBe(50);
  });

  it("returns 0 when maxTick is 0 or negative (no span to position against)", () => {
    expect(tickToPercent(5, 0)).toBe(0);
    expect(tickToPercent(5, -1)).toBe(0);
  });
});

describe("computeDayTicks", () => {
  it("returns one tick per full 24-tick day (ADR-0010), none for a partial trailing day", () => {
    expect(computeDayTicks(50)).toEqual([
      { n: 1, pos: tickToPercent(24, 50) },
      { n: 2, pos: tickToPercent(48, 50) },
    ]);
  });

  it("returns an empty array when there is no span", () => {
    expect(computeDayTicks(0)).toEqual([]);
  });
});

describe("MARKER_TYPE_REGISTRY", () => {
  it("names all 8 taxonomy types exactly once, with role_vacancy/carrier_arrival marked as having no producer", () => {
    const types = MARKER_TYPE_REGISTRY.map((m) => m.type);
    expect(new Set(types).size).toBe(types.length);
    expect(types).toEqual([
      "claim_born",
      "mutation",
      "supersession",
      "grudge_formed",
      "threshold_crossed",
      "role_vacancy",
      "carrier_arrival",
      "events",
    ]);
    const noProducer = MARKER_TYPE_REGISTRY.filter((m) => !m.hasProducer).map((m) => m.type);
    expect(new Set(noProducer)).toEqual(new Set(["role_vacancy", "carrier_arrival"]));
  });
});

describe("deriveTimelineMarkers -- synthetic records for every type", () => {
  const traceRecords: FrameRecord[] = [
    rec({ tick: 10, payload: { record_type: "belief_formed", claim_id: "claim-a", holder_id: "npc-1" } }),
    // A second believer of the same claim must NOT produce a second claim_born marker.
    rec({ tick: 40, payload: { record_type: "belief_formed", claim_id: "claim-a", holder_id: "npc-2" } }),
    rec({ tick: 20, payload: { record_type: "belief_formed", claim_id: "claim-b", holder_id: "npc-3" } }),
    rec({ tick: 15, payload: { record_type: "mutation_applied", claim_id: "claim-a", slot: "cause" } }),
    rec({ tick: 25, payload: { record_type: "supersession", claim_id: "claim-a" } }),
    rec({ tick: 30, payload: { record_type: "grudge_formed", holder_id: "npc-1", target_id: "npc-2" } }),
    rec({ tick: 35, payload: { record_type: "threshold_crossed", rule: "unrest" } }),
  ];
  const eventRecords: FrameRecord[] = [
    rec({ tick: 5, stream: "events", payload: { event_type: "npc_died", npc_id: "npc-9" } }),
    rec({ tick: 6, stream: "events", payload: { event_type: "crime_witnessed", crime_type: "murder", witness_id: "npc-1" } }),
  ];
  const maxTick = computeMaxTick(traceRecords, eventRecords);
  const markers = deriveTimelineMarkers(traceRecords, eventRecords, maxTick);

  it("produces exactly one claim_born marker per claim, at the first belief_formed tick", () => {
    const claimBorn = markers.filter((m) => m.type === "claim_born");
    expect(claimBorn).toHaveLength(2);
    expect(claimBorn.find((m) => m.label.includes("claim-a"))?.tick).toBe(10);
    expect(claimBorn.find((m) => m.label.includes("claim-b"))?.tick).toBe(20);
  });

  it("produces one marker for every other producing type", () => {
    const byType = (t: TimelineMarker["type"]) => markers.filter((m) => m.type === t);
    expect(byType("mutation")).toHaveLength(1);
    expect(byType("supersession")).toHaveLength(1);
    expect(byType("grudge_formed")).toHaveLength(1);
    expect(byType("threshold_crossed")).toHaveLength(1);
    expect(byType("events")).toHaveLength(2);
    // No producer in schema v1 -- never emitted, never errors.
    expect(byType("role_vacancy")).toHaveLength(0);
    expect(byType("carrier_arrival")).toHaveLength(0);
  });

  it("sorts markers by tick ascending", () => {
    const ticks = markers.map((m) => m.tick);
    expect(ticks).toEqual([...ticks].sort((a, b) => a - b));
  });

  it("positions every marker within [0, 100]", () => {
    for (const m of markers) {
      expect(m.pos).toBeGreaterThanOrEqual(0);
      expect(m.pos).toBeLessThanOrEqual(100);
    }
  });

  it("tolerates empty input without error", () => {
    expect(deriveTimelineMarkers([], [], 0)).toEqual([]);
  });
});

describe("groupCoincidentMarkers", () => {
  it("leaves markers at distinct positions untouched", () => {
    const markers: TimelineMarker[] = [
      { tick: 0, type: "events", label: "a", pos: 0 },
      { tick: 50, type: "mutation", label: "b", pos: 25 },
    ];
    expect(groupCoincidentMarkers(markers)).toEqual(markers);
  });

  it("collapses same-position markers into one, combining labels and keeping the first's type", () => {
    const markers: TimelineMarker[] = [
      { tick: 0, type: "events", label: "death: jarl_balgruuf", pos: 0 },
      { tick: 0, type: "events", label: "crime witnessed: murder (proventus)", pos: 0 },
    ];
    const result = groupCoincidentMarkers(markers);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      tick: 0,
      type: "events",
      label: "death: jarl_balgruuf · crime witnessed: murder (proventus)",
      pos: 0,
    });
  });

  it("groups by position across mixed distinct and coincident markers, sorted by tick", () => {
    const markers: TimelineMarker[] = [
      { tick: 50, type: "mutation", label: "solo", pos: 25 },
      { tick: 0, type: "events", label: "first", pos: 0 },
      { tick: 0, type: "claim_born", label: "second", pos: 0 },
    ];
    const result = groupCoincidentMarkers(markers);
    expect(result).toEqual([
      { tick: 0, type: "events", label: "first · second", pos: 0 },
      { tick: 50, type: "mutation", label: "solo", pos: 25 },
    ]);
  });
});

describe("computeHeatStripe", () => {
  const sparseMarkers: TimelineMarker[] = Array.from({ length: 3 }, (_, i) => ({
    tick: i,
    type: "events" as const,
    label: `m${i}`,
    pos: i * 10,
  }));

  it("stays sparse (individual markers) when markers-per-pixel does not exceed 1", () => {
    const result = computeHeatStripe(sparseMarkers, 100);
    expect(result.dense).toBe(false);
    if (!result.dense) expect(result.markers).toEqual(sparseMarkers);
  });

  it("stays sparse when the bar has no measured width yet", () => {
    const result = computeHeatStripe(sparseMarkers, 0);
    expect(result.dense).toBe(false);
  });

  it("buckets into a density stripe when markers-per-pixel exceeds 1", () => {
    // 50 markers spread over a 10px bar: 5 markers/pixel > 1 -- dense.
    const denseMarkers: TimelineMarker[] = Array.from({ length: 50 }, (_, i) => ({
      tick: i,
      type: "events" as const,
      label: `m${i}`,
      pos: (i / 50) * 100,
    }));
    const result = computeHeatStripe(denseMarkers, 10);
    expect(result.dense).toBe(true);
    if (result.dense) {
      const total = result.buckets.reduce((sum, b) => sum + b.count, 0);
      expect(total).toBe(50);
      expect(result.buckets.length).toBeLessThanOrEqual(10);
      for (const b of result.buckets) {
        expect(b.pos).toBeGreaterThanOrEqual(0);
        expect(b.pos).toBeLessThanOrEqual(100);
      }
    }
  });

  it("is deterministic: same input always produces the same buckets", () => {
    const denseMarkers: TimelineMarker[] = Array.from({ length: 20 }, (_, i) => ({
      tick: i,
      type: "events" as const,
      label: `m${i}`,
      pos: (i / 20) * 100,
    }));
    expect(computeHeatStripe(denseMarkers, 5)).toEqual(computeHeatStripe(denseMarkers, 5));
  });
});

/**
 * Against the real demo run (`runs/whiterun-jarl-01`): the coordinator's
 * verified record counts are `belief_formed` (1), `npc_died` (1),
 * `crime_witnessed` (1), and zero for mutation_applied/supersession/
 * grudge_formed/threshold_crossed. `runs/` is gitignored -- degrades to
 * skipped rather than failing when absent, matching
 * `feedReader.realRun.test.ts` / `mapMarkers.realRun.test.ts`'s precedent.
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

describe.skipIf(!runExists)("deriveTimelineMarkers against runs/whiterun-jarl-01 (real demo run)", () => {
  const allEvents = runExists ? loadRecords(EVENTS_FILE) : [];
  const allTrace = runExists ? loadRecords(TRACE_FILE) : [];
  const nonKeyframeEvents = allEvents.filter((r) => r.payload.record_type !== "keyframe");
  const maxTick = computeMaxTick(allTrace, nonKeyframeEvents);
  const markers = deriveTimelineMarkers(allTrace, nonKeyframeEvents, maxTick);

  it("renders exactly the real run's markers: 1 claim born, 2 events (death + crime witnessed), zero of the not-yet-exercised types", () => {
    const byType = (t: TimelineMarker["type"]) => markers.filter((m) => m.type === t);
    expect(byType("claim_born")).toHaveLength(1);
    expect(byType("events")).toHaveLength(2);
    expect(byType("mutation")).toHaveLength(0);
    expect(byType("supersession")).toHaveLength(0);
    expect(byType("grudge_formed")).toHaveLength(0);
    expect(byType("threshold_crossed")).toHaveLength(0);
  });

  it("the claim-born marker is claim-jarl-death at tick 0", () => {
    const claimBorn = markers.find((m) => m.type === "claim_born");
    expect(claimBorn?.tick).toBe(0);
    expect(claimBorn?.label).toContain("claim-jarl-death");
  });

  it("both events markers land at tick 0 (npc_died + crime_witnessed are simultaneous in this run)", () => {
    const events = markers.filter((m) => m.type === "events");
    expect(events.map((m) => m.tick)).toEqual([0, 0]);
    expect(events.some((m) => m.label.includes("death"))).toBe(true);
    expect(events.some((m) => m.label.includes("crime witnessed"))).toBe(true);
  });
});
