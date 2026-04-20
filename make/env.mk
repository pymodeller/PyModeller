# ─────────────────────────────────────────────────────────────────────────────
#  Environment variables management
#  Source of truth: env_spec.yaml
#  CLI: src/orion_mcp/core/env/cli.py
# ─────────────────────────────────────────────────────────────────────────────

ENV_SPEC      := env_datamodel.yaml
ENV_EXAMPLE   := .env.example
ENV_FILE      := .env
ENV_GENERATED := src/orion_mcp/core/env/datamodel.py
ENV_CLI       := uv run orion-mcp env

# ─────────────────────────────────────────────────────────────────────────────
# Main target: generates everything from env_spec.yaml
# Run this before starting the app or running tests.
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: env-generate
env-generate: ## Generate .env.example and typed Pydantic settings from env_spec.yaml
	@echo "$(ARROW) Generating artifacts from $(ENV_SPEC)..."
	@$(ENV_CLI) example --spec $(ENV_SPEC) --out $(ENV_EXAMPLE)
	@$(ENV_CLI) codegen  --spec $(ENV_SPEC) --out $(ENV_GENERATED)
	@uv run ruff format $(ENV_GENERATED)

# ─────────────────────────────────────────────────────────────────────────────
# Validation targets (CI / pre-flight)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: env-check
env-check: ## Validate .env against env_spec.yaml
	@echo "$(ARROW) Validating $(ENV_FILE) against $(ENV_SPEC)..."
	@$(ENV_CLI) check --spec $(ENV_SPEC) --env $(ENV_FILE)

.PHONY: env-diff
env-diff: ## Show variables in env_spec.yaml that are absent from .env
	@echo "$(ARROW) Comparing $(ENV_SPEC) with $(ENV_FILE)..."
	@$(ENV_CLI) diff --spec $(ENV_SPEC) --env $(ENV_FILE)

.PHONY: env-drift
env-drift: ## Detect if datamodel.py is out of sync with env_spec.yaml
	@echo "$(ARROW) Checking drift between $(ENV_SPEC) and $(ENV_GENERATED)..."
	@$(ENV_CLI) drift --spec $(ENV_SPEC) --datamodel $(ENV_GENERATED)
