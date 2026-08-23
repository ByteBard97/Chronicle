<script setup lang="ts">
/**
 * RouteOverlay — the dashed carrier route (Whiterun gate → Markarth),
 * ported from map-c-skyrim.dc.html:43-45. A 100x100 viewBox with
 * preserveAspectRatio="none" stretches over the square crop; the stroke
 * is non-scaling so the dash pattern keeps its screen size.
 */
</script>

<template>
  <svg
    class="route-overlay"
    viewBox="0 0 100 100"
    preserveAspectRatio="none"
    aria-hidden="true"
  >
    <path
      d="M22.2 73.8 Q16 71 11.5 63"
      fill="none"
      stroke-width="1.5"
      stroke-dasharray="3 3"
      vector-effect="non-scaling-stroke"
      opacity="0.75"
    />
  </svg>
</template>

<style scoped>
.route-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.route-overlay path {
  stroke: var(--c-carrier);
}
</style>
