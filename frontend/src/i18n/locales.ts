// Selectable UI locales. Mirrors backend app/services/locales.py SUPPORTED.
export interface LocaleInfo {
  code: string;
  native: string;
  dir: "ltr" | "rtl";
}

export const LOCALES: LocaleInfo[] = [
  { code: "en", native: "English", dir: "ltr" },
  { code: "es", native: "Español", dir: "ltr" },
  { code: "de", native: "Deutsch", dir: "ltr" },
  { code: "fr", native: "Français", dir: "ltr" },
  { code: "pt-BR", native: "Português (Brasil)", dir: "ltr" },
  { code: "ru", native: "Русский", dir: "ltr" },
  { code: "it", native: "Italiano", dir: "ltr" },
  { code: "nl", native: "Nederlands", dir: "ltr" },
  { code: "pl", native: "Polski", dir: "ltr" },
  { code: "uk", native: "Українська", dir: "ltr" },
  { code: "tr", native: "Türkçe", dir: "ltr" },
  { code: "cs", native: "Čeština", dir: "ltr" },
  { code: "zh-CN", native: "简体中文", dir: "ltr" },
  { code: "ja", native: "日本語", dir: "ltr" },
  { code: "ko", native: "한국어", dir: "ltr" },
  { code: "hi", native: "हिन्दी", dir: "ltr" },
  { code: "vi", native: "Tiếng Việt", dir: "ltr" },
  { code: "id", native: "Bahasa Indonesia", dir: "ltr" },
  { code: "th", native: "ไทย", dir: "ltr" },
  { code: "ar", native: "العربية", dir: "rtl" },
  { code: "he", native: "עברית", dir: "rtl" },
  { code: "fa", native: "فارسی", dir: "rtl" },
];

export const LOCALE_CODES = LOCALES.map((l) => l.code);

export function dirFor(code: string): "ltr" | "rtl" {
  return LOCALES.find((l) => l.code === code)?.dir ?? "ltr";
}

export function nativeName(code: string): string {
  return LOCALES.find((l) => l.code === code)?.native ?? code;
}
