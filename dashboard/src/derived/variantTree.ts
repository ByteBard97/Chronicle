/**
 * Variant tree (lane 21, ui-spec §3.5): `SocialState` + raw trace records
 * (`mutation_applied`, `supersession`) -> a render-ready tree model, one
 * tree per claim.
 *
 * Mirrors `mapMarkers.ts`'s idiom: `state` (claims/variants/beliefs) is
 * trusted as already-reconstructed-at-T (the caller's `SocialState`, e.g.
 * from `stores/mapData.ts`), while the raw `traceRecords` array is the
 * *whole* stream and this module does its own `record.tick <= atTick`
 * filtering internally — the same split `deriveMapMarkers` makes for
 * `traceRecords`/`eventRecords`.
 *
 * Node anatomy:
 *  - one canonical root per claim (the claim's "original telling" --
 *    where a null variant id points, per `supersession`/`transmitted`'s
 *    shared idiom) plus one node per `KeyframeVariant` of that claim.
 *  - lineage edges from `parent_variant_id` (null parent -> canonical),
 *    labeled from a matching `mutation_applied` record when one exists
 *    (matched by `variant_id`); a lineage edge with no matching mutation
 *    record is a plain, unlabeled transmission edge.
 *  - dashed cross-links, one per `supersession` record, loser -> winner;
 *    either end can be the canonical root (a null `loser_variant_id` or
 *    `winner_variant_id`), not just the loser side -- confirmed directly
 *    against `runs/carrier-mutation-01/trace.jsonl`, where 2 of the 7
 *    supersessions there have `winner_variant_id: null`.
 *
 * Contested-claim dent: pinned as "the node where a supersession's winner
 * belief holds that variant". This is read straight off each
 * `supersession` record's own `winner_variant_id` (the record's stated
 * outcome), NOT by looking up `winner_belief_id` in `state.beliefs` --
 * deliberately, because `reconstruct.ts`'s `applyTraceRecord` has no
 * `supersession` case (it falls through to the schema §7 skip-and-continue
 * default), so a belief's `variant_id` in `SocialState` is never actually
 * updated when a supersession resolves it onto a different variant. Using
 * the record's `winner_variant_id` keeps the dent anchored to a real
 * cross-link endpoint and sidesteps that reader gap entirely; see this
 * module's "holder count" section below for where the gap DOES leak
 * through (deliberately, per the pinned recipe) and the finding that
 * documents it.
 *
 * Holder count at T: literally "count `state.beliefs` values by
 * `variant_id` (null -> canonical root)" per the work packet's pinned
 * recipe -- this module trusts whatever `state.beliefs` says, as-is.
 *
 * That recipe surfaces a genuine `reconstruct.ts` gap (do-not-touch this
 * lane, reported as a finding rather than fixed): `applyTraceRecord` has
 * no `supersession` case, so a belief's `variant_id` is only ever updated
 * by `belief_formed`/`transmitted`, never by a later `supersession`
 * resolving it onto a different variant. The keyframe writer (the Python
 * sim) *does* bake the resolved `variant_id` into each keyframe's belief
 * snapshot, so reconstructing state AT OR AFTER the first keyframe written
 * after a supersession fires shows the correct, resolved count. The gap
 * only manifests for a T strictly between a supersession's tick and that
 * next keyframe: reconstructing from the (stale, pre-supersession)
 * keyframe plus a delta replay that silently skips the `supersession`
 * record shows the holder still on their pre-resolution variant. Confirmed
 * directly against `runs/carrier-mutation-01` (keyframes every 24 ticks,
 * a supersession chain at ticks 26-28, next keyframe at tick 47): at T=30
 * every one of `relief_caravaneer`/`ysolda`'s beliefs still show their
 * pre-supersession variant (the gap, live); at T=200 (well past the tick-47
 * keyframe) the same beliefs already show their fully-resolved variant
 * (canonical, matching the log's real semantics) -- both pinned by
 * `variantTree.realRun.test.ts`.
 *
 * Layout (pinned, T-independent): x = lineage depth (canonical = 0, a
 * variant's depth = 1 + its parent's, canonical counting as depth 0 for a
 * root-parented variant). y = deterministic order across the whole claim
 * tree: canonical first, then variants sorted by (first-appearance
 * `gamets` ascending, tie -> variant id lexicographic). Because that sort
 * key is fixed per variant (not derived from T), and "as-of-T" only ever
 * *removes* the suffix of variants whose `gamets > atTick`, every node's
 * `(depth, order)` pair is identical across every T at which that node is
 * visible at all -- positions never move as T scrubs, only visibility
 * does.
 */
import type { FrameRecord, KeyframeVariant } from "../log/types";
import type { SocialState } from "../log/reconstruct";

