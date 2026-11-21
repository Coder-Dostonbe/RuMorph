<script setup lang="ts">
// Dashboard: today's work and the learner's results, all counted from their own records by
// tilsim_core (stats.py). The state of the engine, the account and the server is in the admin panel.
import { computed, onMounted, ref, watch } from "vue";
import { grammar, type Summary } from "../core/grammar";
import { loadRecords, utcOffsetMinutes } from "../data/records";
import { readings, readingTexts, type ReadingTextRow } from "../data/userData";
import { dateLocale, format, useI18n } from "../i18n";
import { useCards } from "../stores/cards";
import { useCore } from "../stores/core";
import { callFailed, coreFailed } from "../ui/failure";

const m = useI18n();
const core = useCore();
const cards = useCards();

const summary = ref<Summary | null>(null);
const dueNow = ref(0);
const todayText = ref<ReadingTextRow | null>(null);
const hasTexts = ref(false);
const failure = ref("");

async function load(): Promise<void> {
  if (core.status !== "ready") return;
  try {
    const records = await loadRecords();
    summary.value = await grammar.stats(records, new Date().toISOString(), utcOffsetMinutes());
    await cards.load();
    dueNow.value = (await cards.queue()).length;
    const [texts, history] = await Promise.all([readingTexts.list(), readings.list()]);
    hasTexts.value = texts.length > 0;
    const last = new Map<string, string>();
    for (const h of history) if ((last.get(h.text_id) ?? "") < h.read_at) last.set(h.text_id, h.read_at);
    todayText.value = [...texts].sort((a, b) => (last.get(a.id) ?? "").localeCompare(last.get(b.id) ?? "") || a.created_at.localeCompare(b.created_at))[0] ?? null;
  } catch (e) {
    failure.value = callFailed(m.value, e);
  }
}
onMounted(() => void load());
watch(() => core.status, () => void load());

const bars = computed(() => {
  const days = summary.value?.last_14_days ?? [];
  const values = days.map((d) => ({ day: d.day, n: d.reviews + d.test_answers }));
  const max = Math.max(1, ...values.map((v) => v.n));
  return values.map((v) => ({ ...v, height: (100 * v.n) / max, label: new Date(`${v.day}T12:00:00`).toLocaleDateString(dateLocale(), { day: "numeric", month: "short" }) }));
});
const anyActivity = computed(() => bars.value.some((b) => b.n > 0));
const empty = computed(() => summary.value !== null && summary.value.words.total === 0 && summary.value.cards.total === 0);
</script>

