import { describe, expect, it } from "vitest";
import { buildDisplayItems } from "./feedGrouping";
import type { FeedRow } from "../../log/feedReader";

function row(tick: number, seq: number, outcome: FeedRow["outcome"]): FeedRow {
  const detail: FeedRow["detail"] =
    outcome === "transmitted"
      ? { kind: "transmitted", variantId: null, mutatedSlot: null }
      : outcome === "declined"
        ? { kind: "declined", rule: "r" }
        : outcome === "rolled_against"
          ? { kind: "rolled_against", value: 0.1, threshold: 0.2 }
          : { kind: "nothing_salient", reason: "both-informed" };
  return { tick, seq, location: "x", participants: ["a", "b"], outcome, claimId: null, detail };
}

// tick 0: two rolled-against; tick 1: transmitted; tick 2: nothing_salient; tick 3: declined
const rows: FeedRow[] = [
  row(0, 0, "rolled_against"),
  row(0, 1, "rolled_against"),
  row(1, 2, "transmitted"),
  row(2, 3, "nothing_salient"),
  row(3, 4, "declined"),
];

describe("buildDisplayItems", () => {
  it("developer: full row set, no group chrome", () => {
    const items = buildDisplayItems(rows, "developer", false, new Set());
    expect(items).toHaveLength(5);
    expect(items.every((i) => i.type === "row")).toBe(true);
  });

  it("story: transmissions + declines only", () => {
    const items = buildDisplayItems(rows, "story", false, new Set());
    expect(items).toHaveLength(2);
    expect(items.map((i) => (i.type === "row" ? i.row.outcome : null))).toEqual(["transmitted", "declined"]);
  });

  it("observer: headline rows individual, trace rows collapsed per tick", () => {
    const items = buildDisplayItems(rows, "observer", false, new Set());
    // tick0 group (2 rolled_against), transmitted row, tick2 group (1 nothing_salient), declined row
    expect(items).toHaveLength(4);
    expect(items[0]).toMatchObject({ type: "group", tick: 0 });
    expect((items[0] as { type: "group"; rows: FeedRow[] }).rows).toHaveLength(2);
    expect(items[1]).toMatchObject({ type: "row" });
    expect((items[1] as { type: "row"; row: FeedRow }).row.outcome).toBe("transmitted");
    expect(items[2]).toMatchObject({ type: "group", tick: 2 });
    expect(items[3]).toMatchObject({ type: "row" });
  });

  it("observer: expanding a tick's group reveals its trace rows in place instead of the header", () => {
    const items = buildDisplayItems(rows, "observer", false, new Set([0]));
    expect(items).toHaveLength(5); // tick0's group expanded into its 2 rows
    expect(items[0]).toMatchObject({ type: "row" });
    expect(items[1]).toMatchObject({ type: "row" });
    expect((items[0] as { type: "row"; row: FeedRow }).row.outcome).toBe("rolled_against");
    // tick 2's group stays collapsed (not in expandedTicks)
    expect(items[3]).toMatchObject({ type: "group", tick: 2 });
  });

  it("showAll bypasses grouping/filtering at every salience level", () => {
    for (const level of ["developer", "observer", "story"] as const) {
      const items = buildDisplayItems(rows, level, true, new Set());
      expect(items).toHaveLength(5);
      expect(items.every((i) => i.type === "row")).toBe(true);
    }
  });
});
