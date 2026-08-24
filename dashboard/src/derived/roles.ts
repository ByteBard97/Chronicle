/**
 * Role cards (lane 52, ui-spec §3.10, Tier 5): "role, holder (linked),
 * duties with lapse state, vacancy history, succession record" -- built
 * directly from a run's raw events (`role_installed` / `npc_died` /
 * `status_changed`), NOT from `reconstruct.ts`'s `SocialState.roles`.
 *
 * Why not reuse `SocialState.roles`: that map is a pure roster snapshot
 * (current `holder_id`/`vacated_at` only) -- `applyRoleEvent`'s replace-
 * mutations, mirroring `chronicle/roles.py`'s own `Role` dataclass,
 * deliberately overwrite `vacated_at` to `null` on every succession. A
 * role's vacancy HISTORY (every past vacancy span, not just whether it's
 * currently vacant) is therefore mathematically unrecoverable from the
 * final roster alone -- this module does its own single chronological
 * fold over the raw events, recording each vacancy span and succession as
 * it happens, exactly the "do your own single-pass fold" this lane's
 * packet review flagged.
 *
 * Duty lapse (packet-pinned, matches `chronicle/roles.py`/`framelog.py`'s
 * own division of labor): `Role` has no lapse field, and
 * `ReconstructedState.roles` never gains one either -- a `status_changed`
 * event with `status_kind === "duty_lapsed"` carries `detail` = the
 * LAPSED DUTY'S NAME (not a role id) and `npc_id` = the NPC whose duty
 * lapsed. This module correlates such an event to whichever role (a) owns
 * a duty by that name and (b) had that same NPC as its most recent
 * non-vacant holder at the moment the event fired (`lastNonNullHolder`,
 * tracked inline during the single chronological pass, so ordering ties
 * at the same tick resolve by `seq`, not by tick alone -- see the north-
 * star-01 fixture: `npc_died`(seq 3) / `status_changed(duty_lapsed)`
 * (seq 4) / `status_changed(role_appointed)` (seq 5) all fire at tick 0,
 * and only a seq-ordered pass tells the lapse apart from the succession
 * that immediately follows it in the same tick).
 *
 * A lapse, once recorded, is shown for the rest of the run -- a later
 * succession does NOT retroactively clear it. This is a deliberate,
 * documented design choice (not something `chronicle/roles.py` itself
 * defines, since it has no lapse-clearing rule at all): the north-star-01
 * fixture appoints irileth to `jarl_of_whiterun` the SAME tick
 * `hold_court` lapses under jarl_balgruuf, and the acceptance criterion
 * ("the lapsed hold_court duty visible") reads as "once a duty lapses,
 * that historical fact stays visible," not "only while the same holder
 * who let it lapse still holds the office."
 */
import type { FrameRecord, KeyframeRoleDuty } from "../log/types";

function isString(v: unknown): v is string {
  return typeof v === "string";
}

export interface RoleDuty {
  name: string;
  lapseStatusKind: string;
  lapsed: boolean;
  lapseEvent: { tick: number; seq: number } | null;
}

export interface RoleVacancySpan {
  vacatedAt: number;
  filledAt: number | null;
  filledBy: string | null;
}

export interface RoleSuccession {
  npcId: string;
  tick: number;
  seq: number;
}

export interface RoleCard {
  roleId: string;
  title: string;
  institutionId: string;
  holderId: string | null;
  vacatedAt: number | null;
  duties: RoleDuty[];
  vacancyHistory: RoleVacancySpan[];
  successions: RoleSuccession[];
}

interface RoleAccum {
  title: string;
  institutionId: string;
  dutyDefs: KeyframeRoleDuty[];
  holderId: string | null;
  vacatedAt: number | null;
  lastNonNullHolder: string | null;
  vacancyHistory: RoleVacancySpan[];
  successions: RoleSuccession[];
  dutyLapses: { name: string; tick: number; seq: number }[];
}

/** Every events-stream record with a string `event_type`, sorted by `(tick, seq)` -- schema §2's ordering discipline, defensive since callers may hand in an unsorted `eventRecords` array. */
function sortedRoleEvents(records: FrameRecord[]): FrameRecord[] {
  return [...records]
    .filter((r) => r.stream === "events" && isString(r.payload.event_type))
    .sort((a, b) => (a.tick !== b.tick ? a.tick - b.tick : a.seq - b.seq));
}

