import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import ProvenancePanel from "./ProvenancePanel.vue";
import { emptySocialState, type SocialState } from "../../log/reconstruct";
import type { FrameRecord, KeyframeBelief, KeyframeEvidence } from "../../log/types";

function belief(overrides: Partial<KeyframeBelief> = {}): KeyframeBelief {
  return {
    id: "belief-x",
    holder_id: "npc-x",
    claim_id: "claim-1",
    variant_id: null,
    confidence: 0.9,
    verbatim_strength: 0.9,
    gist_strength: 1.0,
    first_learned: 0,
    last_rehearsed: 0,
    ...overrides,
  };
}

function evidence(overrides: Partial<KeyframeEvidence> = {}): KeyframeEvidence {
  return {
    id: "ev-x",
    belief_id: "belief-x",
    evidence_type: "reported",
    source_id: "npc-y",
    predecessor_belief_id: null,
    gamets: 0,
    strength: 0.9,
    ...overrides,
  };
}

function trace(tick: number, payload: Record<string, unknown>, seq = 0): FrameRecord {
  return { schema_version: 1, seed_id: "seed", save_uuid: "save", generation: 0, tick, stream: "trace", seq, payload };
}

/** A corroborated belief: two parent witnesses, one of them supersession-sourced, plus a plain-retelling run long enough to collapse. */
function corroboratedState(): { state: SocialState; traceRecords: FrameRecord[] } {
  const state = emptySocialState(0);
  state.beliefs.set("belief-witness-a", belief({ id: "belief-witness-a", holder_id: "npc-a" }));
  state.beliefs.set("belief-witness-b", belief({ id: "belief-witness-b", holder_id: "npc-b" }));
  state.beliefs.set("belief-relay-1", belief({ id: "belief-relay-1", holder_id: "npc-relay-1" }));
  state.beliefs.set("belief-relay-2", belief({ id: "belief-relay-2", holder_id: "npc-relay-2" }));
  state.beliefs.set("belief-target", belief({ id: "belief-target", holder_id: "npc-target" }));

  state.evidence.set("ev-witness-a", evidence({ id: "ev-witness-a", belief_id: "belief-witness-a", evidence_type: "witnessed", source_id: "npc-a", predecessor_belief_id: null, gamets: 0 }));
  // A collapsible run of 3 plain retellings down the "a" column.
  state.evidence.set("ev-relay-1", evidence({ id: "ev-relay-1", belief_id: "belief-relay-1", source_id: "npc-a", predecessor_belief_id: "belief-witness-a", gamets: 1 }));
  state.evidence.set("ev-relay-2", evidence({ id: "ev-relay-2", belief_id: "belief-relay-2", source_id: "npc-relay-1", predecessor_belief_id: "belief-relay-1", gamets: 2 }));
  state.evidence.set("ev-1", evidence({ id: "ev-1", belief_id: "belief-target", source_id: "npc-relay-2", predecessor_belief_id: "belief-relay-2", gamets: 3 }));

  state.evidence.set("ev-witness-b", evidence({ id: "ev-witness-b", belief_id: "belief-witness-b", evidence_type: "witnessed", source_id: "npc-b", predecessor_belief_id: null, gamets: 0 }));
  state.evidence.set("ev-2", evidence({ id: "ev-2", belief_id: "belief-target", source_id: "npc-b", predecessor_belief_id: "belief-witness-b", gamets: 5 }));

  const traceRecords = [
    trace(5, {
      record_type: "supersession",
      holder_id: "npc-target",
      teller_id: "npc-b",
      teller_belief_id: "belief-witness-b",
      evidence_id: "ev-2",
      winner_belief_id: "belief-target",
      resolution_rule: "evidence-type-ordering+v1",
      confidence_dent: 0.1,
    }),
  ];

  return { state, traceRecords };
}

