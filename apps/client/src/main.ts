import "@fontsource-variable/noto-sans";
import "./style.css";
import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import { router } from "./app/router";
import { useCore } from "./stores/core";
import { useSession } from "./stores/session";
import { useSettings } from "./stores/settings";
import { useSync } from "./stores/sync";
import { useTranslations } from "./stores/translations";
import { useUpdates } from "./stores/updates";
import { useVocabulary } from "./stores/vocabulary";

const app = createApp(App);
app.use(createPinia());
app.use(router);

const settings = useSettings();
await settings.load();
app.mount("#app");

// These run in the background; the UI shows their progress.
void useCore().start();
void useSession().restore();
useSync().start();
void useVocabulary().load();
useTranslations().start();
useUpdates().startChecking();
