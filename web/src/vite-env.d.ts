/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Gateway origin for REST and WS. Empty string = same origin (dev proxy). */
  readonly VITE_GATEWAY_URL?: string;
}
