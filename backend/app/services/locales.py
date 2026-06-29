"""Locale handling shared by UI and the editor.

`SUPPORTED` is the catalog of selectable UI locales (code, native name, direction).
`co_lang` maps an app locale to the language code the editor expects in the `lang`
URL parameter.
"""

# code -> (native name, direction)
SUPPORTED: dict[str, tuple[str, str]] = {
    "en": ("English", "ltr"),
    "es": ("Español", "ltr"),
    "de": ("Deutsch", "ltr"),
    "fr": ("Français", "ltr"),
    "pt-BR": ("Português (Brasil)", "ltr"),
    "ru": ("Русский", "ltr"),
    "it": ("Italiano", "ltr"),
    "nl": ("Nederlands", "ltr"),
    "pl": ("Polski", "ltr"),
    "uk": ("Українська", "ltr"),
    "tr": ("Türkçe", "ltr"),
    "cs": ("Čeština", "ltr"),
    "zh-CN": ("简体中文", "ltr"),
    "ja": ("日本語", "ltr"),
    "ko": ("한국어", "ltr"),
    "hi": ("हिन्दी", "ltr"),
    "vi": ("Tiếng Việt", "ltr"),
    "id": ("Bahasa Indonesia", "ltr"),
    "th": ("ไทย", "ltr"),
    "ar": ("العربية", "rtl"),
    "he": ("עברית", "rtl"),
    "fa": ("فارسی", "rtl"),
}

# App locale -> editor `lang` code (normalize a few that differ).
_CO_OVERRIDES: dict[str, str] = {
    "en": "en-US",
    "ru": "ru-RU",
    "uk": "uk-UA",
    "cs": "cs-CZ",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "hi": "hi-IN",
    "th": "th-TH",
    "he": "he-IL",
    "fa": "fa-IR",
    "vi": "vi-VN",
    "id": "id-ID",
}


def is_supported(code: str) -> bool:
    return code in SUPPORTED


def direction(code: str) -> str:
    return SUPPORTED.get(code, ("", "ltr"))[1]


def co_lang(code: str) -> str:
    """Return the editor-acceptable language tag for an app locale."""
    if code in _CO_OVERRIDES:
        return _CO_OVERRIDES[code]
    return code
