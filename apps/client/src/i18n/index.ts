import { computed, ref } from "vue";
import en from "./en";
import ru from "./ru";
import uz, { type Messages } from "./uz";

export const locales = ["uz", "ru", "en"] as const;
export type Locale = (typeof locales)[number];
export const localeNames: Record<Locale, string> = { uz: "O'zbekcha", ru: "Русский", en: "English" };

const catalogs: Record<Locale, Messages> = { uz, ru, en };

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (locales as readonly string[]).includes(value);
}

/** The interface language. The settings store loads and saves it. */
export const locale = ref<Locale>("uz");

export const messages = computed<Messages>(() => catalogs[locale.value]);

export function useI18n() {
  return messages;
}

/** Fills {name} placeholders: format("Hi {name}", { name: "Doston" }). */
export function format(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => (key in values ? String(values[key]) : match));
}

export type { Messages };

/** BCP 47 tag for dates and numbers in the interface language. */
export function dateLocale(): string {
  return { uz: "uz-Latn-UZ", ru: "ru-RU", en: "en-GB" }[locale.value];
}
