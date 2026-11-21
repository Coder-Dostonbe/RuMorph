/// <reference types="vite/client" />

declare const __APP_VERSION__: string;

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<object, object, unknown>;
  export default component;
}

interface ImportMetaEnv {
  /** Base URL of the Tilsim API, e.g. https://zabon-api.<account>.workers.dev */
  readonly VITE_API_URL?: string;
}
