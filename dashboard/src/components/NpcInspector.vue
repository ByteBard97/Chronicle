<script setup lang="ts">
/**
 * NpcInspector — the Tier-0 NPC inspector shell (ui-spec §3.2): pinnable,
 * four stable tabs (Beliefs/Relationships/Schedule/History), moodlet-
 * style belief cards with the three strength bars, provenance block,
 * and derived-state honesty for dormant/forgotten beliefs.
 *
 * Scope for this lane: the shell + the Beliefs tab, skinned to the
 * approved mockup (map-c-skyrim.dc.html:120-203) with static,
 * schema-typed fixture data — Lane 6's reader wires the real per-tick
 * belief list at integration. Relationships/Schedule/History render
 * their stable tab chrome with a "not wired yet" placeholder so the
 * tab strip itself (D20: inspectors accumulate, bulk-close) is real.
 */
import { computed, ref } from "vue";
import PanelGlass from "./PanelGlass.vue";
import BeliefCard from "./BeliefCard.vue";
import StrengthBar from "./StrengthBar.vue";
import type { SalienceLevel } from "../stores/salience";

export type InspectorTab = "beliefs" | "relationships" | "schedule" | "history";

const props = withDefaults(
  defineProps<{
    npcName?: string;
    location?: string;
    asOfTick?: number;
    salience?: SalienceLevel;
    pinnedCount?: number;
  }>(),
  {
    npcName: "Fralia Gray-Mane",
    location: "market",
    asOfTick: 31442,
    salience: "observer",
    pinnedCount: 1,
  },
);

const activeTab = ref<InspectorTab>("beliefs");
const watching = ref<"watch" | "follow">("watch");

// ui-spec §2 / design-tokens.md: "salience is a switch over one design,
// never a fork." Only two presentations are traced in the approved
// mockup (isObs/isStory, map-c-skyrim.dc.html:169,176) — developer
// renders the same as observer here (see SalienceSwitch's finding: DEV
// has no traced visual state of its own in the approved mockup either).
const isStory = computed(() => props.salience === "story");

// Static fixture, shape-matched to the approved mockup
// (map-c-skyrim.dc.html:145-197). Real data arrives via Lane 6's
// reader at integration; nothing here is generated (no Date.now, no
// random ids) so the component stays screenshot-stable.
interface BeliefFixture {
  claimId: string;
  stage: "repeated" | "dormant";
  variantLabel?: string;
  text: string;
  confidence?: number;
  verbatim?: number;
  gist?: number;
  verbatimSpark?: string;
  gistSpark?: string;
  toldBy?: string;
  toldByLocation?: string;
  toldByTick?: number;
  witness?: string;
  witnessTick?: number;
  unchangedRelays?: number;
  mutator?: string;
  mutatorNewValue?: string;
  mutationTick?: number;
  hops?: number;
  mutations?: number;
  derivedLastRehearsed?: number;
  derivedHalfLife?: number;
  derivedStrength?: number;
}

const beliefs: BeliefFixture[] = [
  {
    claimId: "C-114",
    stage: "repeated",
    variantLabel: 'v2 · "Imperial agents"',
    text: "Jarl Balgruuf is dead — slain by Imperial agents.",
    confidence: 0.78,
    verbatim: 0.41,
    gist: 0.86,
    verbatimSpark: "0,3 12,5 24,7 34,9 42,10",
    gistSpark: "0,9 12,6 24,4 34,3 42,3",
    toldBy: "Hulda",
    toldByLocation: "The Bannered Mare",
    toldByTick: 29101,
    witness: "Irileth",
    witnessTick: 23301,
    unchangedRelays: 2,
    mutator: "Mikael",
    mutatorNewValue: "Imperial agents",
    mutationTick: 24613,
    hops: 4,
    mutations: 1,
  },
  {
    claimId: "C-087",
    stage: "dormant",
    text: "Eorlund's steel is the finest in Skyrim.",
    derivedLastRehearsed: 12004,
    derivedHalfLife: 8640,
    derivedStrength: 0.22,
  },
];

const totalBeliefs = 14;
</script>

<script lang="ts">
export const INSPECTOR_TABS: readonly InspectorTab[] = [
  "beliefs",
  "relationships",
  "schedule",
  "history",
];
</script>

