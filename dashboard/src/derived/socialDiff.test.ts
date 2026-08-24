import { describe, expect, it } from "vitest";
import { computeSocialDiff, filterDiffRows, grudgeAt, grudgeCooled, matchRuleForEvent } from "./socialDiff";
import type { FrameRecord } from "../log/types";

/**
 * Synthetic two-tick fixtures, one per delta type the packet asks for:
 * belief confidence/stage change, a new belief, a decay-only day (no
 * events, real confidence movement), grudge formed, grudge decayed-
 * crossing, an obligation transition, and a reputation move -- plus
 * rule-chip matching and NPC/rule/type filtering. Records use the real
 * envelope shape (`FrameRecord`), same idiom as `../log/reconstruct.test.ts`.
 */
function record(tick: number, seq: number, stream: "events" | "trace", payload: Record<string, unknown>): FrameRecord {
  return { schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream, seq, payload };
}

describe("computeSocialDiff", () => {
  it("belief confidence/stage change: witnessed then corroborated inside the window, with a matching rule chip and event link", () => {
    const records: FrameRecord[] = [
      record(0, 0, "trace", {
        record_type: "belief_formed",
        belief_id: "belief-1",
        claim_id: "claim-1",
        holder_id: "npc-a",
        evidence_id: "ev-1",
        claim_kind: "theft",
        claim_slots: {},
        canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 },
      }),
      record(10, 0, "trace", {
        record_type: "belief_corroborated",
        belief_id: "belief-1",
        confidence_after: 0.99,
      }),
      record(10, 1, "trace", {
        record_type: "rule_evaluated",
        rule: "reputation-evidence-accumulation",
        inputs: { belief_id: "belief-1", holder_id: "npc-a" },
        fired: true,
        result: { belief_id: "belief-1" },
      }),
    ];

    const rows = computeSocialDiff(records, 10, 5);
    const row = rows.find((r) => r.key === "belief:belief-1");
    expect(row).toBeDefined();
    expect(row!.type).toBe("belief");
    expect(row!.npcs).toEqual(["npc-a"]);
    expect(row!.delta).toBeGreaterThan(0); // corroboration raised confidence
    expect(row!.event).toEqual({ tick: 10, seq: 0, recordType: "belief_corroborated" });
    expect(row!.rule).toEqual({ rule: "reputation-evidence-accumulation", tick: 10, seq: 1 });
  });

  it("new belief: present at T1, absent at T2 -- before is 0, after is the witnessed confidence", () => {
    const records: FrameRecord[] = [
      record(6, 0, "trace", {
        record_type: "belief_formed",
        belief_id: "belief-new",
        claim_id: "claim-1",
        holder_id: "npc-b",
        evidence_id: "ev-2",
        claim_kind: "theft",
        claim_slots: {},
        canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 },
      }),
    ];
    const rows = computeSocialDiff(records, 10, 5);
    const row = rows.find((r) => r.key === "belief:belief-new");
    expect(row).toBeDefined();
    expect(row!.before).toBe(0);
    expect(row!.after).toBeGreaterThan(0);
    expect(row!.event).toEqual({ tick: 6, seq: 0, recordType: "belief_formed" });
  });

  it("decay-only day: a belief exists before T2 and no record touches it in the window, but confidence still moves (real decay, not an event)", () => {
    const records: FrameRecord[] = [
      record(0, 0, "trace", {
        record_type: "belief_formed",
        belief_id: "belief-quiet",
        claim_id: "claim-1",
        holder_id: "npc-c",
        evidence_id: "ev-3",
        claim_kind: "theft",
        claim_slots: {},
        canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 },
      }),
    ];
    // T2 = 200, T1 = 400 -- well past the belief's formation, zero trace records in (200, 400].
    const rows = computeSocialDiff(records, 400, 200);
    const row = rows.find((r) => r.key === "belief:belief-quiet");
    expect(row).toBeDefined();
    expect(row!.event).toBeNull();
    expect(row!.rule).toBeNull();
    expect(row!.delta).toBeLessThan(0); // pure decay: confidence only ever drops
  });

  it("grudge formed inside the window: before 0, after the formation severity, event + rule linked", () => {
    const records: FrameRecord[] = [
      record(8, 0, "trace", {
        record_type: "grudge_formed",
        id: "grudge-1",
        holder_id: "npc-a",
        target_id: "npc-b",
        source_belief_id: "obl-1",
        grievance_type: "obligation_violated",
        severity: 0.8,
        emotional_strength: 1.0,
        evidentiary_strength: 0.6,
        last_rehearsed: 8,
        forgiveness_threshold: 0.2,
      }),
      record(8, 1, "trace", {
        record_type: "rule_evaluated",
        rule: "obligation-issue-fulfill-violate",
        inputs: { obligation_id: "obl-1", issuer_id: "npc-a", debtor_id: "npc-b" },
        fired: true,
        result: { grudge_id: "grudge-1" },
      }),
    ];
    const rows = computeSocialDiff(records, 10, 5);
    const row = rows.find((r) => r.key.startsWith("grudge:"));
    expect(row).toBeDefined();
    expect(row!.npcs).toEqual(["npc-a", "npc-b"]);
    expect(row!.before).toBe(0);
    expect(row!.after).toBeGreaterThan(0);
    expect(row!.event).toEqual({ tick: 8, seq: 0, recordType: "grudge_formed" });
    expect(row!.rule).toEqual({ rule: "obligation-issue-fulfill-violate", tick: 8, seq: 1 });
  });

  it("grudge decayed-crossing: severity was above the forgiveness threshold at T2 and decays below it by T1, with no event in the window", () => {
    const records: FrameRecord[] = [
      record(0, 0, "trace", {
        record_type: "grudge_formed",
        id: "grudge-2",
        holder_id: "npc-a",
        target_id: "npc-c",
        source_belief_id: "obl-2",
        grievance_type: "insult",
        severity: 0.25,
        emotional_strength: 0.3,
        evidentiary_strength: 0.2,
        last_rehearsed: 0,
        forgiveness_threshold: 0.2,
      }),
    ];
    // Emotional half-life 672, evidentiary half-life 336 (ported from
    // chronicle/social.py): at t=100 decayed severity is ~0.217 (still
    // above the 0.2 forgiveness threshold), and by t=1000 it has decayed
    // to ~0.066 (below it) -- the crossing happens strictly inside (100, 1000].
    const rows = computeSocialDiff(records, 1000, 100);
    const row = rows.find((r) => r.key.startsWith("grudge:"));
    expect(row).toBeDefined();
    expect(row!.event).toBeNull();
    expect(row!.rule).toBeNull();
    expect(row!.delta).toBeLessThan(0);
    expect(row!.detail).toContain("threshold");
  });

  it("grudgeAt/grudgeCooled: severity decays from last_rehearsed and crosses forgiveness at the expected point", () => {
    const grudge = {
      id: "g",
      holder_id: "a",
      target_id: "b",
      source_belief_id: "s",
      grievance_type: "insult",
      severity: 0.5,
      emotional_strength: 0.5,
      evidentiary_strength: 0.5,
      last_rehearsed: 0,
      forgiveness_threshold: 0.2,
    };
    expect(grudgeAt(grudge, 0)).toMatchObject({ emotional_strength: 0.5, evidentiary_strength: 0.5, severity: 0.5 });
    expect(grudgeCooled(grudge, 0)).toBe(false);
    expect(grudgeCooled(grudge, 10000)).toBe(true); // long past both half-lives
  });

  it("obligation transition: active -> violated, with a synthetic negative signed delta and a matching rule chip", () => {
    const records: FrameRecord[] = [
      record(0, 0, "events", {
        record_type: "obligation_issued",
        id: "obl-3",
        issuer_id: "npc-a",
        debtor_id: "npc-b",
        beneficiary_id: null,
        action: "repay a debt",
        condition: null,
        deadline: null,
        status: "active",
        witnesses: [],
        sanctions: null,
        created_at: 0,
      }),
      record(8, 0, "trace", {
        record_type: "obligation_resolved",
        obligation_id: "obl-3",
        status: "violated",
        gamets: 8,
        excuse: null,
      }),
      record(8, 1, "trace", {
        record_type: "rule_evaluated",
        rule: "obligation-issue-fulfill-violate",
        inputs: { obligation_id: "obl-3", issuer_id: "npc-a", debtor_id: "npc-b" },
        fired: true,
        result: { status: "violated" },
      }),
    ];
    const rows = computeSocialDiff(records, 10, 5);
    const row = rows.find((r) => r.key === "obligation:obl-3");
    expect(row).toBeDefined();
    expect(row!.delta).toBeLessThan(0);
    expect(row!.detail).toBe("active → violated");
    expect(row!.event).toEqual({ tick: 8, seq: 0, recordType: "obligation_resolved" });
    expect(row!.rule?.rule).toBe("obligation-issue-fulfill-violate");
  });

  it("reputation move: alpha/beta shift raises the mean, event + rule linked", () => {
    const records: FrameRecord[] = [
      record(0, 0, "trace", {
        record_type: "reputation_updated",
        observer_id: "npc-a",
        subject_id: "npc-b",
        context: "civic",
        kind: "witnessed",
        positive: true,
        alpha: 1.0,
        beta: 1.0,
        direct_count: 0,
        witness_count: 0,
        certified_count: 0,
        uncertainty: 0.5,
        last_updated: 0,
      }),
      record(7, 0, "trace", {
        record_type: "reputation_updated",
        observer_id: "npc-a",
        subject_id: "npc-b",
        context: "civic",
        kind: "witnessed",
        positive: true,
        alpha: 3.0,
        beta: 1.0,
        direct_count: 1,
        witness_count: 0,
        certified_count: 0,
        uncertainty: 0.4,
        last_updated: 7,
      }),
      record(7, 1, "trace", {
        record_type: "rule_evaluated",
        rule: "reputation-evidence-accumulation",
        inputs: { observer_id: "npc-a", subject_id: "npc-b", context: "civic" },
        fired: true,
        result: { alpha: 3.0, beta: 1.0 },
      }),
    ];
    const rows = computeSocialDiff(records, 10, 5);
    const row = rows.find((r) => r.type === "reputation");
    expect(row).toBeDefined();
    expect(row!.npcs).toEqual(["npc-a", "npc-b"]);
    expect(row!.delta).toBeGreaterThan(0);
    expect(row!.event).toEqual({ tick: 7, seq: 0, recordType: "reputation_updated" });
    expect(row!.rule?.rule).toBe("reputation-evidence-accumulation");
  });

  it("no double-counting: a reputation with no change anywhere in the window produces no row", () => {
    const records: FrameRecord[] = [
      record(0, 0, "trace", {
        record_type: "reputation_updated",
        observer_id: "npc-a",
        subject_id: "npc-b",
        context: "civic",
        kind: "witnessed",
        positive: true,
        alpha: 1.0,
        beta: 1.0,
        direct_count: 0,
        witness_count: 0,
        certified_count: 0,
        uncertainty: 0.5,
        last_updated: 0,
      }),
    ];
    const rows = computeSocialDiff(records, 10, 5);
    expect(rows.filter((r) => r.type === "reputation")).toHaveLength(0);
  });

  // -------------------------------------------------------------------
  // Role rows (lane 52, ui-spec §3.10: "role rows join the diff panel")

  it("role succession inside the window: a role row with a working event link off event_type (not record_type)", () => {
    const records: FrameRecord[] = [
      record(0, 0, "events", {
        event_type: "role_installed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        role_id: "jarl_of_whiterun",
        title: "Jarl of Whiterun",
        institution_id: "whiterun_court",
        duties: [{ name: "hold_court", lapse_status_kind: "duty_lapsed" }],
        holder_id: "jarl_balgruuf",
      }),
      record(7, 0, "events", {
        event_type: "npc_died",
        gamets: 7,
        wall_ts: 0,
        origin: null,
        npc_id: "jarl_balgruuf",
        cause: "assassination",
        killer_id: "the_player",
        location_id: "dragonsreach",
      }),
      record(7, 1, "events", {
        event_type: "status_changed",
        gamets: 7,
        wall_ts: 0,
        origin: null,
        npc_id: "irileth",
        status_kind: "role_appointed",
        detail: "jarl_of_whiterun",
        location_id: null,
      }),
    ];

    const rows = computeSocialDiff(records, 10, 5);
    const row = rows.find((r) => r.key === "role:jarl_of_whiterun");
    expect(row).toBeDefined();
    expect(row!.type).toBe("role");
    expect(row!.npcs).toEqual(["irileth", "jarl_balgruuf"]);
    expect(row!.detail).toBe("jarl_balgruuf → irileth");
    // The event link must resolve off `event_type`, not `record_type` --
    // role events have no `record_type` at all, so a naive reuse of
    // `toEventLink` would render this as "unknown" (see this module's
    // header finding).
    expect(row!.event).toEqual({ tick: 7, seq: 1, recordType: "status_changed" });
  });

  it("a role installed for the first time inside the window is a new row (T2 never saw it)", () => {
    const records: FrameRecord[] = [
      record(7, 0, "events", {
        event_type: "role_installed",
        gamets: 7,
        wall_ts: 0,
        origin: null,
        role_id: "steward_of_whiterun",
        title: "Steward of Whiterun",
        institution_id: "whiterun_court",
        duties: [],
        holder_id: "proventus",
      }),
    ];
    const rows = computeSocialDiff(records, 10, 5);
    const row = rows.find((r) => r.key === "role:steward_of_whiterun");
    expect(row).toBeDefined();
    expect(row!.detail).toBe("installed, holder proventus");
    expect(row!.before).toBe(0);
    expect(row!.after).toBe(1);
  });

  it("a vacancy (death, no successor yet in the window) produces a role row with a negative delta and no succession row", () => {
    const records: FrameRecord[] = [
      record(0, 0, "events", {
        event_type: "role_installed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        role_id: "steward_of_whiterun",
        title: "Steward of Whiterun",
        institution_id: "whiterun_court",
        duties: [],
        holder_id: "proventus",
      }),
      record(7, 0, "events", {
        event_type: "npc_died",
        gamets: 7,
        wall_ts: 0,
        origin: null,
        npc_id: "proventus",
        cause: "illness",
        killer_id: null,
        location_id: "dragonsreach",
      }),
    ];
    const rows = computeSocialDiff(records, 10, 5);
    const row = rows.find((r) => r.key === "role:steward_of_whiterun")!;
    expect(row.detail).toBe("proventus → (vacant)");
    expect(row.before).toBe(1);
    expect(row.after).toBe(-1);
    expect(row.delta).toBeLessThan(0);
    expect(row.event).toEqual({ tick: 7, seq: 0, recordType: "npc_died" });
  });

  it("a duty_lapsed event inside the window produces its own role row, correlated to the role owning that duty", () => {
    const records: FrameRecord[] = [
      record(0, 0, "events", {
        event_type: "role_installed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        role_id: "jarl_of_whiterun",
        title: "Jarl of Whiterun",
        institution_id: "whiterun_court",
        duties: [{ name: "hold_court", lapse_status_kind: "duty_lapsed" }],
        holder_id: "jarl_balgruuf",
      }),
      record(7, 0, "events", {
        event_type: "status_changed",
        gamets: 7,
        wall_ts: 0,
        origin: null,
        npc_id: "jarl_balgruuf",
        status_kind: "duty_lapsed",
        detail: "hold_court",
        location_id: null,
      }),
    ];
    const rows = computeSocialDiff(records, 10, 5);
    const row = rows.find((r) => r.key.startsWith("role-duty-lapse:"));
    expect(row).toBeDefined();
    expect(row!.type).toBe("role");
    expect(row!.npcs).toEqual(["jarl_balgruuf"]);
    expect(row!.label).toContain("hold_court");
    expect(row!.label).toContain("Jarl of Whiterun");
    expect(row!.event).toEqual({ tick: 7, seq: 0, recordType: "status_changed" });
  });

  it("no role events at all produces zero role rows", () => {
    const rows = computeSocialDiff([], 10, 5);
    expect(rows.filter((r) => r.type === "role")).toHaveLength(0);
  });
});

