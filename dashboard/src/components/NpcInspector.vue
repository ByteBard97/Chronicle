<script setup lang="ts">
/**
 * NpcInspector — the Tier-0 NPC inspector shell (ui-spec §3.2): pinnable,
 * four stable tabs (Beliefs/Relationships/Schedule/History), moodlet-
 * style belief cards with the three strength bars, provenance block,
 * and derived-state honesty for dormant/forgotten beliefs.
 *
 * Lane 28: the Beliefs tab is real data now — `npcName` (still named for
 * the prop's original fixture shape; both host screens already feed it
 * the selected NPC's real id) selects `state.beliefs` values (from
 * `stores/mapData.ts`'s shared `socialState`) held by that id, resolved
 * via `derived/inspectorBeliefs.ts` (claim text, stage, decayed
 * strengths, a summary provenance fact — see that module's header for
 * the reconstruct.ts rumor-rekeying finding it works around).
 * Relationships/Schedule/History still render their stable tab chrome
 * with a "not wired yet" placeholder (later packets) so the tab strip
 * itself (D20: inspectors accumulate, bulk-close) is real.
 *
 * As-of-T: strengths/stage are always computed from
 * `mapData.socialState.tick` (the store's actual reconstructed tick),
 * never from the `asOfTick` prop — `asOfTick` is display-only (the
 * header's "as-of t=" line) and falls back to the store's tick when the
 * host doesn't pass one. See this lane's report: FeedScreen doesn't yet
 * load `mapData` itself (only MapScreen/VariantTreeScreen do), a
 * pre-existing gap outside this component's boundary.
 *
 * Schedule tab (lane 41, ui-spec §3.8): real content now, via the same
 * `ScheduleLanes.vue` the standalone `/scheddiff` route renders (the
 * packet's "two hosts, one component" pin) -- this tab passes
 * `mapData.socialState.baseSchedule`/`mapData.eventRecords`/`atTick`
 * straight through and restricts it to the selected NPC (`npcIds:
 * [npcName]`) rather than computing anything itself.
 */
import { computed, ref } from "vue";
import PanelGlass from "./PanelGlass.vue";
import BeliefCard from "./BeliefCard.vue";
import StrengthBar from "./StrengthBar.vue";
import ScheduleLanes from "./scheddiff/ScheduleLanes.vue";
import type { SalienceLevel } from "../stores/salience";
import { useMapDataStore } from "../stores/mapData";
import { beliefsForNpc } from "../derived/inspectorBeliefs";
import type { RumorStage } from "../derived/rumorStage";
import { GIST_DECAY_HALF_LIFE } from "../derived/constants";

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

const mapData = useMapDataStore();
const atTick = computed(() => mapData.socialState.tick);
const displayTick = computed(() => props.asOfTick ?? atTick.value);

const beliefs = computed(() =>
  props.npcName === undefined ? [] : beliefsForNpc(mapData.socialState, props.npcName, atTick.value),
);

const scheduleNpcIds = computed(() => (props.npcName === undefined ? [] : [props.npcName]));

const STAGE_META: Record<RumorStage, { label: string; tone: "muted" | "stage-repeated" | "stage-dormant" }> = {
  unheard: { label: "UNHEARD", tone: "muted" },
  heard: { label: "HEARD", tone: "muted" },
  repeated: { label: "REPEATED", tone: "stage-repeated" },
  dormant: { label: "DORMANT", tone: "stage-dormant" },
  forgotten: { label: "FORGOTTEN", tone: "muted" },
};