<template>
  <PanelGlass tone="inspector" class="npc-inspector" :padded="false">
    <div class="npc-inspector__header">
      <div class="npc-inspector__title-row">
        <div class="npc-inspector__name">{{ npcName }}</div>
        <a href="#" class="npc-inspector__location">{{ location }}</a>
        <div class="npc-inspector__spacer" />
        <div class="npc-inspector__watch">
          <button
            type="button"
            class="npc-inspector__watch-opt"
            :class="{ 'npc-inspector__watch-opt--active': watching === 'watch' }"
            @click="watching = 'watch'"
          >
            watch
          </button>
          <button
            type="button"
            class="npc-inspector__watch-opt"
            :class="{ 'npc-inspector__watch-opt--active': watching === 'follow' }"
            @click="watching = 'follow'"
          >
            follow
          </button>
        </div>
        <a href="#" title="pin" class="npc-inspector__icon-btn">⊙</a>
        <a href="#" title="close" class="npc-inspector__icon-btn">✕</a>
      </div>
      <div class="npc-inspector__meta">
        as-of t={{ asOfTick.toLocaleString() }} · sel in url ·
        <a href="#">deep-link ⧉</a>
      </div>
    </div>

    <div class="npc-inspector__tabs" role="tablist">
      <button
        v-for="tab in INSPECTOR_TABS"
        :key="tab"
        type="button"
        role="tab"
        class="npc-inspector__tab"
        :class="{ 'npc-inspector__tab--active': activeTab === tab }"
        :aria-selected="activeTab === tab"
        @click="activeTab = tab"
      >
        {{ tab.toUpperCase() }}
      </button>
    </div>

    <div class="npc-inspector__salience-row">
      salience: {{ salience }} ▾
      <span class="npc-inspector__spacer" />
      <a href="#">all events ⤢</a>
    </div>

    <div class="npc-inspector__body">
      <template v-if="activeTab === 'beliefs'">
        <BeliefCard
          v-for="belief in beliefs"
          :key="belief.claimId"
          :claim-id="belief.claimId"
          :stage="
            belief.stage === 'repeated'
              ? { label: 'REPEATED', tone: 'stage-repeated' }
              : { label: 'DORMANT', tone: 'stage-dormant' }
          "
          :variant-label="belief.variantLabel"
          :text="belief.text"
          :active="belief.stage === 'repeated'"
        >
          <template v-if="belief.stage === 'repeated'">
            <StrengthBar label="confidence" tone="confidence" :value="belief.confidence ?? 0">
              <template #value><a href="#">{{ (belief.confidence ?? 0).toFixed(2) }}</a></template>
            </StrengthBar>
            <StrengthBar label="verbatim" tone="verbatim" :value="belief.verbatim ?? 0">
              <template #sparkline>
                <svg width="42" height="12">
                  <polyline
                    :points="belief.verbatimSpark"
                    fill="none"
                    stroke="var(--bar-verbatim)"
                    stroke-width="1.5"
                  />
                </svg>
              </template>
              <template #value><a href="#">{{ (belief.verbatim ?? 0).toFixed(2) }}</a></template>
            </StrengthBar>
            <StrengthBar label="gist" tone="gist" :value="belief.gist ?? 0">
              <template #sparkline>
                <svg width="42" height="12">
                  <polyline
                    :points="belief.gistSpark"
                    fill="none"
                    stroke="var(--bar-gist)"
                    stroke-width="1.5"
                  />
                </svg>
              </template>
              <template #value><a href="#">{{ (belief.gist ?? 0).toFixed(2) }}</a></template>
            </StrengthBar>
            <!-- salience is a switch over one design, never a fork
                 (design-tokens.md conventions) — same DAG-honest chain
                 (D9/D10), two presentations: observer's linked
                 provenance chain vs. story's narrative gloss
                 (map-c-skyrim.dc.html:169-182). -->
            <div v-if="!isStory" class="npc-inspector__provenance">
              ◈ told-by ← <a href="#">{{ belief.toldBy }}</a> ·
              <a href="#">t {{ belief.toldByTick?.toLocaleString() }}</a> ·
              <a href="#">{{ belief.toldByLocation }}</a><br />
              chain: <a href="#">{{ belief.witness }}</a> (witness,
              <a href="#">t {{ belief.witnessTick?.toLocaleString() }}</a>) ←
              <a href="#">{{ belief.unchangedRelays }} unchanged relays ⊕</a> ←
              <a href="#">✱ v{{ belief.variantLabel?.match(/v(\d+)/)?.[1] ?? "2" }} mutation ({{ belief.mutator }}, t
                {{ belief.mutationTick?.toLocaleString() }})</a
              ><br />
              <a href="#">provenance ▸ {{ belief.hops }} hops · {{ belief.mutations }} mutation{{
                (belief.mutations ?? 0) === 1 ? "" : "s"
              }}</a>
              · <a href="#">variant tree ▸</a>
            </div>
            <div v-else class="npc-inspector__provenance npc-inspector__provenance--story">
              Heard from <a href="#">{{ belief.toldBy }}</a> at
              <a href="#">{{ belief.toldByLocation }}</a>.<br />
              The story changed once on its way to her —
              <a href="#">{{ belief.mutator }}</a> made the assassin
              <em>{{ belief.mutatorNewValue }}</em
              >.<br />
              <a href="#">trace the telling ▸ {{ belief.hops }} hops ·
                {{ belief.mutations }} mutation{{
                  (belief.mutations ?? 0) === 1 ? "" : "s"
                }}</a
              >
            </div>
          </template>
          <template v-else>
            <!-- derived-state honesty (ui-spec §3.2, design-tokens.md
                 conventions): dormant/forgotten show their derivation
                 inputs, never presented as a stored fact — in both
                 salience presentations. -->
            <div v-if="!isStory" class="npc-inspector__derived">
              derived: last rehearsed
              <a href="#">t {{ belief.derivedLastRehearsed?.toLocaleString() }}</a>
              · half-life
              <a href="#">{{ belief.derivedHalfLife?.toLocaleString() }}</a>
              → strength
              <a href="#">{{ belief.derivedStrength }}</a>
            </div>
            <div v-else class="npc-inspector__derived npc-inspector__derived--story">
              fading — not spoken of since tick
              <a href="#">{{ belief.derivedLastRehearsed?.toLocaleString() }}</a>
              · strength <a href="#">{{ belief.derivedStrength }}</a>, derived ·
              <a href="#">why ▸</a>
            </div>
          </template>
        </BeliefCard>
        <div class="npc-inspector__footnote">
          {{ totalBeliefs }} beliefs · showing {{ beliefs.length }} salient ·
          <a href="#">all ▸</a>
        </div>
      </template>
      <div v-else class="npc-inspector__placeholder">
        {{ activeTab }} — not wired yet (Lane 6 reader, later packet)
      </div>
    </div>

    <div class="npc-inspector__footer">
      <span>pins: {{ pinnedCount }}</span>
      <span class="npc-inspector__spacer" />
      <a href="#">close all ✕✕</a>
    </div>
  </PanelGlass>