describe("matchRuleForEvent", () => {
  it("matches a fired rule_evaluated at the same tick sharing an id, generically (no rule-name hardcoding)", () => {
    const records: FrameRecord[] = [
      record(5, 0, "trace", { record_type: "rule_evaluated", rule: "some-future-rule", inputs: { x: "npc-z" }, fired: true, result: null }),
      record(5, 1, "trace", { record_type: "rule_evaluated", rule: "wrong-rule", inputs: { x: "someone-else" }, fired: true, result: null }),
    ];
    expect(matchRuleForEvent(records, 5, ["npc-z"])).toEqual({ rule: "some-future-rule", tick: 5, seq: 0 });
  });

  it("ignores a matching id when fired is false", () => {
    const records: FrameRecord[] = [record(5, 0, "trace", { record_type: "rule_evaluated", rule: "r", inputs: { x: "npc-z" }, fired: false, result: null })];
    expect(matchRuleForEvent(records, 5, ["npc-z"])).toBeNull();
  });

  it("ignores a match at a different tick", () => {
    const records: FrameRecord[] = [record(6, 0, "trace", { record_type: "rule_evaluated", rule: "r", inputs: { x: "npc-z" }, fired: true, result: null })];
    expect(matchRuleForEvent(records, 5, ["npc-z"])).toBeNull();
  });
});