function parseDuties(raw: unknown): KeyframeRoleDuty[] {
  if (!Array.isArray(raw)) return [];
  const out: KeyframeRoleDuty[] = [];
  for (const entry of raw) {
    if (entry === null || typeof entry !== "object") continue;
    const name = (entry as Record<string, unknown>).name;
    const lapseKind = (entry as Record<string, unknown>).lapse_status_kind;
    if (isString(name) && isString(lapseKind)) out.push({ name, lapse_status_kind: lapseKind });
  }
  return out;
}

/**
 * The full role-card set as of `uptoTick`: roster, duties (with correlated
 * lapse state), vacancy history, and succession record -- everything
 * ui-spec §3.10 names, from one chronological pass over the run's raw
 * events (see this module's header for why a fresh fold, not
 * `SocialState.roles`, is required).
 */
export function buildRoleCards(records: FrameRecord[], uptoTick: number): RoleCard[] {
  const roles = new Map<string, RoleAccum>();

  for (const record of sortedRoleEvents(records)) {
    if (record.tick > uptoTick) continue;
    const payload = record.payload;
    const eventType = payload.event_type;

    if (eventType === "role_installed") {
      const roleId = payload.role_id;
      const title = payload.title;
      const institutionId = payload.institution_id;
      const holderId = payload.holder_id;
      if (!isString(roleId) || !isString(title) || !isString(institutionId)) continue;
      const parsedHolder = isString(holderId) ? holderId : null;
      roles.set(roleId, {
        title,
        institutionId,
        dutyDefs: parseDuties(payload.duties),
        holderId: parsedHolder,
        vacatedAt: null,
        lastNonNullHolder: parsedHolder,
        vacancyHistory: [],
        successions: [],
        dutyLapses: [],
      });
      continue;
    }

    if (eventType === "npc_died") {
      const npcId = payload.npc_id;
      if (!isString(npcId)) continue;
      const gamets = payload.gamets;
      const vacatedAt = typeof gamets === "number" ? gamets : record.tick;
      for (const [, acc] of roles) {
        if (acc.holderId === npcId) {
          acc.holderId = null;
          acc.vacatedAt = vacatedAt;
          acc.vacancyHistory.push({ vacatedAt, filledAt: null, filledBy: null });
        }
      }
      continue;
    }

    if (eventType === "status_changed") {
      const statusKind = payload.status_kind;
      const npcId = payload.npc_id;
      const detail = payload.detail;

      if (statusKind === "role_appointed") {
        if (!isString(detail) || !isString(npcId)) continue;
        const acc = roles.get(detail);
        if (acc === undefined) continue;
        acc.holderId = npcId;
        acc.vacatedAt = null;
        acc.lastNonNullHolder = npcId;
        const openSpan = acc.vacancyHistory[acc.vacancyHistory.length - 1];
        if (openSpan !== undefined && openSpan.filledAt === null) {
          openSpan.filledAt = record.tick;
          openSpan.filledBy = npcId;
        }
        acc.successions.push({ npcId, tick: record.tick, seq: record.seq });
        continue;
      }

      if (statusKind === "duty_lapsed") {
        if (!isString(detail) || !isString(npcId)) continue;
        for (const [, acc] of roles) {
          if (acc.lastNonNullHolder === npcId && acc.dutyDefs.some((d) => d.name === detail)) {
            acc.dutyLapses.push({ name: detail, tick: record.tick, seq: record.seq });
          }
        }
        continue;
      }
    }
  }

  const cards: RoleCard[] = [];
  for (const [roleId, acc] of roles) {
    const duties: RoleDuty[] = acc.dutyDefs.map((d) => {
      const matches = acc.dutyLapses.filter((e) => e.name === d.name);
      const latest = matches[matches.length - 1];
      return {
        name: d.name,
        lapseStatusKind: d.lapse_status_kind,
        lapsed: latest !== undefined,
        lapseEvent: latest !== undefined ? { tick: latest.tick, seq: latest.seq } : null,
      };
    });

    cards.push({
      roleId,
      title: acc.title,
      institutionId: acc.institutionId,
      holderId: acc.holderId,
      vacatedAt: acc.vacatedAt,
      duties,
      vacancyHistory: acc.vacancyHistory,
      successions: acc.successions,
    });
  }

  return cards.sort((a, b) => a.roleId.localeCompare(b.roleId));
}