/** A single uncorroborated chain, witness -> one plain retelling -> a mutation hop that changes `weapon`. */
function mutationChainState(): { state: SocialState; traceRecords: FrameRecord[] } {
  const state = emptySocialState(0);
  state.beliefs.set("belief-witness", belief({ id: "belief-witness", holder_id: "npc-witness" }));
  state.beliefs.set("belief-relay", belief({ id: "belief-relay", holder_id: "npc-relay" }));
  state.beliefs.set("belief-target", belief({ id: "belief-target", holder_id: "npc-target", variant_id: "variant-mutated" }));

  state.evidence.set(
    "ev-witness",
    evidence({ id: "ev-witness", belief_id: "belief-witness", evidence_type: "witnessed", source_id: "npc-witness", predecessor_belief_id: null, gamets: 0 }),
  );
  state.evidence.set(
    "ev-relay",
    evidence({ id: "ev-relay", belief_id: "belief-relay", source_id: "npc-witness", predecessor_belief_id: "belief-witness", gamets: 24 }),
  );
  state.evidence.set(
    "ev-target",
    evidence({ id: "ev-target", belief_id: "belief-target", source_id: "npc-relay", predecessor_belief_id: "belief-relay", gamets: 96 }),
  );

  const traceRecords = [
    trace(96, {
      record_type: "transmitted",
      claim_id: "claim-1",
      teller_id: "npc-relay",
      teller_belief_id: "belief-relay",
      hearer_id: "npc-target",
      hearer_belief_id: "belief-target",
      evidence_id: "ev-target",
      variant: { variant_id: "variant-mutated", parent_variant_id: "variant-canonical", slots: {}, mutated_slot: "weapon" },
      location_id: "markarth_city",
    }),
    trace(96, {
      record_type: "mutation_applied",
      claim_id: "claim-1",
      parent_variant_id: "variant-canonical",
      variant_id: "variant-mutated",
      slot: "weapon",
      old_value: "a dagger",
      new_value: "a poisoned blade",
      mutation_id: "mut-38f1c74e1c06",
      roll_key: {},
    }),
  ];

  return { state, traceRecords };
}

