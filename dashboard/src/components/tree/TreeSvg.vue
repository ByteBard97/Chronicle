<script setup lang="ts">
/**
 * TreeSvg — the hand-rolled SVG variant tree (ui-spec §3.5: "Fixed
 * generational left-to-right layout, hand-rolled SVG ... no graph
 * library, no force-direction"). Pure presentation over
 * `derived/variantTree.ts`'s model: node.depth/order already give fixed
 * pixel positions (x = depth, y = order), so this component only maps
 * those to pixels and draws lines/paths -- no layout algorithm lives
 * here.
 *
 * - Lineage edges: solid line, parent -> child, labeled (slot: old -> new,
 *   mutation id) when `mutationId` is set; otherwise a plain unlabeled
 *   line (a transmission with no mutation).
 * - Cross-links: dashed curved path, loser -> winner (an arrowhead marks
 *   the winner end), labeled with the resolution rule + confidence dent.
 *   `derived/variantTree.ts` emits one `VariantTreeCrossLink` per raw
 *   `supersession` record, which can repeat the same (fromId, toId) pair
 *   dozens or hundreds of times (a contested claim stuck in a repeated
 *   resolution loop -- confirmed against `runs/north-star-01`, where one
 *   pair alone carries 190 supersessions). Rendering one path+label per
 *   *record* rather than per distinct *edge* is exactly lane 56's M7 bug
 *   (dossier step 4): hundreds of overlapping label copies stacked into an
 *   illegible mass. This component therefore aggregates `crossLinks` down
 *   to one path + one label per distinct (fromId, toId, resolutionRule,
 *   confidenceDent) group (`aggregatedCrossLinks` below) -- the label shows
 *   a "x N" suffix when more than one record collapses into that group, so
 *   the repeated-contradiction signal survives instead of being silently
 *   dropped.
 * - Node fill: `recolorMode` "first-appearance" scales on `order`
 *   (canonical always first/darkest); "holder-count" scales on
 *   `holderCount`. "by-hold" is explicitly out of scope (no hold concept
 *   in the sim) -- not a mode this component accepts.
 * - A dent badge renders on any node with `dents.length > 0`, showing the
 *   most recent (as-of-T) confidence dent.
 */
import { computed } from "vue";
import type { VariantTreeCrossLink, VariantTreeEdge, VariantTreeNode } from "../../derived/variantTree";

export type RecolorMode = "first-appearance" | "holder-count";

const props = defineProps<{
  nodes: VariantTreeNode[];
  edges: VariantTreeEdge[];
  crossLinks: VariantTreeCrossLink[];
  recolorMode: RecolorMode;
  selectedNodeId: string | null;
}>();

const emit = defineEmits<{ (e: "select-node", id: string): void }>();

const DX = 190; // x spacing per lineage depth
const DY = 60; // y spacing per deterministic order
const MARGIN = 48;
const NODE_R = 16;

interface Pt {
  x: number;
  y: number;
}

const pointById = computed<Record<string, Pt>>(() => {
  const out: Record<string, Pt> = {};
  for (const n of props.nodes) {
    out[n.id] = { x: MARGIN + n.depth * DX, y: MARGIN + n.order * DY };
  }
  return out;
});

const width = computed(() => {
  const maxDepth = props.nodes.reduce((m, n) => Math.max(m, n.depth), 0);
  return MARGIN * 2 + maxDepth * DX + NODE_R * 2;
});
const height = computed(() => {
  const maxOrder = props.nodes.reduce((m, n) => Math.max(m, n.order), 0);
  return MARGIN * 2 + maxOrder * DY + NODE_R * 2;
});

