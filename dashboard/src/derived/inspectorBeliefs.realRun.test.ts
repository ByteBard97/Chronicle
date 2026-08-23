import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { beliefsForNpc } from "./inspectorBeliefs";
import { emptySocialState, fromKeyframeState, replayTo, type SocialState } from "../log/reconstruct";
import type { FrameRecord } from "../log/types";

/**
 * Real-run check (precedent: feedReader/mapMarkers/variantTree's
 * `*.realRun.test.ts` files): against `runs/carrier-mutation-01`,
 * `relief_caravaneer` shows their real, resolved belief on
 * `claim-market-murder` at a pinned T -- lane 27 (already landed) fixed
 * `reconstruct.ts`'s supersession replay, so any T >= 30 already shows
 * this belief resolved onto the canonical (null) variant. Pinned at
 * T=96, matching other lanes' precedent for a stable mid-run checkpoint
 * (also used by `variantTree.realRun.test.ts`'s scrub-stability check).
 *
 * `runs/` is gitignored -- degrades to skipped rather than failing when
 * absent, matching this repo's established precedent for real-run tests.
 */
const RUN_DIR = path.resolve(process.cwd(), "../runs/carrier-mutation-01");
const EVENTS_FILE = path.join(RUN_DIR, "events.jsonl");
const TRACE_FILE = path.join(RUN_DIR, "trace.jsonl");
const runExists = existsSync(EVENTS_FILE) && existsSync(TRACE_FILE);

function loadRecords(file: string): FrameRecord[] {
  return readFileSync(file, "utf8")
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as FrameRecord);
}

function stateAt(allEvents: FrameRecord[], allTrace: FrameRecord[], atTick: number): SocialState {
  const keyframes = allEvents.filter((r) => r.payload.record_type === "keyframe" && r.tick <= atTick);
  const latestKeyframe = keyframes.length > 0 ? keyframes[keyframes.length - 1]! : null;
  const start = latestKeyframe ? fromKeyframeState(latestKeyframe.payload.state as never, latestKeyframe.tick) : emptySocialState(-1);
  const deltas = [...allEvents, ...allTrace].filter((r) => r.payload.record_type !== "keyframe" && r.tick > start.tick && r.tick <= atTick);
  return replayTo(start, deltas, atTick);
}

describe.skipIf(!runExists)("beliefsForNpc against runs/carrier-mutation-01 (real demo run)", () => {
  const allEvents = runExists ? loadRecords(EVENTS_FILE) : [];
  const allTrace = runExists ? loadRecords(TRACE_FILE) : [];

  it("at T=96, relief_caravaneer shows their real belief, resolved onto the canonical (null) variant of claim-market-murder", () => {
    const state = stateAt(allEvents, allTrace, 96);
    const items = beliefsForNpc(state, "relief_caravaneer", 96);

    expect(items).toHaveLength(1);
    const [item] = items;
    expect(item.beliefId).toBe("belief-auto-relief_caravaneer-4");
    expect(item.claimId).toBe("claim-market-murder");
    expect(item.variantId).toBeNull();
    expect(item.variantLabel).toBeNull();
    // The supersession-rekeying finding (this module's header): the
    // rumor lookup must fall back past the belief's original (now stale)
    // variant key to find the NPC's actual rumor state, or this would
    // report "unheard" for a belief the NPC plainly holds.
    expect(item.stage).not.toBe("unheard");
  });

  it("the belief's claim text is synthesized from the claim's (canonical, unmutated) slots", () => {
    const state = stateAt(allEvents, allTrace, 96);
    const [item] = beliefsForNpc(state, "relief_caravaneer", 96);
    expect(item.text).toBe("perpetrator: unknown, cause: assassination, location: whiterun_market");
  });
});
