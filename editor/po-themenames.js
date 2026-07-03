/* HAND-MAINTAINED (not generated) — localized document-theme preset names for the Format-tab Themes
   gallery. Unlike po-stylenames.js (extracted from the core sc.mo), the LO engine ships NO translations
   for these built-in colour-theme preset names (Retro/Forest/Sunset/…) — they are proper preset names
   kept English upstream. This map provides curated per-locale translations, consumed DISPLAY-ONLY by the
   iconview source patch (editor/patches/0005-*): the applied theme value stays the English name (the
   gallery selects by row index). Add locales / adjust names here by hand; unknown names pass through.
   Keys must match the English preset names the core sends (see the iconview id 'iconview_theme_colors'). */
window.PO_THEME_NAMES = {
  "ru": {
    "Retro": "Ретро",
    "Forest": "Лес",
    "Sunset": "Закат",
    "Breeze": "Бриз",
    "Classic": "Классическая",
    "Rainbow": "Радуга",
    "Red": "Красная",
    "Office": "Офисная",
    "Chalk": "Мел",
    "Green": "Зелёная",
    "Chart Classic": "Классическая (диаграмма)",
    "Beach": "Пляж",
    "Ocean": "Океан",
    "Purple": "Фиолетовая",
    "Orange": "Оранжевая",
    "Blue": "Синяя",
    "Grey": "Серая"
  }
};
window.getPOThemeName = function (name) {
  var maps = window.PO_THEME_NAMES;
  if (!maps || !name) return name;
  var loc = 'en';
  try { if (String.locale) loc = String.locale; } catch (e) {}
  loc = String(loc).toLowerCase().replace(/-/g, '_');
  var m = maps[loc] || maps[loc.split('_')[0]];
  return (m && m[name]) || name;
};
