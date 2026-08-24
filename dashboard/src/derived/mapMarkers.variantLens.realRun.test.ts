import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { deriveMapMarkers, enumerateCast, variantClassForNpc, type WhiterunMapJson } from "./mapMarkers";
import { emptySocialState, fromKeyframeState, replayTo, type SocialState } from "../log/reconstruct";
import type { FrameRecord } from "../log/types";

/**
 * Verifies the variant lens (lane 35) against `runs/carrier-mutation-01`
 * (lane 17/27's multi-variant, multi-supersession claim), using the exact
 * `stateAt` reconstruction idiom `variantTree.realRun.test.ts` and
 * `mapMarkers.realRun.test.ts` already establish. `runs/` is gitignored --
 * degrades to skipped rather than failing when absent, matching that
 * precedent.
 *
 * Finding (coordinator's pre-dispatch brief needed correcting -- verified
 * directly against the run below, not assumed): the brief described "5
 * holders total" at t=200 (relief_caravaneer/ysolda/belethor on canonical,
 * carlotta on variant-auto-1, caravaneer on variant-auto-3) and predicted a
 * 3 holds-it / 2 holds-different split for the canonical lens. The real
 * keyframe at t=200 has 8 belief holders, not 5 -- three more
 * (markarth_resident_1/2/3, on variant-auto-12/13/14) that the brief's
 * summary omitted. The correct split, confirmed below, is 3 holds-it / 5
 * holds-different (+ a 9th cast member, `whiterun_merchant`, who never
 * holds a belief on this claim at any tick and is always holds-none).
 *
 * Second finding, more load-bearing: `deriveMapMarkers`'s end-to-end
 * *placement* step (`locationAt` + a `mapJson.locations` lookup) resolves
 * to ZERO markers for this run at any tick, lens or no lens --
 * `carrier-mutation-01`'s trace records use `markarth_city`,
 * `road_whiterun_markarth`, and `whiterun_market` as `location_id`s, and
 * none of the three exist in `dashboard/map/whiterun_map.json` (a
 * Whiterun-only map baked for lane 14's original whiterun-jarl-01 demo
 * run). This is a pre-existing lane-14 map-JSON coverage gap, not
 * something this lane introduces or is in scope to fix (the map-JSON asset
 * isn't in this lane's file boundaries, and there is no permissive vector
 * map for Markarth -- see the prior Whiterun-map-sourcing research). The
 * tests below split accordingly: classification-only tests exercise
 * `variantClassForNpc` directly against the real reconstructed state
 * (independent of placement, and the thing this lane actually adds), and
 * one end-to-end `deriveMapMarkers` test substitutes a small synthetic
 * `WhiterunMapJson` keyed to this run's *real* location ids (arbitrary
 * pixel values -- only placement, not position accuracy, is at stake) to
 * prove the full pipeline (cast -> location -> style) still wires the
 * variant lens through correctly once a location is resolvable.
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

/** This run's real location ids, arbitrarily placed -- see module header. */
const SYNTHETIC_MAP_JSON: WhiterunMapJson = {
  locations: {
    markarth_city: { pixel: [1000, 1000] },
    road_whiterun_markarth: { pixel: [1500, 1500] },
    whiterun_market: { pixel: [2000, 2000] },
  },
};

describe.skipIf(!runExists)("variant lens against runs/carrier-mutation-01 (real demo run)", () => {
  const allEvents = runExists ? loadRecords(EVENTS_FILE) : [];
  const allTrace = runExists ? loadRecords(TRACE_FILE) : [];
  const nonKeyframeEvents = allEvents.filter((r) => r.payload.record_type !== "keyframe");
  const CLAIM_ID = "claim-market-murder";

  it("t=200: selecting canonical classifies 3 holds-it, 5 holds-different, 1 holds-none across the 9-member cast", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const cast = enumerateCast(state, allTrace, nonKeyframeEvents);
    expect(cast).toHaveLength(9);
    const classes = Object.fromEntries(cast.map((id) => [id, variantClassForNpc(state, id, CLAIM_ID, null)]));
    expect(classes).toEqual({
      relief_caravaneer: "holds-it",
      ysolda: "holds-it",
      belethor: "holds-it",
      carlotta: "holds-different",
      caravaneer: "holds-different",
      markarth_resident_1: "holds-different",
      markarth_resident_2: "holds-different",
      markarth_resident_3: "holds-different",
      whiterun_merchant: "holds-none",
    });
  });

  it("t=200: selecting variant-auto-1 classifies only carlotta as holds-it", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const cast = enumerateCast(state, allTrace, nonKeyframeEvents);
    const classes = Object.fromEntries(cast.map((id) => [id, variantClassForNpc(state, id, CLAIM_ID, "variant-auto-1")]));
    expect(classes.carlotta).toBe("holds-it");
    expect(classes.whiterun_merchant).toBe("holds-none");
    const different = Object.entries(classes).filter(([, c]) => c === "holds-different").map(([id]) => id);
    expect(new Set(different)).toEqual(
      new Set(["belethor", "relief_caravaneer", "ysolda", "caravaneer", "markarth_resident_1", "markarth_resident_2", "markarth_resident_3"]),
    );
  });

  it("scrubbing T: ysolda flips from holds-different to holds-it (canonical lens) exactly when her supersession resolves, between t=27 and t=28", () => {
    const before = stateAt(allEvents, allTrace, 27);
    const after = stateAt(allEvents, allTrace, 28);
    expect(variantClassForNpc(before, "ysolda", CLAIM_ID, null)).toBe("holds-different"); // still on variant-auto-4
    expect(variantClassForNpc(after, "ysolda", CLAIM_ID, null)).toBe("holds-it"); // resolved onto canonical
  });

  it("scrubbing T: markarth_resident_1 is holds-none before the auto-12 mutation branch exists (t=20) and holds-different once it does (t=200)", () => {
    const early = stateAt(allEvents, allTrace, 20);
    const late = stateAt(allEvents, allTrace, 200);
    expect(variantClassForNpc(early, "markarth_resident_1", CLAIM_ID, null)).toBe("holds-none");
    expect(variantClassForNpc(late, "markarth_resident_1", CLAIM_ID, null)).toBe("holds-different");
  });

  it("end-to-end deriveMapMarkers wires variantClass onto real markers once a location resolves (synthetic map JSON -- see module header)", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const markers = deriveMapMarkers({
      state,
      traceRecords: allTrace,
      eventRecords: nonKeyframeEvents,
      mapJson: SYNTHETIC_MAP_JSON,
      claimId: CLAIM_ID,
      atTick: 200,
      isSelected: () => false,
      variantId: null,
    });
    expect(markers.length).toBeGreaterThan(0);
    const byId = Object.fromEntries(markers.map((m) => [m.id, m.variantClass]));
    expect(byId.belethor).toBe("holds-it");
    expect(byId.carlotta).toBe("holds-different");
  });

  it("with variantId omitted, the real-run markers carry no variantClass (the claim-level lens stays the default)", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const markers = deriveMapMarkers({
      state,
      traceRecords: allTrace,
      eventRecords: nonKeyframeEvents,
      mapJson: SYNTHETIC_MAP_JSON,
      claimId: CLAIM_ID,
      atTick: 200,
      isSelected: () => false,
    });
    expect(markers.length).toBeGreaterThan(0);
    for (const m of markers) expect(m.variantClass).toBeUndefined();
  });
});
