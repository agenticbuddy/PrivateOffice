# PrivateOffice editor image. The liquid-glass theme AND the full rebrand are applied at
# BUILD TIME to the served files, so the editor loads correct on the first paint — no runtime
# DOM patching and no bolt-on override stylesheet. The theme is folded into the editor's own
# bundle.css; the rebrand rewrites the upstream display strings in place.
FROM collabora/code:latest

USER root
ARG DIST=/usr/share/coolwsd/browser/dist

# Self-hosted fonts + the PrivateOffice logo (replaces the upstream butterfly/wordmark).
COPY fonts/ ${DIST}/fonts/
COPY po-logo.svg ${DIST}/images/po-logo.svg
COPY po-toggle.js ${DIST}/po-toggle.js

# Fold the PrivateOffice glass theme into the editor's OWN stylesheet (bundle.css) so it is part
# of the native CSS and correct on first paint — not a separate override sheet. The theme gate
# (po-toggle.js) is a same-origin EXTERNAL script linked parse-blocking in <head>: the editor's
# CSP is `script-src 'self'` (no 'unsafe-inline'), so an inline gate would be blocked — an
# external same-origin script is allowed and runs before the body renders. It sets one attribute
# (data-po) so the glass theme is active on first paint; classic sessions opt out via ?po_design.
COPY branding-privateoffice.css /tmp/po-theme.css
RUN cat /tmp/po-theme.css >> ${DIST}/bundle.css && rm /tmp/po-theme.css \
 && sed -i '/po-theme\.css/d; /po-theme-toggle/d; /po-toggle\.js/d' ${DIST}/cool.html \
 && sed -i "s#</head>#<script id=\"po-theme-toggle\" src=\"%SERVICE_ROOT%/browser/%VERSION%/po-toggle.js\"></script></head>#" ${DIST}/cool.html

# Remove the engine's DEAD bare inline dark-theme <script> (cool.html). The editor's own CSP
# (binary-baked: script-src 'self' 'unsafe-eval', no 'unsafe-inline', no nonce) rejects any inline
# script, so this block logs a CSP violation on every load while never running: it is gated on
# ?darkTheme=true, which our integration never passes (editor.py builds the iframe URL with
# WOPISrc/lang/po_design only; theming is driven by the external po-toggle.js). Deleting it is
# behavior-preserving. We do NOT relax CSP and do NOT externalize (the block's
# %SERVICE_ROOT%/%VERSION% dark-CSS href is only substituted in the HTML template, not in served
# .js, so an external file would ship the literal placeholder). The content-guarded multi-line range
# reads the bare <script>..</script> and deletes it only when it carries the unique
# "Apply dark theme immediately" comment, so the attributed script tags (po-toggle + global/templates/
# bundle) are untouched.
RUN sed -i '/<script>/{:a;N;/<\/script>/!ba;/Apply dark theme immediately/d;}' ${DIST}/cool.html

# Rebrand the product name + copyright everywhere (display strings; safe across JS/HTML/JSON/CSS).
# MPL-2.0 permits modifying this self-hosted build. Phrases first, then the bare upstream word on
# data/markup files only (NOT bundle.js, to keep the editor JS global intact). These sed patterns
# are the search strings that ERASE the upstream name from the build.
RUN PHRASES='s/Collabora Online Development Edition (CODE)/PrivateOffice/g; s/Collabora Online Development Edition/PrivateOffice/g; s/Collabora Online/PrivateOffice/g; s/Collabora Office/PrivateOffice/g; s/Collabora Productivity Limited/PrivateOffice/g; s/Collabora Productivity/PrivateOffice/g' \
 && grep -rIl 'Collabora' ${DIST} --include='*.js' --include='*.html' --include='*.json' --include='*.css' 2>/dev/null | xargs -r sed -i "$PHRASES" \
 && grep -rIl 'Collabora' ${DIST} --include='*.html' --include='*.json' --include='*.css' 2>/dev/null | xargs -r sed -i 's/Collabora/PrivateOffice/g' \
 && sed -i 's/Collabora/PrivateOffice/g' ${DIST}/admin-bundle.js ${DIST}/branding.js

