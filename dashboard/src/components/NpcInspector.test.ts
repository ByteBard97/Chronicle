import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import NpcInspector, { INSPECTOR_TABS } from "./NpcInspector.vue";
import { useMapDataStore } from "../stores/mapData";
import { emptySocialState, type SocialState } from "../log/reconstruct";
import type { KeyframeBelief, KeyframeClaim, KeyframeRumorState, KeyframeVariant } from "../log/types";

/**
 * Lane 28 rewrite (the packet's one authorized rewrite class): the
 * component no longer renders the static "Fralia Gray-Mane" belief
 * fixture -- these tests populate `useMapDataStore()`'s `socialState`
 * directly (mirroring `stores/mapData.test.ts`/`TimelineBar.test.ts`'s
 * idiom) and mount against real derived output.
 */
const CLAIM: KeyframeClaim = {
  id: "claim-1",
  kind: "npc_death",
  slots: { perpetrator: "unknown", cause: "assassination" },
  canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 },
  truth_status: "unconfirmed",
};

function belief(overrides: Partial<KeyframeBelief> = {}): KeyframeBelief {
  return {
    id: "belief-1",
    holder_id: "npc-a",
    claim_id: "claim-1",
    variant_id: null,
    confidence: 0.78,
    verbatim_strength: 0.41,
    gist_strength: 0.86,
    first_learned: 0,
    last_rehearsed: 0,
    ...overrides,
  };
}

function rumor(overrides: Partial<KeyframeRumorState> = {}): KeyframeRumorState {
  return {
    npc_id: "npc-a",
    claim_id: "claim-1",
    variant_id: null,
    stage: "repeated",
    first_heard: 0,
    last_heard: 0,
    last_told: 0,
    exposure_count: 2,
    distinct_source_count: 1,
    ...overrides,
  };
}

function stateWithOneActiveBelief(): SocialState {
  const state = emptySocialState(0);
  state.claims.set(CLAIM.id, CLAIM);
  state.beliefs.set("belief-1", belief());
  state.rumors.set("npc-a claim-1 ", rumor());
  state.evidence.set("ev-1", {
    id: "ev-1",
    belief_id: "belief-1",
    evidence_type: "reported",
    source_id: "npc-teller",
    predecessor_belief_id: null,
    gamets: 0,
    strength: 0.9,
  });
  return state;
}

function setSocialState(state: SocialState) {
  const mapData = useMapDataStore();
  mapData.socialState = state;
}