export const CANONICAL_NODE_ID = "canonical";

export interface VariantDent {
  tick: number;
  resolutionRule: string;
  confidenceDent: number;
  holderId: string;
}

export interface VariantTreeNode {
  id: string;
  /** `null` for the canonical root. */
  variantId: string | null;
  isCanonical: boolean;
  /** x: lineage depth, canonical = 0. */
  depth: number;
  /** y: deterministic order (0 = canonical, then first-appearance order). */
  order: number;
  /** The variant's `gamets` (first-appearance tick); `-1` for canonical. */
  firstAppearance: number;
  slots: Record<string, string | null>;
  mutatedSlot: string | null;
  /** The lineage-parent's node id; `null` only for canonical. */
  parentId: string | null;
  /** Holders (belief count) of this variant at T -- see module header on the reconstruct.ts gap this literally reflects. */
  holderCount: number;
  /** Every supersession, as-of-T, whose winner names this node -- the contested-claim dent(s). */
  dents: VariantDent[];
}

export interface VariantTreeEdge {
  id: string;
  fromId: string;
  toId: string;
  mutationId: string | null;
  slot: string | null;
  oldValue: string | null;
  newValue: string | null;
}

export interface VariantTreeCrossLink {
  id: string;
  /** Loser node id (may be `CANONICAL_NODE_ID`). */
  fromId: string;
  /** Winner node id (may be `CANONICAL_NODE_ID`). */
  toId: string;
  resolutionRule: string;
  confidenceDent: number;
  tick: number;
  holderId: string;
  /** Index within the group of cross-links sharing this exact (fromId, toId) pair -- lets a renderer fan out overlapping bows so duplicate pairs (e.g. two supersessions resolving the same loser->winner edge for different holders) don't render as one indistinguishable curve. */
  pairIndex: number;
  /** Total cross-links sharing this (fromId, toId) pair. */
  pairCount: number;
}

export interface VariantTree {
  claimId: string;
  nodes: VariantTreeNode[];
  edges: VariantTreeEdge[];
  crossLinks: VariantTreeCrossLink[];
}

function isString(v: unknown): v is string {
  return typeof v === "string";
}

/** Claim ids in `SocialState.claims`' insertion (Map) order. */
export function claimIds(state: SocialState): string[] {
  return [...state.claims.keys()];
}

/** The run's first claim -- the tree's default selection (packet: "claim dropdown defaulting to the first claim in SocialState.claims"). */
export function firstClaimId(state: SocialState): string | null {
  const first = state.claims.keys().next();
  return first.done ? null : (first.value as string);
}

function nodeIdFor(variantId: string | null): string {
  return variantId === null ? CANONICAL_NODE_ID : variantId;
}

/** Lineage depth: canonical = 0; a variant's depth = 1 + its parent's (parent_variant_id: null -> canonical, depth 0). Memoized; `parent_variant_id` is singular per variant (facts: a proper tree, no cycles) so this always terminates. */
function computeDepth(variantId: string, variants: Map<string, KeyframeVariant>, cache: Map<string, number>): number {
  const cached = cache.get(variantId);
  if (cached !== undefined) return cached;
  const v = variants.get(variantId);
  if (v === undefined) {
    // Orphaned parent ref (points outside this claim's visible-at-T variant
    // set) -- shouldn't occur per the pinned facts, but degrade to "child
    // of canonical" rather than throwing.
    cache.set(variantId, 1);
    return 1;
  }
  const parentDepth = v.parent_variant_id === null ? 0 : computeDepth(v.parent_variant_id, variants, cache);
  const depth = parentDepth + 1;
  cache.set(variantId, depth);
  return depth;
}

/**
 * Build the tree for one claim, as-of `atTick`. `state` is trusted as
 * already reconstructed at T (its `variants`/`beliefs` reflect exactly the
 * records at or before `atTick`); `traceRecords` is the run's full,
 * unfiltered trace stream, filtered against `atTick` internally here (the
 * `mapMarkers.ts` split) because `mutation_applied`/`supersession` have no
 * `SocialState` representation to read off instead.
 */
