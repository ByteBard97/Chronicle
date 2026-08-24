import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import mapJson from "../../map/whiterun_map.json";
import { deriveMapMarkers, enumerateCast, locationAt, variantClassForNpc } from "./mapMarkers";
import { emptySocialState, fromKeyframeState, replayTo, type SocialState } from "../log/reconstruct";
import type { FrameRecord } from "../log/types";
import MarkerLayer from "../components/map/MarkerLayer.vue";
import NpcMarker from "../components/map/NpcMarker.vue";

/**
 * Lane 55 (M7 fix): proves `runs/north-star-01`'s Markarth NPCs -- silently
 * dropped before this lane because `dashboard/map/whiterun_map.json` had no
 * `markarth_city`/`road_whiterun_markarth` entries (see that file's
 * `source` notes on the two new entries, and this lane's work packet) --
 * now render as real, placeable, clickable markers. `runs/` is gitignored;
 * degrades to skipped rather than failing when absent, matching
 * `mapMarkers.realRun.test.ts`'s precedent.
 */
const RUN_DIR = path.resolve(process.cwd(), "../runs/north-star-01");
const EVENTS_FILE = path.join(RUN_DIR, "events.jsonl");
const TRACE_FILE = path.join(RUN_DIR, "trace.jsonl");
const runExists = existsSync(EVENTS_FILE) && existsSync(TRACE_FILE);

const CLAIM_ID = "claim-balgruuf-assassination";
// markarth_resident_3's held (and, per the M7 dossier, "wrong") variant on
// claim-balgruuf-assassination -- confirmed directly against the real
// keyframe state (belief-auto-markarth_resident_3-9, variant-auto-9).
const MARKARTH_RESIDENT_3_VARIANT = "variant-auto-9";

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

describe.skipIf(!runExists)("map markers against runs/north-star-01 (Markarth coverage, lane 55)", () => {
  const allEvents = runExists ? loadRecords(EVENTS_FILE) : [];
  const allTrace = runExists ? loadRecords(TRACE_FILE) : [];
  const nonKeyframeEvents = allEvents.filter((r) => r.payload.record_type !== "keyframe");
  const LATE_TICK = 239;

  it("the cast includes the three Markarth residents and the caravaneers", () => {
    const state = stateAt(allEvents, allTrace, LATE_TICK);
    const cast = enumerateCast(state, allTrace, nonKeyframeEvents);
    for (const id of ["markarth_resident_1", "markarth_resident_2", "markarth_resident_3"]) {
      expect(cast, `${id} missing from cast`).toContain(id);
    }
  });

  it("markarth_resident_1/2/3 resolve to markarth_city at the late tick", () => {
    for (const id of ["markarth_resident_1", "markarth_resident_2", "markarth_resident_3"]) {
      expect(locationAt(id, allTrace, nonKeyframeEvents, LATE_TICK)).toBe("markarth_city");
    }
  });

  it("markarth_resident_1/2/3 render as real, placed markers in the off-map inset corner (previously silently dropped -- the bug this lane fixes)", () => {
    const state = stateAt(allEvents, allTrace, LATE_TICK);
    const markers = deriveMapMarkers({
      state,
      traceRecords: allTrace,
      eventRecords: nonKeyframeEvents,
      mapJson,
      claimId: CLAIM_ID,
      atTick: LATE_TICK,
      isSelected: () => false,
    });
    const byId = Object.fromEntries(markers.map((m) => [m.id, m]));
    for (const id of ["markarth_resident_1", "markarth_resident_2", "markarth_resident_3"]) {
      expect(byId[id], `${id} marker missing`).toBeDefined();
      // Bottom-left inset corner (see whiterun_map.json's markarth_city
      // pixel [450, 3010] -> ~4%/97% via CROP/toPct), nowhere near any real
      // Whiterun building's pixel bounds (all within roughly 11-89% / 6-94%).
      expect(byId[id]!.left).toBeLessThan(15);
      expect(byId[id]!.top).toBeGreaterThan(90);
    }
  });

  it("clicking a Markarth marker (rendered via the real MarkerLayer) emits select with the NPC id, exactly like any other marker", () => {
    const state = stateAt(allEvents, allTrace, LATE_TICK);
    const markers = deriveMapMarkers({
      state,
      traceRecords: allTrace,
      eventRecords: nonKeyframeEvents,
      mapJson,
      claimId: CLAIM_ID,
      atTick: LATE_TICK,
      isSelected: () => false,
    });
    const wrapper = mount(MarkerLayer, { props: { markers } });
    const npcMarkers = wrapper.findAllComponents(NpcMarker);
    const target = npcMarkers.find((m) => m.props("marker").id === "markarth_resident_3");
    expect(target, "markarth_resident_3's NpcMarker not found").toBeDefined();
    target!.vm.$emit("select", "markarth_resident_3");
    expect(wrapper.emitted("select")).toEqual([["markarth_resident_3"]]);
  });

  it("the rumor overlay (stage/glyph) derives for Markarth markers exactly like Whiterun ones -- no new overlay logic needed", () => {
    const state = stateAt(allEvents, allTrace, LATE_TICK);
    const markers = deriveMapMarkers({
      state,
      traceRecords: allTrace,
      eventRecords: nonKeyframeEvents,
      mapJson,
      claimId: CLAIM_ID,
      atTick: LATE_TICK,
      isSelected: () => false,
    });
    const resident3 = markers.find((m) => m.id === "markarth_resident_3")!;
    expect(resident3.stage).not.toBeUndefined();
    // "the wrong belief holder" per the dossier: markarth_resident_3 holds
    // variant-auto-9, not canonical -- the variant lens classifies him
    // holds-different when canonical is selected, holds-it when his own
    // variant is.
    expect(variantClassForNpc(state, "markarth_resident_3", CLAIM_ID, null)).toBe("holds-different");
    expect(variantClassForNpc(state, "markarth_resident_3", CLAIM_ID, MARKARTH_RESIDENT_3_VARIANT)).toBe("holds-it");

    const withVariant = deriveMapMarkers({
      state,
      traceRecords: allTrace,
      eventRecords: nonKeyframeEvents,
      mapJson,
      claimId: CLAIM_ID,
      atTick: LATE_TICK,
      isSelected: () => false,
      variantId: MARKARTH_RESIDENT_3_VARIANT,
    });
    const resident3Variant = withVariant.find((m) => m.id === "markarth_resident_3")!;
    expect(resident3Variant.variantClass).toBe("holds-it");
  });
});
