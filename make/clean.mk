# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

# Directories & files to clean
CLEAN_DIRS := __pycache__ .pytest_cache .ruff_cache htmlcov site .venv .direnv build dist *.egg-info
CLEAN_FILES := *.pyc .coverage* coverage.xml .python-version

.PHONY: clean
clean: ## Clean generated files and caches
	@echo "$(ARROW) Cleaning generated files and caches..."
	@find . -type d \( $(foreach d,$(CLEAN_DIRS),-name "$(d)" -o ) -false \) -exec rm -rf {} + 2>/dev/null || true
	@find . -type f \( $(foreach f,$(CLEAN_FILES),-name "$(f)" -o ) -false \) -delete 2>/dev/null || true
	@echo "Cleanup completed"

.PHONY: clean-dry-run
clean-dry-run: ## Show files and directories that would be deleted
	@echo "Files / directories that would be deleted:"
	@find . -type d \( $(foreach d,$(CLEAN_DIRS),-name "$(d)" -o ) -false \) -print
	@find . -type f \( $(foreach f,$(CLEAN_FILES),-name "$(f)" -o ) -false \) -print