// The moodlet's warm/highlighted vs. quiet split (BeliefCard's `active`):
// "currently spreading/contested" (heard/repeated) vs. a derived-state
// stage (dormant/forgotten/unheard) that shows its derivation inputs
// instead of live strength bars (ui-spec §3.2's "derived states show
// their derivation" rule, D22).
function isActiveStage(stage: RumorStage): boolean {
  return stage === "heard" || stage === "repeated";
}
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
        <a v-if="location" href="#" class="npc-inspector__location">{{ location }}</a>
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
        as-of t={{ displayTick.toLocaleString() }} · sel in url ·
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
        <template v-if="beliefs.length > 0">
          <BeliefCard
            v-for="belief in beliefs"
            :key="belief.beliefId"
            :claim-id="belief.claimId"
            :stage="STAGE_META[belief.stage]"
            :variant-label="belief.variantLabel ?? undefined"
            :text="belief.text"
            :active="isActiveStage(belief.stage)"
          >
            <template v-if="isActiveStage(belief.stage)">
              <StrengthBar label="confidence" tone="confidence" :value="belief.confidence">
                <template #value>{{ belief.confidence.toFixed(2) }}</template>
              </StrengthBar>
              <StrengthBar label="verbatim" tone="verbatim" :value="belief.verbatimStrength">
                <template #value>{{ belief.verbatimStrength.toFixed(2) }}</template>
              </StrengthBar>
              <StrengthBar label="gist" tone="gist" :value="belief.gistStrength">
                <template #value>{{ belief.gistStrength.toFixed(2) }}</template>
              </StrengthBar>
              <!-- salience is a switch over one design, never a fork
                   (design-tokens.md conventions) — same top-level
                   grounding-evidence fact, two presentations. The full
                   chain render (witness/relay/mutation hops) is lane
                   22's drill-down, not this summary block. -->
              <div v-if="belief.provenance && !isStory" class="npc-inspector__provenance">
                ◈ told-by ← <a href="#">{{ belief.provenance.sourceId }}</a> ·
                <a href="#">t {{ belief.provenance.tick.toLocaleString() }}</a> ·
                {{ belief.provenance.evidenceType }}
              </div>
              <div v-else-if="belief.provenance" class="npc-inspector__provenance npc-inspector__provenance--story">
                Heard from <a href="#">{{ belief.provenance.sourceId }}</a>
                ({{ belief.provenance.evidenceType }}) at tick
                {{ belief.provenance.tick.toLocaleString() }}.
              </div>
            </template>
            <template v-else>
              <!-- derived-state honesty (ui-spec §3.2, design-tokens.md
                   conventions): dormant/forgotten/unheard show their
                   derivation inputs, never presented as a stored fact —
                   in both salience presentations. Gist strength/half-life
                   are the relevant inputs: rumorStageAt's dormant/
                   forgotten thresholds are keyed on decayed gist. -->
              <div v-if="!isStory" class="npc-inspector__derived">
                derived: last rehearsed
                <a href="#">t {{ belief.lastRehearsed.toLocaleString() }}</a>
                · half-life
                <a href="#">{{ GIST_DECAY_HALF_LIFE.toLocaleString() }}</a>
                → strength
                <a href="#">{{ belief.gistStrength.toFixed(2) }}</a>
              </div>
              <div v-else class="npc-inspector__derived npc-inspector__derived--story">
                fading — not spoken of since tick
                <a href="#">{{ belief.lastRehearsed.toLocaleString() }}</a>
                · strength <a href="#">{{ belief.gistStrength.toFixed(2) }}</a>, derived
              </div>
            </template>
          </BeliefCard>
          <div class="npc-inspector__footnote">
            {{ beliefs.length }} belief{{ beliefs.length === 1 ? "" : "s" }}
          </div>
        </template>
        <div v-else class="npc-inspector__placeholder">
          {{ npcName ? `no beliefs held (as of t=${displayTick})` : "select an NPC" }}
        </div>
      </template>
      <template v-else-if="activeTab === 'schedule'">
        <ScheduleLanes
          v-if="npcName !== undefined"
          :base-schedule="mapData.socialState.baseSchedule"
          :event-records="mapData.eventRecords"
          :tick="atTick"
          :run-id="mapData.runId"
          :npc-ids="scheduleNpcIds"
        />
        <div v-else class="npc-inspector__placeholder">select an NPC</div>
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
