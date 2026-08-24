import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import TreeSvg from "./TreeSvg.vue";
import { CANONICAL_NODE_ID, type VariantTreeCrossLink, type VariantTreeEdge, type VariantTreeNode } from "../../derived/variantTree";

/**
 * TreeSvg.test.ts -- lane 56 (M7 fix): regression coverage for the
 * variant-tree edge-label rendering bug (dossier step 4, `runs/north-star-01`
 * `claim-balgruuf-assassination`, where one (fromId, toId) pair alone
 * carries 190 raw `supersession` records). `derived/variantTree.ts` emits
 * one `VariantTreeCrossLink` per raw record, so a tree stuck in a repeated
 * resolution loop can carry hundreds of cross-links between the same two
 * nodes -- rendering one path+label per record (the pre-fix behavior)
 * floods the canvas with overlapping copies of the same string. The fix
 * aggregates cross-links down to one path+label per distinct (fromId,
 * toId) pair; these tests pin "N distinct pairs -> N label elements",
 * never N (raw record count) or N^2.
 */

function node(over: Partial<VariantTreeNode> & Pick<VariantTreeNode, "id" | "depth" | "order">): VariantTreeNode {
  return {
    variantId: over.id === CANONICAL_NODE_ID ? null : over.id,
    isCanonical: over.id === CANONICAL_NODE_ID,
    firstAppearance: -1,
    slots: {},
    mutatedSlot: null,
    parentId: null,
    holderCount: 0,
    dents: [],
    ...over,
  };
}

function edge(over: Partial<VariantTreeEdge> & Pick<VariantTreeEdge, "id" | "fromId" | "toId">): VariantTreeEdge {
  return {
    mutationId: null,
    slot: null,
    oldValue: null,
    newValue: null,
    ...over,
  };
}

function crossLink(
  over: Partial<VariantTreeCrossLink> & Pick<VariantTreeCrossLink, "id" | "fromId" | "toId">,
): VariantTreeCrossLink {
  return {
    resolutionRule: "evidence-type-ordering+v1",
    confidenceDent: 0.1,
    tick: 0,
    holderId: "holder",
    pairIndex: 0,
    pairCount: 1,
    ...over,
  };
}

const NODES: VariantTreeNode[] = [
  node({ id: CANONICAL_NODE_ID, depth: 0, order: 0 }),
  node({ id: "variant-a", depth: 1, order: 1 }),
  node({ id: "variant-b", depth: 1, order: 2 }),
];

const EDGES: VariantTreeEdge[] = [
  edge({ id: "edge:variant-a", fromId: CANONICAL_NODE_ID, toId: "variant-a", mutationId: "mut-a", slot: "loc", oldValue: "market", newValue: "alley" }),
  edge({ id: "edge:variant-b", fromId: "variant-a", toId: "variant-b", mutationId: "mut-b", slot: "loc", oldValue: "alley", newValue: "cellar" }),
];

function mountTree(crossLinks: VariantTreeCrossLink[]) {
  return mount(TreeSvg, {
    props: {
      nodes: NODES,
      edges: EDGES,
      crossLinks,
      recolorMode: "first-appearance",
      selectedNodeId: null,
    },
  });
}

describe("TreeSvg.vue", () => {
  it("lineage edges: one label per edge (baseline -- was never the bug, but pinned as a regression)", () => {
    const wrapper = mountTree([]);
    const labels = wrapper.findAll(".tree-svg__edge-label");
    expect(labels).toHaveLength(2);
    expect(labels.map((l) => l.text())).toEqual(["loc: market → alley (mut-a)", "loc: alley → cellar (mut-b)"]);
  });

  it("cross-links: N raw supersession records sharing one (fromId, toId) pair render exactly ONE label, not N", () => {
    // The exact shape of the M7 bug: 190 real supersession records all
    // between the same two nodes (runs/north-star-01).
    const crossLinks: VariantTreeCrossLink[] = Array.from({ length: 190 }, (_, i) =>
      crossLink({ id: `cross:${i}`, fromId: "variant-a", toId: "variant-b", tick: i }),
    );
    const wrapper = mountTree(crossLinks);
    expect(wrapper.findAll(".tree-svg__cross-link-label")).toHaveLength(1);
    expect(wrapper.findAll(".tree-svg__cross-link-path")).toHaveLength(1);
  });

  it("cross-links: label count matches the number of DISTINCT (fromId, toId) pairs, not the raw record count and not its square", () => {
    const crossLinks: VariantTreeCrossLink[] = [
      ...Array.from({ length: 5 }, (_, i) => crossLink({ id: `cross:ab:${i}`, fromId: "variant-a", toId: "variant-b" })),
      ...Array.from({ length: 3 }, (_, i) => crossLink({ id: `cross:ca:${i}`, fromId: CANONICAL_NODE_ID, toId: "variant-a" })),
      crossLink({ id: "cross:single", fromId: CANONICAL_NODE_ID, toId: "variant-b" }),
    ];
    const wrapper = mountTree(crossLinks);
    // 3 distinct pairs: (a,b) x5, (canonical,a) x3, (canonical,b) x1 -- never 9 (sum), never 81 (N^2).
    expect(wrapper.findAll(".tree-svg__cross-link-label")).toHaveLength(3);
    expect(wrapper.findAll(".tree-svg__cross-link-path")).toHaveLength(3);
  });

  it("an aggregated cross-link label shows a ×N suffix when it collapses more than one raw record, and no suffix for a genuine singleton", () => {
    const crossLinks: VariantTreeCrossLink[] = [
      ...Array.from({ length: 3 }, (_, i) => crossLink({ id: `cross:rep:${i}`, fromId: "variant-a", toId: "variant-b" })),
      crossLink({ id: "cross:single", fromId: CANONICAL_NODE_ID, toId: "variant-a" }),
    ];
    const wrapper = mountTree(crossLinks);
    const texts = wrapper.findAll(".tree-svg__cross-link-label").map((l) => l.text());
    expect(texts).toContain("evidence-type-ordering+v1 (dent 0.1) ×3");
    expect(texts).toContain("evidence-type-ordering+v1 (dent 0.1)");
  });

  it("cross-link labels never collide at a single fixed point -- each aggregated pair's label has distinct, finite coordinates", () => {
    const crossLinks: VariantTreeCrossLink[] = [
      crossLink({ id: "cross:ab", fromId: "variant-a", toId: "variant-b" }),
      crossLink({ id: "cross:ca", fromId: CANONICAL_NODE_ID, toId: "variant-a" }),
      crossLink({ id: "cross:cb", fromId: CANONICAL_NODE_ID, toId: "variant-b" }),
    ];
    const wrapper = mountTree(crossLinks);
    const labelEls = wrapper.findAll(".tree-svg__cross-link-label");
    const coords = labelEls.map((l) => `${l.attributes("x")},${l.attributes("y")}`);
    for (const c of coords) {
      const [x, y] = c.split(",").map(Number);
      expect(Number.isFinite(x)).toBe(true);
      expect(Number.isFinite(y)).toBe(true);
    }
    expect(new Set(coords).size).toBe(coords.length);
  });
});
