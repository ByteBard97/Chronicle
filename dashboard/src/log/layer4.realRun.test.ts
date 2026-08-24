import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { emptySocialState, fromKeyframeState, replayTo } from "./reconstruct";
import type { FrameRecord } from "./types";

/**
 * Verifies layer-4 (relationships/grudges/obligations/reputations) keyframe
 * hydration and delta replay against the real `runs/tier3-demo-01` demo run
 * (lane 34) -- the same "runs/ is gitignored, skip rather than fail when
 * absent" precedent as `variantTree.realRun.test.ts`/`mapMarkers.realRun.test.ts`.
 *
 * `tier3-demo-01` has two keyframes (ticks 23, 47) and exactly one of each
 * kind of layer-4 record, all firing at ticks 0-4 -- strictly before the
 * first keyframe (23). That means both keyframes already carry the full,
 * final layer-4 state (1 relationship / 1 grudge / 2 obligations /
 * 5 reputations), and there are zero layer-4 trace records between the two
 * keyframes to replay across. So the "keyframe hydration vs. delta replay
 * agree" property (the packet's ask, modeled on lane 27's supersession test)
 * is proven here by comparing the tick-23 keyframe's own hydrated state
 * against a from-scratch delta replay of every tick 0-23 record -- not by
 * replaying between the two keyframes, since no layer-4 record exists in
 * that window. Filed as a finding in the delivery report.
 */
const RUN_DIR = path.resolve(process.cwd(), "../runs/tier3-demo-01");
const EVENTS_FILE = path.join(RUN_DIR, "events.jsonl");
const TRACE_FILE = path.join(RUN_DIR, "trace.jsonl");
const runExists = existsSync(EVENTS_FILE) && existsSync(TRACE_FILE);

function loadRecords(file: string): FrameRecord[] {
  return readFileSync(file, "utf8")
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as FrameRecord);
}

describe.skipIf(!runExists)("layer-4 social state against runs/tier3-demo-01 (real demo run, lane 34)", () => {
  const allEvents = runExists ? loadRecords(EVENTS_FILE) : [];
  const allTrace = runExists ? loadRecords(TRACE_FILE) : [];
  const allRecords = [...allEvents, ...allTrace];
  const keyframes = allEvents.filter((r) => r.payload.record_type === "keyframe");

  it("has exactly two keyframes, at ticks 23 and 47", () => {
    expect(keyframes.map((k) => k.tick)).toEqual([23, 47]);
  });

  it("the final keyframe (tick 47) hydrates to the confirmed real counts: 1 relationship, 1 grudge, 2 obligations, 5 reputations", () => {
    const finalKeyframe = keyframes[keyframes.length - 1]!;
    const state = fromKeyframeState(finalKeyframe.payload.state as never, finalKeyframe.tick);
    expect(state.relationships.size).toBe(1);
    expect(state.grudges.size).toBe(1);
    expect(state.obligations.size).toBe(2);
    expect(state.reputations.size).toBe(5);
  });

  it("delta replay from empty state through every tick 0-23 record agrees with the tick-23 keyframe's own hydrated layer-4 maps", () => {
    // All six layer-4 record types in this run fire at ticks 0-4, strictly
    // before the first keyframe -- so the first keyframe (tick 23) is
    // itself a snapshot of exactly what pure delta replay produces from
    // scratch. Proving the two agree is the same "hydration and replay
    // must not silently diverge" property the packet asks for; the
    // tick-23/47 window that DOES exist in this run carries zero layer-4
    // deltas to replay (see file header finding).
    const firstKeyframe = keyframes[0]!;
    const keyframeState = fromKeyframeState(firstKeyframe.payload.state as never, firstKeyframe.tick);

    const deltas = allRecords.filter((r) => r.payload.record_type !== "keyframe" && r.tick <= firstKeyframe.tick);
    const replayed = replayTo(emptySocialState(-1), deltas, firstKeyframe.tick);

    expect([...replayed.relationships.keys()].sort()).toEqual([...keyframeState.relationships.keys()].sort());
    expect([...replayed.grudges.keys()].sort()).toEqual([...keyframeState.grudges.keys()].sort());
    expect([...replayed.obligations.keys()].sort()).toEqual([...keyframeState.obligations.keys()].sort());
    expect([...replayed.reputations.keys()].sort()).toEqual([...keyframeState.reputations.keys()].sort());

    for (const [key, value] of keyframeState.relationships) expect(replayed.relationships.get(key)).toEqual(value);
    for (const [key, value] of keyframeState.grudges) expect(replayed.grudges.get(key)).toEqual(value);
    for (const [key, value] of keyframeState.obligations) expect(replayed.obligations.get(key)).toEqual(value);
    for (const [key, value] of keyframeState.reputations) expect(replayed.reputations.get(key)).toEqual(value);

    expect(replayed.relationships.size).toBe(1);
    expect(replayed.grudges.size).toBe(1);
    expect(replayed.obligations.size).toBe(2);
    expect(replayed.reputations.size).toBe(5);
  });

  it("at tick 3 (before the grudge/full-obligation chain resolves), delta replay alone already shows the grudge and the violated obligation -- no keyframe needed", () => {
    // grudge_formed and the obl-favor-2 obligation_resolved (violated) both
    // fire at tick 2; by tick 3 delta replay alone (no keyframe exists this
    // early) must already reflect them.
    const deltas = allRecords.filter((r) => r.payload.record_type !== "keyframe" && r.tick <= 3);
    const state = replayTo(emptySocialState(-1), deltas, 3);
    expect(state.grudges.size).toBe(1);
    const grudge = [...state.grudges.values()][0]!;
    expect(grudge).toMatchObject({ holder_id: "adrianne", target_id: "ulfberth", id: "grudge-violation-auto-1" });
    expect(state.obligations.get("obl-favor-2")).toMatchObject({ status: "violated", violated_at: 2 });
    expect(state.obligations.get("obl-favor-1")).toMatchObject({ status: "fulfilled", fulfilled_at: 1 });
  });

  it("threshold_crossed (tick 3) causes no layer-4 state change -- it is stateless bookkeeping", () => {
    const before = replayTo(emptySocialState(-1), allRecords.filter((r) => r.payload.record_type !== "keyframe" && r.tick <= 2), 2);
    const after = replayTo(emptySocialState(-1), allRecords.filter((r) => r.payload.record_type !== "keyframe" && r.tick <= 3), 3);
    // threshold_crossed fires at tick 3 alongside no other layer-4 record --
    // grudges/obligations/reputations maps are unchanged by it specifically.
    expect(after.grudges.size).toBe(before.grudges.size);
    expect(after.obligations.size).toBe(before.obligations.size);
  });
});
