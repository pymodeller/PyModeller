
# ─────────────────────────────────────────────────────────────────────────────
# Build & Publish
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: build
build:  ## Build python package(s)
	@echo "$(ARROW) Building package(s)..."
	@uv build || { echo "$(FAIL) Build failed"; exit 1; }
	@echo "$(OK) Build completed"

.PHONY: artifact
artifact: build

.PHONY: publish
publish:  ## Publish release using semantic-release
	@echo "$(ARROW) Publishing release..."
	@uv run semantic-release publish || { echo "$(FAIL) Publish failed"; exit 1; }
	@echo "$(OK) Release published"

.PHONY: semantic-release
semantic-release: ## Calculate next version (dry-run)
	@echo "$(ARROW) Running semantic-release version..."
	@uv run semantic-release -vv version
	@echo "$(OK) Semantic release version check completed"
