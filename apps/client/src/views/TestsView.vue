<script setup lang="ts">
// Exercises: a test of one kind of question, or the quick-answer game (60 s, mixed kinds).
// Questions come from tilsim_core (exercises.py); results go to test_results.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useSync } from "../stores/sync";
import { grammar, type ExerciseKind, type Question } from "../core/grammar";
import { testResults, type TestResultRow } from "../data/userData";
import { dateLocale, format, useI18n } from "../i18n";
import { useCore } from "../stores/core";
import { useGrammar } from "../stores/grammar";
import { useTranslations, type TranslationEntry } from "../stores/translations";
import { useVocabulary } from "../stores/vocabulary";
import QuestionCard from "../ui/QuestionCard.vue";
import { callFailed, coreFailed } from "../ui/failure";

const KINDS: ExerciseKind[] = ["case_form", "conjugation", "preposition", "gender", "aspect", "translation"];
const LEVELS = ["500", "1000", "3000"] as const;
const GAME_KINDS: ExerciseKind[] = ["case_form", "conjugation", "preposition", "gender"];
const GAME_SECONDS = 60;
const PENALTY_SECONDS = 3;

const m = useI18n();
const core = useCore();
const vocab = useVocabulary();
const tr = useTranslations();
const g = useGrammar();

/** What was asked, in words: "jo'nalish kelishigi, ko'plik", "у …", "1-shaxs, birlik". */
function asked(q: Question): string {
  const parts = (q.prompt.grammemes ?? []).map((c) => g.name(c));
  return [q.prompt.preposition ? `${q.prompt.preposition} …` : "", ...parts].filter(Boolean).join(", ");
}

const kind = ref<ExerciseKind>("case_form");
const level = ref<(typeof LEVELS)[number]>("1000");
const count = ref(10);
const failure = ref("");
const history = ref<TestResultRow[]>([]);

type Mode = "setup" | "test" | "result" | "game" | "gameover";
const mode = ref<Mode>("setup");
const questions = ref<Question[]>([]);
const position = ref(0);
const answers = ref<number[]>([]);
const chosen = ref<number | null>(null);
const score = ref(0);
const timeLeft = ref(GAME_SECONDS);
let clock: ReturnType<typeof setInterval> | undefined;

function err(e: unknown): string {
  return callFailed(m.value, e);
}

async function loadHistory(): Promise<void> {
  history.value = (await testResults.list()).sort((a, b) => b.taken_at.localeCompare(a.taken_at));
}
// A sync brought changes from another device.
watch(() => useSync().revision, () => void loadHistory());
onMounted(() => {
  void loadHistory();
  void vocab.load();
  void tr.load();
});
onBeforeUnmount(() => clearInterval(clock));

// Translation questions use the learner's own words when at least four of them have different
// translations; otherwise every translated word.
const distinct = (list: TranslationEntry[]) => new Set(list.map((e) => e.translation)).size;
const translated = computed(() => {
  const mine = vocab.rows.map((r) => tr.all.get(r.lexeme_id)).filter((e): e is TranslationEntry => e !== undefined);
  return distinct(mine) >= 4 ? mine : [...tr.all.values()];
});
const distinctTranslations = computed(() => distinct(translated.value));
function available(k: ExerciseKind): boolean {
  return k !== "translation" || distinctTranslations.value >= 4;
}

const seed = (): number => Math.floor(Math.random() * 2 ** 31);
const vocabularyArg = () => translated.value.map((e) => ({ lexeme_id: e.lexeme_id, lemma: e.lemma, translation: e.translation }));

async function startTest(): Promise<void> {
  failure.value = "";
  try {
    const qs = await grammar.exercises(kind.value, count.value, seed(), Number(level.value), kind.value === "translation" ? vocabularyArg() : []);
    if (qs.length === 0) {
      failure.value = m.value.tests.tooFew;
      return;
    }
    questions.value = qs;
    position.value = 0;
    answers.value = [];
    chosen.value = null;
    mode.value = "test";
  } catch (e) {
    failure.value = err(e);
  }
}

const current = computed(() => questions.value[position.value] ?? null);

function choose(index: number): void {
  if (chosen.value !== null || !current.value) return;
  chosen.value = index;
  answers.value.push(index);
  if (mode.value === "game") {
    if (index === current.value.answer) score.value += 1;
    else timeLeft.value = Math.max(0, timeLeft.value - PENALTY_SECONDS);
    setTimeout(() => void nextGameQuestion(), index === current.value.answer ? 350 : 1100);
  }
}

