/* PrivateOffice theme gate. Loaded parse-blocking from cool.html <head> as a same-origin
   external script (allowed by the editor's CSP `script-src 'self'`, unlike an inline script),
   so it runs BEFORE the body renders — the glass theme is active on the first paint with no
   runtime DOM patching afterwards. The session's design is passed in the iframe URL as
   ?po_design=glass|classic by the app; classic opts out and keeps the default editor look. */
(function () {
  try {
    if (new URLSearchParams(location.search).get("po_design") === "classic") return;
    document.documentElement.setAttribute("data-po", "glass");
  } catch (e) {
    /* noop */
  }
})();