describe("filterDiffRows", () => {
  const rows = computeSocialDiff(
    [
      { schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick: 0, stream: "trace", seq: 0, payload: { record_type: "belief_formed", belief_id: "b1", claim_id: "c1", holder_id: "npc-a", evidence_id: "e1", claim_kind: "theft", claim_slots: {}, canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 } } },
      { schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick: 6, stream: "trace", seq: 0, payload: { record_type: "belief_corroborated", belief_id: "b1", confidence_after: 0.99 } },
      { schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick: 6, stream: "trace", seq: 1, payload: { record_type: "rule_evaluated", rule: "some-rule", inputs: { belief_id: "b1" }, fired: true, result: null } },
    ],
    10,
    5,
  );

  it("filters by npc", () => {
    expect(filterDiffRows(rows, { npc: "npc-a" })).toHaveLength(1);
    expect(filterDiffRows(rows, { npc: "npc-nonexistent" })).toHaveLength(0);
  });

  it("filters by rule", () => {
    expect(filterDiffRows(rows, { rule: "some-rule" })).toHaveLength(1);
    expect(filterDiffRows(rows, { rule: "other-rule" })).toHaveLength(0);
  });

  it("filters by type", () => {
    expect(filterDiffRows(rows, { type: "belief" })).toHaveLength(1);
    expect(filterDiffRows(rows, { type: "grudge" })).toHaveLength(0);
  });
});
