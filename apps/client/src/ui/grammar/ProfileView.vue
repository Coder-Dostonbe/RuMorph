<script setup lang="ts">
// Which rules explain a lexeme (classify.py): its class and its exceptions, each with the
// rule's explanation and this word's own example.
import { computed } from "vue";
import type { Profile } from "../../core/grammar";
import { useI18n } from "../../i18n";
import { useGrammar } from "../../stores/grammar";

const props = defineProps<{ profile: Profile | null }>();
const m = useI18n();
const g = useGrammar();

const category = computed(() => (props.profile?.category ? g.rules[props.profile.category] ?? null : null));
const findings = computed(() =>
  (props.profile?.findings ?? []).map((f) => ({ ...f, rule: g.rules[f.rule] ?? null, id: f.rule })),
);
const pending = computed(
  () =>
    (category.value?.review_status ?? "") === "pending_specialist_review" ||
    findings.value.some((f) => f.rule?.review_status === "pending_specialist_review"),
);
</script>

<template>
  <div class="profile">
    <p v-if="!profile || !category" class="muted">{{ m.analyze.noProfile }}</p>
    <template v-else>
      <div class="rule main">
        <div class="rule-name">{{ category.name }}</div>
        <p>{{ category.explanation }}</p>
        <p v-if="category.example" class="example" lang="ru">{{ category.example }}</p>
      </div>
      <div v-for="f in findings" :key="f.id + f.detail" class="rule">
        <div class="rule-name">{{ f.rule?.name ?? f.id }}</div>
        <p class="detail" lang="ru">{{ f.detail }}</p>
        <p v-if="f.rule" class="muted small">{{ f.rule.explanation }}</p>
      </div>
      <p v-if="pending" class="muted small">{{ m.analyze.reviewPending }}</p>
    </template>
  </div>
</template>

<style scoped>
.profile {
  display: grid;
  gap: 0.6rem;
}
.rule {
  border-left: 3px solid var(--border);
  padding: 0.1rem 0 0.1rem 0.75rem;
}
.rule.main {
  border-left-color: var(--accent);
}
.rule p {
  margin: 0.2rem 0 0;
}
.rule-name {
  font-weight: 650;
}
.detail {
  font-weight: 600;
  color: var(--accent);
}
.example {
  color: var(--muted);
  font-size: 0.9rem;
}
</style>
