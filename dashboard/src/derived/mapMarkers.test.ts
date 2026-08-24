import { describe, expect, it } from "vitest";
import {
  claimStageBreakdown,
  deriveMapMarkers,
  displayName,
  enumerateCast,
  firstClaimId,
  glyphForNpcClaim,
  locationAt,
  seededJitter,
  stageForNpcClaim,
  variantClassForNpc,
  variantMarkerStyle,
  type WhiterunMapJson,
} from "./mapMarkers";
import { emptySocialState, rumorKey, type SocialState } from "../log/reconstruct";
import type { FrameRecord } from "../log/types";
import type { KeyframeBelief, KeyframeRumorState } from "../log/types";
import { STAGE_STYLE } from "../fixtures/whiterunMock";

function trace(tick: number, payload: Record<string, unknown>, seq = 0): FrameRecord {
  return { schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "trace", seq, payload };
}

function event(tick: number, payload: Record<string, unknown>, seq = 0): FrameRecord {
  return { schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "events", seq, payload };
}

function belief(over: Partial<KeyframeBelief> & Pick<KeyframeBelief, "id" | "holder_id" | "claim_id">): KeyframeBelief {
  return {
    variant_id: null,
    confidence: 0.9,
    verbatim_strength: 1,
    gist_strength: 1,
    first_learned: 0,
    last_rehearsed: 0,
    ...over,
  };
}

function rumor(over: Partial<KeyframeRumorState> & Pick<KeyframeRumorState, "npc_id" | "claim_id">): KeyframeRumorState {
  return {
    variant_id: null,
    stage: "heard",
    first_heard: 0,
    last_heard: 0,
    last_told: null,
    exposure_count: 1,
    distinct_source_count: 1,
    ...over,
  };
}

const MAP_JSON: WhiterunMapJson = {
  locations: {
    dragonsreach: { pixel: [2970, 285] },
    bannered_mare: { pixel: [2278, 2345] },
  },
};

describe("enumerateCast", () => {
  it("finds belief holders, trace participants, relationship endpoints, and npc_died subjects", () => {
    const state = emptySocialState(0);
    state.beliefs.set("b1", belief({ id: "b1", holder_id: "irileth", claim_id: "c1" }));
    const traceRecords: FrameRecord[] = [
      trace(0, { record_type: "relationship_formed", from_id: "guard1", to_id: "jarl_balgruuf" }),
      trace(1, { record_type: "encounter_rolled", npc_a: "irileth", npc_b: "proventus" }),
    ];
    const eventRecords: FrameRecord[] = [event(0, { event_type: "npc_died", npc_id: "jarl_balgruuf" })];

    const cast = enumerateCast(state, traceRecords, eventRecords);
    expect(new Set(cast)).toEqual(new Set(["irileth", "proventus", "guard1", "jarl_balgruuf"]));
  });

  it("the corrected recipe catches a death-only NPC the packet's literal (belief+trace-participant) wording would drop", () => {
    // No belief, no trace participation at all -- exactly jarl_balgruuf's shape in the real run.
    const state = emptySocialState(0);
    const traceRecords: FrameRecord[] = [];
    const eventRecords: FrameRecord[] = [event(0, { event_type: "npc_died", npc_id: "victim" })];
    expect(enumerateCast(state, traceRecords, eventRecords)).toEqual(["victim"]);
  });
});

describe("locationAt", () => {
  it("picks the latest observation at or before T", () => {
    const traceRecords: FrameRecord[] = [
      trace(0, { npc_a: "irileth", npc_b: "proventus", location_id: "dragonsreach" }),
      trace(150, { teller_id: "proventus", hearer_id: "ysolda", location_id: "bannered_mare" }),
    ];
    expect(locationAt("proventus", traceRecords, [], 0)).toBe("dragonsreach");
    expect(locationAt("proventus", traceRecords, [], 200)).toBe("bannered_mare");
  });

  it("ignores observations after T", () => {
    const traceRecords: FrameRecord[] = [trace(300, { npc_a: "irileth", npc_b: "proventus", location_id: "dragonsreach" })];
    expect(locationAt("irileth", traceRecords, [], 200)).toBeNull();
  });

  it("ties at the same tick break by which location this NPC has been observed at more often overall", () => {
    const traceRecords: FrameRecord[] = [
      trace(0, { npc_a: "x", npc_b: "y", location_id: "dragonsreach" }, 0),
      trace(1, { npc_a: "x", npc_b: "y", location_id: "dragonsreach" }, 1),
      // At the tied max tick (2), x is observed at both locations -- frequency (2 dragonsreach vs 1 bannered_mare so far) breaks the tie.
      trace(2, { npc_a: "x", npc_b: "y", location_id: "dragonsreach" }, 2),
      trace(2, { npc_a: "x", npc_b: "y", location_id: "bannered_mare" }, 3),
    ];
    expect(locationAt("x", traceRecords, [], 2)).toBe("dragonsreach");
  });

  it("falls back to the npc_died event location when there is no trace observation at all", () => {
    const eventRecords: FrameRecord[] = [event(0, { event_type: "npc_died", npc_id: "jarl_balgruuf", location_id: "dragonsreach" })];
    expect(locationAt("jarl_balgruuf", [], eventRecords, 0)).toBe("dragonsreach");
    expect(locationAt("jarl_balgruuf", [], eventRecords, 200)).toBe("dragonsreach");
  });

  it("resolves to null when neither a trace observation nor a death event exists", () => {
    expect(locationAt("nobody", [], [], 0)).toBeNull();
  });
});

