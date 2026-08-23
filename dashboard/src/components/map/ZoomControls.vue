<script setup lang="ts">
/**
 * ZoomControls — the +/−/⌖ vertical button stack and the pan/zoom hint
 * pill from map-c-skyrim.dc.html:90-97, docked top-right of the map
 * well. Decorative for now: the buttons preventDefault and emit nothing
 * (real zoom/pan is later-lane work).
 */
</script>

<template>
  <div class="zoom-controls">
    <div class="zoom-controls__stack">
      <a
        href="#"
        class="zoom-controls__btn"
        title="zoom in"
        @click.prevent
        >+</a
      >
      <a
        href="#"
        class="zoom-controls__btn"
        title="zoom out"
        @click.prevent
        >−</a
      >
      <a
        href="#"
        class="zoom-controls__btn zoom-controls__btn--fit"
        title="fit city"
        @click.prevent
        >⌖</a
      >
    </div>
    <div class="zoom-controls__hint">scroll zoom · drag pan</div>
  </div>
</template>

<style scoped>
.zoom-controls {
  position: absolute;
  right: 12px;
  top: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-end;
}

.zoom-controls__stack {
  display: flex;
  flex-direction: column;
  /* mockup border rgba(201,168,106,.3) — between --c-hairline (.26) and
   * --c-chip-active-border (.4); no exact token, literal from
   * map-c-skyrim.dc.html:91 */
  border: 1px solid rgba(201, 168, 106, 0.3);
  border-radius: 6px;
  overflow: hidden;
  background: var(--c-panel-glass-soft);
  backdrop-filter: blur(10px);
}

.zoom-controls__btn {
  padding: 4px 9px;
  color: var(--c-text-body);
  border-bottom: 1px solid var(--c-divider);
  text-align: center;
}

.zoom-controls__btn--fit {
  color: var(--c-text-dim);
  border-bottom: none;
}

.zoom-controls__hint {
  background: var(--c-panel-glass);
  /* rgba(133,127,112,.25) — dimmer than --chip-muted-border (.35); no
   * token, literal from map-c-skyrim.dc.html:96 */
  border: 1px solid rgba(133, 127, 112, 0.25);
  border-radius: var(--radius-chip);
  padding: 2px 7px;
  color: var(--c-text-faint);
  font-size: 8.5px;
}
</style>
