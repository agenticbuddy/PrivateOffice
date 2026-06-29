import { createI18n } from "vue-i18n";
import en from "./messages/en.json";
import { dirFor } from "./locales";

// Bundle every available message catalog. Missing keys fall back to English.
const modules = import.meta.glob<{ default: Record<string, unknown> }>(
  "./messages/*.json",
  { eager: true },
);
const messages: Record<string, Record<string, unknown>> = {};
for (const path in modules) {
  const code = path.match(/\/([^/]+)\.json$/)?.[1];
  if (code) messages[code] = modules[path].default;
}

export const AVAILABLE_CATALOGS = Object.keys(messages);

export const i18n = createI18n({
  legacy: false,
  locale: "en",
  fallbackLocale: "en",
  messages: messages as never,
  missingWarn: false,
  fallbackWarn: false,
});

export function applyLocale(code: string): void {
  // Use the catalog if present; otherwise keep English strings but still flip dir.
  i18n.global.locale.value = (messages[code] ? code : "en") as never;
  document.documentElement.lang = code;
  document.documentElement.dir = dirFor(code);
}

export function applyDesign(design: string): void {
  document.documentElement.setAttribute("data-design", design === "classic" ? "classic" : "glass");
}

export const messagesByLocale = messages;
