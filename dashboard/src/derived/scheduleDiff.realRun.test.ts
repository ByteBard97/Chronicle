import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { computeScheduleDiff } from "./scheduleDiff";
import { fromKeyframeState } from "../log/reconstruct";
import type { FrameRecord } from "../log/types";

/**
 * `computeScheduleDiff` against the real `runs/mourning-demo-01` demo run
 * (real `schedule_rewrite` data, no synthetic fixture needed -- lane 41's
 * dispatcher note that the packet's "no demo run has this yet" claim is
 * stale). Same "runs/ is gitignored, skip rather than fail when absent"
 * precedent as `log/layer4.realRun.test.ts`.
 */
const RUN_DIR = path.resolve(process.cwd(), "../runs/mourning-demo-01");
const EVENTS_FILE = path.join(RUN_DIR, "events.jsonl");
const runExists = existsSync(EVENTS_FILE);

function loadEvents(): FrameRecord[] {
  return readFileSync(EVENTS_FILE, "utf8")
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as FrameRecord);
}

describe.skipIf(!runExists)("computeScheduleDiff against runs/mourning-demo-01", () => {
  const allEvents = runExists ? loadEvents() : [];
  const firstKeyframe = allEvents.find((r) => r.payload.record_type === "keyframe")!;
  const baseSchedule = runExists ? fromKeyframeState(firstKeyframe.payload.state as never, firstKeyframe.tick).baseSchedule : [];
  const nonKeyframeEvents = allEvents.filter((r) => r.payload.record_type !== "keyframe");

  it("at tick 10 (before the first keyframe, inside the overlay window), sven and erik show inserted temple_of_kynareth blocks linked to their causing rule/event", () => {
    const diffs = computeScheduleDiff(baseSchedule, nonKeyframeEvents, 10);
    const sven = diffs.find((d) => d.npcId === "sven")!;
    const erik = diffs.find((d) => d.npcId === "erik")!;

    expect(sven.overridden).toBe(true);
    expect(sven.inserted).toHaveLength(1);
    expect(sven.inserted[0]).toMatchObject({
      locationId: "temple_of_kynareth",
      startTick: 0,
      endTick: 72,
      cause: "mourning",
      rule: "schedule-write-back",
    });
    expect(sven.inserted[0].triggerEventKey.seq).toBe(1);
    expect(sven.removed).toEqual([{ npcId: "sven", locationId: "sven_house", startTick: 0, endTick: 144 }]);

    expect(erik.overridden).toBe(true);
    expect(erik.inserted[0]).toMatchObject({ locationId: "temple_of_kynareth" });

    // Uninvolved NPCs (e.g. ysolda) are untouched.
    const ysolda = diffs.find((d) => d.npcId === "ysolda");
    expect(ysolda?.overridden).toBe(false);
  });

  it("at tick 100 (past end_tick 72), sven and erik are back on their base blocks", () => {
    const diffs = computeScheduleDiff(baseSchedule, nonKeyframeEvents, 100);
    const sven = diffs.find((d) => d.npcId === "sven")!;
    expect(sven.overridden).toBe(false);
    expect(sven.after).toEqual([{ npcId: "sven", locationId: "sven_house", startTick: 0, endTick: 144 }]);
  });
});