describe("seededJitter", () => {
  it("is deterministic for the same (npc_id, location_id)", () => {
    expect(seededJitter("irileth", "dragonsreach")).toEqual(seededJitter("irileth", "dragonsreach"));
  });

  it("differs across different npc/location pairs (not a per-location round robin)", () => {
    const a = seededJitter("irileth", "dragonsreach");
    const b = seededJitter("proventus", "dragonsreach");
    const c = seededJitter("irileth", "bannered_mare");
    expect(a).not.toEqual(b);
    expect(a).not.toEqual(c);
  });
});

describe("stageForNpcClaim / glyphForNpcClaim", () => {
  function stateWith(rumors: KeyframeRumorState[], beliefs: KeyframeBelief[]): SocialState {
    const state = emptySocialState(0);
    for (const r of rumors) state.rumors.set(rumorKey(r.npc_id, r.claim_id, r.variant_id), r);
    for (const b of beliefs) state.beliefs.set(b.id, b);
    return state;
  }

  it("is unheard when the NPC has no rumor entry for the claim", () => {
    const state = emptySocialState(0);
    expect(stageForNpcClaim(state, "nobody", "c1", 100)).toBe("unheard");
    expect(glyphForNpcClaim(state, "nobody", "c1", 100)).toBeNull();
  });

  it("takes the worst stage across multiple variants of one claim (repeated beats heard)", () => {
    const state = stateWith(
      [
        rumor({ npc_id: "n", claim_id: "c1", variant_id: "v1", stage: "heard" }),
        rumor({ npc_id: "n", claim_id: "c1", variant_id: "v2", stage: "repeated", last_told: 5 }),
      ],
      [
        belief({ id: "b1", holder_id: "n", claim_id: "c1", variant_id: "v1", first_learned: 0 }),
        belief({ id: "b2", holder_id: "n", claim_id: "c1", variant_id: "v2", first_learned: 0 }),
      ],
    );
    expect(stageForNpcClaim(state, "n", "c1", 10)).toBe("repeated");
  });

  it("glyph S: told within the last 24 ticks takes precedence over N", () => {
    const state = stateWith(
      [rumor({ npc_id: "n", claim_id: "c1", stage: "repeated", last_told: 50 })],
      [belief({ id: "b1", holder_id: "n", claim_id: "c1", first_learned: 0 })],
    );
    expect(glyphForNpcClaim(state, "n", "c1", 60)).toBe("S");
    expect(glyphForNpcClaim(state, "n", "c1", 90)).toBeNull(); // 90 - 50 = 40 > 24
  });

  it("glyph N: belief formed within the current game-day (24-tick boundary)", () => {
    const state = stateWith(
      [rumor({ npc_id: "n", claim_id: "c1" })],
      [belief({ id: "b1", holder_id: "n", claim_id: "c1", first_learned: 20 })],
    );
    expect(glyphForNpcClaim(state, "n", "c1", 23)).toBe("N"); // same day (0)
    expect(glyphForNpcClaim(state, "n", "c1", 24)).toBeNull(); // day 1, no longer "today"
  });
});

describe("displayName", () => {
  it("formats snake_case npc ids as title case", () => {
    expect(displayName("irileth")).toBe("Irileth");
    expect(displayName("whiterun_guard_1")).toBe("Whiterun Guard 1");
    expect(displayName("jarl_balgruuf")).toBe("Jarl Balgruuf");
  });
});

describe("firstClaimId", () => {
  it("returns the first claim in insertion order, or null when there are none", () => {
    const state = emptySocialState(0);
    expect(firstClaimId(state)).toBeNull();
    state.claims.set("c1", {
      id: "c1",
      kind: "npc_death",
      slots: {},
      canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 },
      truth_status: "unconfirmed",
    });
    expect(firstClaimId(state)).toBe("c1");
  });
});

