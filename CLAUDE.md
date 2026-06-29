# Project: PrivateOffice (self-hosted document workspace)

FastAPI+Vue SPA + an embedded self-hosted editor engine (CODE), behind nginx, with Postgres/MinIO.
Run on http://localhost:8088 (`docker compose up -d --build`). The WAL lives in
`.claude/update-log.md` — document every change there.

## CONVENTIONS

### Fix at the source — never override as a substitute for fixing
When something renders/behaves wrong, **fix the actual element in its own source code**
so the correct result loads on the first paint. It is FORBIDDEN to mask a problem with an
override layer *instead of* fixing it, i.e.:
- no bolt-on override stylesheets / extra `!important` rules piled on top to beat a default,
- no runtime DOM patching / `setInterval` scrubbers,
- no wrapper or post-load hacks.

For the embedded editor specifically: its CSS, branding and HTML in the image ARE editable
at build time (`editor/Dockerfile`). Theme it through the editor's **own** files and native
CSS variables (`branding.css`, the `--color-*` / `--co-primary-element` tokens, the real
class rules) so menus, hovers, submenus, dialogs are correct natively — do not bolt a separate
override sheet on top to patch individual elements. Overriding is acceptable ONLY when the
source genuinely cannot be edited.

### Git: commit self-contained tasks automatically
Initialize/maintain the repo and commit each self-contained, completed+verified task on your
own (no need to ask each time). One logical task = one commit, clear message. Don't commit
debugging artifacts (root-level screenshots, zips, `.playwright-mcp/`).
