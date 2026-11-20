<script setup lang="ts">
// A lexeme's paradigm as the engine arranged it (tables.py). Row and column names are grammeme
// names from the engine, in the interface language.
import { computed } from "vue";
import type { Row, Table } from "../../core/grammar";
import { useI18n } from "../../i18n";
import { useGrammar } from "../../stores/grammar";
import FormCell from "./FormCell.vue";

const props = defineProps<{ table: Table; selected?: number | null }>();
const m = useI18n();
const g = useGrammar();

/** "accs.anim" → "tushum kelishigi (jonli)", "pres.actv" → "hozirgi zamon, aniq nisbat". */
function label(key: string): string {
  if (key === "form") return m.value.analyze.columns.form;
  if (key === "after_prep") return m.value.analyze.columns.afterPrep;
  const dot = key.indexOf(".");
  if (dot < 0) return g.name(key);
  const head = key.slice(0, dot);
  const tail = key.slice(dot + 1);
  return head === "accs" ? `${g.name(head)} (${g.name(tail)})` : `${g.name(head)}, ${g.name(tail)}`;
}

const verb = computed(() => (props.table.kind === "verb" ? props.table : null));
const adjective = computed(() => (props.table.kind === "adjective" ? props.table : null));
const grid = computed(() =>
  props.table.kind === "noun" || props.table.kind === "pronoun" || props.table.kind === "numeral" ? props.table : null,
);

function hasForms(rows: Row[]): boolean {
  return rows.some((r) => r.cells.some((c) => c.length > 0));
}
</script>

