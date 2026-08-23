<script setup lang="ts">
/**
 * MapBackdrop — the square cropped bake of Whiterun, ported from
 * map-c-skyrim.dc.html:40-42. The container is a height:100%,
 * aspect-ratio:1/1 square centered in the map well by the parent; the
 * 4k image is over-cropped (width 136.5%, offset left -11% / top -3%)
 * to reproduce the mockup's exact crop rect (330,90,3000,3000), then a
 * radial vignette darkens the edges.
 *
 * The default slot sits above the vignette — route SVG, satellite node,
 * carrier, labels and markers are all positioned in percent of this
 * square.
 */
</script>

<template>
  <div class="map-backdrop">
    <img
      class="map-backdrop__img"
      src="/assets/whiterun_topdown_4k.webp"
      alt="Whiterun top-down render"
    />
    <div class="map-backdrop__vignette" />
    <slot />
  </div>
</template>

<style scoped>
.map-backdrop {
  height: 100%;
  aspect-ratio: 1/1;
  position: relative;
  flex: none;
  overflow: hidden;
}

.map-backdrop__img {
  position: absolute;
  width: 136.5%;
  left: -11%;
  top: -3%;
  filter: saturate(0.88) brightness(0.94);
}

.map-backdrop__vignette {
  position: absolute;
  inset: 0;
  /* vignette color rgba(4,6,9,.68) — no token (map-well bg is the hex
   * only); literal from map-c-skyrim.dc.html:42 */
  background: radial-gradient(
    ellipse at 55% 48%,
    transparent 46%,
    rgba(4, 6, 9, 0.68) 100%
  );
  pointer-events: none;
}
</style>
