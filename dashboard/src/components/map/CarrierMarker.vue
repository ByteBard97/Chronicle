<script setup lang="ts">
/**
 * CarrierMarker — the pulsing carrier dot on the route (Ri'saad,
 * carrying C-114 v2 toward Markarth), ported from
 * map-c-skyrim.dc.html:55-58. The pulse is the global `cpulse`
 * keyframes from tokens.css; the label chip rides 12px right of the dot.
 */
withDefaults(
  defineProps<{
    /** Label chip text. */
    label?: string;
  }>(),
  { label: "carrier: Ri'saad ▸ ETA D14 · carrying v2" },
);
</script>

<template>
  <div class="carrier-marker">
    <div class="carrier-marker__dot" />
    <div class="carrier-marker__chip">
      <a href="#">{{ label }}</a>
    </div>
  </div>
</template>

<style scoped>
.carrier-marker {
  position: absolute;
  left: 16.2%;
  top: 69.5%;
  transform: translate(-50%, -50%);
}

.carrier-marker__dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--c-carrier);
  /* halo/glow alphas — no tokens; literals from map-c-skyrim.dc.html:56 */
  box-shadow:
    0 0 0 2px rgba(4, 6, 9, 0.7),
    0 0 10px rgba(88, 193, 212, 0.8);
  animation: cpulse 1.8s infinite;
}

.carrier-marker__chip {
  position: absolute;
  left: 12px;
  top: -4px;
  white-space: nowrap;
  font-size: var(--fs-micro);
  /* rgba(6,9,12,.8) plate / carrier 35% border — no tokens; literals
   * from map-c-skyrim.dc.html:57 */
  background: rgba(6, 9, 12, 0.8);
  border: 1px solid rgba(88, 193, 212, 0.35);
  padding: 1px 5px;
  border-radius: 2px;
}

.carrier-marker__chip a {
  color: var(--c-carrier-text);
}
</style>
