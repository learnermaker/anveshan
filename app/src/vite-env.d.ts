/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Service base URL; '' = same origin; 'mock' = canned SYNTHETIC fixtures in the browser. */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