<template>
  <section class="page">
    <h1>{{ m.home.title }}</h1>
    <p class="muted intro">{{ m.home.intro }}</p>
    <div v-if="core.status !== 'ready' && core.status !== 'failed'" class="alert warn">{{ m.analyze.coreLoading }}</div>
    <div v-if="core.status === 'failed'" class="alert err">{{ coreFailed(m, core.error) }}</div>
    <div v-if="failure" class="alert err">{{ failure }}</div>

    <article class="card today">
      <h2>{{ m.home.today }}</h2>
      <p v-if="empty" class="muted">{{ m.home.startHere }}</p>
      <ul class="plan">
        <li>
          <span>{{ dueNow ? format(m.home.dueCards, { n: dueNow }) : m.home.noDue }}</span>
          <RouterLink v-if="dueNow" to="/cards" class="btn primary">{{ m.home.review }}</RouterLink>
        </li>
        <li>
          <span>{{ todayText ? format(m.home.todayText, { title: todayText.title }) : m.home.noText }}</span>
          <RouterLink v-if="todayText" :to="{ path: '/reading', query: { text: todayText.id } }" class="btn">{{ m.home.read }}</RouterLink>
          <RouterLink v-else to="/reading" class="btn">{{ m.home.addText }}</RouterLink>
        </li>
        <li>
          <span v-if="summary">{{ format(m.home.doneToday, { reviews: summary.today_done.reviews, tests: summary.today_done.tests, words: summary.today_done.words_added }) }}</span>
          <RouterLink to="/tests" class="btn">{{ m.home.practice }}</RouterLink>
        </li>
      </ul>
    </article>

    <div v-if="summary" class="tiles">
      <RouterLink :to="{ path: '/dictionary', query: { tab: 'mine' } }" class="card tile">
        <span class="num">{{ summary.words.total }}</span>
        <span class="label">{{ m.home.words }}</span>
        <span class="muted small">{{ format(m.home.wordsDetail, summary.words) }}</span>
      </RouterLink>
      <RouterLink to="/cards" class="card tile">
        <span class="num">{{ summary.cards.total }}</span>
        <span class="label">{{ m.home.cards }}</span>
        <span class="muted small">{{ format(m.home.cardsDetail, summary.cards) }}</span>
      </RouterLink>
      <div class="card tile">
        <span class="num">{{ summary.week.reviews }}</span>
        <span class="label">{{ m.home.reviews7 }}</span>
        <span class="muted small">{{ summary.week.review_accuracy === null ? m.home.noAccuracy : format(m.home.accuracy, { p: summary.week.review_accuracy }) }}</span>
      </div>
      <div class="card tile">
        <span class="num">{{ summary.week.test_accuracy === null ? "—" : `${summary.week.test_accuracy}%` }}</span>
        <span class="label">{{ m.home.tests7 }}</span>
        <span class="muted small">{{ summary.week.test_accuracy === null ? m.home.noAccuracy : format(m.home.accuracy, { p: summary.week.test_accuracy }) }}</span>
      </div>
      <div class="card tile">
        <span class="num">{{ summary.week.reading_minutes }}</span>
        <span class="label">{{ m.home.reading7 }}</span>
        <span class="muted small">{{ format(m.home.minutes, { n: summary.week.reading_minutes }) }}</span>
      </div>
      <RouterLink to="/calendar" class="card tile">
        <span class="num">{{ summary.week.active_days }}</span>
        <span class="label">{{ m.home.active }}</span>
        <span class="muted small">{{ format(m.home.activeDetail, { week: summary.week.active_days, month: summary.month_active_days }) }}</span>
      </RouterLink>
    </div>

    <article v-if="summary && anyActivity" class="card">
      <h2>{{ m.home.activity }}</h2>
      <div class="chart" role="img" :aria-label="m.home.activity">
        <div v-for="b in bars" :key="b.day" class="col" :title="format(m.home.activityBar, { day: b.label, n: b.n })">
          <span class="value small">{{ b.n || "" }}</span>
          <span class="bar" :style="{ height: `${Math.max(b.height, b.n ? 4 : 0)}%` }" />
          <span class="day small">{{ b.label }}</span>
        </div>
      </div>
      <table class="visually-hidden">
        <caption>{{ m.home.activity }}</caption>
        <tbody><tr v-for="b in bars" :key="b.day"><th scope="row">{{ b.label }}</th><td>{{ b.n }}</td></tr></tbody>
      </table>
    </article>

  </section>
</template>

<style scoped>
.page {
  max-width: 1000px;
  display: grid;
  gap: 1rem;
  align-content: start;
}
.intro {
  margin: 0;
  max-width: 70ch;
}
.plan {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
}
.plan li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.6rem 0;
  border-bottom: 1px solid var(--border);
}
.plan li:last-child {
  border-bottom: none;
}
.plan .btn {
  text-decoration: none;
  flex: none;
}
.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}
.tile {
  display: grid;
  gap: 0.1rem;
  color: var(--text);
  text-decoration: none;
}
a.tile:hover {
  border-color: var(--accent);
}
.num {
  font-size: 1.8rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.label {
  font-weight: 600;
}
.chart {
  display: grid;
  grid-template-columns: repeat(14, 1fr);
  gap: 2px;
  height: 160px;
  align-items: end;
  border-bottom: 1px solid var(--border);
  padding-top: 1.2rem;
}
.col {
  display: grid;
  grid-template-rows: auto 1fr;
  height: 100%;
  align-items: end;
  justify-items: center;
  position: relative;
}
.bar {
  width: min(70%, 28px);
  background: var(--accent);
  border-radius: 4px 4px 0 0;
  align-self: end;
}
.value {
  color: var(--muted);
  align-self: end;
}
.day {
  position: absolute;
  bottom: -1.5rem;
  color: var(--muted);
  font-size: 0.7rem;
  white-space: nowrap;
}
.col:nth-child(odd) .day {
  visibility: hidden;
}
.chart {
  margin-bottom: 1.6rem;
}
.chart + table + * {
  margin-top: 1.6rem;
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
