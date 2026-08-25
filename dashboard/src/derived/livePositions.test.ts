import { describe, expect, it } from "vitest";
import { deriveLiveMarkers, worldToPercent } from "./livePositions";

describe("worldToPercent", () => {
  it("matches whiterun_map.json's own baked pixel for a known location (amrens_house)", () => {
    // world [21934.3, -3923.3] -> pixel [1519.9, 1603.7] (whiterun_map.json's
    // own fixture data) -> crop-square percent via CROP (330, 90, 3000).
    const [left, top] = worldToPercent(21934.3, -3923.3);
    expect(left).toBeCloseTo(((1519.9 - 330) / 30), 1);
    expect(top).toBeCloseTo(((1603.7 - 90) / 30), 1);
  });
});

describe("deriveLiveMarkers", () => {
  it("returns an empty array for a null snapshot", () => {
    expect(deriveLiveMarkers(null)).toEqual([]);
  });

  it("projects every npc in the snapshot to a left/top percent marker", () => {
    const markers = deriveLiveMarkers({
      wall_ts: 1000,
      npcs: [{ id: "jarl_balgruuf", name: "Jarl Balgruuf", x: 21934.3, y: -3923.3 }],
    });
    expect(markers).toHaveLength(1);
    expect(markers[0]!.id).toBe("jarl_balgruuf");
    expect(markers[0]!.name).toBe("Jarl Balgruuf");
    expect(markers[0]!.left).toBeGreaterThan(0);
    expect(markers[0]!.top).toBeGreaterThan(0);
  });

  it("skips npcs that project outside the crop square", () => {
    const markers = deriveLiveMarkers({
      wall_ts: 1000,
      // Far outside WhiterunWorld's exterior cell entirely.
      npcs: [{ id: "somewhere_else", name: "", x: 1_000_000, y: 1_000_000 }],
    });
    expect(markers).toEqual([]);
  });
});
