<script setup lang="ts">
// Learning calendar: per local day, what was done (reviews, reading, tests, new words) and how
// many cards fall due. Counted by tilsim_core (stats.py) from the learner's own records.
import { computed, onMounted, ref, watch } from "vue";
import { grammar, type DayActivity } from "../core/grammar";
import { loadRecords, utcOffsetMinutes, type Records } from "../data/records";
import { dateLocale, format, useI18n } from "../i18n";
import { useCore } from "../stores/core";

const m = useI18n();
const core = useCore();

const now = new Date();
const year = ref(now.getFullYear());
const month = ref(now.getMonth() + 1);
const days = ref<DayActivity[]>([]);
const records = ref<Records | null>(null);
const selected = ref<string | null>(null);
const failure = ref("");
const todayKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;

async function load(): Promise<void> {
  if (core.status !== "ready") return;
  try {
    records.value ??= await loadRecords();
    days.value = await grammar.calendar(records.value, year.value, month.value, utcOffsetMinutes());
  } catch (e) {
    failure.value = String(e);
  }
}
onMounted(load);
watch([() => core.status, year, month], load);

function shift(by: number): void {
  const index = year.value * 12 + (month.value - 1) + by;
  year.value = Math.floor(index / 12);
  month.value = (index % 12) + 1;
  selected.value = null;
}

const title = computed(() => new Date(year.value, month.value - 1, 1).toLocaleDateString(dateLocale(), { month: "long", year: "numeric" }));
/** Blank cells before the 1st so weeks start on Monday. */
const lead = computed(() => (new Date(year.value, month.value - 1, 1).getDay() + 6) % 7);
const active = (d: DayActivity): boolean => d.reviews + d.readings + d.tests + d.words_added > 0;
const chosen = computed(() => days.value.find((d) => d.day === selected.value) ?? null);
</script>

<template>
  <section class="page">
    <h1>{{ m.calendar.title }}</h1>
    <p class="muted intro">{{ m.calendar.intro }}</p>
    <div v-if="core.status !== 'ready' && core.status !== 'failed'" class="alert warn">{{ m.analyze.coreLoading }}</div>
    <div v-if="failure" class="alert err">{{ failure }}</div>

    <div class="card">
      <div class="head">
        <button type="button" class="btn" :aria-label="m.calendar.prev" @click="shift(-1)">‹</button>
        <h2>{{ title }}</h2>
        <button type="button" class="btn" :aria-label="m.calendar.next" @click="shift(1)">›</button>
      </div>
      <div class="grid" role="grid">
        <span v-for="w in m.calendar.weekdays" :key="w" class="wd muted small">{{ w }}</span>
        <span v-for="n in lead" :key="`blank-${n}`" />
        <button v-for="d in days" :key="d.day" type="button" class="day"
          :class="{ active: active(d), today: d.day === todayKey, selected: d.day === selected }" @click="selected = d.day">
          <span class="n">{{ Number(d.day.slice(8)) }}</span>
          <span v-if="active(d)" class="dot" :title="m.calendar.legendDone" />
          <span v-if="d.due" class="due small" :title="format(m.calendar.due, { n: d.due })">{{ d.due }}</span>
        </button>
      </div>
      <p class="legend small muted">
        <span><span class="dot" /> {{ m.calendar.legendDone }}</span>
        <span><span class="due">3</span> {{ m.calendar.legendDue }}</span>
      </p>
    </div>

    <div v-if="chosen" class="card">
      <h2>{{ new Date(`${chosen.day}T12:00:00`).toLocaleDateString(dateLocale(), { weekday: "long", day: "numeric", month: "long" }) }}</h2>
      <ul v-if="active(chosen) || chosen.due" class="details">
        <li v-if="chosen.reviews">{{ format(m.calendar.reviews, { n: chosen.reviews, right: chosen.reviews_right }) }}</li>
        <li v-if="chosen.readings">{{ format(m.calendar.readings, { n: chosen.readings, min: chosen.reading_minutes }) }}</li>
        <li v-if="chosen.tests">{{ format(m.calendar.tests, { n: chosen.tests, right: chosen.test_right, answers: chosen.test_answers }) }}</li>
        <li v-if="chosen.words_added">{{ format(m.calendar.words, { n: chosen.words_added }) }}</li>
        <li v-if="chosen.due">{{ format(m.calendar.due, { n: chosen.due }) }}</li>
      </ul>
      <p v-else class="muted">{{ m.calendar.nothing }}</p>
    </div>
  </section>
</template>

<style scoped>
.page {
  max-width: 720px;
  display: grid;
  gap: 1rem;
  align-content: start;
}
.intro {
  margin: 0;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.8rem;
}
.head h2 {
  margin: 0;
  text-transform: capitalize;
}
.grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 4rem));
  justify-content: center;
  gap: 4px;
}
.wd {
  text-align: center;
  font-weight: 600;
}
.day {
  aspect-ratio: 1;
  min-height: 2.6rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text);
  font: inherit;
  cursor: pointer;
  position: relative;
  display: grid;
  place-items: center;
}
.day.active {
  background: var(--accent-soft);
}
.day.today {
  border-color: var(--accent);
  border-width: 2px;
}
.day.selected {
  box-shadow: 0 0 0 2px var(--gold);
}
.n {
  font-weight: 600;
}
.dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
}
.day .dot {
  position: absolute;
  bottom: 5px;
}
.due {
  display: inline-block;
  min-width: 1.1rem;
  padding: 0 0.2rem;
  border-radius: 999px;
  background: var(--gold);
  color: #1a1f4e;
  font-size: 0.68rem;
  font-weight: 700;
  text-align: center;
}
.day .due {
  position: absolute;
  top: 3px;
  right: 3px;
}
.legend {
  display: flex;
  gap: 1.2rem;
  margin: 0.8rem 0 0;
}
.legend > span {
  display: inline-flex;
  gap: 0.4rem;
  align-items: center;
}
.details {
  margin: 0;
  padding-left: 1.1rem;
}
</style>
