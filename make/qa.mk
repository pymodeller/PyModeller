# ─────────────────────────────────────────────────────────────────────────────
# Quality Assurance & Checks
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: ci
ci: check test   ## Run full QA pipeline
	@echo "✨ QA pipeline completed successfully"

.PHONY: check
check: ## Run pre-commit checks
	@echo "$(ARROW) Running pre-commit checks..."
	@uv run pre-commit run --all-files

# ─────────────────────────────────────────────────────────────────────────────
# Formatting & Fixing
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: fix
fix: format lint ## Format and auto-fix code
	@echo "Code formatted and fixed $(OK)"

.PHONY: format
format:  ## Format code with ruff
	@echo "$(ARROW) Formatting code (ruff)..."
	@uv run ruff format

.PHONY: lint
lint:  ## Auto-fix lint issues with ruff
	@echo "$(ARROW) Auto-fixing lint issues (ruff)..."
	@uv run ruff check --fix

# ─────────────────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: test
test: sync  ## Run test suite
	@echo "$(ARROW) Running tests..."
	@uv run pytest -m "not functional" || { echo "❌ Tests failed."; exit 1; }
	@echo "All tests passed $(OK)"

.PHONY: e2e-test
e2e-test:  ## Execute an end to end test
	@uv run pytest -m functional -n 0 # tests/e2e
