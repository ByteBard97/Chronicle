import { describe, expect, it } from "vitest";
import { buildRoleCards } from "./roles";
import type { FrameRecord } from "../log/types";

function eventRecord(tick: number, seq: number, payload: Record<string, unknown>): FrameRecord {
  return {
    schema_version: 1,
    seed_id: "s",
    save_uuid: "save-1",
    generation: 0,
    tick,
    stream: "events",
    seq,
    payload,
  };
}

describe("buildRoleCards", () => {
  it("a plain install with no lifecycle events: one card, no lapses/vacancies/successions", () => {
    const records = [
      eventRecord(0, 1, {
        event_type: "role_installed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        role_id: "steward_of_whiterun",
        title: "Steward of Whiterun",
        institution_id: "whiterun_court",
        duties: [{ name: "collect_taxes", lapse_status_kind: "duty_lapsed" }],
        holder_id: "proventus",
      }),
    ];
    const cards = buildRoleCards(records, 10);
    expect(cards).toHaveLength(1);
    const card = cards[0]!;
    expect(card.roleId).toBe("steward_of_whiterun");
    expect(card.title).toBe("Steward of Whiterun");
    expect(card.institutionId).toBe("whiterun_court");
    expect(card.holderId).toBe("proventus");
    expect(card.vacatedAt).toBeNull();
    expect(card.duties).toEqual([
      { name: "collect_taxes", lapseStatusKind: "duty_lapsed", lapsed: false, lapseEvent: null },
    ]);
    expect(card.vacancyHistory).toEqual([]);
    expect(card.successions).toEqual([]);
  });

  it("full lifecycle: install -> death (vacancy) -> duty lapse -> succession, all at the same tick, seq-ordered", () => {
    // Reproduces runs/north-star-01's exact shape (see the packet): three
    // role events plus one duty_lapsed, all tick 0, distinguished only by
    // seq -- npc_died before the lapse, the lapse before the appointment.
    const records = [
      eventRecord(0, 1, {
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
      eventRecord(0, 2, {
        event_type: "npc_died",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        npc_id: "jarl_balgruuf",
        cause: "assassination",
        killer_id: "the_player",
        location_id: "dragonsreach",
      }),
      eventRecord(0, 3, {
        event_type: "status_changed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        npc_id: "jarl_balgruuf",
        status_kind: "duty_lapsed",
        detail: "hold_court",
        location_id: null,
      }),
      eventRecord(0, 4, {
        event_type: "status_changed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        npc_id: "irileth",
        status_kind: "role_appointed",
        detail: "jarl_of_whiterun",
        location_id: null,
      }),
    ];

    const card = buildRoleCards(records, 0)[0]!;
    expect(card.holderId).toBe("irileth");
    expect(card.vacatedAt).toBeNull(); // succession clears the vacancy

    // Vacancy history: one span, opened and closed the same tick.
    expect(card.vacancyHistory).toEqual([{ vacatedAt: 0, filledAt: 0, filledBy: "irileth" }]);

    // Succession record: the one role_appointed event.
    expect(card.successions).toEqual([{ npcId: "irileth", tick: 0, seq: 4 }]);

    // The duty stays flagged as lapsed even though the role has since been
    // filled -- a recorded historical fact, not a "currently unperformed"
    // flag (see this module's header).
    expect(card.duties).toEqual([
      { name: "hold_court", lapseStatusKind: "duty_lapsed", lapsed: true, lapseEvent: { tick: 0, seq: 3 } },
    ]);
  });

  it("a vacancy with no successor yet: holder null, vacancy span still open (filledAt null)", () => {
    const records = [
      eventRecord(0, 1, {
        event_type: "role_installed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        role_id: "steward_of_whiterun",
        title: "Steward of Whiterun",
        institution_id: "whiterun_court",
        duties: [{ name: "collect_taxes", lapse_status_kind: "duty_lapsed" }],
        holder_id: "proventus",
      }),
      eventRecord(5, 1, {
        event_type: "npc_died",
        gamets: 5,
        wall_ts: 0,
        origin: null,
        npc_id: "proventus",
        cause: "illness",
        killer_id: null,
        location_id: "dragonsreach",
      }),
    ];
    const card = buildRoleCards(records, 10)[0]!;
    expect(card.holderId).toBeNull();
    expect(card.vacatedAt).toBe(5);
    expect(card.vacancyHistory).toEqual([{ vacatedAt: 5, filledAt: null, filledBy: null }]);
    expect(card.successions).toEqual([]);
  });

  it("uptoTick excludes later events -- a query before the death still shows the original holder", () => {
    const records = [
      eventRecord(0, 1, {
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
      eventRecord(5, 1, {
        event_type: "npc_died",
        gamets: 5,
        wall_ts: 0,
        origin: null,
        npc_id: "proventus",
        cause: "illness",
        killer_id: null,
        location_id: "dragonsreach",
      }),
    ];
    const card = buildRoleCards(records, 3)[0]!;
    expect(card.holderId).toBe("proventus");
    expect(card.vacancyHistory).toEqual([]);
  });
});
