import { defineStore } from "pinia";
import { ref, watch } from "vue";
import { grammar, type Grammemes, type LexiconInfo, type Rule } from "../core/grammar";
import { locale, type Locale } from "../i18n";
import { useCore } from "./core";

/** Grammeme names, rule texts and lexicon details from the engine, in the interface language.
 *  They come from tilsim_core so the app and the engine never disagree on a name. */
export const useGrammar = defineStore("grammar", () => {
  const core = useCore();
  const grammemes = ref<Grammemes | null>(null);
  const rules = ref<Record<string, Rule>>({});
  const lexicon = ref<LexiconInfo | null>(null);
  const loadedFor = ref<Locale | null>(null);
  const error = ref("");

  async function load(lang: Locale): Promise<void> {
    if (core.status !== "ready" || loadedFor.value === lang) return;
    try {
      const [names, list, info] = await Promise.all([
        grammar.grammemes(lang),
        grammar.rules(lang),
        lexicon.value ? Promise.resolve(lexicon.value) : grammar.lexiconInfo(),
      ]);
      grammemes.value = names;
      rules.value = Object.fromEntries(list.map((r) => [r.id, r]));
      lexicon.value = info;
      loadedFor.value = lang;
      error.value = "";
    } catch (e) {
      error.value = String(e);
    }
  }

  watch([() => core.status, locale], () => void load(locale.value), { immediate: true });

  /** The name of a grammeme code ("gent" → "qaratqich kelishigi"); the code itself if unknown. */
  function name(code: string): string {
    return grammemes.value?.grammemes[code]?.name ?? code;
  }

  return { grammemes, rules, lexicon, error, name, load };
});