# Localize the ribbon group "more options" expander at source. Upstream's createMoreButton builds
# both the aria-label and the hover tooltip as the raw concat "More options for "+id, so it never
# passes through the _() translator (English in every locale) and leaks the internal control id
# (e.g. "More options for home-font"). Rewrite BOTH byte-identical sites to mirror the engine's OWN
# localized sidebar path (_("More options for {1}").replace(...)), feeding the human-readable group
# label (groupLabel.textContent, already set from data.name) through the existing catalog key
# "More options for {1}" (present in 38 locales; missing locales fall back to the EN template filled
# with the localized name — still id-free). id/groupLabel/_() are all in scope in createMoreButton.
RUN sed -i "s#\"More options for \"+id#_(\"More options for {1}\").replace(\"{1}\",groupLabel\&\&groupLabel.textContent?groupLabel.textContent:id)#g" ${DIST}/bundle.js

# Localize the combobox dropdown button's accessible name (Font Name / Font Size / name-box). Upstream's
# ui-combobox-button builder composes it by concatenating fragment msgids: _("Open ")+value+_(" list").
# Concatenated i18n is un-localizable: missing fragments leak English around a localized value (ru
# "Open Гарнитура list"), and where the fragments exist they freeze placeholder order/spacing
# (uk "Відкрити Шрифт список", zh "打开 字体名称 列表"). Rewrite the unique site to mirror the builder's OWN
# sibling template one line up (_("Open {name}").replace("{name}",buttonText)), reusing the existing
# "Open {name}" key (present in 37 locales) so the position/spacing are locale-controlled. Keep the
# empty-label branch as _("Open list") (existing key in 22 locales) to avoid a trailing space. Locales
# lacking "Open {name}" (e.g. ar) fall back to the EN template filled with the localized value — id-free
# and correctly ordered, same accepted behavior as the "More options for {1}" fix above.
RUN sed -i "s#dataAriaLabel?_(\"Open \")+dataAriaLabel+_(\" list\"):_(\"Open list\")#dataAriaLabel?_(\"Open {name}\").replace(\"{name}\",dataAriaLabel):_(\"Open list\")#" ${DIST}/bundle.js

