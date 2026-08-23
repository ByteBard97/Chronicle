<script setup lang="ts">
/**
 * TransportControls — the transport cluster at the left of the timeline
 * bar (map-c-skyrim.dc.html:207-218): play/pause, ±1 day skip, day-
 * boundary stepping, and the ¼×/1×/4×/8× speed presets. Lane 16 wires all
 * of it to `urlState.t` ('replace' history mode, per the pinned contract).
 *
 * Speed is a display multiplier only, never a tick rate (ui-spec §2:59):
 * 1× = 1 tick/second, so the interval between ticks is `1000ms / speed`
 * (250ms at 4×, 125ms at 8×, 4000ms at ¼×) rather than varying how many
 * ticks each fixed-cadence poll advances — this keeps the math exact and
 * deterministic under fake timers.
 *
 * FINDING (named, not improvised): the mockup's "prev/next block" glyphs
 * (◀|/|▶) implied schedule-block stepping (ui-spec §2:59's "segment
 * stepping at game-day *and schedule-block* boundaries"). The frame log
 * doesn't carry schedule-block data dashboard-side (no schedule reader
 * exists yet), so per the packet those two buttons are repurposed as
 * *day-boundary* stepping (snap to the nearest 24-tick multiple) — distinct
 * from the ◀◀D/D▶▶ buttons' ±1 day *skip* (relative ±24 ticks from
 * wherever the playhead currently is). Schedule-block stepping itself
 * remains unimplemented; a future lane needs schedule data before it can
 * exist.
 *
 * Pausing on manual edits: this component treats *any* change to
 * `urlState.t` it did not itself just write (a marker click in
 * `TimelineTrack`, a hand-edited URL, browser back/forward) as a manual
 * edit and stops playback, per the pinned "pause on any manual t edit"
 * rule.
 */
import { onBeforeUnmount, ref, watch } from "vue";
import { useUrlState } from "../../state/urlState";

const props = defineProps<{ maxTick: number }>();

const urlState = useUrlState();

interface SpeedPreset {
  label: string;
  value: number;
}

const SPEED_PRESETS: SpeedPreset[] = [
  { label: "¼×", value: 0.25 },
  { label: "1×", value: 1 },
  { label: "4×", value: 4 },
  { label: "8×", value: 8 },
];

const speed = ref<number>(1);
const playing = ref(false);
let timer: ReturnType<typeof setInterval> | null = null;
let selfWrite = false;

function currentTick(): number {
  return urlState.t.value ?? 0;
}

function writeTick(next: number) {
  const clamped = Math.max(0, Math.min(props.maxTick, Math.round(next)));
  selfWrite = true;
  urlState.t.value = clamped;
}

function stopTimer() {
  if (timer !== null) {
    clearInterval(timer);
    timer = null;
  }
}

function startTimer() {
  stopTimer();
  const intervalMs = 1000 / speed.value;
  timer = setInterval(() => {
    const next = currentTick() + 1;
    if (next > props.maxTick) {
      playing.value = false;
      return;
    }
    writeTick(next);
  }, intervalMs);
}

function togglePlay() {
  playing.value = !playing.value;
}

watch(playing, (isPlaying) => {
  if (isPlaying) startTimer();
  else stopTimer();
});

watch(speed, () => {
  if (playing.value) startTimer();
});

watch(urlState.t, () => {
  if (selfWrite) {
    selfWrite = false;
    return;
  }
  playing.value = false;
});

function stepDay(direction: 1 | -1) {
  playing.value = false;
  writeTick(currentTick() + direction * 24);
}

function stepDayBoundary(direction: 1 | -1) {
  playing.value = false;
  const day = Math.floor(currentTick() / 24);
  const nextDay = direction > 0 ? day + 1 : day - 1;
  writeTick(Math.max(0, nextDay * 24));
}

onBeforeUnmount(stopTimer);
</script>

<template>
  <div class="transport">
    <button
      type="button"
      class="transport__btn"
      title="-1 day"
      data-testid="transport-skip-back-day"
      @click="stepDay(-1)"
    >
      ◀◀D
    </button>
    <button
      type="button"
      class="transport__btn"
      title="prev day boundary"
      data-testid="transport-prev-day-boundary"
      @click="stepDayBoundary(-1)"
    >
      ◀|
    </button>
    <button
      type="button"
      class="transport__btn transport__btn--primary"
      :title="playing ? 'pause' : 'play'"
      data-testid="transport-play-pause"
      @click="togglePlay"
    >
      {{ playing ? "⏸" : "▶" }}
    </button>
    <button
      type="button"
      class="transport__btn"
      title="next day boundary"
      data-testid="transport-next-day-boundary"
      @click="stepDayBoundary(1)"
    >
      |▶
    </button>
    <button
      type="button"
      class="transport__btn"
      title="+1 day"
      data-testid="transport-skip-forward-day"
      @click="stepDay(1)"
    >
      D▶▶
    </button>
    <div class="transport__speeds">
      <button
        v-for="s in SPEED_PRESETS"
        :key="s.label"
        type="button"
        class="transport__speed"
        :class="{ 'transport__speed--active': s.value === speed }"
        @click="speed = s.value"
      >
        {{ s.label }}
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
