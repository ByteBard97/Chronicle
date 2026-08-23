import { describe, expect, it } from "vitest";
import { rumorStageAt } from "./rumorStage";
import { RUMOR_DORMANT_AFTER, RUMOR_FORGOTTEN_GIST_THRESHOLD } from "./constants";
import type { KeyframeBelief, KeyframeRumorState } from "../log/types";

const belief: KeyframeBelief = {
  id: "b1",
  holder_id: "npc-a",
  claim_id: "c1",
  variant_id: null,
  confidence: 0.9,
  verbatim_strength: 0.9,
  gist_strength: 1.0,
  first_learned: 0,
  last_rehearsed: 0,
};

const heardRumor: KeyframeRumorState = {
  npc_id: "npc-a",
  claim_id: "c1",
  variant_id: null,
  stage: "heard",
  first_heard: 0,
  last_heard: 0,
  last_told: null,
  exposure_count: 1,
  distinct_source_count: 1,
};

describe("rumorStageAt", () => {
  it("is 'unheard' when no RumorState exists -- the absence, never a stored value (claims.py's RumorState docstring)", () => {
    expect(rumorStageAt(null, null, 100)).toBe("unheard");
  });

  it("is the stored stage ('heard') shortly after hearing", () => {
    expect(rumorStageAt(heardRumor, belief, 1)).toBe("heard");
  });

  it("is 'repeated' once the NPC has told it on", () => {
    const told: KeyframeRumorState = { ...heardRumor, stage: "repeated", last_told: 5 };
    expect(rumorStageAt(told, belief, 6)).toBe("repeated");
  });

  it("derives 'dormant' once quiet longer than RUMOR_DORMANT_AFTER since the last activity", () => {
    const atDormant = RUMOR_DORMANT_AFTER + 1;
    expect(rumorStageAt(heardRumor, belief, atDormant)).toBe("dormant");
    // last_told, not last_heard, is "the last activity" once it exists (claims.py stage_at()).
    const toldRumor: KeyframeRumorState = { ...heardRumor, last_told: 10 };
    expect(rumorStageAt(toldRumor, belief, 10 + RUMOR_DORMANT_AFTER + 1)).toBe("dormant");
    expect(rumorStageAt(toldRumor, belief, 10 + RUMOR_DORMANT_AFTER - 1)).not.toBe("dormant");
  });

  it("derives 'forgotten' once the belief's decayed gist_strength drops below threshold, overriding dormancy (rule 19)", () => {
    // gist_strength=1.0 decays below RUMOR_FORGOTTEN_GIST_THRESHOLD well before
    // RUMOR_DORMANT_AFTER ticks pass, at this belief's half-life -- forgotten
    // wins even though the dormancy check alone wouldn't have fired yet at a
    // shorter elapsed time.
    const halfLivesToCross = Math.log2(1 / RUMOR_FORGOTTEN_GIST_THRESHOLD);
    const gistHalfLife = 1440.0; // derived/constants.ts's GIST_DECAY_HALF_LIFE
    const elapsed = Math.ceil(halfLivesToCross * gistHalfLife) + 1;
    expect(rumorStageAt(heardRumor, belief, elapsed)).toBe("forgotten");
  });
});
