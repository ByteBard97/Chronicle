<script setup lang="ts">
/**
 * LensPanel — the "LENS — ONE OVERLAY ACTIVE" glass panel from
 * map-c-skyrim.dc.html:75-79: which lens is on (rumor-stage), which
 * claim it stains for (C-114), and the tracked-count line. All content
 * is prop-driven; defaults reproduce the approved mockup render.
 */
import PanelGlass from "../PanelGlass.vue";

withDefaults(
  defineProps<{
    /** Active lens name. */
    lensName?: string;
    /** Claim id the lens stains for. */
    claimId?: string;
    /** Claim text shown quoted after the id. */
    claimText?: string;
    /** Number of tracked cast members (reconciles with STAGE_LEGEND). */
    trackedCount?: number;
  }>(),
  {
    lensName: "rumor-stage",
    claimId: "C-114",
    claimText: "Jarl Balgruuf is dead",
    trackedCount: 26,
  },
);
</script>

<template>
  <PanelGlass class="lens-panel" :padded="false">
    <div class="lens-panel__title">LENS — ONE OVERLAY ACTIVE</div>
    <a href="#" class="lens-panel__lens" @click.prevent>
      {{ lensName }} ·
      <span class="lens-panel__claim">{{ claimId }} "{{ claimText }}"</span>
      ▾
    </a>
    <div class="lens-panel__meta">
      all variants · {{ trackedCount }} tracked ·
      <a href="#" @click.prevent>variant tree ▸</a>
    </div>
  </PanelGlass>
</template>

<style scoped>
.lens-panel {
  padding: 9px 11px;
}

.lens-panel__title {
  font-family: var(--font-display);
  color: var(--c-panel-title);
  font-size: var(--fs-panel-title);
  letter-spacing: 0.22em;
  margin-bottom: 5px;
}

.lens-panel__lens {
  display: block;
  font-size: var(--fs-body);
}

.lens-panel__claim {
  color: var(--c-text-primary);
}

.lens-panel__meta {
  color: var(--c-text-dim);
  font-size: var(--fs-secondary);
  margin-top: 3px;
}
</style>
