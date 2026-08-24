import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { buildRoleCards } from "./roles";
import type { FrameRecord } from "../log/types";

/**
 * `buildRoleCards` against the real `runs/north-star-01` T6 north-star run
 * (lane 49's fixture, packet-pinned as this lane's real test data) -- same
 * "runs/ is gitignored, skip rather than fail when absent" precedent as
 * `layer4.realRun.test.ts`/`socialDiff.realRun.test.ts`.
 *
 * Confirmed directly against `events.jsonl`: two `role_installed` records
 * at tick 0 (`steward_of_whiterun`/proventus, `jarl_of_whiterun`/
 * jarl_balgruuf), an `npc_died` for jarl_balgruuf, a
 * `status_changed(duty_lapsed)` for jarl_balgruuf/`hold_court`, and a
 * `status_changed(role_appointed)` for irileth -> `jarl_of_whiterun`, all
 * at tick 0 (seq 3/4/5) -- immediate succession, no vacancy gap. This is
 * also the run this lane's live-browser verification (`/roles?run=
 * north-star-01`) and its `runReader` keyframe-boundary regression test
 * both use: the run's first keyframe is at tick 23, well after these
 * tick-0 role events.
 */
const RUN_DIR = path.resolve(process.cwd(), "../runs/north-star-01");
const EVENTS_FILE = path.join(RUN_DIR, "events.jsonl");
const runExists = existsSync(EVENTS_FILE);

function loadRecords(file: string): FrameRecord[] {
  return readFileSync(file, "utf8")
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as FrameRecord);
}

describe.skipIf(!runExists)("buildRoleCards against runs/north-star-01 (real T6 run)", () => {
  const allEvents = runExists ? loadRecords(EVENTS_FILE) : [];
  const eventRecords = allEvents.filter((r) => r.payload.record_type !== "keyframe");

  it("produces exactly the two installed roles, at a late tick past every keyframe", () => {
    const cards = buildRoleCards(eventRecords, 239);
    expect(cards.map((c) => c.roleId)).toEqual(["jarl_of_whiterun", "steward_of_whiterun"]);
  });

  it("jarl_of_whiterun: irileth succeeded jarl_balgruuf the same tick he died, hold_court stays flagged lapsed", () => {
    const card = buildRoleCards(eventRecords, 239).find((c) => c.roleId === "jarl_of_whiterun")!;
    expect(card.holderId).toBe("irileth");
    expect(card.vacatedAt).toBeNull();
    expect(card.successions).toEqual([{ npcId: "irileth", tick: 0, seq: 5 }]);
    expect(card.vacancyHistory).toEqual([{ vacatedAt: 0, filledAt: 0, filledBy: "irileth" }]);
    const duty = card.duties.find((d) => d.name === "hold_court")!;
    expect(duty.lapsed).toBe(true);
    expect(duty.lapseEvent).toEqual({ tick: 0, seq: 4 });
  });

  it("steward_of_whiterun: untouched, proventus still holds it, no lapse", () => {
    const card = buildRoleCards(eventRecords, 239).find((c) => c.roleId === "steward_of_whiterun")!;
    expect(card.holderId).toBe("proventus");
    expect(card.vacancyHistory).toEqual([]);
    expect(card.successions).toEqual([]);
    expect(card.duties.every((d) => !d.lapsed)).toBe(true);
  });
});