<template>
  <div class="paradigm">
    <!-- Nouns, pronouns, numerals: cases in rows. -->
    <div v-if="grid" class="scroll">
      <table>
        <thead>
          <tr>
            <th scope="col" />
            <th v-for="c in grid.columns" :key="c" scope="col">{{ label(c) }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in grid.rows" :key="row.key">
            <th scope="row">{{ label(row.key) }}</th>
            <td v-for="(cell, i) in row.cells" :key="i"><FormCell :cells="cell" :selected="selected" /></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Adjectives (and pronouns that agree like them). -->
    <template v-else-if="adjective">
      <div v-if="adjective.rows.length" class="scroll">
        <table>
          <thead>
            <tr>
              <th scope="col" />
              <th v-for="c in adjective.columns" :key="c" scope="col">{{ label(c) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in adjective.rows" :key="row.key">
              <th scope="row">{{ label(row.key) }}</th>
              <td v-for="(cell, i) in row.cells" :key="i"><FormCell :cells="cell" :selected="selected" /></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="adjective.short" class="scroll">
        <h4>{{ m.analyze.adjective.short }}</h4>
        <table>
          <thead>
            <tr><th v-for="c in adjective.columns" :key="c" scope="col">{{ label(c) }}</th></tr>
          </thead>
          <tbody>
            <tr><td v-for="(cell, i) in adjective.short" :key="i"><FormCell :cells="cell" :selected="selected" /></td></tr>
          </tbody>
        </table>
      </div>
      <p v-if="adjective.comparative" class="line">
        <span class="line-label">{{ m.analyze.adjective.comparative }}:</span>
        <FormCell :cells="adjective.comparative" :selected="selected" />
      </p>
    </template>

    <!-- Verbs. -->
    <template v-else-if="verb">
      <p class="line">
        <span class="line-label">{{ m.analyze.verb.infinitive }}:</span>
        <FormCell :cells="verb.infinitive" :selected="selected" />
        <span v-if="verb.aspect" class="muted small">
          {{ verb.aspect === "both" ? m.analyze.verb.aspectBoth : g.name(verb.aspect) }}<template
            v-if="verb.transitivity">, {{ g.name(verb.transitivity) }}</template>
        </span>
      </p>
      <div v-for="part in verb.nonpast" :key="part.tense" class="scroll">
        <h4>{{ part.tense === "pres" ? m.analyze.verb.pres : m.analyze.verb.futr }}</h4>
        <table>
          <thead>
            <tr>
              <th scope="col" />
              <th v-for="c in part.columns" :key="c" scope="col">{{ label(c) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in part.rows" :key="row.key">
              <th scope="row">{{ label(row.key) }}</th>
              <td v-for="(cell, i) in row.cells" :key="i"><FormCell :cells="cell" :selected="selected" /></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="verb.future_compound" class="scroll">
        <h4>{{ m.analyze.verb.futureCompound }}</h4>
        <p class="muted small note">{{ m.analyze.constructed }}: {{ g.rules["verb.future_compound"]?.explanation }}</p>
        <table>
          <tbody>
            <tr v-for="row in verb.future_compound" :key="row.key">
              <th scope="row">{{ label(row.key) }}</th>
              <td v-for="(cell, i) in row.cells" :key="i"><FormCell :cells="cell" quiet /></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="verb.past" class="scroll">
        <h4>{{ m.analyze.verb.past }}</h4>
        <table>
          <thead>
            <tr><th v-for="c in verb.past.columns" :key="c" scope="col">{{ label(c) }}</th></tr>
          </thead>
          <tbody>
            <tr><td v-for="(cell, i) in verb.past.cells" :key="i"><FormCell :cells="cell" :selected="selected" /></td></tr>
          </tbody>
        </table>
      </div>
      <div v-if="verb.imperative.length" class="scroll">
        <h4>{{ m.analyze.verb.imperative }}</h4>
        <table>
          <thead>
            <tr>
              <th scope="col" />
              <th scope="col">{{ label("sing") }}</th>
              <th scope="col">{{ label("plur") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in verb.imperative" :key="row.key">
              <th scope="row">{{ label(row.key) }}</th>
              <td v-for="(cell, i) in row.cells" :key="i"><FormCell :cells="cell" :selected="selected" /></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-for="ger in verb.gerunds" :key="ger.key" class="line">
        <span class="line-label">{{ m.analyze.verb.gerunds }} ({{ label(ger.key) }}):</span>
        <FormCell :cells="ger.cells" :selected="selected" />
      </p>
      <template v-if="verb.participles.length">
        <h4>{{ m.analyze.verb.participles }}</h4>
        <details v-for="p in verb.participles" :key="p.key" class="participle">
          <summary>
            <FormCell :cells="p.lemma" :selected="selected" />
            <span class="muted small">{{ label(p.key) }}</span>
          </summary>
          <div v-if="hasForms(p.rows)" class="scroll">
            <table>
              <thead>
                <tr>
                  <th scope="col" />
                  <th v-for="c in p.columns" :key="c" scope="col">{{ label(c) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in p.rows" :key="row.key">
                  <th scope="row">{{ label(row.key) }}</th>
                  <td v-for="(cell, i) in row.cells" :key="i"><FormCell :cells="cell" :selected="selected" /></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="p.short" class="line">
            <span class="line-label">{{ m.analyze.adjective.short }}:</span>
            <FormCell :cells="p.short.flat()" :selected="selected" />
          </p>
        </details>
      </template>
    </template>

    <!-- Forms outside the grid, or every form of a word without a table. -->
    <details v-if="table.extra.length" class="extra" :open="table.kind === 'list'">
      <summary>{{ m.analyze.extra }} ({{ table.extra.length }})</summary>
      <ul>
        <li v-for="e in table.extra" :key="e.index" :class="{ selected: e.index === selected }">
          <span lang="ru" class="extra-form">{{ e.form }}</span>
          <span class="muted small">{{ e.description }}</span>
          <small v-if="e.rare" class="muted">({{ m.analyze.rare }})</small>
        </li>
      </ul>
    </details>
  </div>
</template>

<style scoped>
.paradigm {
  display: grid;
  gap: 0.9rem;
}
.scroll {
  overflow-x: auto;
}
h4 {
  margin: 0 0 0.35rem;
  font-size: 0.92rem;
  font-weight: 650;
}
table {
  border-collapse: collapse;
  width: 100%;
  font-size: 0.93rem;
}
th,
td {
  text-align: left;
  vertical-align: top;
  padding: 0.4rem 0.45rem;
  border-bottom: 1px solid var(--border);
}
thead th {
  font-size: 0.78rem;
  font-weight: 650;
  color: var(--muted);
  white-space: nowrap;
}
tbody th {
  font-weight: 550;
  color: var(--muted);
  font-size: 0.85rem;
  /* Long case names wrap so that every column fits without scrolling sideways. */
  min-width: 6.5rem;
  max-width: 10rem;
}
thead th {
  white-space: normal;
}
.note {
  margin: 0 0 0.35rem;
}
.line {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.5rem;
  margin: 0;
}
.line-label {
  font-weight: 600;
  font-size: 0.9rem;
}
.participle {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.4rem 0.7rem;
  margin-bottom: 0.4rem;
}
.participle summary {
  display: flex;
  gap: 0.6rem;
  align-items: baseline;
  cursor: pointer;
}
.extra summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
}
.extra ul {
  margin: 0.5rem 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.25rem;
}
.extra li {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: baseline;
}
.extra li.selected .extra-form {
  color: var(--accent);
  font-weight: 700;
}
</style>
