.DEFAULT_GOAL := help

# ---- deploy knobs (override on the command line, e.g. `make deploy ADMIN_PASS=secret`) ----
APP_URL                  ?= http://localhost:8088
ADMIN_USER               ?= admin              # nginx BasicAuth user gating /admin (from nginx/htpasswd)
ADMIN_PASS               ?= 123                # nginx BasicAuth password gating /admin
BOOTSTRAP_ADMIN_EMAIL    ?= admin@example.com
BOOTSTRAP_ADMIN_PASSWORD ?= admin123           # password set on the SPA administrator account by `make deploy`

.PHONY: help deploy init up down restart logs ps admin _wait-healthy _admin-password info \
        l10n l10n-overlap-check l10n-overlap-offline

help:
	@printf '%s\n' \
		'PrivateOffice — targets:' \
		'' \
		'  make deploy    One command: config + build + start + admin setup + access info' \
		'  make init      Alias for `make deploy`' \
		'  make up        (Re)build + start the stack (no admin setup / info)' \
		'  make down      Stop + remove containers (data volumes are kept)' \
		'  make restart   down + deploy' \
		'  make logs      Follow all container logs' \
		'  make ps        Stack status' \
		'  make admin     Print the admin-panel URL + credentials' \
		'' \
		'  make l10n                  Override overlap check (needs the editor running)' \
		'  make l10n-overlap-offline  Offline approximation (editor not required)'

# ============================ Deploy / run ============================

# One command to stand the whole thing up and make the admin usable.
deploy: up _wait-healthy _admin-password info
init: deploy

# Build + start the whole stack. The first editor build compiles Collabora Online from source
# (slow, ~15-25 min once; fast from cache after). scripts/up.sh stamps BUILD_ID so editor assets
# cache-bust per build.
up:
	@test -f .env || { cp deploy/.env.example .env; echo "-> created .env from deploy/.env.example (edit secrets before production)"; }
	./scripts/up.sh

down:
	docker compose down

restart: down deploy

logs:
	docker compose logs -f

ps:
	docker compose ps

admin: info

# Wait until the app answers its health check (DB + app ready).
_wait-healthy:
	@printf '%s' '-> waiting for the app to become healthy'
	@for i in $$(seq 1 120); do \
		if curl -sf $(APP_URL)/api/health >/dev/null 2>&1; then echo ' ok'; exit 0; fi; \
		printf '.'; sleep 3; \
	done; echo ' (timeout - check `make logs`)'

# Give the bootstrapped SPA administrator (BOOTSTRAP_ADMIN_EMAIL) a password so it can sign in.
# Idempotent; /admin/api is gated by nginx BasicAuth (ADMIN_USER/ADMIN_PASS). Non-fatal on failure.
_admin-password:
	@id=$$(curl -s -u $(ADMIN_USER):$(ADMIN_PASS) $(APP_URL)/admin/api/users 2>/dev/null \
	  | python3 -c "import sys,json;print(next((u['id'] for u in json.load(sys.stdin) if u.get('email')=='$(BOOTSTRAP_ADMIN_EMAIL)'),''))" 2>/dev/null); \
	if [ -n "$$id" ]; then \
	  curl -s -o /dev/null -u $(ADMIN_USER):$(ADMIN_PASS) -X POST $(APP_URL)/admin/api/users/$$id/password \
	    -H 'Content-Type: application/json' -d '{"password":"$(BOOTSTRAP_ADMIN_PASSWORD)"}' \
	    && echo "-> SPA administrator password set"; \
	else echo "-> admin user not ready yet - set a password later from the admin panel"; fi

info:
	@printf '\n  PrivateOffice is up.\n\n'
	@printf '     App (SPA):    %s\n' '$(APP_URL)'
	@printf '     Admin panel:  %s/admin   -> BasicAuth  %s / %s\n' '$(APP_URL)' '$(ADMIN_USER)' '$(ADMIN_PASS)'
	@printf '     SPA sign-in:  %s / %s   (administrator; create end-users from the admin panel)\n\n' '$(BOOTSTRAP_ADMIN_EMAIL)' '$(BOOTSTRAP_ADMIN_PASSWORD)'

# ============================ Localization checks ============================

l10n: l10n-overlap-check

# Authoritative: upstream baseline AND active catalog both come from the running editor, and both
# are MANDATORY — a missing/unreachable editor service fails the check (non-zero exit).
l10n-overlap-check:
	python3 scripts/check-l10n-overrides.py --upstream-from-active --active-service editor

# Offline approximation only (no running editor needed): upstream from the pinned base image, active
# check optional. The report is tagged OFFLINE-approx; use it as a hint, not a verdict.
l10n-overlap-offline:
	python3 scripts/check-l10n-overrides.py --active-service editor --active-optional
