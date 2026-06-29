"""co_lang maps app locales to canonical tags the editor core can resolve.

Non-canonical bare tags (e.g. 'ru') the core cannot match to a LangID, so it
renders an on-the-fly autonym with a literal '{ru}' suffix in the status bar and
breaks a downstream JSON.parse. Canonicalizing to a registered region tag fixes
both symptoms at the source (PROB-014).
"""
from app.services import locales


def test_ru_is_canonicalized_to_region_tag():
    # Regression: bare 'ru' produced 'русский {ru}' + a console parse error.
    assert locales.co_lang("ru") == "ru-RU"


def test_known_overrides_are_region_tags():
    assert locales.co_lang("en") == "en-US"
    assert locales.co_lang("uk") == "uk-UA"
    assert locales.co_lang("cs") == "cs-CZ"


def test_locale_without_override_passes_through():
    # Tags already carrying a region are forwarded unchanged.
    assert locales.co_lang("pt-BR") == "pt-BR"
    assert locales.co_lang("zh-CN") == "zh-CN"
