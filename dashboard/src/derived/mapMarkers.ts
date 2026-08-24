/**
 * Map markers (lane 14, ui-spec §3.1): SocialState + raw trace/event
 * observations + the map-JSON pixel source of truth -> render-ready marker
 * models for the map view.
 *
 * Deliberately does NOT go through `reconstruct.ts` for position: like
 * `feedReader.ts` (lane 11), this module reads the raw trace/events streams
 * itself, because `encounter_rolled`/`transmitted`/`npc_died` are no-ops (or
 * absent) in `SocialState` — there is no "current location" field to read
 * off the reconstructed state.
 *
 * Cast enumeration (coordinator correction over the work packet's original
 * wording, documented in the lane report): the packet's literal recipe
 * ("belief holder_ids + trace participant ids") only finds 5 of the 6 NPCs
 * in `runs/whiterun-jarl-01` — it silently drops `jarl_balgruuf`, the
 * scenario's murder victim, who never holds a belief and never appears as a
 * trace participant (he dies at tick 0, before any of that). The union used
 * here adds two more sources: relationship endpoints (`relationship_formed`
 * `from_id`/`to_id`) and `npc_died` event subject ids, both of which do
 * catch him.
 *
 * Position: "latest observation <= T wins, tie-break by frequency" is
 * implemented literally. Note (finding, not fixed here): the packet frames
 * NPC locations as "static per run", but `runs/whiterun-jarl-01` itself
 * contradicts that — `proventus` is observed at `dragonsreach` through
 * roughly tick 150 and at `bannered_mare` by tick 200 (he relays the claim
 * there). The literal latest-observation-<=T rule this module implements
 * is what actually produces the right answer at both ticks; a truly static
 * per-run position would get tick 200 wrong.
 *
 * An NPC enumerated into the cast (a run-wide, T-independent union) is only
 * rendered as a marker once a location is resolvable *at that T* — either a
 * trace observation at or before T, or (for an NPC who has none at all,
 * e.g. because they die before ever being observed) their `npc_died`
 * event's location, which is treated as their fixed position for the whole
 * run. An NPC with neither is simply absent from the map at that T, not
 * placed at a dummy origin. `jarl_balgruuf` is exactly the second case: no
 * belief, no trace observation, ever — he renders at `dragonsreach` (his
 * `npc_died` location) for the full run, always `"unheard"` (no stage
 * derivation applies to him; `rumorStageAt(null, null, t)` is `"unheard"`
 * by construction), per the coordinator's explicit call not to invent a
 * "deceased" stage or glyph this lane.
 */
import type { FrameRecord } from "../log/types";
import type { SocialState } from "../log/reconstruct";
import type { KeyframeBelief, KeyframeRumorState } from "../log/types";
import { rumorStageAt, type RumorStage } from "./rumorStage";
import { toPct, STAGE_STYLE } from "../fixtures/whiterunMock";

// ---------------------------------------------------------------------------
// The map-JSON shape this module needs (a subset of dashboard/map/whiterun_map.json)

export interface WhiterunMapLocation {
  pixel: number[];
  [extra: string]: unknown;
}

export interface WhiterunMapJson {
  locations: Record<string, WhiterunMapLocation>;
  [extra: string]: unknown;
}

/** S/N only this lane — D (schedule deviation) and G (grudge) need Tier 3/4 state the reader doesn't reconstruct. */
export type MapGlyph = "S" | "N" | null;

/**
 * Lane 35 (ui-spec §3.5's map half): a holder's relationship to the
 * variant selected in the tree, for one claim. `holds-it` includes the
 * canonical (`null`) case matching itself. Populated on `DerivedMarker`
 * only when `DeriveMapMarkersInput.variantId` is provided (see
 * `deriveMapMarkers`) — absent otherwise, so the claim-level lens stays
 * byte-identical to before this lane.
 */
export type VariantHoldClass = "holds-it" | "holds-different" | "holds-none";

export interface DerivedMarker {
  id: string;
  name: string;
  /** Percent within the crop square (see fixtures/whiterunMock.ts's CROP/toPct). */
  left: number;
  top: number;
  stage: RumorStage;
  glyph: MapGlyph;
  selected: boolean;
  /** Set only when the variant lens is active (see `VariantHoldClass`). */
  variantClass?: VariantHoldClass;
}

function isString(v: unknown): v is string {
  return typeof v === "string";
}

// ---------------------------------------------------------------------------
// Cast enumeration

