# ─────────────────────────────────────────────────────────────────────────────
# Dependencies & Environment
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: sync
sync: ## Sync dependencies based on lockfile
	@echo "$(ARROW) Syncing dependencies (uv sync)..."
	@uv sync
	@echo "Sync completed $(OK)"

.PHONY: sync-all
sync-all: ## Sync all dependencies
	@echo "$(ARROW) Syncing dependencies (uv sync --all-groups --all-packages)..."
	@uv sync --all-groups --all-packages
	@echo "Dependencies updated $(OK)"

.PHONY: update
update: check-venv  ## Update dependencies & pre-commit hooks
	@echo "$(ARROW) Updating dependencies and pre-commit hooks..."
	@uv lock --upgrade || { echo "❌ uv lock upgrade failed."; exit 1; }
	@uv sync || { echo "❌ uv sync failed."; exit 1; }
	@uv run pre-commit autoupdate || { echo "❌ pre-commit autoupdate failed."; exit 1; }
	@echo "Update completed $(OK)"

.PHONY: windows-uv
windows-uv: ## Check if is windows environment
	@echo "Windows detected. Install uv manually:";
	@echo "  PowerShell: irm https://astral.sh/uv/install.ps1 | iex";
	@echo "  Or: winget install --id astral-sh.uv -e";

.PHONY: check-uv
check-uv:  ## Verify uv installed
	@if ! command -v uv >/dev/null 2>&1; then echo "$(ARROW) uv not found. Installing..."; \
		if [ "$$(uname)" = "Darwin" ] || [ "$$(uname)" = "Linux" ]; then \
			curl -LsSf https://astral.sh/uv/install.sh | sh; \
		else $(MAKE) windows-uv fi; echo "uv installed $(OK)"; \
	else echo "uv already installed: $$(uv --version)"; fi

.PHONY: no-venv
no-venv:  ## No venv activated
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "❌ No virtual environment active. Run: source $(VENV_DIR)/bin/activate"; \
		exit 1; \
	fi

.PHONY: wrong-venv
wrong-venv: ## Wrong venv activated
	@if [ "$$VIRTUAL_ENV" != "$(PWD)/$(VENV_DIR)" ]; then \
		echo "❌ Wrong venv active: $$VIRTUAL_ENV"; \
		echo "   Expected: $(PWD)/$(VENV_DIR)"; \
		echo "   Run: deactivate"; exit 1; \
	fi

.PHONY: check-venv
check-venv: check-uv no-venv wrong-venv ## Verify virtual environment
	@uv lock --locked
	@echo "Correct virtual environment active $(OK)"