describe("NpcInspector", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders the four stable tabs, Beliefs active by default", () => {
    const wrapper = mount(NpcInspector);
    const tabs = wrapper.findAll(".npc-inspector__tab");
    expect(tabs.map((t) => t.text())).toEqual([
      "BELIEFS",
      "RELATIONSHIPS",
      "SCHEDULE",
      "HISTORY",
    ]);
    expect(INSPECTOR_TABS).toEqual([
      "beliefs",
      "relationships",
      "schedule",
      "history",
    ]);
    expect(tabs[0].classes()).toContain("npc-inspector__tab--active");
  });

  it("switches to a placeholder body on the other tabs (not wired yet)", async () => {
    const wrapper = mount(NpcInspector);
    await wrapper.findAll(".npc-inspector__tab")[1].trigger("click");
    expect(wrapper.find(".npc-inspector__placeholder").text()).toContain(
      "relationships",
    );
  });

  it("renders no belief cards, and an honest empty state, when no npc is selected", () => {
    const wrapper = mount(NpcInspector);
    expect(wrapper.findAll(".belief-card")).toHaveLength(0);
    expect(wrapper.find(".npc-inspector__placeholder").text()).toBe("select an NPC");
  });

  it("renders an honest empty state for a selected NPC who holds no beliefs (not the removed fixture)", () => {
    setSocialState(emptySocialState(50));
    const wrapper = mount(NpcInspector, { props: { npcName: "npc-a" } });
    expect(wrapper.findAll(".belief-card")).toHaveLength(0);
    expect(wrapper.find(".npc-inspector__placeholder").text()).toContain("no beliefs held");
  });

  it("renders one real belief card per belief the selected NPC holds, with strengths/stage at T", () => {
    setSocialState(stateWithOneActiveBelief());
    const wrapper = mount(NpcInspector, { props: { npcName: "npc-a" } });
    const cards = wrapper.findAll(".belief-card");
    expect(cards).toHaveLength(1);
    expect(cards[0].classes()).toContain("belief-card--active");
    expect(cards[0].find(".belief-card__text").text()).toBe("perpetrator: unknown, cause: assassination");
    expect(wrapper.text()).toContain("REPEATED");
    expect(wrapper.text()).toContain("0.78");
  });

  it("scrubbing T (via the store) changes the shown beliefs -- dormant once the rumor has gone quiet long enough", () => {
    const state = stateWithOneActiveBelief();
    setSocialState(state);
    const wrapper = mount(NpcInspector, { props: { npcName: "npc-a" } });
    expect(wrapper.find(".belief-card").classes()).toContain("belief-card--active");

    const mapData = useMapDataStore();
    mapData.socialState = { ...state, tick: 2000 }; // past RUMOR_DORMANT_AFTER
    return wrapper.vm.$nextTick().then(() => {
      expect(wrapper.find(".belief-card").classes()).toContain("belief-card--quiet");
      expect(wrapper.find(".npc-inspector__derived").exists()).toBe(true);
    });
  });

  it("renders a variant chip and slot-substituted text for a varianted belief", () => {
    const state = emptySocialState(5);
    state.claims.set(CLAIM.id, CLAIM);
    const variant: KeyframeVariant = {
      id: "variant-1",
      claim_id: "claim-1",
      parent_variant_id: null,
      slots: { perpetrator: "a bandit chief", cause: "assassination" },
      mutated_slot: "perpetrator",
      gamets: 1,
    };
    state.variants.set(variant.id, variant);
    state.beliefs.set("belief-1", belief({ variant_id: "variant-1" }));
    state.rumors.set("npc-a claim-1 variant-1", rumor({ variant_id: "variant-1" }));
    setSocialState(state);

    const wrapper = mount(NpcInspector, { props: { npcName: "npc-a" } });
    expect(wrapper.find(".belief-card__text").text()).toBe("perpetrator: a bandit chief, cause: assassination");
    const chips = wrapper.findAll(".chip");
    expect(chips.map((c) => c.text())).toContain("perpetrator: a bandit chief");
  });

  it("switches provenance/derived presentation between observer and story salience (a switch, never a fork)", () => {
    setSocialState(stateWithOneActiveBelief());
    const observer = mount(NpcInspector, { props: { npcName: "npc-a", salience: "observer" } });
    expect(observer.find(".npc-inspector__provenance--story").exists()).toBe(false);
    expect(observer.text()).toContain("told-by");

    const story = mount(NpcInspector, { props: { npcName: "npc-a", salience: "story" } });
    expect(story.find(".npc-inspector__provenance--story").exists()).toBe(true);
    expect(story.text()).toContain("Heard from");
  });

  it("shows props for name/location/as-of tick and pin count", () => {
    const wrapper = mount(NpcInspector, {
      props: {
        npcName: "Test NPC",
        location: "somewhere",
        asOfTick: 100,
        pinnedCount: 3,
      },
    });
    expect(wrapper.find(".npc-inspector__name").text()).toBe("Test NPC");
    expect(wrapper.find(".npc-inspector__location").text()).toBe("somewhere");
    expect(wrapper.text()).toContain("t=100");
    expect(wrapper.text()).toContain("pins: 3");
  });

  it("omits the location link entirely when the host doesn't pass one (not derivable from SocialState)", () => {
    const wrapper = mount(NpcInspector, { props: { npcName: "npc-a" } });
    expect(wrapper.find(".npc-inspector__location").exists()).toBe(false);
  });
});
