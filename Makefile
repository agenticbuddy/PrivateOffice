.DEFAULT_GOAL := help

.PHONY: help l10n l10n-overlap-check l10n-overlap-offline

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make l10n                  Override overlap check (AUTHORITATIVE: requires the editor running;' \
		'                             upstream = unmerged source-built snapshot, active = merged catalog)' \
		'  make l10n-overlap-check    Same as `make l10n`' \
		'  make l10n-overlap-offline  Offline approximation: base-image upstream, active check skipped when' \
		'                             the editor is not running (can drift — do not trust for accept/reject)'

l10n: l10n-overlap-check

# Authoritative: upstream baseline AND active catalog both come from the running editor, and both
# are MANDATORY — a missing/unreachable editor service fails the check (non-zero exit).
l10n-overlap-check:
	python3 scripts/check-l10n-overrides.py --upstream-from-active --active-service editor

# Offline approximation only (no running editor needed): upstream from the pinned base image, active
# check optional. The report is tagged OFFLINE-approx; use it as a hint, not a verdict.
l10n-overlap-offline:
	python3 scripts/check-l10n-overrides.py --active-service editor --active-optional