/**
 * The run-wide cast: union of (a) belief holder_ids in SocialState, (b)
 * trace participant ids (teller_id/hearer_id/npc_a/npc_b), (c) relationship
 * endpoints (from_id/to_id), (d) npc_died event subject ids. See module
 * header for why (c) and (d) are necessary beyond the work packet's
 * original (a)+(b) wording.
 */
export function enumerateCast(
  state: SocialState,
  traceRecords: FrameRecord[],
  eventRecords: FrameRecord[],
): string[] {
  const ids = new Set<string>();

  for (const b of state.beliefs.values()) ids.add(b.holder_id);

  for (const r of traceRecords) {
    const p = r.payload;
    for (const key of ["teller_id", "hearer_id", "npc_a", "npc_b"] as const) {
      const v = p[key];
      if (isString(v)) ids.add(v);
    }
    if (p.record_type === "relationship_formed") {
      if (isString(p.from_id)) ids.add(p.from_id);
      if (isString(p.to_id)) ids.add(p.to_id);
    }
  }

  for (const r of eventRecords) {
    if (r.payload.event_type === "npc_died" && isString(r.payload.npc_id)) {
      ids.add(r.payload.npc_id);
    }
  }

  return [...ids];
}

// ---------------------------------------------------------------------------
// Position

const LOCATION_PARTICIPANT_KEYS = ["npc_a", "npc_b", "teller_id", "hearer_id"] as const;

/**
 * The NPC's location, or `null` if none is resolvable: the observed
 * location at the latest trace tick <= atTick where this NPC is a
 * participant and the record carries a `location_id`; ties at that same
 * tick between distinct locations are broken by which location this NPC
 * has been observed at more often overall (up to atTick).
 */
export function locationFromTrace(npcId: string, traceRecords: FrameRecord[], atTick: number): string | null {
  const observations: { tick: number; location: string }[] = [];
  for (const r of traceRecords) {
    if (r.tick > atTick) continue;
    const p = r.payload;
    const loc = p.location_id;
    if (!isString(loc)) continue;
    const isParticipant = LOCATION_PARTICIPANT_KEYS.some((key) => p[key] === npcId);
    if (isParticipant) observations.push({ tick: r.tick, location: loc });
  }
  if (observations.length === 0) return null;

  const maxTick = Math.max(...observations.map((o) => o.tick));
  const atMax = [...new Set(observations.filter((o) => o.tick === maxTick).map((o) => o.location))];
  if (atMax.length === 1) return atMax[0]!;

  const freq = new Map<string, number>();
  for (const o of observations) freq.set(o.location, (freq.get(o.location) ?? 0) + 1);
  return [...atMax].sort((a, b) => (freq.get(b) ?? 0) - (freq.get(a) ?? 0))[0]!;
}

/** The location an NPC died at, or `null` if this run has no `npc_died` event for them. */
export function deathLocation(npcId: string, eventRecords: FrameRecord[]): string | null {
  for (const r of eventRecords) {
    const p = r.payload;
    if (p.event_type === "npc_died" && p.npc_id === npcId && isString(p.location_id)) {
      return p.location_id;
    }
  }
  return null;
}

/** Trace observation wins; an NPC never observed (e.g. dead before any trace record) falls back to their death location. */
export function locationAt(
  npcId: string,
  traceRecords: FrameRecord[],
  eventRecords: FrameRecord[],
  atTick: number,
): string | null {
  return locationFromTrace(npcId, traceRecords, atTick) ?? deathLocation(npcId, eventRecords);
}

// ---------------------------------------------------------------------------
// Seeded jitter (ui-spec §3.1: markers anchor at the door pixel, jitter
// seeded by (npc_id, location_id) — a deterministic hash offset, NOT the
// fixture's per-location round-robin JITTER_RING).

