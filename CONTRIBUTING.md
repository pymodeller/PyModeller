# Contributing

 ## Using the Makefile (Recommended)

 This project provides a robust Makefile to simplify and standardize common development tasks.

 **Quick Start:** We strongly recommend running the following command to see all available shortcuts and descriptions:

 ```bash
 make help
 ```

 Contributors are encouraged to use the Makefile during development, as it:
 - Ensures consistent command execution across the entire team.
 - Seamlessly integrates core tooling such as `uv`, `ruff`, `pytest`, `pre-commit`, and `mkdocs`.
 - Simplifies complex workflows into memorable single-word commands.


### Frequently Used Commands

| Command | Purpose |
|---------|---------|
| `make qa` | Run full quality checks (recommended before committing) |
| `make test` | Run the test suite |
| `make fix` | Format and fix code |
| `make sync` | Install or update dependencies |
| `make docs` | Serve documentation locally |
| `make run` | Start the development server |

> **Note:** While all commands can be executed manually, the Makefile is the canonical way to interact with the project during development.


## Contribution Guidelines
Please keep the following guidelines in mind when contributing:
- Follow the coding style and conventions used in the project. See [Style Guide](./styleguide.md).
- Write clear and concise commit messages.
- Include tests for any new functionality or bug fixes.
- Be respectful and considerate of other contributors.

### Semantic Commit Messages 👌
Notice how a small change in the style of your commit messages can make you a better programmer.

Format:
<type>(<scope>): [issue] <subject>

- <issue>: User story or tracking tool ticket related to the change being committed.
- <scope>: Optional. If your change affects one or two specific packages, consider adding a scope.
Scopes should be short but recognizable, for example: content-docs, theme-classic, core.

Example:
```
feat(core): [JIRA02-33] allow webpack configuration override
^--^^----^  ^---------^ ^----------------------------------^
|   |       |           |
|   |       |           +-> Short summary in present tense. Use lowercase.
|   |       |
|   |       +-> User story or ticket reference.
|   |
|   +-> Package(s) affected by this change.
|
+-------> Commit type (see list above).
```

## Versioning 📌
We use [SemVer](http://semver.org/) for versioning
All published versions can be viewed as Git tags in this repository.

### Automated Versioning with Semantic Release
The project uses python‑semantic‑release to automatically determine the next version based on the commit messages that follow the Conventional Commits syntax.
You can trigger the version calculation using the Makefile:
```bash
make semantic-release      # Calculate next version (dry-run)
```

### What this command does

* It analyzes the commit history and determines the next version number automatically.
* It applies SemVer rules based on the commit message types (e.g., fix, feat, BREAKING CHANGE, etc.).
* During the process, it will prompt you to enter your Bitbucket Personal Access Token.
This token is required so semantic‑release can:
    * authenticate against Bitbucket, and
    * push the newly created version tag to the remote repository.

### Branch rules
Semantic release enforces the following branching model:

* main

    Only releases triggered from main will produce stable versions (e.g., 1.4.0, 2.0.1).
* Secondary branches (develop, feature/*, etc.)

    These branches cannot produce stable versions.

    Instead, they generate pre‑release versions in the form of release candidates (e.g., 1.4.0-rc.1).

    These versions are meant for testing and validation before merging into main.


This ensures that only fully validated work merged into main becomes an official, stable release.

## Testing
All changes must include appropriate test coverage
Pull Requests without tests may be rejected unless properly justified
You can run the test suite using the Makefile command:
```bash
make test
```

## Pull Request Checklist
Before submitting a Pull Request, please ensure that:
- [ ] qa passed: 'make qa'
- [ ] tests passed: 'make test'

## Security
Do not include secrets, credentials, or sensitive information in commits or Pull Requests.
