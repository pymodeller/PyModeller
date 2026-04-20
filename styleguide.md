# 2025 Enhanced Git Commit Message Style Guide

## Overview
This guide defines the conventions for writing Git commit messages in a Python-based data science project. It aligns with the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification to ensure clarity, consistency, and maintainability in the project's version history. Well-crafted commit messages facilitate collaboration, debugging, and automation (e.g., generating changelogs).

## Message Structure
A commit message consists of three parts:
- **Type**: Subject
- **Body** (Optional)
- **Footer** (Optional)

**Important Format: type: subject**

- Begin your commit message with a valid type (e.g., feat, fix, docs) followed by a colon and a space.
- The subject should be a concise, imperative summary (ideally ≤50 characters) that starts with a capital letter and avoids ending punctuation.

Example:
• feat: Add new authentication method

### Type
The type indicates the nature of the change. Use one of the following:
- `feat`: A new feature (e.g., adding a new model or functionality)
- `fix`: A bug fix (e.g., correcting an error in data processing)
- `docs`: Changes to documentation (e.g., updating README or docstrings)
- `style`: Formatting or code style changes (e.g., applying PEP 8) with no functional change
- `refactor`: Refactoring production code (e.g., restructuring code for clarity)
- `test`: Adding or refactoring tests (e.g., unit tests) with no production code change
- `setup`: Updating build tasks or package configurations (e.g., updating `pyproject.toml`)
- `data`: Adding or updating data files (e.g., CSV, Parquet datasets)
- `release`: Creating a new release (e.g., publishing a Python package)
- `perf`: Performance improvements (e.g., optimizing a query or algorithm)
- `revert`: Reverting a previous commit (e.g., undoing a problematic change)
- `clean`: Cleaning up code (e.g., removing unused files, functions, comments)

### Subject
The subject is a concise summary of the change. It must:
- Be no longer than 50 characters
- Begin with a capital letter
- Not end with a period
- Use an imperative tone (e.g., "Add", "Fix", "Update")

### Body (Optional)
- Use the body to provide additional context for complex changes or to explain the reasoning behind the change.
- Wrap lines at 72 characters for readability.
- Include details such as:
  - Why the change was made
  - What components are affected
  - Any trade-offs or considerations

### Footer (Optional)
- Use the footer for metadata, such as:
  - Issue references (e.g., "Closes #123")
  - Breaking changes (e.g., "BREAKING CHANGE: description")
  - Other notes or references
- Indicate breaking changes with a `!` after the type (e.g., `feat!`) or a "BREAKING CHANGE" footer.

## Best Practices
- **Imperative Mood**: Write subjects in the imperative mood (e.g., "Add feature" instead of "Added feature").
- **Clarity and Conciseness**: Ensure the subject is descriptive enough to understand the change at a glance.
- **Consistency**: Adhere to the defined types and structure for all commits.
- **When to Use a Body**: Include a body for:
  - Complex changes requiring explanation
  - Changes with significant impact
  - Providing context for code reviewers
- **Breaking Changes**: Clearly mark breaking changes using `!` or a "BREAKING CHANGE" footer to alert team members.
- **Issue Tracking**: Reference issue numbers in the footer (e.g., "Closes #123") if using an issue tracker like GitHub Issues.
- **Python and Data Science Considerations**:
  - Use `setup` for changes to Python dependencies or build tools (e.g., uv, setup scripts..).
  - Use `data` for commits involving datasets, which are common in data science projects.
  - Prioritize clear messages for Python-specific changes, as readability is a core principle of Python (per PEP 20).

## Examples
### Basic Examples
```
• feat: "Add Ollama integration"
• docs: "Add instructions for executing the open OCR app"
• refactor: "Move the missing features function to the helper library"
• feat: "Add a dummy classifier to the helper library"
• feat: "Automate (stratified) training/test and features/target splits"
• fix: "Display categorical targets (previously not shown)"
• fix: "Binary target parsed to float instead of int"
• perf: "Optimize database query for faster performance"
• revert: "Revert 'feat: Add feature X' due to critical bug"

```
### Extended Example with Body and Footer
```
feat: Add new authentication mechanism

This commit introduces an OAuth2-based authentication method, replacing the deprecated basic auth system. The new method improves security and aligns with modern standards. Existing users will need to update their credentials.

BREAKING CHANGE: The old authentication method is deprecated and will be removed in the next major release.
Closes #456
```

## Benefits
- **Collaboration**: Clear messages help team members understand changes, improving code reviews.
- **Debugging**: Detailed commit messages make it easier to trace bugs or changes in the project history.
- **Automation**: Structured messages support tools that generate release notes or changelogs.
- **Onboarding**: Informative commit messages help new developers understand the project’s evolution.

## Python and Data Science Notes
- **Dependency Management**: Use the `setup` type for changes to Python package configurations (e.g., updating `pyproject.toml`).
- **Data Files**: Use the `data` type for commits involving datasets, such as adding new CSV files or updating Parquet files, which are common in data science workflows.
- **Model Updates**: Use `feat` or `fix` for changes to ML / GenAI models, ensuring the subject clearly describes the update (e.g., "Combine LLM & M for time-series prediction").
- **Readability**: Python emphasizes readability (per PEP 20), so commit messages should be clear and descriptive, especially for complex data processing or model training changes.

## Credits
- This guide incorporates principles from the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.
- Based on best practices from the open-source community and tailored for Python and data science projects. Refernce: https://github.com/angelmtenor/ai-circus/blob/develop/styleguide.md