/**
 * One path/label per distinct (fromId, toId, resolutionRule,
 * confidenceDent) group -- see the module header on why `props.crossLinks`
 * (one entry per raw `supersession` record) can't be rendered 1:1 without
 * flooding the canvas. The label's own content is part of the group key,
 * not just (fromId, toId): confirmed uniform per pair across every fixture
 * under `runs/*` today, but keying on exactly what the rendered label shows
 * means a future run where the same pair resolves under two different
 * rules/dents still gets two honest labels instead of one that silently
 * mis-states the dent for some of the collapsed records.
 *
 * `pairIndex`/`pairCount` are irrelevant post-aggregation: with duplicates
 * collapsed there is exactly one curve per group, so the fan-out bow (which
 * was only ever driven by these two fields) is always centered (bow = 0)
 * here. They're kept on `AggregatedCrossLink`/passed as 0/1 purely to
 * satisfy `CrossLinkGeom`'s shape, not because the bow still does anything.
 */
interface AggregatedCrossLink {
  id: string;
  fromId: string;
  toId: string;
  resolutionRule: string;
  confidenceDent: number;
  count: number;
  pairIndex: number;
  pairCount: number;
}

const aggregatedCrossLinks = computed<AggregatedCrossLink[]>(() => {
  const order: string[] = [];
  const groups = new Map<string, VariantTreeCrossLink[]>();
  for (const link of props.crossLinks) {
    const key = `${link.fromId}->${link.toId}::${link.resolutionRule}::${link.confidenceDent}`;
    const existing = groups.get(key);
    if (existing === undefined) {
      groups.set(key, [link]);
      order.push(key);
    } else {
      existing.push(link);
    }
  }
  return order.map((key) => {
    const group = groups.get(key)!;
    const rep = group[0]!;
    return {
      id: key,
      fromId: rep.fromId,
      toId: rep.toId,
      resolutionRule: rep.resolutionRule,
      confidenceDent: rep.confidenceDent,
      count: group.length,
      pairIndex: 0,
      pairCount: 1,
    };
  });
});

const maxOrder = computed(() => Math.max(1, ...props.nodes.map((n) => n.order)));
const maxHolderCount = computed(() => Math.max(1, ...props.nodes.map((n) => n.holderCount)));

/** Deterministic accent-gold ramp -- lightness scales with the 0..1 value; never a hue change (tokens.css only defines the one accent hue). */
function colorFor(value01: number): string {
  const clamped = Math.max(0, Math.min(1, value01));
  const lightness = 28 + clamped * 42; // 28%..70%
  return `hsl(38, 46%, ${lightness}%)`;
}

function fillFor(node: VariantTreeNode): string {
  if (node.isCanonical) return "var(--c-accent-hover)";
  if (props.recolorMode === "holder-count") {
    return colorFor(node.holderCount / maxHolderCount.value);
  }
  return colorFor(node.order / maxOrder.value);
}

function edgeLabel(edge: VariantTreeEdge): string | null {
  if (edge.mutationId === null) return null;
  return `${edge.slot}: ${edge.oldValue ?? "?"} → ${edge.newValue ?? "?"} (${edge.mutationId})`;
}

/** Deterministic string hash -> [0, 1), reused to stagger label placement per-link rather than always at the curve's exact midpoint. */
function hash01(s: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0) / 0xffffffff;
}

/** Structural shape the curve-geometry helpers need -- satisfied by both a raw `VariantTreeCrossLink` and an `AggregatedCrossLink`. */
type CrossLinkGeom = Pick<VariantTreeCrossLink, "id" | "fromId" | "toId" | "pairIndex" | "pairCount">;

/** The quadratic-bezier control point for one cross-link (shared by the path and its label so they always agree). Same-pair duplicates fan out via a perpendicular bow keyed on `pairIndex`. */
function crossLinkControl(link: CrossLinkGeom, from: Pt, to: Pt): Pt {
  const mid = { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 };
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const len = Math.hypot(dx, dy) || 1;
  const nx = -dy / len;
  const ny = dx / len;
  const centered = link.pairIndex - (link.pairCount - 1) / 2;
  const bow = centered * 26;
  return { x: mid.x + nx * (24 + bow), y: mid.y + ny * (24 + bow) };
}

function quadraticPoint(from: Pt, ctrl: Pt, to: Pt, t: number): Pt {
  const u = 1 - t;
  return {
    x: u * u * from.x + 2 * u * t * ctrl.x + t * t * to.x,
    y: u * u * from.y + 2 * u * t * ctrl.y + t * t * to.y,
  };
}