export function buildVariantTree(state: SocialState, traceRecords: FrameRecord[], claimId: string, atTick: number): VariantTree {
  const variants = [...state.variants.values()].filter((v) => v.claim_id === claimId && v.gamets <= atTick);
  const variantMap = new Map(variants.map((v) => [v.id, v]));
  const depthCache = new Map<string, number>();

  // Deterministic order: canonical (0), then variants by (gamets asc, id asc).
  const ordered = [...variants].sort((a, b) => a.gamets - b.gamets || a.id.localeCompare(b.id));

  const claim = state.claims.get(claimId);
  const nodes: VariantTreeNode[] = [
    {
      id: CANONICAL_NODE_ID,
      variantId: null,
      isCanonical: true,
      depth: 0,
      order: 0,
      firstAppearance: -1,
      slots: claim?.slots ?? {},
      mutatedSlot: null,
      parentId: null,
      holderCount: 0,
      dents: [],
    },
  ];

  ordered.forEach((v, i) => {
    nodes.push({
      id: v.id,
      variantId: v.id,
      isCanonical: false,
      depth: computeDepth(v.id, variantMap, depthCache),
      order: i + 1,
      firstAppearance: v.gamets,
      slots: v.slots,
      mutatedSlot: v.mutated_slot,
      parentId: nodeIdFor(v.parent_variant_id),
      holderCount: 0,
      dents: [],
    });
  });

  const nodeById = new Map(nodes.map((n) => [n.id, n]));

  // Holder count at T: `state.beliefs` grouped by variant_id (null -> canonical), this claim only.
  for (const b of state.beliefs.values()) {
    if (b.claim_id !== claimId) continue;
    const n = nodeById.get(nodeIdFor(b.variant_id));
    if (n !== undefined) n.holderCount++;
  }

  // Edges: lineage, labeled from a matching mutation_applied record when present.
  const mutationByVariant = new Map<string, Record<string, unknown>>();
  for (const r of traceRecords) {
    if (r.tick > atTick) continue;
    const p = r.payload;
    if (p.record_type !== "mutation_applied") continue;
    if (p.claim_id !== claimId) continue;
    if (isString(p.variant_id)) mutationByVariant.set(p.variant_id, p);
  }

  const edges: VariantTreeEdge[] = ordered.map((v) => {
    const p = mutationByVariant.get(v.id);
    return {
      id: `edge:${v.id}`,
      fromId: nodeIdFor(v.parent_variant_id),
      toId: v.id,
      mutationId: p !== undefined && isString(p.mutation_id) ? p.mutation_id : null,
      slot: p !== undefined && isString(p.slot) ? p.slot : null,
      oldValue: p !== undefined ? ((p.old_value as string | null) ?? null) : null,
      newValue: p !== undefined ? ((p.new_value as string | null) ?? null) : null,
    };
  });

  // Cross-links: one per supersession record, as-of-T; either end may be canonical.
  const rawCrossLinks: Omit<VariantTreeCrossLink, "pairIndex" | "pairCount">[] = [];
  for (const r of traceRecords) {
    if (r.tick > atTick) continue;
    const p = r.payload;
    if (p.record_type !== "supersession") continue;
    if (p.claim_id !== claimId) continue;
    const loserVariantId = isString(p.loser_variant_id) ? p.loser_variant_id : null;
    const winnerVariantId = isString(p.winner_variant_id) ? p.winner_variant_id : null;
    const resolutionRule = isString(p.resolution_rule) ? p.resolution_rule : "";
    const confidenceDent = typeof p.confidence_dent === "number" ? p.confidence_dent : 0;
    const holderId = isString(p.holder_id) ? p.holder_id : "";
    const fromId = nodeIdFor(loserVariantId);
    const toId = nodeIdFor(winnerVariantId);

    rawCrossLinks.push({
      id: `cross:${r.tick}:${r.seq}`,
      fromId,
      toId,
      resolutionRule,
      confidenceDent,
      tick: r.tick,
      holderId,
    });

    // Contested-claim dent, read off the record's own winner_variant_id
    // (see module header for why this isn't a state.beliefs lookup).
    const winnerNode = nodeById.get(toId);
    if (winnerNode !== undefined) {
      winnerNode.dents.push({ tick: r.tick, resolutionRule, confidenceDent, holderId });
    }
  }

  for (const n of nodes) n.dents.sort((a, b) => a.tick - b.tick);

  // Group duplicate (fromId, toId) pairs (e.g. two supersessions resolving
  // the same loser->winner edge for different holders) so a renderer can
  // fan out overlapping bows rather than drawing one indistinguishable
  // curve per pair.
  const pairCounts = new Map<string, number>();
  for (const c of rawCrossLinks) {
    const key = `${c.fromId}->${c.toId}`;
    pairCounts.set(key, (pairCounts.get(key) ?? 0) + 1);
  }
  const seenInPair = new Map<string, number>();
  const crossLinks: VariantTreeCrossLink[] = rawCrossLinks.map((c) => {
    const key = `${c.fromId}->${c.toId}`;
    const pairIndex = seenInPair.get(key) ?? 0;
    seenInPair.set(key, pairIndex + 1);
    return { ...c, pairIndex, pairCount: pairCounts.get(key) ?? 1 };
  });

  return { claimId, nodes, edges, crossLinks };
}
