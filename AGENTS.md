# AI Agent Development Guidelines

This document is the behavioral mandate for AI agents and developers working on this repository. It defines the canonical workflows, architecture rules, quality gates, and hard constraints.

CRITICAL: Before making any code change, you MUST also read CONVENTIONS.md — it contains the tech stack, code conventions, and structural reference that all agents are required to follow.

---

## 🚀 Core Workflows

### 1. Environment Setup & Onboarding
- Initial setup: Always run make setup first. This triggers the environment credential setup via the Python CLI.
- Portability: All scripts and Makefile targets must be POSIX-compliant (WSL, Linux, macOS). Use Python for complex logic — never long bash in Makefiles.
- Credential safety: Authentication tokens live in .env and are backed up to .env.backup on make clean. Never commit these files.

### 2. Monorepo Architecture
- Root Package = Source of truth (all core logic lives here).
- Dev dependencies: Path-based (editable) for local development. Production: Switch to the central registry index.
- Environment Schema: The py_modeller.yaml lives in the source directory and is bundled as package data. Never copy it manually — it should be resolved dynamically from the installed package.
- Env propagation: Root .env variables must be exported to sub-processes. Sub-project Makefiles should look for a parent .env if a local one is missing.

### 3. Quality Assurance (CI)
- Always run make ci before proposing any change. Includes:
  - checkmake — Makefile linter (strict target line limits).
  - ruff — Python linter (complexity ≤ 10, line length 120).
  - Type checking (e.g., pyright or pyrefly).
  - pytest — Full test suite.

---

## 🛠 Technical Standards

### Makefile Patterns
- Complex logic → Python: Delegate to uv run <bin> ... or Python scripts. Never write long bash in targets.
- No shell scripts: Use Make targets + Python CLI only for cross-platform compatibility.
- Portable sed: sed "..." file > file.tmp && mv file.tmp file — never sed -i.
- Export vars: Use export so child processes receive .env variables.
- Target line limit: Keep targets short (linting enforces this).


#### doctor target convention
doctor must only call non-interactive check targets:
```makefile
doctor: ## Check uv-artifactory configuration
	@echo "$(ARROW) Check environment..."
	@$(MAKE) sync-all
```
**Never** add interactive prompts (like credential setup) to doctor — it blocks CI.

### Env Data Model System
py_modeller.yaml is the single source of truth for all environment variables.

- Generated artifact: The Pydantic settings classes are auto-generated from YAML. Never edit the generated Python file manually.
- Workflow: Always edit py_modeller.yaml first, then run make env-generate.
- Validation: CI must verify that the generated code is in sync with the YAML spec and that the .env file contains no duplicates.

### Git Hygiene
- Branch naming: feature/TASK-description.
- Commit standards: Use a email address for all commits.

---

## ✅ Quality Gates

Before suggesting or applying any change, verify it passes:

1. ruff check — Linting and formatting.
2. Type checking — Static analysis.
3. pytest — All tests pass.
4. checkmake — Makefile targets are concise.

---

## 🚫 Hard Constraints

- NEVER use print() — Use a proper logger (loguru) or rich.
- NEVER use pip — Always use uv.
- NEVER use sed -i — Use the portable redirection pattern.
- NEVER use standalone shell scripts — Use Make targets + Python CLI.
- NEVER commit .env, .env.backup, or any secrets/tokens.
- NEVER add unnecessary abstractions — Keep complexity minimal.
- NEVER hardcode paths to package files — Use dynamic resolution.
- NEVER add interactive steps to non-interactive targets like doctor or ci.
