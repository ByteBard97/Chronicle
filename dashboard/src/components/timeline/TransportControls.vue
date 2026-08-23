<script setup lang="ts">
/**
 * TransportControls — the transport cluster at the left of the timeline bar
 * (map-c-skyrim.dc.html:207-218): the five scrub/play buttons plus the
 * ¼× 1× 4× 8× speed presets (1× active). Visual parity only for now —
 * buttons render the mockup's glyphs and title tooltips; playback wiring
 * lands with the frame-log lane.
 */
interface TransportButton {
  glyph: string;
  title?: string;
  primary?: boolean;
}

const BUTTONS: TransportButton[] = [
  { glyph: "◀◀D", title: "-1 day" },
  { glyph: "◀|", title: "prev block" },
  { glyph: "▶", primary: true },
  { glyph: "|▶", title: "next block" },
  { glyph: "D▶▶", title: "+1 day" },
];

const SPEEDS = ["¼×", "1×", "4×", "8×"];

withDefaults(defineProps<{ activeSpeed?: string }>(), { activeSpeed: "1×" });
</script>

<template>
  <div class="transport">
    <button
      v-for="b in BUTTONS"
      :key="b.glyph"
      type="button"
      class="transport__btn"
      :class="{ 'transport__btn--primary': b.primary }"
      :title="b.title"
    >
      {{ b.glyph }}
    </button>
    <div class="transport__speeds">
      <button
        v-for="s in SPEEDS"
        :key="s"
        type="button"
        class="transport__speed"
        :class="{ 'transport__speed--active': s === activeSpeed }"
      >
        {{ s }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.transport {
  display: flex;
  align-items: center;
  gap: 5px;
  flex: none;
}

.transport__btn {
  appearance: none;
  font-family: inherit;
  font-size: inherit;
  border: 1px solid rgba(201, 168, 106, 0.3);
  background: transparent;
  color: var(--c-accent);
  padding: 3px 7px;
  border-radius: var(--radius-chip);
  white-space: nowrap;
  cursor: pointer;
}

.transport__btn--primary {
  border-color: rgba(201, 168, 106, 0.5);
  background: var(--c-chip-active-fill);
  color: var(--c-accent-hover);
  padding: 3px 10px;
}

.transport__speeds {
  display: flex;
  gap: 3px;
  margin-left: 6px;
}

.transport__speed {
  appearance: none;
  font-family: inherit;
  border: 1px solid transparent;
  background: transparent;
  color: var(--c-text-dim);
  font-size: var(--fs-micro);
  padding: 2px 5px;
  border-radius: 2px;
  cursor: pointer;
}

.transport__speed--active {
  background: var(--c-chip-active-fill);
  border-color: var(--c-chip-active-border);
  color: var(--c-accent-hover);
}
</style>
