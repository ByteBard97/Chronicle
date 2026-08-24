<script setup lang="ts">
/**
 * RoleCard — one role's full detail (ui-spec §3.10): title/institution,
 * current holder (linked to that NPC's inspector), duties with lapse
 * state, vacancy history, and the succession record -- each "drill-down-
 * able like any derivation" via a plain event link to the feed at the
 * causing record's tick (the packet's pinned reading: lane 22's
 * `panelUrlState.ts` drill idiom is belief-id-specific, not generically
 * reusable -- same conclusion lanes 30/31/35 independently reached for
 * their own drill sites -- so this mirrors `DiffRow.vue`'s
 * `eventHref`/`ruleHref` plain-`<a>` pattern instead).
 *
 * Holder link: a full-navigation `<a href="/map?run=...&sel=...">`, same
 * idiom as `ViewSwitcher.vue`/`DiffRow.vue` (both plain `<a>`, not
 * `router-link`, so this component works whether or not a router happens
 * to be present in a test harness) -- built against the frozen `sel`
 * codec (`state/urlState.ts`), never a hand-rolled query string. Landing
 * on `/map` (rather than a dedicated NPC route, which doesn't exist)
 * matches every other cross-view "select an NPC" link in this app:
 * `MapScreen.vue`'s `NpcInspector` renders off the selection store, keyed
 * by `sel`.
 */
import { computed } from "vue";
import { codecs } from "../../state/urlState";
import type { RoleCard } from "../../derived/roles";
import Chip from "../Chip.vue";

const props = defineProps<{
  card: RoleCard;
  runId: string | null;
}>();

function npcHref(npcId: string): string {
  const params = new URLSearchParams();
  if (props.runId !== null) params.set("run", props.runId);
  const encoded = codecs.sel.encode([npcId]);
  if (encoded !== undefined) params.set("sel", encoded);
  return `/map?${params.toString()}`;
}

function feedHref(tick: number): string {
  const params = new URLSearchParams();
  if (props.runId !== null) params.set("run", props.runId);
  params.set("t", String(tick));
  return `/feed?${params.toString()}`;
}

const holderHref = computed(() => (props.card.holderId !== null ? npcHref(props.card.holderId) : null));
</script>

<template>
  <div class="role-card">
    <header class="role-card__header">
      <div class="role-card__title">{{ card.title }}</div>
      <div class="role-card__id">{{ card.roleId }} · {{ card.institutionId }}</div>
    </header>

    <div class="role-card__holder-row">
      <span class="role-card__field-label">holder</span>
      <a v-if="holderHref !== null" :href="holderHref" class="role-card__holder-link">{{ card.holderId }}</a>
      <Chip v-else tone="muted">vacant{{ card.vacatedAt !== null ? ` since t${card.vacatedAt}` : "" }}</Chip>
    </div>

    <section class="role-card__section">
      <h3 class="role-card__section-title">duties</h3>
      <ul v-if="card.duties.length > 0" class="role-card__duties">
        <li v-for="duty in card.duties" :key="duty.name" class="role-card__duty" :data-lapsed="duty.lapsed">
          <span class="role-card__duty-name">{{ duty.name }}</span>
          <Chip v-if="duty.lapsed" tone="stage-dormant">
            lapsed
            <a v-if="duty.lapseEvent" :href="feedHref(duty.lapseEvent.tick)" class="role-card__duty-lapse-link"
              >t{{ duty.lapseEvent.tick }}</a
            >
          </Chip>
          <span v-else class="role-card__duty-ok">active</span>
        </li>
      </ul>
      <div v-else class="role-card__empty">no duties recorded</div>
    </section>

    <section class="role-card__section">
      <h3 class="role-card__section-title">vacancy history</h3>
      <ul v-if="card.vacancyHistory.length > 0" class="role-card__vacancies">
        <li v-for="(span, i) in card.vacancyHistory" :key="i" class="role-card__vacancy">
          <a :href="feedHref(span.vacatedAt)" class="role-card__event-link">t{{ span.vacatedAt }}</a>
          vacated
          <template v-if="span.filledAt !== null">
            → filled t{{ span.filledAt }} by
            <a v-if="span.filledBy !== null" :href="npcHref(span.filledBy)" class="role-card__event-link">{{ span.filledBy }}</a>
          </template>
          <span v-else class="role-card__vacancy-open">→ still vacant</span>
        </li>
      </ul>
      <div v-else class="role-card__empty">never vacated</div>
    </section>

    <section class="role-card__section">
      <h3 class="role-card__section-title">succession record</h3>
      <ul v-if="card.successions.length > 0" class="role-card__successions">
        <li v-for="succession in card.successions" :key="`${succession.tick}-${succession.seq}`" class="role-card__succession">
          <a :href="npcHref(succession.npcId)" class="role-card__event-link">{{ succession.npcId }}</a>
          appointed
          <a :href="feedHref(succession.tick)" class="role-card__event-link">t{{ succession.tick }}</a>
        </li>
      </ul>
      <div v-else class="role-card__empty">no successions on record</div>
    </section>
  </div>
</template>

<style scoped>
.role-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--c-hairline);
  border-radius: var(--radius-panel);
  background: var(--c-panel-glass-inspector);
}

.role-card__header {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.role-card__title {
  font-family: var(--font-display);
  font-size: var(--fs-primary);
  color: var(--c-text-body);
}

.role-card__id {
  font-family: var(--font-data);
  font-size: var(--fs-micro);
  color: var(--c-text-faint);
}

.role-card__holder-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-secondary);
}

.role-card__field-label {
  color: var(--c-text-dim);
  text-transform: uppercase;
  font-size: var(--fs-micro);
  letter-spacing: 0.05em;
}

.role-card__holder-link,
.role-card__event-link,
.role-card__duty-lapse-link {
  color: var(--c-accent-hover);
  font-family: var(--font-data);
}

.role-card__section {
  border-top: 1px solid var(--c-hairline-soft);
  padding-top: 8px;
}

.role-card__section-title {
  margin: 0 0 6px;
  font-size: var(--fs-micro);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--c-panel-title);
}

.role-card__duties,
.role-card__vacancies,
.role-card__successions {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: var(--fs-secondary);
}

.role-card__duty {
  display: flex;
  align-items: center;
  gap: 8px;
}

.role-card__duty[data-lapsed="true"] .role-card__duty-name {
  color: var(--ev-grudge);
}

.role-card__duty-ok {
  color: var(--c-text-dim);
  font-size: var(--fs-micro);
}

.role-card__vacancy-open {
  color: var(--ev-grudge);
}

.role-card__empty {
  color: var(--c-text-faint);
  font-size: var(--fs-secondary);
}
</style>
