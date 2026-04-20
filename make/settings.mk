# ──────────────────────────────────────────────────────────────────────────────
#  Configuration & Variables
# ──────────────────────────────────────────────────────────────────────────────


VENV_DIR        := .venv
ENV_SCRIPT      := activate_env.sh

PROJECT_NAME    := $(notdir $(CURDIR))
CONTAINER_NAME  := $(shell echo "$(PROJECT_NAME)" | tr '[:upper:]' '[:lower:]' | tr -s ' _-' '-' | sed 's/-*$$//; s/^-*//')
REPO_URL        := $(shell git remote get-url origin 2>/dev/null)
REGISTRY_URL := $(shell echo "$(REPO_URL)" | \
                  sed -e 's|.*@||' \
                      -e 's|https://||' \
                      -e 's|gitlab\.agrubio\.dev/|registry.agrubio.dev/|' \
                      -e 's|\.git$$||' \
                      -e 's|^|https://|')
REGISTRY_PATH   := $(shell echo "$(REGISTRY_URL)" | sed 's|https://||')

ifeq ($(strip $(VERSION)),)
VERSION     := v$(shell grep '^version[[:space:]]*=' pyproject.toml | head -n 1 | sed 's/version[[:space:]]*=[[:space:]]*"\(.*\)"/\1/')
endif

# Colors & symbols
NO_COLOR    := \033[0m
ERROR       := \033[0;31m
SUCCESS     := \033[0;32m
WARNING     := \033[0;33m
INFO        := \033[0;36m
UNDERLINE   := \033[4m
BOLD        := \033[1m

OK      := $(SUCCESS)✓$(NO_COLOR)
FAIL    := $(ERROR)✗$(NO_COLOR)
ARROW   := $(INFO)→$(NO_COLOR)

# Variables
VENV_DIR := .venv

.DEFAULT_GOAL := help

# ─────────────────────────────────────────────────────────────────────────────
# Help / Default target
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help message
	@echo "$(BOLD)Available Makefile commands$(NO_COLOR)"
	@echo "Usage: make $(UNDERLINE)target$(NO_COLOR)"
	@echo ""
	@grep -H -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN { \
		FS = ":.*?## "; \
		printf "  $(BOLD)%-25s %-20s %-35s$(NO_COLOR)\n", "COMMAND", "FILE", "EXPLANATION"; \
		printf "  %-25s %-20s %-35s\n", "-------", "----", "-----------" \
	} \
	{ \
		split($$0, a, ":"); \
		file = a[1]; \
		sub("^make/", "", file); \
		sub("\\.mk$$", "", file); \
		target = a[2]; \
		help = $$2; \
		printf "  $(INFO)%-25s$(NO_COLOR) %-20s %-35s\n", target, file, help \
	}'
