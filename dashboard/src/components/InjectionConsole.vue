<script setup lang="ts">
/**
 * InjectionConsole — Tier-0 injection console (ui-spec §3.1). No
 * mockup exists for this view; built in the same token language as the
 * approved chrome, simplest thing consistent with the design: a form
 * for canonical-event fields, a live JSON preview, and the
 * `chronicle inject` CLI invocation it corresponds to (per §3.1: "the
 * runner is not a backend" — the dashboard shows what to run, it does
 * not run it). Developer-only salience per §3.1.
 *
 * Presentational only: the computed JSON/CLI strings are a display
 * projection of local form state, not a submission path. Lane 6 (or a
 * later packet) wires an actual submit/fork-confirmation flow.
 */
import { computed, reactive } from "vue";
import PanelGlass from "./PanelGlass.vue";
import Chip from "./Chip.vue";

const EVENT_TYPES = [
  "claim_born",
  "mutation",
  "grudge_formed",
  "threshold_crossed",
] as const;

const form = reactive({
  eventType: EVENT_TYPES[0] as (typeof EVENT_TYPES)[number],
  runId: "t6-jarl-01",
  atTick: 31442,
  actor: "",
  payload: '{\n  "text": ""\n}',
});

const payloadJson = computed(() => {
  let parsed: unknown = null;
  let valid = true;
  try {
    parsed = JSON.parse(form.payload);
  } catch {
    valid = false;
  }
  return { valid, preview: valid ? JSON.stringify(parsed, null, 2) : null };
});

const eventJson = computed(() =>
  JSON.stringify(
    {
      type: form.eventType,
      run_id: form.runId,
      at_tick: form.atTick,
      actor: form.actor || null,
      payload: payloadJson.value.valid ? JSON.parse(form.payload) : null,
    },
    null,
    2,
  ),
);

const cliInvocation = computed(
  () =>
    `chronicle inject --run ${form.runId} --at ${form.atTick} --type ${form.eventType}` +
    (form.actor ? ` --actor ${form.actor}` : "") +
    ` --payload '${form.payload.replace(/\n\s*/g, " ").trim()}'`,
);

// A forked-history warning is a display concern, not a submit action:
// §3.1's fork semantics say appending at a historical tick < LIVE forks
// the run. This console names that consequence; it does not perform it.
const forksHistory = computed(() => form.atTick < 31442 - 1);
</script>

<template>
  <PanelGlass tone="strong" class="injection-console">
    <div class="injection-console__header">
      <span class="injection-console__title">INJECTION CONSOLE</span>
      <Chip tone="muted">developer-only</Chip>
    </div>

    <form class="injection-console__form" @submit.prevent>
      <label class="injection-console__field">
        <span>event type</span>
        <select v-model="form.eventType">
          <option v-for="t in EVENT_TYPES" :key="t" :value="t">{{ t }}</option>
        </select>
      </label>
      <label class="injection-console__field">
        <span>run</span>
        <input v-model="form.runId" type="text" />
      </label>
      <label class="injection-console__field">
        <span>at tick</span>
        <input v-model.number="form.atTick" type="number" />
      </label>
      <label class="injection-console__field">
        <span>actor (optional)</span>
        <input v-model="form.actor" type="text" placeholder="npc id" />
      </label>
      <label class="injection-console__field injection-console__field--payload">
        <span>payload (JSON)</span>
        <textarea v-model="form.payload" rows="4" spellcheck="false" />
      </label>
    </form>

    <div v-if="forksHistory" class="injection-console__fork-warning">
      forking from tick {{ form.atTick }} — this appends before LIVE and
      creates a new generation, re-simulated from here (§3.1)
    </div>

    <div class="injection-console__preview">
      <div class="injection-console__preview-label">event JSON preview</div>
      <pre class="injection-console__code">{{ eventJson }}</pre>
    </div>

    <div class="injection-console__preview">
      <div class="injection-console__preview-label">chronicle inject invocation</div>
      <pre class="injection-console__code injection-console__code--cli">{{ cliInvocation }}</pre>
    </div>
  </PanelGlass>
</template>

<style scoped>
.injection-console {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 480px;
}

.injection-console__header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.injection-console__title {
  font-family: var(--font-display);
  color: var(--c-panel-title);
  font-size: var(--fs-panel-title);
  letter-spacing: var(--ls-panel-title);
}

.injection-console__form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.injection-console__field {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: var(--fs-secondary);
  color: var(--c-text-dim);
}

.injection-console__field input,
.injection-console__field select,
.injection-console__field textarea {
  font-family: var(--font-data);
  font-size: var(--fs-body);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--c-hairline);
  border-radius: var(--radius-chip);
  color: var(--c-text-body);
  padding: 4px 7px;
}

.injection-console__field--payload textarea {
  resize: vertical;
}

.injection-console__fork-warning {
  border: 1px solid var(--ev-grudge, #7e2a18);
  background: rgba(224, 82, 82, 0.08);
  color: #ffb3ad;
  border-radius: var(--radius-chip);
  padding: 6px 9px;
  font-size: var(--fs-secondary);
  line-height: 1.5;
}

.injection-console__preview-label {
  color: var(--c-text-faint);
  font-size: var(--fs-micro);
  margin-bottom: 3px;
}

.injection-console__code {
  margin: 0;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--c-hairline-soft);
  border-radius: var(--radius-chip);
  padding: 8px 9px;
  font-size: var(--fs-secondary);
  color: var(--c-text-secondary);
  overflow-x: auto;
  white-space: pre;
}

.injection-console__code--cli {
  color: var(--c-accent-hover);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
