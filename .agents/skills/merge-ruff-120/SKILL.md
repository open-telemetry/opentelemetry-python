---
name: merge-ruff-120
description: "Reformat code on a feature branch and merge main cleanly after the Ruff line-length increase from 79 to 120 (merged August 7, 2026, commit 0110bb1d273dbe848312d429326b844da9e86d93, PR #5514). Relevant for branches created before August 2026."
---

# Merging main and Reformatting Code (Ruff 120 Line Length)

## Overview

In PR #5514 (merged on August 7, 2026, commit `0110bb1d273dbe848312d429326b844da9e86d93`), OpenTelemetry Python updated its Ruff configuration in `pyproject.toml` to increase `line-length` from 79 to 120 characters and reformatted the entire codebase.

Feature branches created prior to August 7, 2026 (before this commit) will encounter extensive merge conflicts if merged directly. This skill instructs an agent on how to detect this situation and perform a clean multi-step merge without formatting conflict markers.

## Detection: When to Use This Skill

An agent can test whether a branch needs this reformatting workflow:

```bash
# Returns non-zero (exit code 1) if the branch was created BEFORE the Ruff 120 change (August 7, 2026):
git merge-base --is-ancestor 0110bb1d273dbe848312d429326b844da9e86d93 HEAD
```

If the commit is **not** an ancestor of `HEAD`, follow the workflow below.

---

## Workflow

Follow these steps on the contributor's feature branch:

### Step 1: Identify upstream remote, ensure workspace is clean & sync dependencies

First, inspect configured remotes to identify which remote points to the upstream `open-telemetry/opentelemetry-python` repository (typically `upstream` or `origin`):

```bash
git remote -v
```

> **Note**: In a fork-based workflow, `upstream` typically points to `open-telemetry/opentelemetry-python` and `origin` points to the contributor's fork. In direct clones, `origin` points to `open-telemetry/opentelemetry-python`. In the steps below, replace `<remote>` with the name of the remote pointing to `open-telemetry/opentelemetry-python` (e.g., `upstream` or `origin`).

Fetch latest changes and sync dependencies:

```bash
uv sync --frozen --all-packages
git fetch <remote> main
```

### Step 2: Merge the commit before the line-length change

Merge all changes up to the commit immediately *before* the Ruff 120 reformat:

```bash
git merge 0110bb1d273dbe848312d429326b844da9e86d93^
```

Because both sides are still 79-column code, there are zero formatting conflicts. Resolve any real semantic conflicts if present, then commit the merge.

### Step 3: Merge the reformatting commit with `-X ours --no-commit`

Merge the reformat commit, automatically choosing the branch's code on any formatting conflicts and pausing before creating the merge commit:

```bash
git merge -X ours --no-commit 0110bb1d273dbe848312d429326b844da9e86d93
```

### Step 4: Format and lint the branch to 120 columns

Ensure `pyproject.toml` has `line-length = 120` (under `[tool.ruff]`). Use file editing tools or Python to avoid macOS vs Linux `sed -i` incompatibilities:

```bash
python3 -c "import pathlib; p = pathlib.Path('pyproject.toml'); p.write_text(p.read_text().replace('line-length = 79', 'line-length = 120'))"
uv run ruff format
uv run ruff check --fix
```

### Step 5: Finalize the merge commit

```bash
git commit -am "chore: merge Ruff 120 reformat and format branch"
```

### Step 6: Catch up with latest `main`

Merge the rest of `main` from the upstream remote:

```bash
git merge <remote>/main
```