</template>

<style scoped>
.npc-inspector {
  width: 372px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-radius: 0;
  border-left: 1px solid var(--c-hairline);
  border-top: none;
  border-right: none;
  border-bottom: none;
}

.npc-inspector__header {
  padding: 12px 16px 9px;
  border-bottom: 1px solid var(--c-hairline-soft);
}

.npc-inspector__title-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.npc-inspector__name {
  font-family: var(--font-display);
  font-size: var(--fs-npc-name);
  font-weight: 600;
  color: var(--c-text-primary);
  white-space: nowrap;
}

.npc-inspector__location {
  font-size: 10px;
}

.npc-inspector__spacer {
  flex: 1;
}

.npc-inspector__watch {
  display: flex;
  border: 1px solid var(--c-hairline);
  border-radius: var(--radius-chip);
  overflow: hidden;
  font-size: 9px;
}

.npc-inspector__watch-opt {
  appearance: none;
  border: none;
  border-left: 1px solid var(--c-hairline);
  background: transparent;
  color: var(--c-text-dim);
  padding: 2px 6px;
  font-family: inherit;
  cursor: pointer;
}

.npc-inspector__watch-opt:first-child {
  border-left: none;
}

.npc-inspector__watch-opt--active {
  background: var(--c-chip-active-fill);
  color: var(--c-accent-hover);
}

.npc-inspector__icon-btn {
  color: var(--c-text-dim);
}

.npc-inspector__meta {
  color: var(--c-text-faint);
  font-size: var(--fs-micro);
  margin-top: 3px;
}

.npc-inspector__tabs {
  display: flex;
  border-bottom: 1px solid var(--c-hairline-soft);
  font-size: 10px;
}

.npc-inspector__tab {
  appearance: none;
  border: none;
  background: transparent;
  font-family: inherit;
  padding: 7px 12px;
  color: var(--c-text-dim);
  border-bottom: 2px solid transparent;
  cursor: pointer;
}

.npc-inspector__tab--active {
  color: var(--c-text-primary);
  border-bottom-color: var(--c-accent);
}

.npc-inspector__salience-row {
  padding: 6px 16px;
  border-bottom: 1px solid var(--c-hairline-soft);
  display: flex;
  gap: 8px;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}

.npc-inspector__body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-width: 0;
  padding: 11px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.npc-inspector__provenance,
.npc-inspector__derived {
  font-size: var(--fs-secondary);
  color: var(--c-text-secondary);
  line-height: 1.6;
  border-top: 1px solid var(--c-hairline-soft);
  padding-top: 7px;
  margin-top: 5px;
  overflow-wrap: break-word;
}

.npc-inspector__derived {
  color: var(--c-text-dim);
}

.npc-inspector__provenance--story {
  font-family: var(--font-narrative);
  font-style: italic;
  font-size: var(--fs-story-provenance);
  color: var(--c-story-text-active);
  line-height: 1.65;
}

.npc-inspector__derived--story {
  font-family: var(--font-narrative);
  font-style: italic;
  font-size: 11.5px;
  color: var(--c-story-text-quiet);
  line-height: 1.65;
}

.npc-inspector__footnote {
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}

.npc-inspector__placeholder {
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
  padding: 8px 0;
}

.npc-inspector__footer {
  padding: 7px 16px;
  border-top: 1px solid var(--c-hairline-soft);
  display: flex;
  font-size: var(--fs-secondary);
  color: var(--c-text-faint);
}
</style>