# Fill the localized COOL ribbon/sidebar/menu chrome strings that fall back to English. These are
# client _() calls in bundle.js whose msgid is simply ABSENT from the merged catalog the engine loads
# (ui-<loc>.json), so _() returns the raw English key (worst in RU/AR, partial in UK/ZH). Honest fix =
# inject the missing key->translation into the real ui-<loc>.json the engine fetches -- no override
# sheet, no runtime DOM patch. Generic terms take the authoritative LibreOffice value from the in-image
# LO-core .mo (mnemonic-stripped), cross-locale consistent (Clipboard/Cells/Alignment/Category/Chart/
# Shape/Number Format/Expand Formula Bar); the COOL-only terms with no .mo source (Editing, Merge &
# Center, Insert Note) use the LibreOffice-verified RU/AR values from the issue. We only INSERT where
# the key is missing and CORRECT the one wrong value (UK Chart transliteration). Values are \u-escaped
# to match the catalogs' all-ASCII style; '&' in the "Merge & Center" key is escaped (it is sed's
# match-ref) and a DOUBLE backslash \\u is used so GNU sed emits a literal \u, not an uppercase op.
# Out of scope (NOT a missing browser key -> a catalog edit would be a no-op/mask): server-rendered
# strings localized by LO-core .mo/.ui -- RU number-format General (sc STR_GENERAL; the client catalog
# already holds the LO-standard sidebar value), sidebar _Category (.ui), Pivot Calculated Field and
# Remove Table (not _() literals); and COOL-only strings with no authoritative source for the missing
# locales (Table Design, Show sheet list, Navigation Panel, Print Grid Lines, Add Theme...), left as
# the English fallback rather than guessed. See .qa/round-1/problems/PROB-018.md.
RUN sed -i 's#^{#{"Illustrations": "\\u0627\\u0644\\u0631\\u0633\\u0648\\u0645 \\u0627\\u0644\\u062a\\u0648\\u0636\\u064a\\u062d\\u064a\\u0629", "Clipboard": "\\u0627\\u0644\\u062d\\u0627\\u0641\\u0638\\u0629", "Cells": "\\u062e\\u0644\\u0627\\u064a\\u0627", "Alignment": "\\u0645\\u062d\\u0627\\u0630\\u0627\\u0629", "Category": "\\u0627\\u0644\\u0635\\u0646\\u0641", "Chart": "\\u0627\\u0644\\u0645\\u062e\\u0637\\u0637 \\u0627\\u0644\\u0628\\u064a\\u0627\\u0646\\u064a", "Shape": "\\u0634\\u0643\\u0644", "Expand Formula Bar": "\\u0648\\u0633\\u0651\\u0639 \\u0634\\u0631\\u064a\\u0637 \\u0627\\u0644\\u0645\\u0639\\u0627\\u062f\\u0644\\u0629", "Editing": "\\u062a\\u062d\\u0631\\u064a\\u0631", "Merge \& Center": "\\u062f\\u0645\\u062c \\u0648\\u062a\\u0648\\u0633\\u064a\\u0637", "Insert Note": "\\u0625\\u062f\\u0631\\u0627\\u062c \\u0645\\u0644\\u0627\\u062d\\u0638\\u0629", #' ${DIST}/l10n/ui-ar.json \
 && sed -i 's#^{#{"Chart": "Graf", #' ${DIST}/l10n/ui-cs.json \
 && sed -i 's#^{#{"Chart": "Diagramme", #' ${DIST}/l10n/ui-fr.json \
 && sed -i 's#^{#{"Chart": "\\u05ea\\u05e8\\u05e9\\u05d9\\u05dd", #' ${DIST}/l10n/ui-he.json \
 && sed -i 's#^{#{"Shape": "Forma", #' ${DIST}/l10n/ui-it.json \
 && sed -i 's#^{#{"Clipboard": "\\u30af\\u30ea\\u30c3\\u30d7\\u30dc\\u30fc\\u30c9", "Cells": "\\u30bb\\u30eb", "Alignment": "\\u914d\\u7f6e", "Category": "\\u30ab\\u30c6\\u30b4\\u30ea\\u30fc", "Chart": "\\u30b0\\u30e9\\u30d5", "Shape": "\\u30b7\\u30a7\\u30a4\\u30d7", "Expand Formula Bar": "\\u6570\\u5f0f\\u30d0\\u30fc\\u3092\\u5c55\\u958b", "Number Format": "\\u6570\\u306e\\u66f8\\u5f0f", #' ${DIST}/l10n/ui-ja.json \
 && sed -i 's#^{#{"Clipboard": "\\ud074\\ub9bd\\ubcf4\\ub4dc", "Cells": "\\uc140", "Alignment": "\\ub9de\\ucda4", "Chart": "\\ucc28\\ud2b8", "Shape": "\\ub3c4\\ud615", "Expand Formula Bar": "\\uc218\\uc2dd \\ud45c\\uc2dc\\uc904 \\ud655\\uc7a5", "Number Format": "\\uc22b\\uc790 \\ud615\\uc2dd", #' ${DIST}/l10n/ui-ko.json \
 && sed -i 's#^{#{"Clipboard": "\\u00c1rea de transfer\\u00eancia", "Cells": "C\\u00e9lulas", "Alignment": "Alinhamento", "Category": "Categoria", "Chart": "Gr\\u00e1fico", "Shape": "Forma", "Expand Formula Bar": "Expandir a linha de entrada", "Number Format": "Formato num\\u00e9rico", #' ${DIST}/l10n/ui-pt_BR.json \
 && sed -i 's#^{#{"Illustrations": "\\u0418\\u043b\\u043b\\u044e\\u0441\\u0442\\u0440\\u0430\\u0446\\u0438\\u0438", "Clipboard": "\\u0411\\u0443\\u0444\\u0435\\u0440 \\u043e\\u0431\\u043c\\u0435\\u043d\\u0430", "Cells": "\\u042f\\u0447\\u0435\\u0439\\u043a\\u0438", "Alignment": "\\u0412\\u044b\\u0440\\u0430\\u0432\\u043d\\u0438\\u0432\\u0430\\u043d\\u0438\\u0435", "Chart": "\\u0414\\u0438\\u0430\\u0433\\u0440\\u0430\\u043c\\u043c\\u0430", "Editing": "\\u0420\\u0435\\u0434\\u0430\\u043a\\u0442\\u0438\\u0440\\u043e\\u0432\\u0430\\u043d\\u0438\\u0435", "Merge \& Center": "\\u041e\\u0431\\u044a\\u0435\\u0434\\u0438\\u043d\\u0438\\u0442\\u044c \\u0438 \\u043f\\u043e\\u043c\\u0435\\u0441\\u0442\\u0438\\u0442\\u044c \\u0432 \\u0446\\u0435\\u043d\\u0442\\u0440\\u0435", "Insert Note": "\\u0412\\u0441\\u0442\\u0430\\u0432\\u0438\\u0442\\u044c \\u043f\\u0440\\u0438\\u043c\\u0435\\u0447\\u0430\\u043d\\u0438\\u0435", #' ${DIST}/l10n/ui-ru.json \
 && sed -i 's#^{#{"Clipboard": "Pano", "Cells": "H\\u00fccreler", "Alignment": "Hizalama", "Category": "Kategori", "Chart": "Grafik", "Number Format": "Say\\u0131 bi\\u00e7imi", #' ${DIST}/l10n/ui-tr.json \
 && sed -i 's#^{#{"Chart": "\\u0110\\u1ed3 th\\u1ecb", #' ${DIST}/l10n/ui-vi.json \
 && sed -i 's#"Chart": "[^"]*"#"Chart": "\\u0414\\u0456\\u0430\\u0433\\u0440\\u0430\\u043c\\u0430"#' ${DIST}/l10n/ui-uk.json