describe("deriveMapMarkers", () => {
  it("renders a death-only NPC (no belief, no trace observation) as unheard at their death location, for the full run", () => {
    const state = emptySocialState(0);
    const eventRecords: FrameRecord[] = [event(0, { event_type: "npc_died", npc_id: "jarl_balgruuf", location_id: "dragonsreach" })];

    for (const atTick of [0, 200]) {
      const markers = deriveMapMarkers({
        state,
        traceRecords: [],
        eventRecords,
        mapJson: MAP_JSON,
        claimId: "claim-jarl-death",
        atTick,
        isSelected: () => false,
      });
      expect(markers).toHaveLength(1);
      expect(markers[0]).toMatchObject({ id: "jarl_balgruuf", stage: "unheard", glyph: null });
      // dragonsreach's pixel is [2970, 285]; jitter is at most ~2 percentage points.
      expect(markers[0]!.left).toBeGreaterThan(80);
      expect(markers[0]!.top).toBeLessThan(10);
    }
  });

  it("omits a cast member with no resolvable location at T rather than placing them at a dummy origin", () => {
    const state = emptySocialState(0);
    state.beliefs.set("b1", belief({ id: "b1", holder_id: "guard1", claim_id: "c1", first_learned: 50 }));
    state.rumors.set(rumorKey("guard1", "c1", null), rumor({ npc_id: "guard1", claim_id: "c1" }));
    // guard1 is cast (holds a belief) but has no trace observation before tick 50.
    const markers = deriveMapMarkers({
      state,
      traceRecords: [trace(50, { npc_a: "guard1", npc_b: "irileth", location_id: "dragonsreach" })],
      eventRecords: [],
      mapJson: MAP_JSON,
      claimId: "c1",
      atTick: 0,
      isSelected: () => false,
    });
    expect(markers).toHaveLength(0);
  });

  it("wires the selected flag from the injected predicate", () => {
    const state = emptySocialState(0);
    const eventRecords: FrameRecord[] = [event(0, { event_type: "npc_died", npc_id: "jarl_balgruuf", location_id: "dragonsreach" })];
    const markers = deriveMapMarkers({
      state,
      traceRecords: [],
      eventRecords,
      mapJson: MAP_JSON,
      claimId: "c1",
      atTick: 0,
      isSelected: (id) => id === "jarl_balgruuf",
    });
    expect(markers[0]!.selected).toBe(true);
  });
});

describe("variantClassForNpc (lane 35: the variant lens)", () => {
  it("holds-none when the holder has no belief on the claim at all", () => {
    const state = emptySocialState(0);
    expect(variantClassForNpc(state, "nobody", "c1", null)).toBe("holds-none");
    expect(variantClassForNpc(state, "nobody", "c1", "v1")).toBe("holds-none");
  });

  it("holds-it when the holder's belief variant_id matches the selected variant, including canonical (null === null)", () => {
    const state = emptySocialState(0);
    state.beliefs.set("b1", belief({ id: "b1", holder_id: "n", claim_id: "c1", variant_id: null }));
    expect(variantClassForNpc(state, "n", "c1", null)).toBe("holds-it");

    const state2 = emptySocialState(0);
    state2.beliefs.set("b2", belief({ id: "b2", holder_id: "n", claim_id: "c1", variant_id: "v1" }));
    expect(variantClassForNpc(state2, "n", "c1", "v1")).toBe("holds-it");
  });

  it("holds-different when the holder's belief is on a different variant than selected", () => {
    const state = emptySocialState(0);
    state.beliefs.set("b1", belief({ id: "b1", holder_id: "n", claim_id: "c1", variant_id: "v1" }));
    expect(variantClassForNpc(state, "n", "c1", "v2")).toBe("holds-different");
    expect(variantClassForNpc(state, "n", "c1", null)).toBe("holds-different"); // holds v1, canonical selected
  });

  it("only looks at beliefs for the given claim_id, ignoring beliefs on other claims", () => {
    const state = emptySocialState(0);
    state.beliefs.set("b1", belief({ id: "b1", holder_id: "n", claim_id: "other-claim", variant_id: "v1" }));
    expect(variantClassForNpc(state, "n", "c1", "v1")).toBe("holds-none");
  });
});

