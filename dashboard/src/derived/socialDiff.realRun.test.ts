import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { computeSocialDiff } from "./socialDiff";
import type { FrameRecord } from "../log/types";

/**
 * `computeSocialDiff` against the real `runs/tier3-demo-01` demo run
 * (lane 34's fixture), at the packet-pinned T1=47/T2=23 window (its two
 * keyframes) -- same "runs/ is gitignored, skip rather than fail when
 * absent" precedent as `../log/layer4.realRun.test.ts`.
 *
 * FINDING (documented, not a bug): every layer-4-affecting record in this
 * run (`belief_formed`/`belief_corroborated`/`transmitted`/`supersession`/
 * `grudge_formed`/`obligation_issued`/`obligation_resolved`/
 * `reputation_updated`) fires at tick <= 4 -- confirmed directly against
 * `trace.jsonl`/`events.jsonl` (zero such records in ticks 5-47). So the
 * packet's T1=47/T2=23 window contains NO belief/grudge/obligation/
 * reputation trace records at all -- it is, in its entirety, the panel's
 * "decay-only day" case: every row below is produced purely by
 * derived-at-T decay (belief confidence, grudge severity), not by an
 * event in the window. That's exactly the property ui-spec §3.7 is
 * pinned on ("a quiet day shows real decay, not just events"), so this
 * window is still a meaningful real-data proof for that half of the
 * panel's contract -- it just doesn't exercise the rule-chip/event-link
 * half (see the synthetic tests in `socialDiff.test.ts` for that).
 */
const RUN_DIR = path.resolve(process.cwd(), "../runs/tier3-demo-01");
const EVENTS_FILE = path.join(RUN_DIR, "events.jsonl");
const TRACE_FILE = path.join(RUN_DIR, "trace.jsonl");
const runExists = existsSync(EVENTS_FILE) && existsSync(TRACE_FILE);

function loadRecords(file: string): FrameRecord[] {
  return readFileSync(file, "utf8")
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as FrameRecord);
}

describe.skipIf(!runExists)("computeSocialDiff against runs/tier3-demo-01 (real demo run)", () => {
  const allEvents = runExists ? loadRecords(EVENTS_FILE) : [];
  const allTrace = runExists ? loadRecords(TRACE_FILE) : [];
  // Mirrors stores/mapData.ts's contract: eventRecords excludes keyframes.
  const allRecords = [...allEvents.filter((r) => r.payload.record_type !== "keyframe"), ...allTrace];

  const rows = runExists ? computeSocialDiff(allRecords, 47, 23) : [];

  it("produces exactly one row per of the run's 23 beliefs, all decay-only", () => {
    const beliefRows = rows.filter((r) => r.type === "belief");
    expect(beliefRows).toHaveLength(23);
    for (const row of beliefRows) {
      // No belief-touching trace record exists in (23, 47] (header finding)
      // -- every belief row must be pure decay: no event, no rule, and a
      // strictly negative delta (confidence only ever decays with no
      // rehearsal in the window).
      expect(row.event).toBeNull();
      expect(row.rule).toBeNull();
      expect(row.delta).toBeLessThan(0);
      expect(row.after).toBeLessThan(row.before);
    }
  });

  it("produces exactly one grudge row (the run's single grudge), decay-only and not yet crossing forgiveness", () => {
    const grudgeRows = rows.filter((r) => r.type === "grudge");
    expect(grudgeRows).toHaveLength(1);
    const row = grudgeRows[0]!;
    expect(row.npcs).toEqual(["adrianne", "ulfberth"]);
    expect(row.event).toBeNull();
    expect(row.rule).toBeNull();
    // Severity only decays (no rehearsal in the window) -- strictly negative delta, no threshold crossing this soon.
    expect(row.delta).toBeLessThan(0);
    expect(row.detail).not.toContain("threshold");
  });

  it("produces zero obligation/reputation rows (both are static, discrete/stored values unchanged in this window)", () => {
    expect(rows.filter((r) => r.type === "obligation")).toHaveLength(0);
    expect(rows.filter((r) => r.type === "reputation")).toHaveLength(0);
  });

  it("every row is sorted with decay-only (eventless) rows grouped, and every row has a stable unique key", () => {
    const keys = rows.map((r) => r.key);
    expect(new Set(keys).size).toBe(keys.length);
  });
});