# Neutralize every external upstream URL at source (the header-logo link, release-notes, docs and
# proxy links in the localizations) so nothing can phone home or leak the upstream identity.
RUN grep -rIl 'collabora' ${DIST} --include='*.js' --include='*.html' --include='*.json' --include='*.css' 2>/dev/null \
      | xargs -r sed -i 's|https\?://[a-zA-Z0-9._/?=&:%~-]*collabora[a-zA-Z0-9./?=&:%~_-]*|about:blank|g' \
 && grep -rIl 'col\.la' ${DIST} --include='*.js' --include='*.html' --include='*.json' --include='*.css' 2>/dev/null \
      | xargs -r sed -i 's|https\?://col\.la[a-zA-Z0-9./?=&:%~_-]*|about:blank|g'

# Replace the upstream logo image files (About wordmark + header logo) with the PrivateOffice mark.
RUN for f in $(ls ${DIST}/images/ | grep -iE 'collabora|full-logo|lc_about|toolbar-bg-logo'); do \
      cp ${DIST}/images/po-logo.svg ${DIST}/images/$f; \
    done

# Provide the Paste Special context-menu icon the engine deterministically requests but upstream
# omits. getIconNameOfCommand(".uno:PasteSpecial") -> "lc_pastespecial.svg" (no iconURLAliases entry,
# PasteSpecial not in commandWithoutIcon), so comboboxEntry->setImage->getImageURL fetches a file that
# isn't shipped -> 404 + blank icon in every locale. Honest fix: materialize the missing asset from
# the shipped paste art for both light and dark themes (lc_pastespecial is in no localizedIcons list,
# so base + dark cover all 22 locales). Not an override sheet / runtime patch / nginx alias.
RUN cp ${DIST}/images/lc_paste.svg ${DIST}/images/lc_pastespecial.svg \
 && cp ${DIST}/images/dark/lc_paste.svg ${DIST}/images/dark/lc_pastespecial.svg \
 && chmod a+r ${DIST}/images/lc_pastespecial.svg ${DIST}/images/dark/lc_pastespecial.svg

# Don't request an empty images/ URL for icon-less entries. Submenu context-menu entries carry the
# synthetic key "submenuN", which getIconNameOfCommand maps to "" ; getImageURL("") then builds
# getURL("images/"+"")=getURL("images/") -> a non-empty path that getURL's own `if(path==="")return""`
# guard misses -> a stray GET /browser/<v>/images/ 404. Mirror that guard one level up: return "" when
# imgName is empty (setImage then sets src="" = no request, no error handler), matching the engine's
# existing empty-path behavior while leaving every icon-bearing entry unchanged.
RUN sed -i 's#getImageURL=function(imgName){var _a;#getImageURL=function(imgName){var _a;if(!imgName)return"";#' ${DIST}/bundle.js

