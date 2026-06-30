.DEFAULT_GOAL := help

.PHONY: help l10n l10n-overlap-check

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make l10n                Check localization override overlaps' \
		'  make l10n-overlap-check  Same check, explicit target name'

l10n: l10n-overlap-check

l10n-overlap-check:
	python3 scripts/check-l10n-overrides.py --active-service editor --active-optional
