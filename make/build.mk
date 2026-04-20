
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
	@GITLAB_CICD_TOKEN=$(UV_INDEX_GITLAB_PASSWORD) uv run semantic-release publish || { echo "$(FAIL) Publish failed"; exit 1; }
	@echo "$(OK) Release published"

.PHONY: semantic-release
semantic-release: ## Calculate next version (dry-run)
	@echo "$(ARROW) Running semantic-release version..."
	@GITLAB_CICD_TOKEN=$(UV_INDEX_GITLAB_PASSWORD) uv run semantic-release -vv version
	@echo "$(OK) Semantic release version check completed"


ifeq ($(strip $(CI_API_V4_URL)),)
CI_API_V4_URL     := http://localhost:8181/api/v4
endif
ifeq ($(strip $(CI_PROJECT_ID)),)
CI_PROJECT_ID     := 64
endif

TWINE_USERNAME ?= gitlab-ci-token
TWINE_REPOSITORY_URL ?= $(CI_API_V4_URL)/projects/$(CI_PROJECT_ID)/packages/pypi

.PHONY: push-package
push-package:
	@echo "$(ARROW) Publishing package..."
	@TWINE_REPOSITORY_URL=$(TWINE_REPOSITORY_URL) TWINE_PASSWORD=$(UV_INDEX_GITLAB_PASSWORD) \
		TWINE_USERNAME=$(TWINE_USERNAME) uv run twine upload --verbose dist/*
	@echo "$(OK) Package published"