# Privacy + rebrand of coolwsd's SERVE-TIME template placeholders. cool.html ships %PLACEHOLDER%
# tokens that coolwsd substitutes when serving (from its compiled branding), so the bare-word
# rebrand sed above never sees them — %PRODUCT_BRANDING_NAME% becomes "Collabora Online Development
# Edition (CODE)" (the editor <title> and the header-logo tooltip) and %PRODUCT_BRANDING_URL%
# becomes the collaboraonline.com product link (the logo's href → "leads to them"). Replace the
# placeholders with our own values here so coolwsd has nothing to substitute: name → PrivateOffice,
# product URL → about:blank. Also empties welcome/feedback/buyproduct (zero phone-home) and disables
# auto-welcome; deletes the welcome assets. (Update check is off via compose.)
RUN sed -i 's/%FEEDBACK_URL%//g; s/%WELCOME_URL%//g; s/%BUYPRODUCT_URL%//g; s/%AUTO_SHOW_WELCOME%/false/g; s/%PRODUCT_BRANDING_NAME%/PrivateOffice/g; s|%PRODUCT_BRANDING_URL%|about:blank|g' ${DIST}/cool.html \
 && sed -i 's#<!--%BRANDING_JS%-->#<script src="%SERVICE_ROOT%/browser/%VERSION%/branding.js"></script>#' ${DIST}/cool.html \
 && rm -rf ${DIST}/welcome ${DIST}/welcome.html ${DIST}/welcome.js \
 && chmod -R a+r ${DIST}/fonts ${DIST}/images

# Per-build cache-bust token for the engine assets. coolwsd derives every /browser asset's
# ETag from the compile-time COOLWSD_VERSION_HASH, which the sed/cp content patches above never
# change -- so a returning browser, holding a 128-day max-age copy under the unchanged hash,
# would keep STALE bundle.js/l10n after a redeploy (a forced revalidation would even 304 against
# the unchanged-hash ETag). ver_suffix is the engine's OWN lever for exactly this (its desc:
# "Appended to etags to allow easy refresh of changed files"): stamp the build id into
# coolwsd.xml so each patched rebuild yields a fresh ETag (<hash><BUILD_ID>) -> revalidation
# returns 200 with the corrected bytes on first paint, while an unchanged build still 304s
# (cheap). Pairs with the nginx /browser no-cache policy that overrides coolwsd's 128-day
# max-age. The entrypoint execs coolwsd against this coolwsd.xml unchanged, so the baked value
# is effective. Set BUILD_ID to the git short SHA at build (docker-compose.yml editor.build.args);
# placed last so changing it rebuilds only this tiny layer, not the content-patch chain.
ARG BUILD_ID=dev
# Write BUILD_ID as the ELEMENT TEXT of <ver_suffix>…</ver_suffix> (coolwsd reads the element
# content, NOT the `default` attribute — setting the attribute is a no-op for the ETag), so each
# patched rebuild yields a fresh ETag "<hash><BUILD_ID>".
RUN sed -i "s#\(<ver_suffix [^>]*>\)</ver_suffix>#\1${BUILD_ID}</ver_suffix>#" /etc/coolwsd/coolwsd.xml

# Cache-bust the cool.html-referenced engine assets with ?b=<BUILD_ID>. The ver_suffix ETag only
# helps browsers that REVALIDATE; a browser still holding a 128-day max-age copy (served before the
# nginx /browser no-cache policy existed) won't even ask. cool.html itself is never cached (unique
# WOPI token per session), so changing the asset URLs here forces those already-cached browsers to
# refetch the patched theme (bundle.css), app+rebrand (bundle.js), and l10n catalogs on next open.
RUN sed -i -E "s#(%SERVICE_ROOT%/browser/%VERSION%/[A-Za-z0-9._/-]+\.(css|js|json))#\1?b=${BUILD_ID}#g" ${DIST}/cool.html

USER cool
