import { describe, expect, it } from "vitest";
import { decayValue, decayBelief } from "./decay";
import { CONFIDENCE_DECAY_HALF_LIFE, GIST_DECAY_HALF_LIFE, VERBATIM_DECAY_HALF_LIFE } from "./constants";
import type { KeyframeBelief } from "../log/types";

describe("decayValue", () => {
  it("ports the exact formula docs/frame-log-schema.md §8 cites (chronicle/claims.py:71)", () => {
    // value * 0.5 ** (elapsed / half_life)
    expect(decayValue(1.0, 168, 168)).toBeCloseTo(0.5, 12);
    expect(decayValue(0.8, 0, 168)).toBe(0.8);
  });

  it("halves at exactly one half-life, quarters at two", () => {
    expect(decayValue(1.0, 336, 168)).toBeCloseTo(0.25, 12);
  });

  it("does not decay for non-positive elapsed time", () => {
    expect(decayValue(0.5, -10, 168)).toBe(0.5);
  });
});

describe("decayBelief", () => {
  const belief: KeyframeBelief = {
    id: "b1",
    holder_id: "npc-a",
    claim_id: "c1",
    variant_id: null,
    confidence: 0.8,
    verbatim_strength: 0.6,
    gist_strength: 0.9,
    first_learned: 0,
    last_rehearsed: 10,
  };

  it("is a no-op at or before last_rehearsed", () => {
    expect(decayBelief(belief, 10)).toEqual(belief);
    expect(decayBelief(belief, 5)).toEqual(belief);
  });

  it("decays each of confidence/verbatim/gist independently by elapsed time since last_rehearsed", () => {
    const at = 10 + CONFIDENCE_DECAY_HALF_LIFE;
    const decayed = decayBelief(belief, at);
    expect(decayed.confidence).toBeCloseTo(0.4, 12);
    expect(decayed.verbatim_strength).toBeCloseTo(
      0.6 * Math.pow(0.5, CONFIDENCE_DECAY_HALF_LIFE / VERBATIM_DECAY_HALF_LIFE),
      12,
    );
    expect(decayed.gist_strength).toBeCloseTo(
      0.9 * Math.pow(0.5, CONFIDENCE_DECAY_HALF_LIFE / GIST_DECAY_HALF_LIFE),
      12,
    );
  });

  it("never mutates the input belief record", () => {
    const copy = { ...belief };
    decayBelief(belief, 1000);
    expect(belief).toEqual(copy);
  });
});