async function next(): Promise<void> {
  if (position.value + 1 < questions.value.length) {
    position.value += 1;
    chosen.value = null;
    return;
  }
  const correct = questions.value.filter((q, i) => answers.value[i] === q.answer).length;
  await testResults.insert({
    kind: kind.value, taken_at: new Date().toISOString(), total: questions.value.length, correct,
    details: questions.value.map((q, i) => ({ lexeme: q.lexeme, lemma: q.lemma, prompt: q.prompt, options: q.options, answer: q.answer, given: answers.value[i] })),
  });
  await loadHistory();
  mode.value = "result";
}

const correctCount = computed(() => questions.value.filter((q, i) => answers.value[i] === q.answer).length);
const mistakes = computed(() => questions.value.map((q, i) => ({ q, given: answers.value[i] })).filter((x) => x.given !== x.q.answer));

// --- game ---------------------------------------------------------------------------------------
async function fetchGameQuestions(): Promise<Question[]> {
  const batches = await Promise.all(GAME_KINDS.map((k) => grammar.exercises(k, 10, seed(), 1000)));
  return batches.flat().sort(() => Math.random() - 0.5);
}

async function startGame(): Promise<void> {
  failure.value = "";
  try {
    questions.value = await fetchGameQuestions();
  } catch (e) {
    failure.value = err(e);
    return;
  }
  position.value = 0;
  answers.value = [];
  chosen.value = null;
  score.value = 0;
  timeLeft.value = GAME_SECONDS;
  mode.value = "game";
  clearInterval(clock);
  clock = setInterval(() => {
    timeLeft.value -= 1;
    if (timeLeft.value <= 0) void endGame();
  }, 1000);
}

async function nextGameQuestion(): Promise<void> {
  if (mode.value !== "game") return;
  if (timeLeft.value <= 0) return endGame();
  position.value += 1;
  chosen.value = null;
  if (position.value >= questions.value.length - 2) {
    try {
      questions.value = [...questions.value, ...(await fetchGameQuestions())];
    } catch (e) {
      failure.value = err(e);
    }
  }
}

async function endGame(): Promise<void> {
  if (mode.value !== "game") return;
  clearInterval(clock);
  mode.value = "gameover";
  const answered = answers.value.length;
  await testResults.insert({
    kind: "game_quick", taken_at: new Date().toISOString(), total: answered, correct: score.value, details: [],
  });
  await loadHistory();
}

const bestGame = computed(() => Math.max(0, ...history.value.filter((h) => h.kind === "game_quick").map((h) => h.correct)));

function kindName(k: string): string {
  return k === "game_quick" ? m.value.tests.game : (m.value.tests.kinds as Record<string, string>)[k] ?? k;
}

