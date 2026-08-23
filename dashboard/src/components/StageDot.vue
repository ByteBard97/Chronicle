<script setup lang="ts">
/**
 * StageDot — the legend/DOM rendering of a rumor-stage marker (the
 * canvas version is the map's job, out of scope for this lane per
 * ui-spec §3.4/build order). Five real states, deuteranopia-checked by
 * hue + value + shape per design-tokens.md.
 */
export type RumorStage = "unheard" | "heard" | "repeated" | "dormant" | "forgotten";

defineProps<{
  stage: RumorStage;
  /** True when this dot sits in the map legend as opposed to the marker
   *  itself — legend dots are 3px smaller (map-c-skyrim.dc.html:287). */
  legend?: boolean;
}>();
</script>

<script lang="ts">
export const RUMOR_STAGES: readonly RumorStage[] = [
  "unheard",
  "heard",
  "repeated",
  "dormant",
  "forgotten",
];
</script>

<template>
  <span class="stage-dot" :class="[`stage-dot--${stage}`, { 'stage-dot--legend': legend }]" />
</template>

<style scoped>
.stage-dot {
  display: inline-block;
  border-radius: 50%;
  border: var(--marker-ring-width) solid transparent;
  box-shadow: 0 0 0 var(--marker-halo-width) var(--c-marker-halo);
  flex: none;
}

.stage-dot--unheard {
  width: var(--stage-unheard-size);
  height: var(--stage-unheard-size);
  background: var(--stage-unheard-fill);
  border-color: var(--stage-unheard-ring);
}

.stage-dot--heard {
  width: var(--stage-heard-size);
  height: var(--stage-heard-size);
  background: var(--stage-heard-fill);
  border-color: var(--stage-heard-ring);
}

.stage-dot--repeated {
  width: var(--stage-repeated-size);
  height: var(--stage-repeated-size);
  background: var(--stage-repeated-fill);
  border-color: var(--stage-repeated-ring);
}

.stage-dot--dormant {
  width: var(--stage-dormant-size);
  height: var(--stage-dormant-size);
  background: var(--stage-dormant-fill);
  border-color: var(--stage-dormant-ring);
}

.stage-dot--forgotten {
  width: var(--stage-forgotten-size);
  height: var(--stage-forgotten-size);
  background: var(--stage-forgotten-fill);
  border-color: var(--stage-forgotten-ring);
}

/* Legend dots render 3px smaller than the marker size, per-stage (not
 * a uniform scale factor — see tokens.css's *-legend-size comment). */
.stage-dot--legend.stage-dot--unheard {
  width: var(--stage-unheard-legend-size);
  height: var(--stage-unheard-legend-size);
}
.stage-dot--legend.stage-dot--heard {
  width: var(--stage-heard-legend-size);
  height: var(--stage-heard-legend-size);
}
.stage-dot--legend.stage-dot--repeated {
  width: var(--stage-repeated-legend-size);
  height: var(--stage-repeated-legend-size);
}
.stage-dot--legend.stage-dot--dormant {
  width: var(--stage-dormant-legend-size);
  height: var(--stage-dormant-legend-size);
}
.stage-dot--legend.stage-dot--forgotten {
  width: var(--stage-forgotten-legend-size);
  height: var(--stage-forgotten-legend-size);
}
</style>
