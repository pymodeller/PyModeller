ENV_FILE := .env

define prompt_and_store
    @if [ -z "$($(1))" ]; then \
        echo "$(ARROW) Enter $(1):"; \
        if [ "$(2)" = "secret" ]; then \
            read -s value; echo ""; \
        else \
            read value; \
        fi; \
        echo "$(1)=$$value" >> $(ENV_FILE); \
        export $(1)="$$value"; \
    fi
endef

.PHONY: setup
setup: ## Execute project setup
	@echo "$(ARROW) Running interactive setup..."
	@if [ -f $(ENV_FILE) ]; then \
		cp $(ENV_FILE) .env.backup; \
		echo "Creating backup: .env.backup"; \
	else \
		cp .env.example $(ENV_FILE); \
		echo "$(ARROW) Created .env from .env.example"; \
	fi
	$(call prompt_and_store,GITHUB_USER,plain)
	$(call prompt_and_store,GITHUB_TOKEN,secret)
	@$(MAKE) configure-github
	@$(MAKE) doctor
	@echo "✅ Setup completed successfully"

.PHONY: doctor
doctor: ## Check uv-artifactory configuration
	@echo "$(ARROW) Check environment..."
	@$(MAKE) sync-all
	@$(MAKE) env-drift
