# AGENTS.md

Context file for AI agents working on opentelemetry-python.

**Dual Format**: This file combines Category A (Operations Manual) and Category B (Context Guide) for comprehensive agent guidance.

## Project Overview

opentelemetry-python is a Python project using Python (pip).

**Key Info:**
- **Primary Language:** Python
- **Build System:** Python (pip)
- **Test Framework:** pytest
- **Total Files:** 1122
- **Test Files:** 333
- **AI Readiness Score:** 98/100 (Agent-Optimized)

---

## 🚨 AI Policy & Operations

Extracted from CONTRIBUTING.md - operational constraints and procedures.

### AI Policy

- If you are using AI agents to assist with contributions, please read [AGENTS.md](AGENTS.md) for guidance on how to use them responsibly in this project.
- It's especially valuable to read through the [library guidelines](https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/library-guidelines.md).

### Key Requirements

- Before you can contribute, you will need to sign the [Contributor License Agreement](https://docs.linuxfoundation.org/lfx/easycla/contributors).
- If your change does not need a changelog entry, add the "Skip Changelog" label to the PR.
- If your work requires more extensive changes, consider a series of small, self-contained PRs instead.
- merged, your PR will require rebasing. Since only maintainers can merge your PR it is

### Development Procedures

- context, reviewing PRs, and helping those get merged. Buddies will not be available 24/7, but is committed to responding
- some aspects of development, including testing against multiple Python versions.
- To install `tox`, run:
- pip install tox
- You can also run tox with `uv` support. By default [tox.ini](./tox.ini) will automatically create a provisioned tox environment with `tox-uv`, but you can install it at host level:

### Known Workarounds & Caveats

- Urgent fix can take exception as long as it has been actively communicated.



## 🏗️ Architecture & Context Guide

This section provides architectural context and agent-understanding for the codebase.

### Prerequisites

- **Python:** >=3.10 (or applicable language version)
- **Package Manager:** pip or uv
- **Test Runner:** pytest



### Project Structure

```
opentelemetry-python/
├── pyproject.toml
├── pyproject.toml
├── pyproject.toml
├── src/                  # Source code
├── tests/                # Test suite (333 files)
└── README.md             # Project documentation
```

### Architecture Overview

#### Key Components
- **Main Entry:** main.py, app.py, app.py, app.py, app.py
- **Test Suite:** 333 test files
- **Build Configuration:** pyproject.toml, pyproject.toml, pyproject.toml

#### Design Principles

1. **Modularity** - Code organized by functionality with clear separation of concerns
2. **Testability** - Comprehensive test coverage across critical paths
3. **Clarity** - Explicit naming and structure for AI agent understanding
4. **Consistency** - Uniform patterns and conventions throughout codebase
5. **Maintainability** - Well-documented code with clear intent

### Directory Map

| Directory | Purpose |
|-----------|----------|
| `docs/` | Documentation |
| `scripts/` | Build and utility scripts |
| `tests/` | Test suite |


### Development Workflow

#### Initial Setup

```bash
git clone https://github.com/YOUR_ORG/opentelemetry-python.git
cd opentelemetry-python
pip install -e .
# or
uv sync --all-groups
```

#### Development Commands

**Running Tests:**
```bash
pytest                    # Run all tests
pytest tests/             # Run specific test directory
pytest -v                 # Verbose output with test names
pytest -x                 # Stop on first failure
coverage run -m pytest && coverage report  # With coverage report
```

#### Code Quality
```bash
ruff check .              # Lint with ruff
ruff format .             # Format code
mypy .                    # Type checking (if configured)
```

### Code Style & Conventions

- **Naming:** Use Python conventions (snake_case for functions, PascalCase for classes)
- **Type Hints:** Yes (strongly encouraged)
- **Error Handling:** Yes - handle errors at boundaries; let exceptions propagate when another layer owns recovery
- **Logging:** Yes
- **Testing:** Yes - write tests alongside code changes

### Testing Strategy

**Framework:** pytest
**Test Files:** 333 found

Before committing:
1. Run the full test suite: `pytest`
2. Ensure all tests pass
3. Check type hints: `mypy .`
4. Format code: `ruff format .`

### Writing Documentation

When updating docs:
1. Always include explanatory text before code snippets
2. Describe *why* and *what* before showing *how*
3. Keep sections focused on a single concept
4. Use clear, concrete examples

## Known Gotchas & Warnings

- Don't include the PR number — towncrier adds it automatically

### Contributing Guidelines

This project has a detailed contribution guide at **`CONTRIBUTING.md`**.

**Key Requirements:**
- **Performance Work**: Requires benchmarks and performance metrics in PR description

**Before submitting:**
1. Read `CONTRIBUTING.md` in full
2. Check recent merged PRs for patterns
3. Follow the specific requirements above

### Common Patterns

When contributing to this project:
1. Read existing code in the area you're modifying
2. Follow the established patterns and style
3. Write tests for new functionality
4. Use clear, descriptive variable and function names
5. Add docstrings for public APIs
6. Update tests when changing behavior

### What We Value

✅ Well-tested code with clear intent
✅ Consistent code style and naming conventions
✅ Code that is easy for AI agents to understand
✅ Clear, descriptive commit messages
✅ Modular, reusable components
✅ Comprehensive documentation

### What We Avoid

❌ Large functions doing multiple things
❌ Commented-out dead code
❌ Inconsistent naming or patterns
❌ Unclear error messages
❌ Unexplained magic numbers or strings
❌ Skipped tests or test TODOs

### AI Readiness Dimensions (Scoring)

This project is evaluated across 8 dimensions:

1. **Architecture** (20/100) - Code organization and modularity
2. **Testing** (15/100) - Test coverage and quality
3. **Dependencies** (12/100) - Dependency management
4. **Conventions** (8/100) - Consistent patterns
5. **Entry Points** (10/100) - Clear main/start locations
6. **Security** (15/100) - Input validation and error handling
7. **Build** (10/100) - Clear build/setup instructions
8. **Documentation** (8/100) - Code and project documentation

### Next Steps

Before making changes:
1. Read relevant source files to understand the existing code
2. Look at existing tests for similar functionality
3. Follow the patterns you see in the codebase
4. Write tests for your changes
5. Run `pytest` to verify nothing breaks
6. Run code quality checks: `ruff check . && mypy .`
7. Format your code: `ruff format .`

---

*Generated by Braxis - keeping AI agents in sync with your code*