describe("variantMarkerStyle", () => {
  it("holds-it uses the normal per-stage style", () => {
    expect(variantMarkerStyle("repeated", "holds-it")).toEqual(STAGE_STYLE.repeated);
    expect(variantMarkerStyle("heard", "holds-it")).toEqual(STAGE_STYLE.heard);
  });

  it("holds-none forces the unheard gray regardless of stage", () => {
    expect(variantMarkerStyle("repeated", "holds-none")).toEqual(STAGE_STYLE.unheard);
  });

  it("holds-different is a fixed dimmed style, distinct from both holds-it's stage color and holds-none's gray", () => {
    const dimmed = variantMarkerStyle("repeated", "holds-different");
    expect(dimmed).not.toEqual(STAGE_STYLE.repeated);
    expect(dimmed).not.toEqual(STAGE_STYLE.unheard);
    // Same regardless of underlying stage -- holds-different never reads as stage-colored.
    expect(variantMarkerStyle("heard", "holds-different")).toEqual(dimmed);
  });
});

describe("deriveMapMarkers's variantId input (lane 35)", () => {
  function stateWithBeliefs(beliefs: KeyframeBelief[]): SocialState {
    const state = emptySocialState(0);
    for (const b of beliefs) state.beliefs.set(b.id, b);
    return state;
  }

  it("when variantId is omitted, markers carry no variantClass at all (byte-identical to pre-lane-35 behavior)", () => {
    const eventRecords: FrameRecord[] = [event(0, { event_type: "npc_died", npc_id: "jarl_balgruuf", location_id: "dragonsreach" })];
    const markers = deriveMapMarkers({
      state: emptySocialState(0),
      traceRecords: [],
      eventRecords,
      mapJson: MAP_JSON,
      claimId: "c1",
      atTick: 0,
      isSelected: () => false,
    });
    expect(markers[0]).not.toHaveProperty("variantClass");
    expect("variantClass" in markers[0]!).toBe(false);
  });

  it("classifies each cast member's variantClass when variantId is provided", () => {
    const state = stateWithBeliefs([
      belief({ id: "b1", holder_id: "holds-it-npc", claim_id: "c1", variant_id: "v1" }),
      belief({ id: "b2", holder_id: "holds-diff-npc", claim_id: "c1", variant_id: "v2" }),
    ]);
    const traceRecords: FrameRecord[] = [
      trace(0, { npc_a: "holds-it-npc", npc_b: "holds-diff-npc", location_id: "dragonsreach" }),
      trace(0, { npc_a: "holds-none-npc", npc_b: "holds-it-npc", location_id: "bannered_mare" }),
    ];
    const markers = deriveMapMarkers({
      state,
      traceRecords,
      eventRecords: [],
      mapJson: MAP_JSON,
      claimId: "c1",
      atTick: 0,
      isSelected: () => false,
      variantId: "v1",
    });
    const byId = Object.fromEntries(markers.map((m) => [m.id, m.variantClass]));
    expect(byId["holds-it-npc"]).toBe("holds-it");
    expect(byId["holds-diff-npc"]).toBe("holds-different");
    expect(byId["holds-none-npc"]).toBe("holds-none");
  });

  it("variantId: null selects the canonical variant", () => {
    const state = stateWithBeliefs([
      belief({ id: "b1", holder_id: "canon-npc", claim_id: "c1", variant_id: null }),
      belief({ id: "b2", holder_id: "variant-npc", claim_id: "c1", variant_id: "v1" }),
    ]);
    const traceRecords: FrameRecord[] = [trace(0, { npc_a: "canon-npc", npc_b: "variant-npc", location_id: "dragonsreach" })];
    const markers = deriveMapMarkers({
      state,
      traceRecords,
      eventRecords: [],
      mapJson: MAP_JSON,
      claimId: "c1",
      atTick: 0,
      isSelected: () => false,
      variantId: null,
    });
    const byId = Object.fromEntries(markers.map((m) => [m.id, m.variantClass]));
    expect(byId["canon-npc"]).toBe("holds-it");
    expect(byId["variant-npc"]).toBe("holds-different");
  });
});

describe("claimStageBreakdown", () => {
  it("counts every cast member (including those deriveMapMarkers can't place) and computes coverage", () => {
    const state = emptySocialState(0);
    state.beliefs.set("b1", belief({ id: "b1", holder_id: "irileth", claim_id: "c1", first_learned: 0 }));
    state.rumors.set(rumorKey("irileth", "c1", null), rumor({ npc_id: "irileth", claim_id: "c1", stage: "heard" }));
    const cast = ["irileth", "jarl_balgruuf", "guard1"];
    const { counts, coverage } = claimStageBreakdown(state, cast, "c1", 0);
    expect(counts).toEqual({ unheard: 2, heard: 1, repeated: 0, dormant: 0, forgotten: 0 });
    expect(coverage).toBe("coverage 1/3");
  });
});
