<script setup lang="ts">
/**
 * RolesScreen — the role inspector (lane 52, ui-spec §3.10, Tier 5, the
 * last dashboard view in the spec's build order): "role, holder (linked),
 * duties with lapse state, vacancy history, succession record drill-down-
 * able like any derivation." Chrome (RunPicker/ViewSwitcher, the combined
 * `[run, t]` watcher for `frameLog.ts`'s documented load-before-tick
 * ordering hazard) mirrors every other top-level screen
 * (SchedDiffScreen.vue/DiffScreen.vue/RuleLogScreen.vue).
 *
 * Data: `derived/roles.ts`'s `buildRoleCards`, fed `mapData.eventRecords`
 * (the full events stream, keyframes excluded -- lane 14's contract) and
 * the current `atTick` -- a pure, from-scratch fold over the raw events on
 * every recompute, same "small-scale, not a general-purpose reader"
 * precedent `SchedDiffScreen.vue`'s header documents for
 * `computeScheduleDiff`. `mapData.socialState` itself is not read here:
 * `SocialState.roles` (reconstruct.ts) is a plain roster snapshot with no
 * vacancy/succession history, and this view needs the history (see
 * `derived/roles.ts`'s own header for why).
 *
 * Role selection is view-local UI state (a plain ref), not URL state --
 * the frozen `state/urlState.ts` schema has no per-role selection field,
 * and adding one would be an out-of-bounds edit for this lane (edit list
 * is `router/index.ts`/`ViewSwitcher.vue`/`socialDiff.ts`/`log/*` only).
 * The `?run=...&t=...` deep link -- the actual acceptance-tested case --
 * already fully determines which role CARDS render; which one is
 * currently expanded in the list is not part of that contract.
 */
import { computed, ref, watch } from "vue";
import RunPicker from "../components/RunPicker.vue";
import ViewSwitcher from "../components/ViewSwitcher.vue";
import RoleCard from "../components/roles/RoleCard.vue";
import { useUrlState } from "../state/urlState";
import { useMapDataStore } from "../stores/mapData";
import { buildRoleCards } from "../derived/roles";

const urlState = useUrlState();
const mapData = useMapDataStore();

// Single combined [run, t] watcher (same idiom as every other top-level
// screen): loading the run always finishes before a tick decision is
// made against it.
watch(
  [urlState.run, urlState.t],
  async ([runId, t], oldValue) => {
    const oldRunId = oldValue?.[0];
    if (runId !== oldRunId || oldValue === undefined) {
      await mapData.load(runId);
    }
    if (t === null) {
      await mapData.dockToLatest();
    } else {
      await mapData.setTick(t);
    }
  },
  { immediate: true },
);

const hasLoadedRun = computed(() => mapData.status === "loaded");
const atTick = computed(() => mapData.socialState.tick);

const roleCards = computed(() => (hasLoadedRun.value ? buildRoleCards(mapData.eventRecords, atTick.value) : []));

const selectedRoleId = ref<string | null>(null);
watch(roleCards, (cards) => {
  if (selectedRoleId.value !== null && cards.some((c) => c.roleId === selectedRoleId.value)) return;
  selectedRoleId.value = cards[0]?.roleId ?? null;
});

const selectedCard = computed(() => roleCards.value.find((c) => c.roleId === selectedRoleId.value) ?? null);

function selectRole(roleId: string) {
  selectedRoleId.value = roleId;
}
</script>

<template>
  <div class="roles-screen">
    <header class="roles-screen__chrome">
      <div class="roles-screen__wordmark">CHRONICLE</div>
      <RunPicker v-model="urlState.run.value" />
      <span class="roles-screen__meta">as-of t={{ atTick }}</span>
      <div class="roles-screen__spacer" />
      <ViewSwitcher current="roles" />
    </header>

    <div v-if="!hasLoadedRun" class="roles-screen__placeholder">no run loaded</div>
    <div v-else class="roles-screen__body">
      <nav class="roles-screen__list" aria-label="roles">
        <button
          v-for="card in roleCards"
          :key="card.roleId"
          type="button"
          class="roles-screen__list-item"
          :class="{ 'roles-screen__list-item--active': card.roleId === selectedRoleId }"
          @click="selectRole(card.roleId)"
        >
          <span class="roles-screen__list-title">{{ card.title }}</span>
          <span class="roles-screen__list-holder">{{ card.holderId ?? "(vacant)" }}</span>
        </button>
        <div v-if="roleCards.length === 0" class="roles-screen__empty">no roles installed as of this tick</div>
      </nav>

      <div class="roles-screen__detail">
        <RoleCard v-if="selectedCard !== null" :card="selectedCard" :run-id="urlState.run.value" />
        <div v-else class="roles-screen__empty">select a role</div>
      </div>
    </div>

    <footer class="roles-screen__footer">
      <span class="roles-screen__count">{{ roleCards.length }} role{{ roleCards.length === 1 ? "" : "s" }}</span>
    </footer>
  </div>
</template>

<style scoped>
.roles-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--c-page-bg);
  overflow: hidden;
  font-size: var(--fs-body);
}

.roles-screen__chrome {
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 16px;
  border-bottom: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-strong);
}

.roles-screen__wordmark {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.3em;
  color: var(--c-accent-hover);
}

.roles-screen__meta {
  color: var(--c-text-dim);
  white-space: nowrap;
  font-size: var(--fs-secondary);
}

.roles-screen__spacer {
  flex: 1;
}

.roles-screen__placeholder {
  padding: 24px;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}

.roles-screen__body {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.roles-screen__list {
  width: 220px;
  flex: none;
  overflow-y: auto;
  border-right: 1px solid var(--c-hairline);
  display: flex;
  flex-direction: column;
}

.roles-screen__list-item {
  appearance: none;
  border: none;
  border-bottom: 1px solid var(--c-hairline-soft);
  background: transparent;
  color: var(--c-text-body);
  text-align: left;
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-family: inherit;
}

.roles-screen__list-item:hover {
  background: var(--c-chip-active-fill);
}

.roles-screen__list-item--active {
  background: var(--c-chip-active-fill);
  border-left: 2px solid var(--c-accent-hover);
}

.roles-screen__list-title {
  font-size: var(--fs-secondary);
}

.roles-screen__list-holder {
  font-family: var(--font-data);
  font-size: var(--fs-micro);
  color: var(--c-text-dim);
}

.roles-screen__detail {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

.roles-screen__empty {
  padding: 16px;
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}

.roles-screen__footer {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 16px;
  border-top: 1px solid var(--c-hairline);
  background: var(--c-panel-glass-inspector);
  font-size: var(--fs-secondary);
  color: var(--c-text-dim);
}
</style>
