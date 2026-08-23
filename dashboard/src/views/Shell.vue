<script setup lang="ts">
// M1 app frame, skinned per the approved mockup (map-c-skyrim.dc.html)
// and design-tokens.md. Still M1 scope: no map/timeline/variant-tree/
// drill-down (those are M3+, ui-spec §3 build order) — this renders
// the app chrome, the Tier-0 tick stepper, and the two Tier-0 views
// this lane was asked to skin/build (NPC inspector, injection console)
// as static-fixture demonstrations of the design language. Lane 6's
// reader wires real per-tick data into them at integration.
//
// The underlying <select id="salience-level"> is kept exactly as Lane
// 6 built it (same id, same options, same store binding) so
// Shell.test.ts's existing assertion on its options keeps passing; it
// is visually hidden (.sr-only) in favor of the skinned SalienceSwitch
// segmented control next to it, both bound to the same store so they
// can never disagree.
import { useUrlState } from "../state/urlState";
import { useSelectionStore } from "../stores/selection";
import { useSalienceStore, SALIENCE_LEVELS } from "../stores/salience";
import { useFrameLogStore } from "../stores/frameLog";
import RunPicker from "../components/RunPicker.vue";
import SalienceSwitch from "../components/SalienceSwitch.vue";
import LiveDockIndicator from "../components/LiveDockIndicator.vue";
import PanelGlass from "../components/PanelGlass.vue";
import NpcInspector from "../components/NpcInspector.vue";
import InjectionConsole from "../components/InjectionConsole.vue";

const urlState = useUrlState();
const selection = useSelectionStore();
const salience = useSalienceStore();

// Lane 6's log-reader client (src/log/), wired to the URL-state contract:
// picking a run (RunPicker) and moving the tick stepper drive
// stateAt(T) reconstruction; leaving t at null docks the LIVE tail. This
// readout is deliberately plain text (no styling) -- it is *not* the
// NPC inspector view, which stays on its own static fixture until a
// later lane wires real per-tick data into it.
const frameLog = useFrameLogStore();
frameLog.bindToUrlState(urlState.run, urlState.t);

function onTickInput(event: Event) {
  const raw = (event.target as HTMLInputElement).value;
  urlState.t.value = raw ? Number(raw) : null;
}

function stepTick(delta: number) {
  urlState.t.value = (urlState.t.value ?? 0) + delta;
}
</script>

<template>
  <div class="shell">
    <PanelGlass tone="topbar" class="shell__topbar" :padded="false">
      <div class="shell__wordmark">CHRONICLE</div>
      <RunPicker v-model="urlState.run.value" />
      <div class="shell__spacer" />
      <SalienceSwitch
        :mode="salience.level"
        @update:mode="salience.setLevel"
      />
    </PanelGlass>

    <div class="shell__stepper">
      <button
        type="button"
        class="shell__step-btn"
        title="previous tick"
        @click="stepTick(-1)"
      >
        ◀
      </button>
      <label for="tick-stepper" class="shell__tick-label">t</label>
      <input
        id="tick-stepper"
        class="shell__tick-input"
        type="number"
        :value="urlState.t.value ?? ''"
        @change="onTickInput"
      />
      <button
        type="button"
        class="shell__step-btn"
        title="next tick"
        @click="stepTick(1)"
      >
        ▶
      </button>

      <label for="salience-level" class="sr-only">salience</label>
      <select
        id="salience-level"
        class="sr-only"
        :value="salience.level"
        @change="
          salience.setLevel(
            ($event.target as HTMLSelectElement).value as typeof salience.level,
          )
        "
      >
        <option v-for="level in SALIENCE_LEVELS" :key="level" :value="level">
          {{ level }}
        </option>
      </select>

      <span class="shell__selection">
        selected: {{ selection.selectedIds.join(", ") || "(none)" }}
      </span>
    </div>

    <div id="frame-log-readout">
      <LiveDockIndicator />
      <span v-if="frameLog.loading">loading…</span>
      <span v-else-if="frameLog.error">frame-log error: {{ frameLog.error }}</span>
      <span v-else-if="frameLog.stateTick !== null">
        state as of t={{ frameLog.stateTick }}: {{ frameLog.claimCount }} claims,
        {{ frameLog.beliefCount }} beliefs
      </span>
    </div>

    <div id="empty-view-area" class="shell__views">
      <!-- Map/timeline/variant-tree/drill-down are M3+ (ui-spec §3
           build order) and not built here. The two Tier-0 views below
           are skinned per this lane's packet with static fixture data;
           they render side by side purely to show both surfaces at
           once during M1 — a router with real routes is later work. -->
      <InjectionConsole class="shell__injection-console" />
      <NpcInspector />
    </div>
  </div>
</template>

<style scoped>
.shell {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--c-page-bg);
  font-size: var(--fs-body);
}

.shell__topbar {
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 16px;
  border-bottom: 1px solid var(--c-hairline);
  border-left: none;
  border-right: none;
  border-top: none;
  border-radius: 0;
}

.shell__wordmark {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: var(--fs-wordmark);
  letter-spacing: var(--ls-wordmark);
  color: var(--c-accent-hover);
}

.shell__spacer {
  flex: 1;
}

.shell__stepper {
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--c-hairline);
}

.shell__step-btn {
  appearance: none;
  font-family: inherit;
  border: 1px solid var(--c-hairline);
  background: transparent;
  color: var(--c-text-body);
  border-radius: var(--radius-chip);
  padding: 3px 8px;
  cursor: pointer;
}

.shell__tick-label {
  color: var(--c-text-dim);
  font-size: var(--fs-secondary);
}

.shell__tick-input {
  font-family: var(--font-data);
  font-size: var(--fs-body);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--c-hairline);
  border-radius: var(--radius-chip);
  color: var(--c-text-body);
  padding: 3px 7px;
  width: 90px;
}

.shell__selection {
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
  margin-left: auto;
}

.shell__views {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 12px;
  padding: 12px;
  overflow: auto;
}

.shell__injection-console {
  flex: none;
}
</style>