function crossLinkPath(link: CrossLinkGeom): string {
  const from = pointById.value[link.fromId];
  const to = pointById.value[link.toId];
  if (from === undefined || to === undefined) return "";
  if (link.fromId === link.toId) {
    // Degenerate self-referencing case (shouldn't occur -- both ends would
    // have to be the same node, e.g. two nulls -- guarded rather than
    // emitting a zero-length/invisible path).
    const loopR = 22;
    return `M ${from.x} ${from.y - NODE_R} C ${from.x - loopR} ${from.y - NODE_R - loopR}, ${from.x + loopR} ${from.y - NODE_R - loopR}, ${from.x} ${from.y - NODE_R}`;
  }
  const ctrl = crossLinkControl(link, from, to);
  return `M ${from.x} ${from.y} Q ${ctrl.x} ${ctrl.y} ${to.x} ${to.y}`;
}

/**
 * Label placement: distinct (fromId, toId) pairs converging on the same
 * cluster of nodes (e.g. several supersessions all resolving onto one
 * winner) produce curves whose *midpoints* land on top of each other even
 * though the curves themselves differ. Staggering each label's position
 * along its own curve (t in [0.3, 0.7], keyed by a hash of the link id) —
 * rather than fixing every label at t=0.5 — spreads distinct pairs' labels
 * apart without needing to know about each other.
 */
function crossLinkLabelPoint(link: CrossLinkGeom): Pt {
  const from = pointById.value[link.fromId];
  const to = pointById.value[link.toId];
  if (from === undefined || to === undefined) return { x: 0, y: 0 };
  const ctrl = crossLinkControl(link, from, to);
  const t = 0.3 + hash01(link.id) * 0.4;
  return quadraticPoint(from, ctrl, to, t);
}

/** Cross-link label text: the resolution rule + dent, plus a "x N" suffix when this aggregated edge collapses more than one raw supersession record. */
function crossLinkLabel(link: AggregatedCrossLink): string {
  const base = `${link.resolutionRule} (dent ${link.confidenceDent})`;
  return link.count > 1 ? `${base} ×${link.count}` : base;
}

/** Clamp a label's text-anchor-middle x so it can't run off the (scrollable) canvas edge. */
function clampLabelX(x: number): number {
  return Math.max(60, Math.min(width.value - 60, x));
}

function nodeTitle(node: VariantTreeNode): string {
  const slotSummary = Object.entries(node.slots)
    .map(([k, v]) => `${k}=${v ?? "?"}`)
    .join(", ");
  const dentSummary = node.dents.length > 0 ? ` | dent ${node.dents[node.dents.length - 1]!.confidenceDent}` : "";
  const label = node.isCanonical ? "canonical" : node.id;
  return `${label} | holders ${node.holderCount} | ${slotSummary}${dentSummary}`;
}
</script>

