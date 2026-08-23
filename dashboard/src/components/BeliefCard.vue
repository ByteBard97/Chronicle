<script setup lang="ts">
/**
 * BeliefCard — the moodlet-style belief card shell from the NPC
 * inspector's Beliefs tab (map-c-skyrim.dc.html:145-197): claim id chip,
 * stage chip, optional variant chip, the claim text in the narrative
 * face, then caller-supplied detail content (strength bars + provenance
 * for an active belief; a single derived-state line for a
 * dormant/forgotten one — ui-spec §3.2's "derived states show their
 * derivation" rule, D22).
 *
 * This component only owns the card chrome + header chips; the two very
 * different detail bodies (full bars+chain vs. one derived-state line)
 * are the caller's slot content, composed from StrengthBar/Chip.
 */
import Chip, { type ChipTone } from "./Chip.vue";

export interface BeliefCardStage {
  /** Display label, e.g. "REPEATED", "DORMANT". */
  label: string;
  /** Chip tone to render it in — only repeated/dormant have traced
   *  tri-color chip tokens; anything else falls back to "muted". */
  tone: ChipTone;
}

defineProps<{
  claimId: string;
  claimHref?: string;
  stage: BeliefCardStage;
  variantLabel?: string;
  text: string;
  /** Active beliefs (currently spreading/contested) get the warm
   *  highlighted card; quiet ones (dormant/forgotten/canonical-and-
   *  unremarkable) render de-emphasized (map-c-skyrim.dc.html:184,
   *  opacity:.85 + the quiet border/bg pair). */
  active?: boolean;
}>();
</script>

<template>
  <div class="belief-card" :class="{ 'belief-card--active': active, 'belief-card--quiet': !active }">
    <div class="belief-card__header">
      <Chip :href="claimHref ?? '#'">{{ claimId }}</Chip>
      <Chip :tone="stage.tone">{{ stage.label }}</Chip>
      <Chip v-if="variantLabel" tone="variant">{{ variantLabel }}</Chip>
    </div>
    <div class="belief-card__text">{{ text }}</div>
    <div class="belief-card__body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.belief-card {
  border-radius: var(--radius-panel);
  padding: 11px 12px;
}

.belief-card--active {
  border: 1px solid var(--card-active-border);
  background: var(--card-active-bg);
}

.belief-card--quiet {
  border: 1px solid var(--card-quiet-border);
  background: var(--card-quiet-bg);
  opacity: 0.85;
}

.belief-card__header {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.belief-card__text {
  font-family: var(--font-narrative);
  color: var(--c-text-primary);
  line-height: 1.45;
  margin-bottom: 8px;
}

.belief-card--active .belief-card__text {
  font-size: var(--fs-claim-text);
}

.belief-card--quiet .belief-card__text {
  font-size: 12.5px;
  color: var(--c-text-body);
}

.belief-card__body {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
</style>
