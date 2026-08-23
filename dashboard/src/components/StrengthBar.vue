<script setup lang="ts">
/**
 * StrengthBar — a labeled 0-1 strength bar with an optional inline
 * sparkline slot, per design-tokens.md's belief moodlet bars
 * (confidence / verbatim / gist, map-c-skyrim.dc.html:152-167).
 *
 * D6 doctrine ("every rendered field links to its cause") is the
 * caller's job, not this component's — pass the numeric readout
 * through the `value` slot (e.g. wrapped in an <a>) when the caller
 * has somewhere for it to link; a plain default is rendered otherwise.
 */
export type BarTone = "confidence" | "verbatim" | "gist";

const props = withDefaults(
  defineProps<{
    label: string;
    /** 0..1 strength; clamped for the rendered width. */
    value: number;
    tone?: BarTone;
  }>(),
  { tone: "confidence" },
);

const pct = () => `${Math.max(0, Math.min(1, props.value)) * 100}%`;
</script>

<template>
  <div class="strength-bar" :class="`strength-bar--${tone}`">
    <span class="strength-bar__label">{{ label }}</span>
    <div class="strength-bar__track">
      <div class="strength-bar__fill" :style="{ width: pct() }" />
    </div>
    <span v-if="$slots.sparkline" class="strength-bar__sparkline">
      <slot name="sparkline" />
    </span>
    <span class="strength-bar__value">
      <slot name="value">{{ value.toFixed(2) }}</slot>
    </span>
  </div>
</template>

<style scoped>
.strength-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.strength-bar__label {
  width: 68px;
  flex: none;
  color: var(--c-text-dim);
  font-size: var(--fs-secondary);
  white-space: nowrap;
}

.strength-bar__track {
  flex: 1;
  background: var(--bar-track);
  border-radius: 2px;
  height: var(--bar-height-strength);
}

.strength-bar--confidence .strength-bar__track {
  height: var(--bar-height-confidence);
}

.strength-bar__fill {
  height: 100%;
  border-radius: 2px;
}

.strength-bar--confidence .strength-bar__fill {
  background: linear-gradient(
    90deg,
    var(--bar-confidence-grad-a),
    var(--bar-confidence-grad-b)
  );
}

.strength-bar--verbatim .strength-bar__fill {
  background: var(--bar-verbatim);
}

.strength-bar--gist .strength-bar__fill {
  background: var(--bar-gist);
}

.strength-bar__sparkline {
  flex: none;
  line-height: 0;
}

.strength-bar__value {
  flex: none;
  font-size: 10px;
}
</style>
