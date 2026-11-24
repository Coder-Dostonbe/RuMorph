import { createRouter, createWebHashHistory } from "vue-router";
import AboutView from "../views/AboutView.vue";
import AccountView from "../views/AccountView.vue";
import AdminView from "../views/AdminView.vue";
import AnalyzeView from "../views/AnalyzeView.vue";
import CalendarView from "../views/CalendarView.vue";
import DictionaryView from "../views/DictionaryView.vue";
import FlashcardsView from "../views/FlashcardsView.vue";
import GrammarView from "../views/GrammarView.vue";
import ReadingView from "../views/ReadingView.vue";
import SpellView from "../views/SpellView.vue";
import TestsView from "../views/TestsView.vue";
import MoreView from "../views/MoreView.vue";
import HomeView from "../views/HomeView.vue";
import SettingsView from "../views/SettingsView.vue";
import { useAdmin } from "../stores/admin";

// Only finished sections get a route: there are no placeholder pages.
export const router = createRouter({
  // Hash history works the same on every Tauri platform (no server-side routing).
  history: createWebHashHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/dictionary", name: "dictionary", component: DictionaryView },
    { path: "/cards", name: "cards", component: FlashcardsView },
    { path: "/reading", name: "reading", component: ReadingView },
    { path: "/tests", name: "tests", component: TestsView },
    { path: "/grammar", name: "grammar", component: GrammarView },
    { path: "/spell", name: "spell", component: SpellView },
    { path: "/calendar", name: "calendar", component: CalendarView },
    { path: "/analyze", name: "analyze", component: AnalyzeView },
    { path: "/more", name: "more", component: MoreView },
    { path: "/account", name: "account", component: AccountView },
    { path: "/settings", name: "settings", component: SettingsView },
    { path: "/about", name: "about", component: AboutView },
    // Reached only from "About" (the hidden entry); asks for the password itself.
    { path: "/admin", name: "admin", component: AdminView },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

// Admin-only pages are not reachable while the admin mode is locked.
router.beforeEach((to) => (to.meta.admin && !useAdmin().unlocked ? { name: "admin" } : true));
