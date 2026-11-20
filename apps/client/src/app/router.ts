import { createRouter, createWebHashHistory } from "vue-router";
import AboutView from "../views/AboutView.vue";
import AccountView from "../views/AccountView.vue";
import AnalyzeView from "../views/AnalyzeView.vue";
import DictionaryView from "../views/DictionaryView.vue";
import FlashcardsView from "../views/FlashcardsView.vue";
import GrammarView from "../views/GrammarView.vue";
import SpellView from "../views/SpellView.vue";
import TestsView from "../views/TestsView.vue";
import MoreView from "../views/MoreView.vue";
import HomeView from "../views/HomeView.vue";
import SettingsView from "../views/SettingsView.vue";

// Only finished sections get a route: there are no placeholder pages.
export const router = createRouter({
  // Hash history works the same on every Tauri platform (no server-side routing).
  history: createWebHashHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/dictionary", name: "dictionary", component: DictionaryView },
    { path: "/cards", name: "cards", component: FlashcardsView },
    { path: "/tests", name: "tests", component: TestsView },
    { path: "/grammar", name: "grammar", component: GrammarView },
    { path: "/spell", name: "spell", component: SpellView },
    { path: "/analyze", name: "analyze", component: AnalyzeView },
    { path: "/more", name: "more", component: MoreView },
    { path: "/account", name: "account", component: AccountView },
    { path: "/settings", name: "settings", component: SettingsView },
    { path: "/about", name: "about", component: AboutView },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});
