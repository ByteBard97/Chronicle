<script setup lang="ts">
/**
 * SatelliteNode — the Markarth satellite marker (a hold the rumor has
 * not reached), ported from map-c-skyrim.dc.html:46-54: a 52px dashed
 * carrier-colored circle with a hollow inner dot, plus a Cinzel label
 * and a salience-switched sub-line (observer: "satellite · 0/9 heard",
 * story: "the word has not yet arrived · 0 of 9" — the caller picks the
 * string, this component stays salience-agnostic).
 */
withDefaults(
  defineProps<{
    /** Hold name rendered in Cinzel caps. */
    name?: string;
    /** Salience-appropriate sub-line (observer/story variant). */
    subLine: string;
  }>(),
  { name: "MARKARTH" },
);
</script>

<template>
  <div class="satellite-node">
    <div class="satellite-node__circle">
      <div class="satellite-node__dot" />
    </div>
    <div class="satellite-node__label">
      <div class="satellite-node__name">{{ name }}</div>
      <div class="satellite-node__sub">
        <a href="#">{{ subLine }}</a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.satellite-node {
  position: absolute;
  left: 11.5%;
  top: 63%;
  transform: translate(-50%, -50%);
}

.satellite-node__circle {
  width: 52px;
  height: 52px;
  border: 1.5px dashed var(--c-carrier);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  /* rgba(6,9,12,.74) — no token for this plate fill; literal from
   * map-c-skyrim.dc.html:47 */
  background: rgba(6, 9, 12, 0.74);
}

.satellite-node__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  /* #454b55 / #2a2f38 — no tokens for the satellite dot; literals from
   * map-c-skyrim.dc.html:48 */
  background: #454b55;
  border: 2px solid #2a2f38;
}

.satellite-node__label {
  position: absolute;
  left: 60px;
  top: 50%;
  transform: translateY(-50%);
  text-align: left;
}

.satellite-node__name {
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.2em;
  color: var(--c-carrier-text);
  white-space: nowrap;
}

.satellite-node__sub {
  font-size: var(--fs-micro);
  white-space: nowrap;
  margin-top: 2px;
}

.satellite-node__sub a {
  color: var(--c-text-dim);
}
</style>