describe("ProvenancePanel", () => {
  it("narrates a mutation hop inline: slot, old value, and new value all appear in the rendered chain", () => {
    const { state, traceRecords } = mutationChainState();
    const wrapper = mount(ProvenancePanel, {
      props: { open: true, beliefId: "belief-target", state, traceRecords, atTick: 200 },
    });
    const mutationLine = wrapper.find(".provenance-hop__mutation");
    expect(mutationLine.exists()).toBe(true);
    expect(mutationLine.text()).toContain("weapon");
    expect(mutationLine.text()).toContain("a dagger");
    expect(mutationLine.text()).toContain("a poisoned blade");
    // The mutation hop is always-expanded per the collapse rule -- it must not be hidden behind a "N retellings" toggle.
    expect(wrapper.find(".provenance-hop--mutation").exists()).toBe(true);
  });


  it("renders nothing when closed", () => {
    const { state, traceRecords } = corroboratedState();
    const wrapper = mount(ProvenancePanel, {
      props: { open: false, beliefId: "belief-target", state, traceRecords, atTick: 10 },
    });
    expect(wrapper.find(".provenance-panel").exists()).toBe(false);
  });

  it("DAG honesty at the DOM level: a corroborated belief renders 2 parallel column elements, not a spanning-tree pick", () => {
    const { state, traceRecords } = corroboratedState();
    const wrapper = mount(ProvenancePanel, {
      props: { open: true, beliefId: "belief-target", state, traceRecords, atTick: 10 },
    });
    const columns = wrapper.findAll('[data-testid="provenance-column"]');
    expect(columns).toHaveLength(2);
    // Both parent witnesses actually appear in the rendered DOM.
    expect(wrapper.text()).toContain("npc-a");
    expect(wrapper.text()).toContain("npc-b");
  });

  it("collapses the plain 3-hop retelling run behind a count, and expands it on click", async () => {
    const { state, traceRecords } = corroboratedState();
    const wrapper = mount(ProvenancePanel, {
      props: { open: true, beliefId: "belief-target", state, traceRecords, atTick: 10 },
    });
    const toggle = wrapper.find(".provenance-collapsed__toggle");
    expect(toggle.exists()).toBe(true);
    expect(toggle.text()).toContain("3 retellings");
    expect(wrapper.find(".provenance-collapsed__hops").exists()).toBe(false);

    await toggle.trigger("click");
    expect(wrapper.find(".provenance-collapsed__hops").exists()).toBe(true);
  });

  it("renders the superseded column grayed with the resolution rule as an interstitial fact", () => {
    const { state, traceRecords } = corroboratedState();
    const wrapper = mount(ProvenancePanel, {
      props: { open: true, beliefId: "belief-target", state, traceRecords, atTick: 10 },
    });
    const superseded = wrapper.find(".provenance-hop--superseded");
    expect(superseded.exists()).toBe(true);
    expect(superseded.text()).toContain("evidence-type-ordering+v1");
  });

  it("emits close when the close button is clicked", async () => {
    const { state, traceRecords } = corroboratedState();
    const wrapper = mount(ProvenancePanel, {
      props: { open: true, beliefId: "belief-target", state, traceRecords, atTick: 10 },
    });
    await wrapper.find(".provenance-panel__close").trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1);
  });

  it("shows an honest empty state when no belief is selected", () => {
    const state = emptySocialState(0);
    const wrapper = mount(ProvenancePanel, {
      props: { open: true, beliefId: null, state, traceRecords: [], atTick: 10 },
    });
    expect(wrapper.find(".provenance-panel__empty").text()).toContain("no belief selected");
  });

  it("anchors near the trigger's click position (a fixed document-level pointerdown), not a fixed screen corner -- two different trigger positions land the panel in two different places", async () => {
    const { state, traceRecords } = corroboratedState();
    const wrapper = mount(ProvenancePanel, {
      props: { open: false, beliefId: "belief-target", state, traceRecords, atTick: 10 },
      attachTo: document.body,
    });

    document.dispatchEvent(new MouseEvent("pointerdown", { clientX: 200, clientY: 150 }));
    await wrapper.setProps({ open: true });
    const styleA = (wrapper.find(".provenance-panel").element as HTMLElement).style;
    expect(styleA.left).toBe("212px");
    expect(styleA.top).toBe("162px");

    await wrapper.setProps({ open: false });
    document.dispatchEvent(new MouseEvent("pointerdown", { clientX: 400, clientY: 300 }));
    await wrapper.setProps({ open: true });
    const styleB = (wrapper.find(".provenance-panel").element as HTMLElement).style;
    expect(styleB.left).toBe("412px");
    expect(styleB.top).toBe("312px");
    expect(styleB.left).not.toBe(styleA.left);
    expect(styleB.top).not.toBe(styleA.top);

    wrapper.unmount();
  });

  it("clamps the anchored position so the panel stays fully on-screen near a bottom-right trigger", async () => {
    const { state, traceRecords } = corroboratedState();
    const originalInnerWidth = window.innerWidth;
    const originalInnerHeight = window.innerHeight;
    Object.defineProperty(window, "innerWidth", { value: 1000, configurable: true });
    Object.defineProperty(window, "innerHeight", { value: 700, configurable: true });

    const wrapper = mount(ProvenancePanel, {
      props: { open: false, beliefId: "belief-target", state, traceRecords, atTick: 10 },
      attachTo: document.body,
    });
    document.dispatchEvent(new MouseEvent("pointerdown", { clientX: 990, clientY: 690 }));
    await wrapper.setProps({ open: true });
    const style = (wrapper.find(".provenance-panel").element as HTMLElement).style;
    // Panel is 460px wide with a 12px margin -- clamped left can't exceed 1000 - 460 - 12 = 528.
    expect(Number.parseInt(style.left, 10)).toBeLessThanOrEqual(528);
    expect(Number.parseInt(style.top, 10)).toBeLessThanOrEqual(700 - 160 - 12);

    wrapper.unmount();
    Object.defineProperty(window, "innerWidth", { value: originalInnerWidth, configurable: true });
    Object.defineProperty(window, "innerHeight", { value: originalInnerHeight, configurable: true });
  });

  it("falls back to a fixed default position (not a crash, not off-screen) when opened with no recorded click, e.g. a deep link", () => {
    const { state, traceRecords } = corroboratedState();
    const wrapper = mount(ProvenancePanel, {
      props: { open: true, beliefId: "belief-target", state, traceRecords, atTick: 10 },
    });
    const style = (wrapper.find(".provenance-panel").element as HTMLElement).style;
    expect(style.left).toBe("12px");
    expect(style.top).toBe("54px");
  });

  it("re-derives the shown chain when atTick changes (as-of-T)", async () => {
    const { state, traceRecords } = corroboratedState();
    const wrapper = mount(ProvenancePanel, {
      props: { open: true, beliefId: "belief-target", state, traceRecords, atTick: 2 },
    });
    // At t=2, belief-relay-2 (gamets 2) exists but belief-target's own
    // evidence (ev-1 at gamets 3, ev-2 at gamets 5) hasn't been folded into
    // this synthetic state's Maps yet in a real reconstruct -- but since this
    // test constructs the full state directly (not via replay), what we're
    // actually exercising is that changing atTick changes rendered confidence
    // values (decay), proving the panel doesn't cache anything from open time.
    const before = wrapper.text();
    await wrapper.setProps({ atTick: 500 });
    const after = wrapper.text();
    expect(after).not.toBe(before);
  });
});
