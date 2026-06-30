# Collabora Online source patches

Source-level changes to the **Collabora Online** source (coolwsd + the browser bundle) that
`editor/Dockerfile.online` clones at build time. Use this when a fix belongs in the editor's OWN
source — not as a post-build `sed` on a built artifact, and not as a runtime override.

## How it works
- Put unified diffs here: `editor/patches/NNNN-short-name.patch`.
- `editor/Dockerfile.online` runs, right after `git clone` and before `configure`:
  `git apply` for every `editor/patches/*.patch` against the cloned tree (`/build/online`).
- No `.patch` file → no-op. A patch that fails to apply **breaks the build on purpose**.
- Catalogue each patch in `editor/manifests/patchset.json`.

## Authoring a patch
Patches are pinned to `online_from_source.ref` in `editor/manifests/upstream.json`
(currently `cp-26.04.1-4`). Generate against THAT ref:

```bash
git clone --branch cp-26.04.1-4 https://github.com/CollaboraOnline/online.mirror /tmp/online
cd /tmp/online
# edit files under browser/ , coolwsd , etc.
git diff > /path/to/repo/editor/patches/0001-my-change.patch
```

Paths inside the diff are repo-relative (`a/browser/... b/browser/...`), the form `git apply` expects.

## On re-pin
When `ONLINE_REF` changes, every patch must be **rebased** against the new source (re-generate or
fix the hunks). A stale patch will fail `git apply` and stop the build — that is the intended signal.

## When NOT to use a source patch
- Tweaking an already-built artifact (`bundle.js`, `cool.html`, catalogs) → the post-build steps in
  `Dockerfile.online` (catalogued in `patchset.json`).
- Translation data → `editor/l10n/overrides/`.
- Changing the LibreOffice **core** (engine) source → out of scope here; the engine is the prebuilt
  base-image binary, not built from source.
