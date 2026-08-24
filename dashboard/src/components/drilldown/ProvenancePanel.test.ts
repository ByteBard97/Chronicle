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

describe("ProvenancePanel", () => {
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
