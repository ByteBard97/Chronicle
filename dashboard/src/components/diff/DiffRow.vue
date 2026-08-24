<script setup lang="ts">
/**
 * DiffRow — one social-state delta (ui-spec §3.7: "every social-state
 * delta with signed Δ, firing-rule chip, triggering-event link"). Signed
 * Δ colored by sign (reusing existing tokens -- `--ev-grudge` red for a
 * decrease, `--c-accent-hover` gold for an increase; no new CSS values,
 * governance rule). The rule chip links to lane 31's rule-log route
 * (`/rules?filters={"rule":...}`, built directly against the `filters`
 * codec -- `panelUrlState.ts`'s `drill:` helper doesn't apply here, per
 * the packet). `run` is carried through the link (lane-31 finding: a
 * bare `<a>` is a full-page navigation, so a run-less link silently
 * dropped the loaded run) -- mirrors `eventHref`'s pattern below.
 * The event link jumps to the encounter feed at the triggering record's
 * tick (`/feed?run=...&t=...`), the M3 cross-view deep-link idiom already
 * established by row clicks elsewhere in the app.
 */
import { computed } from "vue";
import type { DiffRow } from "../../derived/socialDiff";
import { codecs } from "../../state/urlState";
import Chip from "../Chip.vue";

const props = defineProps<{
  row: DiffRow;
  runId: string | null;
}>();

const TYPE_LABEL: Record<DiffRow["type"], string> = {
  belief: "belief",
  grudge: "grudge",
  obligation: "obligation",
  reputation: "reputation",
};

const deltaSign = computed(() => (props.row.delta > 0 ? "positive" : props.row.delta < 0 ? "negative" : "zero"));
const deltaText = computed(() => `${props.row.delta >= 0 ? "+" : ""}${props.row.delta.toFixed(3)}`);

const ruleHref = computed(() => {
  const rule = props.row.rule;
  if (rule === null) return null;
  const encoded = codecs.filters.encode({ rule: rule.rule });
  const params = new URLSearchParams();
  if (props.runId !== null) params.set("run", props.runId);
  if (encoded !== undefined) params.set("filters", encoded);
  return `/rules?${params.toString()}`;
});

const eventHref = computed(() => {
  const event = props.row.event;
  if (event === null) return null;
  const params = new URLSearchParams();
  if (props.runId !== null) params.set("run", props.runId);
  params.set("t", String(event.tick));
  return `/feed?${params.toString()}`;
});
</script>

<template>
  <tr class="diff-row" :data-type="row.type">
    <td class="diff-row__type">
      <Chip tone="default">{{ TYPE_LABEL[row.type] }}</Chip>
    </td>
    <td class="diff-row__npcs">{{ row.npcs.join(", ") }}</td>
    <td class="diff-row__label">{{ row.label }}</td>
    <td class="diff-row__detail">{{ row.detail }}</td>
    <td class="diff-row__delta" :data-sign="deltaSign">{{ deltaText }}</td>
    <td class="diff-row__rule">
      <Chip v-if="row.rule !== null" tone="muted" :href="ruleHref ?? undefined">{{ row.rule.rule }}</Chip>
      <span v-else class="diff-row__none">(decay only)</span>
    </td>
    <td class="diff-row__event">
      <a v-if="eventHref !== null" :href="eventHref" class="diff-row__event-link">t{{ row.event!.tick }} · {{ row.event!.recordType }}</a>
      <span v-else class="diff-row__none">—</span>
    </td>
  </tr>
</template>

<style scoped>
.diff-row td {
  padding: 4px 8px;
  border-bottom: 1px solid var(--c-hairline-soft);
  font-size: var(--fs-secondary);
  color: var(--c-text-body);
  vertical-align: middle;
}

.diff-row__npcs {
  color: var(--c-text-secondary);
  white-space: nowrap;
}

.diff-row__label {
  color: var(--c-text-dim);
  font-size: var(--fs-micro);
}

.diff-row__delta {
  font-family: var(--font-data);
  text-align: right;
  white-space: nowrap;
}

.diff-row__delta[data-sign="positive"] {
  color: var(--c-accent-hover);
}

.diff-row__delta[data-sign="negative"] {
  color: var(--ev-grudge);
}

.diff-row__delta[data-sign="zero"] {
  color: var(--c-text-dim);
}

.diff-row__none {
  color: var(--c-text-faint);
  font-size: var(--fs-micro);
}

.diff-row__event-link {
  font-size: var(--fs-secondary);
  white-space: nowrap;
}
</style>