<template>
  <svg
    class="tree-svg"
    :viewBox="`0 0 ${width} ${height}`"
    :width="width"
    :height="height"
    role="img"
    aria-label="variant lineage tree"
  >
    <defs>
      <marker id="tree-svg__arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
        <path d="M0,0 L6,3 L0,6 Z" fill="var(--c-accent)" />
      </marker>
    </defs>

    <!-- Lineage edges -->
    <g class="tree-svg__edges">
      <g v-for="edge in edges" :key="edge.id">
        <line
          v-if="pointById[edge.fromId] && pointById[edge.toId]"
          class="tree-svg__edge-line"
          :x1="pointById[edge.fromId]!.x"
          :y1="pointById[edge.fromId]!.y"
          :x2="pointById[edge.toId]!.x"
          :y2="pointById[edge.toId]!.y"
        />
        <text
          v-if="edgeLabel(edge) !== null && pointById[edge.fromId] && pointById[edge.toId]"
          class="tree-svg__edge-label"
          :x="clampLabelX((pointById[edge.fromId]!.x + pointById[edge.toId]!.x) / 2)"
          :y="(pointById[edge.fromId]!.y + pointById[edge.toId]!.y) / 2 - 6"
        >
          {{ edgeLabel(edge) }}
        </text>
      </g>
    </g>

    <!-- Supersession cross-links (dashed) -->
    <g class="tree-svg__cross-links">
      <g v-for="link in aggregatedCrossLinks" :key="link.id">
        <path class="tree-svg__cross-link-path" :d="crossLinkPath(link)" marker-end="url(#tree-svg__arrow)" />
        <text
          class="tree-svg__cross-link-label"
          :x="clampLabelX(crossLinkLabelPoint(link).x)"
          :y="crossLinkLabelPoint(link).y"
        >
          {{ crossLinkLabel(link) }}
        </text>
      </g>
    </g>

    <!-- Nodes -->
    <g class="tree-svg__nodes">
      <g
        v-for="node in nodes"
        :key="node.id"
        class="tree-svg__node"
        :class="{ 'tree-svg__node--selected': node.id === selectedNodeId, 'tree-svg__node--contested': node.dents.length > 0 }"
        :transform="`translate(${pointById[node.id]!.x}, ${pointById[node.id]!.y})`"
        tabindex="0"
        role="button"
        :aria-label="nodeTitle(node)"
        @click="emit('select-node', node.id)"
        @keydown.enter="emit('select-node', node.id)"
      >
        <title>{{ nodeTitle(node) }}</title>
        <rect
          v-if="node.isCanonical"
          class="tree-svg__node-shape"
          :x="-NODE_R"
          :y="-NODE_R"
          :width="NODE_R * 2"
          :height="NODE_R * 2"
          :fill="fillFor(node)"
        />
        <circle v-else class="tree-svg__node-shape" :r="NODE_R" :fill="fillFor(node)" />
        <text class="tree-svg__node-count" y="4">{{ node.holderCount }}</text>
        <text class="tree-svg__node-name" :y="NODE_R + 14">{{ node.isCanonical ? "canonical" : node.id }}</text>
        <circle v-if="node.dents.length > 0" class="tree-svg__dent-badge" :cx="NODE_R - 4" :cy="-NODE_R + 4" r="5" />
      </g>
    </g>
  </svg>
</template>

<style scoped>
.tree-svg {
  display: block;
  background: var(--c-page-bg);
}

.tree-svg__edge-line {
  stroke: var(--c-hairline);
  stroke-width: 1.5;
}

.tree-svg__edge-label {
  fill: var(--c-text-dim);
  font-family: var(--font-data);
  font-size: var(--fs-micro);
  text-anchor: middle;
  /* Halo so overlapping labels in a dense cluster stay legible over each other and over edge/cross-link lines. */
  paint-order: stroke;
  stroke: var(--c-page-bg);
  stroke-width: 3px;
  stroke-linejoin: round;
}

.tree-svg__cross-link-path {
  fill: none;
  stroke: var(--c-accent);
  stroke-width: 1.5;
  stroke-dasharray: 4 3;
  opacity: 0.85;
}

.tree-svg__cross-link-label {
  fill: var(--c-accent-hover);
  font-family: var(--font-data);
  font-size: var(--fs-micro);
  text-anchor: middle;
  paint-order: stroke;
  stroke: var(--c-page-bg);
  stroke-width: 3px;
  stroke-linejoin: round;
}

.tree-svg__node {
  cursor: pointer;
}

.tree-svg__node-shape {
  stroke: var(--c-hairline);
  stroke-width: 1.5;
}

.tree-svg__node--selected .tree-svg__node-shape {
  stroke: var(--c-accent-hover);
  stroke-width: 3;
}

.tree-svg__node-count {
  fill: var(--c-page-bg);
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  font-weight: 600;
  text-anchor: middle;
}

.tree-svg__node-name {
  fill: var(--c-text-body);
  font-family: var(--font-data);
  font-size: var(--fs-micro);
  text-anchor: middle;
}

.tree-svg__dent-badge {
  fill: #c96a4a;
  stroke: var(--c-page-bg);
  stroke-width: 1;
}
</style>
