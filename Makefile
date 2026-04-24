# ==============================================================================
#                     			Makefile
#                  Author: PyModeller
#                  Created: 2026
#                  Purpose: Development workflow
# ==============================================================================

# ──────────────────────────────────────────────────────────────────────────────
#  Configuration & Variables
# ──────────────────────────────────────────────────────────────────────────────
ifneq (,$(wildcard .env))
    include .env
    export
endif

# ──────────────────────────────────────────────────────────────────────────────
#  include files
# ──────────────────────────────────────────────────────────────────────────────
include make/build.mk
include make/clean.mk
include make/docs.mk
include make/qa.mk
include make/settings.mk
include make/setup.mk
include make/uv.mk

# ──────────────────────────────────────────────────────────────────────────────
# CI CD METHODOLOGY
# ──────────────────────────────────────────────────────────────────────────────
.PHONY: pr-review
pr-review: ## Backup if .env exists, otherwise skip backup, Ask for confirmation before overwriting
	git pull
	@test -f .env && cp .env .env.backup && echo "Backup created: .env.backup" || echo "No .env found to backup."
	@echo -n "Overwrite .env with .env.example? [y/N] " && read ans && [ $${ans:-N} = y ]
	cp .env.example .env
	$(MAKE) ci
