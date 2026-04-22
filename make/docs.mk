# ─────────────────────────────────────────────────────────────────────────────
# Documentation
# ─────────────────────────────────────────────────────────────────────────────

# Detect the operating system
UNAME_S := $(shell uname -s)

# Command definition
ifeq ($(UNAME_S),Darwin)
    SED_FIX = sed -i ''
else
    SED_FIX = sed -i
endif


.PHONY: docs
docs: 	## Serve documentation locally
	@echo "$(ARROW) Serving documentation (mkdocs)..."
	@uv run mkdocs serve --livereload

.PHONY: docs-build
docs-build: ## Build documentation site
	@echo "$(ARROW) Building documentation site..."
	@uv run mkdocs build
	@echo "Documentation built $(OK)"

.PHONY: create-ln
create-ln: ## Create a symbolic link
	@cd docs && ln -s ../README.md index.md
	@cd docs && ln -s ../CONTRIBUTING.md CONTRIBUTING.md
	@cd docs && ln -s ../styleguide.md styleguide.md


.PHONY: generate-docs
generate-docs: ## Generate mkdocs files from src
	@echo "Generating docs structure from src..."
	@find src -type f -name "*.py" ! -name "__init__.py" | while read file; do \
		rel_path=$${file#src/}; \
		dir_path=$$(dirname $$rel_path); \
		base_name=$$(basename $$file .py); \
		mkdir -p docs/code/$$dir_path; \
		module_path=$$(echo $$rel_path | sed 's|/|.|g' | sed 's|.py$$||'); \
		echo "::: $$module_path" > docs/code/$$dir_path/$$base_name.md; \
	done
	@echo "Docs generated in docs/code"



.PHONY: fix-links
fix-links: ## target to clean links
	$(SED_FIX) 's/(docs\//(/' README.md
