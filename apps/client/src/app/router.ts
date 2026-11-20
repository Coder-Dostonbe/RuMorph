import { createRouter, createWebHashHistory } from "vue-router";
import AboutView from "../views/AboutView.vue";
import AccountView from "../views/AccountView.vue";
import HomeView from "../views/HomeView.vue";
import SettingsView from "../views/SettingsView.vue";

// Only finished sections get a route: there are no placeholder pages.
export const router = createRouter({
  // Hash history works the same on every Tauri platform (no server-side routing).
  history: createWebHashHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/account", name: "account", component: AccountView },
    { path: "/settings", name: "settings", component: SettingsView },
    { path: "/about", name: "about", component: AboutView },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});