function hashSeed(s: string): number {
  // FNV-1a, 32-bit.
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** Deterministic (npc_id, location_id) -> percent offset, magnitude comparable to the fixture's JITTER_RING. */
export function seededJitter(npcId: string, locationId: string): [number, number] {
  const seed = hashSeed(`${npcId}::${locationId}`);
  const angle = (seed % 360) * (Math.PI / 180);
  const radius = 0.8 + ((seed >>> 9) % 100) / 100;
  return [+(radius * Math.cos(angle)).toFixed(2), +(radius * Math.sin(angle)).toFixed(2)];
}

// ---------------------------------------------------------------------------
// Stage rollup

/**
 * "Worst"-stage ordering across a holder's multiple variants of one claim,
 * matching the visual weight already frozen in STAGE_STYLE (dot size):
 * repeated(13) > heard(11) > dormant(10) > unheard(9) > forgotten(7).
 * Unreached by `runs/whiterun-jarl-01` (no holder there has two variants of
 * `claim-jarl-death`) — covered by a synthetic test instead.
 */
const STAGE_SEVERITY: Record<RumorStage, number> = {
  repeated: 4,
  heard: 3,
  dormant: 2,
  unheard: 1,
  forgotten: 0,
};

function worstStage(stages: RumorStage[]): RumorStage {
  return stages.reduce((worst, s) => (STAGE_SEVERITY[s] > STAGE_SEVERITY[worst] ? s : worst), stages[0]!);
}

/** Every (rumor, matching belief) pair a holder has for one claim, across variants. */
function rumorBeliefPairsFor(
  state: SocialState,
  npcId: string,
  claimId: string,
): { rumor: KeyframeRumorState; belief: KeyframeBelief | null }[] {
  const rumors = [...state.rumors.values()].filter((r) => r.npc_id === npcId && r.claim_id === claimId);
  return rumors.map((rumor) => {
    const belief =
      [...state.beliefs.values()].find(
        (b) => b.holder_id === npcId && b.claim_id === claimId && b.variant_id === rumor.variant_id,
      ) ?? null;
    return { rumor, belief };
  });
}

/** Per-(npc, claim) stage at T: worst stage across every variant the holder has of this claim. */
export function stageForNpcClaim(state: SocialState, npcId: string, claimId: string, atTick: number): RumorStage {
  const pairs = rumorBeliefPairsFor(state, npcId, claimId);
  if (pairs.length === 0) return "unheard";
  return worstStage(pairs.map(({ rumor, belief }) => rumorStageAt(rumor, belief, atTick)));
}

// ---------------------------------------------------------------------------
// Variant lens (lane 35, ui-spec §3.5's map half: node click in the variant
// tree -> map overlay switches to the selected variant).
//
// Distinct from `stageForNpcClaim`'s claim-level rollup (worst stage across
// EVERY variant a holder has): this is a *per-variant* classification —
// does this specific holder currently believe THIS variant (`holds-it`,
// which includes the canonical/null case matching itself), a different one
// (`holds-different`), or nothing on this claim at all (`holds-none`,
// folded onto the existing "unheard" gray). "Currently" is as-of-T because
// `state` here is always the reconstructed state at the caller's T (lane
// 14's `mapData` store) — there is no separate T parameter to thread.

/** A holder's relationship to `variantId` (`null` = canonical) for one claim, at the state's T. */
export function variantClassForNpc(
  state: SocialState,
  npcId: string,
  claimId: string,
  variantId: string | null,
): VariantHoldClass {
  const beliefs = [...state.beliefs.values()].filter((b) => b.holder_id === npcId && b.claim_id === claimId);
  if (beliefs.length === 0) return "holds-none";
  return beliefs.some((b) => b.variant_id === variantId) ? "holds-it" : "holds-different";
}

export interface VariantMarkerStyle {
  fill: string;
  ring: string;
  size: number;
}

/**
 * Fixed dimmed/contrasted style for `holds-different` — deliberately NOT
 * stage-colored (a holder of a superseded/sibling variant should read as
 * "off" regardless of how strongly they hold it), distinct from both the
 * full stage palette and `STAGE_STYLE.unheard`'s gray.
 */
const VARIANT_DIFFERENT_STYLE: VariantMarkerStyle = { fill: "rgba(143,180,217,.28)", ring: "#3d4b58", size: 9 };

/**
 * Marker style for the variant lens: `holds-it` keeps the holder's normal
 * per-stage style (so freshness still reads for the variant you're
 * tracking); `holds-none` forces `STAGE_STYLE.unheard` (matching the
 * claim-level lens's own "knows nothing about this claim" gray, per the
 * pinned decision); `holds-different` is the fixed dimmed/contrasted style
 * above.
 */
export function variantMarkerStyle(stage: RumorStage, variantClass: VariantHoldClass): VariantMarkerStyle {
  if (variantClass === "holds-it") return STAGE_STYLE[stage];
  if (variantClass === "holds-none") return STAGE_STYLE.unheard;
  return VARIANT_DIFFERENT_STYLE;
}

// ---------------------------------------------------------------------------
// Glyph (S/N only this lane; D/G always null — pin, see module header)

const GAME_DAY_TICKS = 24; // ADR-0010: 1 tick = 1 game-hour.
const TOLD_WINDOW_TICKS = 24;

function gameDay(tick: number): number {
  return Math.floor(tick / GAME_DAY_TICKS);
}

/** S ("actively spreading") ▸ N ("newly formed belief this game-day"); D/G never render this lane. */
export function glyphForNpcClaim(state: SocialState, npcId: string, claimId: string, atTick: number): MapGlyph {
  const pairs = rumorBeliefPairsFor(state, npcId, claimId);
  if (pairs.length === 0) return null;

  const toldRecently = pairs.some(
    ({ rumor }) => rumor.last_told !== null && atTick - rumor.last_told >= 0 && atTick - rumor.last_told <= TOLD_WINDOW_TICKS,
  );
  if (toldRecently) return "S";

  const formedToday = pairs.some(({ belief }) => belief !== null && gameDay(belief.first_learned) === gameDay(atTick));
  if (formedToday) return "N";

  return null;
}

// ---------------------------------------------------------------------------
// Display name

/** "irileth" -> "Irileth"; "whiterun_guard_1" -> "Whiterun Guard 1" — no name source exists, so this is a formatting helper, not a lookup. */
export function displayName(npcId: string): string {
  return npcId
    .split("_")
    .filter((part) => part.length > 0)
    .map((part) => part[0]!.toUpperCase() + part.slice(1))
    .join(" ");
}

// ---------------------------------------------------------------------------
// Active claim

/** The run's first claim (insertion order of `state.claims`, a Map — pinned: "this lane, the run's first claim is the active claim"). */
export function firstClaimId(state: SocialState): string | null {
  const first = state.claims.keys().next();
  return first.done ? null : first.value;
}

// ---------------------------------------------------------------------------
// Top-level derivation

export interface DeriveMapMarkersInput {
  state: SocialState;
  traceRecords: FrameRecord[];
  eventRecords: FrameRecord[];
  mapJson: WhiterunMapJson;
  claimId: string;
  atTick: number;
  isSelected: (id: string) => boolean;
  /**
   * Lane 35: the variant lens. `undefined` (the default, and the only value
   * every pre-lane-35 call site passes implicitly) means "lens off" —
   * markers get no `variantClass` and rendering is byte-identical to
   * before this lane. `null` means the canonical variant is selected;
   * a string selects that variant.
   */
  variantId?: string | null;
}

/**
 * StageLegend's real per-stage counts + coverage (ui-spec: "coverage" =
 * cast members who currently know something and haven't forgotten it —
 * total minus unheard minus forgotten, mirroring the fixture's own
 * STAGE_LEGEND reconciliation: 26 - 5 unheard - 1 forgotten = 20).
 *
 * Deliberately over the *full* cast (`enumerateCast`'s result), not just
 * the subset of NPCs `deriveMapMarkers` could place a marker for — stage is
 * defined independently of whether a position is resolvable at T (see
 * `deriveMapMarkers`'s header on why some cast members render at some T and
 * not others).
 */
export function claimStageBreakdown(
  state: SocialState,
  cast: string[],
  claimId: string,
  atTick: number,
): { counts: Record<RumorStage, number>; coverage: string } {
  const counts: Record<RumorStage, number> = { unheard: 0, heard: 0, repeated: 0, dormant: 0, forgotten: 0 };
  for (const id of cast) {
    counts[stageForNpcClaim(state, id, claimId, atTick)]++;
  }
  const total = cast.length;
  const covered = total - counts.unheard - counts.forgotten;
  return { counts, coverage: `coverage ${covered}/${total}` };
}

export function deriveMapMarkers(input: DeriveMapMarkersInput): DerivedMarker[] {
  const { state, traceRecords, eventRecords, mapJson, claimId, atTick, isSelected, variantId } = input;
  const cast = enumerateCast(state, traceRecords, eventRecords);
  const markers: DerivedMarker[] = [];

  for (const id of cast) {
    const location = locationAt(id, traceRecords, eventRecords, atTick);
    if (location === null) continue; // not yet observed at T — see module header
    const loc = mapJson.locations[location];
    if (loc === undefined) continue; // location_id has no map-JSON entry — nothing to place

    const [baseLeft, baseTop] = toPct(loc.pixel[0], loc.pixel[1]);
    const [jx, jy] = seededJitter(id, location);

    const marker: DerivedMarker = {
      id,
      name: displayName(id),
      left: +(baseLeft + jx).toFixed(1),
      top: +(baseTop + jy).toFixed(1),
      stage: stageForNpcClaim(state, id, claimId, atTick),
      glyph: glyphForNpcClaim(state, id, claimId, atTick),
      selected: isSelected(id),
    };
    if (variantId !== undefined) {
      marker.variantClass = variantClassForNpc(state, id, claimId, variantId);
    }
    markers.push(marker);
  }

  return markers;
}