function onKey(event: KeyboardEvent): void {
  if ((mode.value !== "test" && mode.value !== "game") || !current.value) return;
  const n = Number(event.key);
  if (chosen.value === null && n >= 1 && n <= current.value.options.length) choose(n - 1);
  else if (chosen.value !== null && mode.value === "test" && event.key === "Enter") void next();
}
onMounted(() => window.addEventListener("keydown", onKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
watch(() => core.status, () => (failure.value = ""));
</script>

<template>
  <section class="page">
    <h1>{{ m.tests.title }}</h1>
    <div v-if="core.status === 'failed'" class="alert err">{{ coreFailed(m, core.error) }}</div>
    <div v-else-if="core.status !== 'ready'" class="alert warn">{{ m.analyze.coreLoading }}</div>
    <div v-if="failure" class="alert err">{{ failure }}</div>

    <template v-if="mode === 'setup'">
      <p class="muted intro">{{ m.tests.intro }}</p>
      <div class="card">
        <div class="kinds" role="radiogroup" :aria-label="m.tests.title">
          <button v-for="k in KINDS" :key="k" type="button" role="radio" class="kind" :class="{ active: kind === k }"
            :aria-checked="kind === k" :disabled="!available(k)" @click="kind = k">
            <strong>{{ m.tests.kinds[k] }}</strong>
            <span class="muted small">{{ available(k) ? m.tests.kindHints[k] : format(m.tests.needWords, { n: distinctTranslations }) }}</span>
          </button>
        </div>
        <div class="row">
          <label v-if="kind !== 'translation'" class="field-inline">
            {{ m.tests.level }}
            <select v-model="level" class="input">
              <option v-for="l in LEVELS" :key="l" :value="l">{{ m.tests.levels[l] }}</option>
            </select>
          </label>
          <label class="field-inline">
            {{ m.tests.count }}
            <select v-model.number="count" class="input">
              <option :value="10">10</option>
              <option :value="20">20</option>
            </select>
          </label>
          <button type="button" class="btn primary" :disabled="core.status !== 'ready' || !available(kind)" @click="startTest">
            {{ m.tests.start }}
          </button>
        </div>
      </div>

      <div class="card">
        <h2>{{ m.tests.game }}</h2>
        <p class="muted">{{ m.tests.gameIntro }}</p>
        <p v-if="bestGame" class="small">{{ format(m.tests.best, { n: bestGame }) }}</p>
        <button type="button" class="btn primary" :disabled="core.status !== 'ready'" @click="startGame">{{ m.tests.gameStart }}</button>
      </div>

      <div class="card">
        <h2>{{ m.tests.history }}</h2>
        <p v-if="history.length === 0" class="muted">{{ m.tests.noHistory }}</p>
        <table v-else>
          <tbody>
            <tr v-for="h in history.slice(0, 10)" :key="h.id">
              <td>{{ kindName(h.kind) }}</td>
              <td class="num">
                <template v-if="h.kind === 'game_quick'">{{ format(m.tests.score, { n: h.correct }) }}</template>
                <template v-else>{{ h.correct }} / {{ h.total }}</template>
              </td>
              <td class="muted small">{{ new Date(h.taken_at).toLocaleString(dateLocale()) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <template v-else-if="mode === 'test' && current">
      <p class="muted small">{{ format(m.tests.question, { n: position + 1, total: questions.length }) }} · {{ m.tests.kinds[current.kind] }}</p>
      <QuestionCard :question="current" :chosen="chosen" show-rule @choose="choose" />
      <button v-if="chosen !== null" type="button" class="btn primary" @click="next">
        {{ position + 1 < questions.length ? m.tests.next : m.tests.finish }}
      </button>
    </template>

    <template v-else-if="mode === 'result'">
      <div class="card">
        <h2>{{ format(m.tests.result, { correct: correctCount, total: questions.length, percent: Math.round((100 * correctCount) / questions.length) }) }}</h2>
        <template v-if="mistakes.length">
          <h3>{{ m.tests.mistakes }}</h3>
          <ul class="mistakes">
            <li v-for="(x, i) in mistakes" :key="i">
              <span lang="ru" class="w">{{ x.q.lemma }}</span>
              <span v-if="asked(x.q)" class="muted small">({{ asked(x.q) }})</span>:
              <span class="ok-text" :lang="x.q.option_kind ? undefined : 'ru'">{{ x.q.options[x.q.answer] }}</span>
              <span class="muted small">≠ <span :lang="x.q.option_kind ? undefined : 'ru'">{{ x.q.options[x.given ?? 0] }}</span></span>
            </li>
          </ul>
        </template>
        <div class="row">
          <button type="button" class="btn primary" @click="startTest">{{ m.tests.again }}</button>
          <button type="button" class="btn" @click="mode = 'setup'">{{ m.tests.title }}</button>
        </div>
      </div>
    </template>

    <template v-else-if="mode === 'game' && current">
      <div class="game-bar">
        <strong class="num">{{ format(m.tests.timeLeft, { s: Math.max(0, timeLeft) }) }}</strong>
        <span class="num">{{ format(m.tests.score, { n: score }) }}</span>
      </div>
      <QuestionCard :question="current" :chosen="chosen" @choose="choose" />
    </template>

    <div v-else-if="mode === 'gameover'" class="card">
      <h2>{{ format(m.tests.gameOver, { n: score }) }}</h2>
      <p class="muted">{{ format(m.tests.best, { n: bestGame }) }}</p>
      <div class="row">
        <button type="button" class="btn primary" @click="startGame">{{ m.tests.gameStart }}</button>
        <button type="button" class="btn" @click="mode = 'setup'">{{ m.tests.title }}</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.page > .btn {
  justify-self: start;
  min-width: 10rem;
}
.page {
  max-width: 820px;
  display: grid;
  gap: 1rem;
  align-content: start;
}
.intro {
  margin: 0;
  max-width: 70ch;
}
.kinds {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.kind {
  display: grid;
  gap: 0.2rem;
  text-align: left;
  padding: 0.7rem 0.8rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font: inherit;
  cursor: pointer;
}
.kind.active {
  border-color: var(--accent);
  box-shadow: inset 3px 0 0 var(--accent);
}
.kind:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}
.field-inline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}
.field-inline .input {
  width: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
}
td {
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid var(--border);
}
.num {
  font-variant-numeric: tabular-nums;
}
.mistakes {
  padding-left: 1.1rem;
}
.w {
  font-weight: 700;
}
.ok-text {
  color: var(--ok);
  font-weight: 650;
}
.game-bar {
  display: flex;
  justify-content: space-between;
  font-size: 1.2rem;
}
</style>
