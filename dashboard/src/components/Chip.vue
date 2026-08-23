<script setup lang="ts">
/**
 * Chip — small pill/tag used everywhere in the mockup: claim id
 * ("C-114"), stage/variant labels ("REPEATED", "DORMANT", "v2 ·
 * ..."), layer toggles ("glyphs", "labels", "routes"), the run/branch/
 * seed strip. Tone controls fill/border/text; every tone here traces to
 * a specific mockup use (see tokens.css comments for line refs).
 */
export type ChipTone =
  | "default" // hairline border, no fill — run/branch/seed strip
  | "active" // gold fill — active layer toggles, active salience tab
  | "muted" // dim border only — inactive layer toggle, "no producer" states
  | "stage-repeated"
  | "stage-dormant"
  | "variant";

withDefaults(
  defineProps<{
    tone?: ChipTone;
    /** Renders as an <a> (mockup default) instead of a <span>. */
    href?: string;
  }>(),
  { tone: "default" },
);
</script>

<template>
  <component
    :is="href !== undefined ? 'a' : 'span'"
    :href="href"
    class="chip"
    :class="`chip--${tone}`"
  >
    <slot />
  </component>
</template>

<style scoped>
.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-chip);
  padding: 1px 6px;
  border-radius: var(--radius-chip);
  white-space: nowrap;
  line-height: 1.6;
}

.chip--default {
  border: 1px solid var(--c-hairline);
  color: var(--c-text-body);
}

.chip--active {
  border: 1px solid var(--c-chip-active-border);
  background: var(--c-chip-active-fill);
  color: var(--c-accent-hover);
}

.chip--muted {
  border: 1px solid var(--chip-muted-border);
  color: var(--c-text-dim);
}

.chip--stage-repeated {
  border: 1px solid var(--chip-repeated-border);
  background: var(--chip-repeated-fill);
  color: var(--chip-repeated-text);
}

.chip--stage-dormant {
  border: 1px solid var(--chip-dormant-border);
  background: var(--chip-dormant-fill);
  color: var(--chip-dormant-text);
}

.chip--variant {
  border: 1px solid var(--chip-variant-border);
  background: var(--chip-variant-fill);
  color: var(--chip-variant-text);
}
</style>
