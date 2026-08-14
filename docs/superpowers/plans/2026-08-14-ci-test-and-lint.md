# Minimal CI: Data Test + Lint — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a GitHub Actions CI that asserts the generated CRS dataset is correct (exact code count, exact `EPSG:4326` record) and that Python and JS/JSON/YAML/Markdown are lint-clean under the strictest settings.

**Architecture:** Three independent concerns, four tasks. The data test uses Node's built-in test runner against `index.js` (the published surface), so it needs no new runtime dependency but does need `pnpm run build` first, because `proj-codes.json` is gitignored. Linting is split by toolchain: `pre-commit` drives ruff plus generic file hooks; prettier runs as a pnpm script, matching how jupytergis invokes it. One workflow file wires it together as two parallel jobs.

**Tech Stack:** `node:test` (Node 24), pre-commit 4.x, ruff 0.15.20, prettier 3.9.6, pixi (Python 3.14 + pyproj + Node + pnpm), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-14-ci-test-and-lint-design.md`

## Global Constraints

- Branch: `add-ci-tests-and-lint`. Do not commit to `main`.
- Expected CRS count is **exactly** `6990` — asserted with `assert.equal`, never a `>=` floor. Verified locally against the pinned `pyproj >=3.7.2,<4`.
- Expected `EPSG:4326` record, verbatim: `{ auth_name: 'EPSG', code: '4326', name: 'WGS 84', proj4string: '+proj=longlat +datum=WGS84 +no_defs +type=crs' }`.
- Pinned versions: `pre-commit/pre-commit-hooks` **v6.0.0**, `astral-sh/ruff-pre-commit` **v0.15.20**, prettier **^3.9.6**. These match jupytergis where the hook is shared.
- Ruff config is `select = ["ALL"]` with exactly three ignores: `COM812`, `D203`, `D213`. See Task 2 for why these are not a loosening.
- GitHub Actions are referenced by **tag**, not SHA, matching the existing style in `.github/workflows/publish.yml`. (SHA pinning is a deliberate follow-up.)
- Every `actions/checkout` uses `persist-credentials: false`. Every workflow declares top-level `permissions: {}`.
- All new YAML/JS/JSON/Markdown must be prettier-clean under the config added in Task 3 — notably **single-quoted** YAML strings.
- Do not modify `.github/workflows/publish.yml` except for the prettier reformat in Task 3. Its two real bugs are follow-ups, not this change.
- Do not add eslint or zizmor.

## Pre-flight

- [ ] **Confirm you are on the right branch**

```bash
git branch --show-current   # expected: add-ci-tests-and-lint
git status --short          # expected: clean
```

If `pixi.lock` ever shows as modified during this work, you have an older pixi than the
lockfile format. Run `git restore pixi.lock` and do not commit that churn.

---

### Task 1: Data test

Delivers the actual ask from the upstream issue. Independently verifiable before any lint work exists.

**Files:**

- Create: `test/proj-codes.test.js`
- Modify: `package.json` (the `scripts.test` line, currently `echo "Error: no test specified" && exit 1`)

**Interfaces:**

- Consumes: the default export of `index.js` — an object keyed `"AUTHORITY:CODE"`, each value `{ auth_name, code, name, proj4string }`, all strings.
- Produces: `pnpm test` → runs `node --test`. Task 4's `test` job calls this.

- [ ] **Step 1: Build the dataset so the test has something to import**

`proj-codes.json` is gitignored and generated. Without this step the test fails on a
missing module, not on a bad assertion.

```bash
pixi install
pixi run pnpm run build
```

Expected: `proj-codes.json` appears in the repo root. A `UserWarning` from pyproj about
losing projection information when converting to a PROJ string is normal and expected —
`generate.py` deliberately converts to proj4 for proj4js consumers.

- [ ] **Step 2: Write the failing test**

Create `test/proj-codes.test.js`:

```js
import assert from 'node:assert/strict';
import { test } from 'node:test';

import projCodes from '../index.js';

test('contains the expected number of CRS codes', () => {
  assert.equal(Object.keys(projCodes).length, 6989);
});

test('EPSG:4326 (WGS 84) matches expected', () => {
  assert.deepEqual(projCodes['EPSG:4326'], {
    auth_name: 'EPSG',
    code: '4326',
    name: 'WGS 84',
    proj4string: '+proj=longlat +datum=WGS84 +no_defs +type=crs',
  });
});
```

Note the count is **deliberately wrong** (`6989`) for now. A test that has never failed
has not been tested — Step 4 corrects it.

- [ ] **Step 3: Wire up the test script**

In `package.json`, replace the `test` script:

```json
"scripts": {
  "build": "python generate.py",
  "test": "node --test"
},
```

Leave the `files` array alone — it lists only `index.js` and `proj-codes.json`, so
`test/` is already excluded from the published tarball.

- [ ] **Step 4: Run the test and confirm it fails for the right reason**

```bash
pixi run pnpm test
```

Expected: `pass 1`, `fail 1`. The failure is
`contains the expected number of CRS codes`, with an
`AssertionError` reporting `6990 !== 6989`. The `EPSG:4326` test passes.

If instead **both** tests fail, or the run errors with `Cannot find module`, stop — the
build in Step 1 did not produce `proj-codes.json`.

- [ ] **Step 5: Correct the expected count**

Change `6989` to `6990` in `test/proj-codes.test.js`:

```js
assert.equal(Object.keys(projCodes).length, 6990);
```

- [ ] **Step 6: Run the tests and confirm both pass**

```bash
pixi run pnpm test
```

Expected:

```
✔ contains the expected number of CRS codes
✔ EPSG:4326 (WGS 84) matches expected
ℹ tests 2
ℹ pass 2
ℹ fail 0
```

- [ ] **Step 7: Commit**

```bash
git add test/proj-codes.test.js package.json
git commit -m "Add tests for generated CRS dataset

Asserts the exact CRS code count and the exact EPSG:4326 record. The
count is exact rather than a floor so that a PROJ database change fails
loudly and gets reviewed deliberately.

Tests import index.js rather than the JSON directly, so a broken JSON
import export fails here too."
```

---

### Task 2: pre-commit with strict ruff

**Files:**

- Create: `.pre-commit-config.yaml`
- Create: `pyproject.toml`
- Modify: `generate.py` (all 10 ruff findings)

**Interfaces:**

- Consumes: nothing from Task 1.
- Produces: `pre-commit run --all-files` as the Python/generic lint entry point. Task 4's `lint` job invokes it via `pre-commit/action`.

- [ ] **Step 1: Add the pre-commit config**

Create `.pre-commit-config.yaml`. These are jupytergis's hooks at jupytergis's pinned
revisions, minus the four that have nothing to act on here (`rstcheck` — no `.rst`
files; `validate-cff` — no `CITATION.cff`; `nbstripout` — no notebooks;
`requirements-txt-fixer` — no `requirements.txt`).

```yaml
ci:
  autoupdate_schedule: quarterly
  autofix_prs: false

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: forbid-new-submodules
      - id: end-of-file-fixer
      - id: check-case-conflict
      - id: check-added-large-files
        args: ['--maxkb=5000']
      - id: check-json
      - id: check-toml
      - id: check-yaml
        args: ['--allow-multiple-documents']
      - id: debug-statements
      - id: check-builtin-literals
      - id: trailing-whitespace
        exclude: ^proj-codes\.csv$

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.20
    hooks:
      - id: ruff
        args: ['--fix', '--show-fixes', '--exit-non-zero-on-fix']
      - id: ruff-format
```

- [ ] **Step 2: Add the ruff config**

Create `pyproject.toml`. This file exists only for ruff — pixi prefers `pixi.toml` when
both manifests are present, so it does not affect the environment.

```toml
[tool.ruff.lint]
select = ["ALL"]

# The only ignores. Each resolves a conflict inside ruff itself rather than
# relaxing a check, so removing them produces warnings, not stricter linting:
#   COM812 - ruff-format warns that this rule conflicts with the formatter
#   D203   - mutually exclusive with D211, which is also in ALL
#   D213   - mutually exclusive with D212, which is also in ALL
ignore = ["COM812", "D203", "D213"]
```

- [ ] **Step 3: See the failures before fixing them**

```bash
uvx ruff@0.15.20 check .
```

Expected: exactly 9 findings, all in `generate.py` —

```
generate.py:1:1:   D100   Missing docstring in public module
generate.py:1:1:   I001   Import block is un-sorted or un-formatted
generate.py:7:5:   ANN201 Missing return type annotation for public function `build_crs_dict`
generate.py:7:5:   D103   Missing docstring in public function
generate.py:29:5:  ANN201 Missing return type annotation for public function `main`
generate.py:29:5:  D103   Missing docstring in public function
generate.py:32:10: PTH123 `open()` should be replaced by `Path.open()`
generate.py:35:10: PTH123 `open()` should be replaced by `Path.open()`
generate.py:43:11: W292 No newline at end of file
```

`ruff` should print no warnings. If you see
`D203 and D211 are incompatible` or a `COM812 may cause conflicts with the formatter`
warning, `pyproject.toml` is not being picked up — check you are running from the repo
root.

Note what is **not** flagged: `INP001` (implicit-namespace-package) does not fire on a
root-level script. Do not add an ignore for it.

- [ ] **Step 4: Commit the configs before the fixes**

This intentionally leaves the branch briefly lint-failing, so the diff that _adds_
tooling stays readable separately from the diff that _reacts_ to it.

```bash
git add .pre-commit-config.yaml pyproject.toml
git commit -m "Add pre-commit with strict ruff config

Mirrors the jupytergis hook set and pins, minus hooks with nothing to
act on in this repo. Ruff runs select=[\"ALL\"]; the three ignores each
resolve a conflict internal to ruff rather than relaxing a check."
```

- [ ] **Step 5: Fix all 10 findings**

Replace the entire contents of `generate.py` with this. It is behavior-preserving:
`Path.open()` is equivalent to `open()` here, and the added annotations, docstrings,
import sort, trailing comma, and trailing newline change nothing at runtime.

```python
"""Generate proj-codes.json and proj-codes.csv from the PROJ CRS database."""

import csv
import json
from pathlib import Path

from pyproj import CRS
from pyproj.database import query_crs_info
from pyproj.exceptions import CRSError


def build_crs_dict() -> dict[str, dict[str, str]]:
    """Map "AUTHORITY:CODE" to CRS metadata for every proj4-expressible EPSG CRS."""
    crs_list = query_crs_info(
        auth_name="EPSG",
        pj_types=None,
        allow_deprecated=False,
    )

    crs_dict = {}
    for crs in crs_list:
        try:
            proj4string = CRS.from_authority(crs.auth_name, crs.code).to_proj4()
        except CRSError:
            continue  # skips codes that can't be used in proj4js
        crs_dict[f"{crs.auth_name}:{crs.code}"] = {
            "auth_name": crs.auth_name,
            "code": crs.code,
            "name": crs.name,
            "proj4string": proj4string,
        }
    return crs_dict


def main() -> None:
    """Write the CRS dictionary to proj-codes.json and proj-codes.csv."""
    crs_dict = build_crs_dict()

    with Path("proj-codes.json").open("w") as f:
        json.dump(crs_dict, f)

    with Path("proj-codes.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["auth_name", "code", "name"])
        for crs in crs_dict.values():
            writer.writerow([crs["auth_name"], crs["code"], crs["name"]])


if __name__ == "__main__":
    main()
```

Docstrings use `"""..."""` with embedded `"AUTHORITY:CODE"` quotes — this is valid and
ruff-format leaves it alone. Do not "fix" it to single quotes.

- [ ] **Step 6: Run pre-commit and confirm it passes**

```bash
pre-commit install
pre-commit run --all-files
```

Expected: every hook `Passed`, except that `end-of-file-fixer` and/or
`trailing-whitespace` may report `Failed` on the **first** run while fixing files that
lack a trailing newline (`README.md` is one). That is the hook doing its job. Re-run:

```bash
pre-commit run --all-files
```

Expected on the second run: all hooks `Passed`, no files modified.

- [ ] **Step 7: Confirm the refactor did not change the output**

This is the step that proves Step 5 was behavior-preserving. Regenerate and diff the
committed CSV — it must be byte-identical.

```bash
pixi run pnpm run build
git diff --stat proj-codes.csv
pixi run pnpm test
```

Expected: `git diff --stat` prints **nothing** (no change to `proj-codes.csv`), and both
tests still pass. If the CSV changed, the refactor broke something — stop and diff
`generate.py` against the block in Step 5.

- [ ] **Step 8: Commit the fixes**

```bash
git add generate.py README.md
git status --short   # confirm nothing unexpected got modified by the hooks
git commit -m "Satisfy strict ruff in generate.py

Adds module and function docstrings, return type annotations, sorted
imports, pathlib-based file opens, and a trailing newline. Verified
behavior-preserving: regenerated proj-codes.csv is byte-identical."
```

---

### Task 3: Prettier

**Files:**

- Create: `.prettierrc`
- Create: `.prettierignore`
- Modify: `package.json` (add `devDependencies` and two scripts)
- Modify: `pnpm-lock.yaml` (regenerated by `pnpm install`)
- Modify: `index.js`, `README.md`, `.github/workflows/publish.yml` (reformatted)

**Interfaces:**

- Consumes: `scripts.test` from Task 1 (do not clobber it when editing `scripts`).
- Produces: `pnpm run prettier:check` as the JS/JSON/YAML/Markdown lint entry point. Task 4's `lint` job calls this.

- [ ] **Step 1: Add the prettier config**

Create `.prettierrc`, copied verbatim from jupytergis:

```json
{
  "singleQuote": true,
  "trailingComma": "all",
  "arrowParens": "avoid",
  "endOfLine": "auto"
}
```

- [ ] **Step 2: Add the ignore file**

Create `.prettierignore`. This is **required**, not optional: `pixi.lock` and
`pnpm-lock.yaml` are YAML, so prettier would happily rewrite both. `pixi.lock` is
additionally marked `-diff linguist-generated=true` in `.gitattributes` and must not be
reformatted. `proj-codes.json` is a multi-megabyte generated file that exists locally
after any build.

```
node_modules/
.pixi/
pixi.lock
pnpm-lock.yaml
proj-codes.json
proj-codes.csv
```

- [ ] **Step 3: Add prettier as a devDependency and add the scripts**

In `package.json`, extend `scripts` and add a `devDependencies` block. Keep the `test`
script from Task 1:

```json
  "scripts": {
    "build": "python generate.py",
    "test": "node --test",
    "prettier": "prettier --write .",
    "prettier:check": "prettier --check ."
  },
  "devDependencies": {
    "prettier": "^3.9.6"
  },
```

- [ ] **Step 4: Install, and commit the updated lockfile**

CI runs `pnpm install --frozen-lockfile`, which **fails** if `pnpm-lock.yaml` does not
already contain prettier. The lockfile must be regenerated and committed.

```bash
pixi run pnpm install
git diff --stat pnpm-lock.yaml   # expected: shows prettier added
```

- [ ] **Step 5: See what prettier will change**

```bash
pixi run pnpm run prettier:check
```

Expected: `Code style issues found in 3 files` — `index.js`, `README.md`, and
`.github/workflows/publish.yml`. `package.json` is already clean.

The three diffs, so none of them surprise you:

- `index.js` — the single-line export is wrapped across four lines.
- `README.md` — a blank line is inserted after the `## About` heading, trailing
  whitespace is stripped, a trailing newline is added, and inside the JS code fence
  `[-122.2730, 37.8715]` becomes `[-122.273, 37.8715]` (prettier formats embedded code
  blocks; the trailing zero is not significant).
- `publish.yml` — every double-quoted YAML string becomes single-quoted.

If you would rather not have prettier touch YAML at all, add `.github/` to
`.prettierignore` instead — but then Task 4's `ci.yml` also goes unchecked. The plan
assumes the reformat.

- [ ] **Step 6: Apply the reformat**

```bash
pixi run pnpm run prettier
pixi run pnpm run prettier:check
```

Expected from the second command: `All matched files use Prettier code style!`

- [ ] **Step 7: Confirm nothing broke**

`index.js` was rewritten, so re-run the tests — they import through it.

```bash
pixi run pnpm test
pre-commit run --all-files
```

Expected: 2 tests pass, all pre-commit hooks pass.

- [ ] **Step 8: Commit as two commits**

Tooling first, mechanical churn second, so the reformat noise does not bury the config.

```bash
git add .prettierrc .prettierignore package.json pnpm-lock.yaml
git commit -m "Add prettier with the jupytergis config

Runs as a pnpm script rather than a pre-commit hook, since
pre-commit/mirrors-prettier is archived. Lockfiles and generated files
are ignored so prettier cannot rewrite them."

git add index.js README.md .github/workflows/publish.yml
git commit -m "Apply prettier formatting

Mechanical only, no behavior change."
```

---

### Task 4: CI workflow

**Files:**

- Create: `.github/workflows/ci.yml`

**Interfaces:**

- Consumes: `pnpm test` (Task 1), `pre-commit run --all-files` via `pre-commit/action` (Task 2), `pnpm run prettier:check` (Task 3).
- Produces: two required checks on pull requests, `lint` and `test`.

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/ci.yml`. Strings are single-quoted because Task 3's prettier
config checks this file.

```yaml
name: 'CI'

on:
  push:
    branches: 'main'
  pull_request:
    branches: '*'

permissions: {}

jobs:
  lint:
    name: 'pre-commit & prettier'
    runs-on: 'ubuntu-latest'
    steps:
      - uses: 'actions/checkout@v7'
        with:
          persist-credentials: false

      - uses: 'actions/setup-python@v6'
        with:
          python-version: '3.14'

      - uses: 'pre-commit/action@v3.0.1'

      - uses: 'actions/setup-node@v6'
        with:
          node-version: '24'

      - uses: 'pnpm/action-setup@v6'
        with:
          version: '11.20.0'

      - run: 'pnpm install --frozen-lockfile'

      - run: 'pnpm run prettier:check'

  test:
    name: 'node --test'
    runs-on: 'ubuntu-latest'
    steps:
      - uses: 'actions/checkout@v7'
        with:
          persist-credentials: false

      - uses: 'prefix-dev/setup-pixi@v0.8.8'

      - run: 'pixi install'

      - run: 'pixi run pnpm run build'

      - run: 'pixi run pnpm test'
```

Three deliberate choices:

- `pnpm/action-setup` gets an explicit `version` because this repo declares pnpm under
  `devEngines.packageManager`, not the `packageManager` field the action reads.
- The `test` job runs no `pnpm install` — the build is `python generate.py` and
  `node --test` needs no dependencies. pixi supplies Python, pyproj, Node, and pnpm.
- `setup-pixi@v0.8.8` matches the pin already in `publish.yml`. Keep the two files
  consistent.

- [ ] **Step 2: Confirm the workflow is itself lint-clean**

The new file is YAML, so both toolchains check it.

```bash
pixi run pnpm run prettier:check
pre-commit run --all-files
```

Expected: both clean. If prettier rewrites `ci.yml`, you used double quotes — accept its
version.

- [ ] **Step 3: Full local dress rehearsal**

Run everything CI will run, in CI's order, before pushing.

```bash
pre-commit run --all-files
pixi run pnpm install --frozen-lockfile
pixi run pnpm run prettier:check
pixi run pnpm run build
pixi run pnpm test
```

Expected: all five succeed. `--frozen-lockfile` succeeding here is what proves Task 3
Step 4's lockfile commit was complete.

- [ ] **Step 4: Commit and push**

```bash
git add .github/workflows/ci.yml
git commit -m "Add CI workflow for tests and linting

Two parallel jobs: pre-commit plus prettier for linting, and a pixi
build followed by node --test for the generated dataset."
git push -u origin add-ci-tests-and-lint
```

- [ ] **Step 5: Verify CI actually passes on the PR**

Local success is not CI success — the runner has a different PROJ database build, which
is exactly what the exact-count assertion is there to catch.

```bash
gh pr create --fill
gh pr checks --watch
```

Expected: both `lint` and `test` pass.

If `test` fails on the code count, do not reflexively edit the number to match. Compare
the runner's `pyproj`/PROJ version against the local one first and decide whether the
difference is legitimate — that judgment call is the entire reason the assertion is
exact.

---

## Verification summary

The change is done when all of these hold:

| Check                          | Command                                                     | Expected                    |
| ------------------------------ | ----------------------------------------------------------- | --------------------------- |
| Tests pass                     | `pixi run pnpm test`                                        | 2 passed, 0 failed          |
| Test actually fails when wrong | temporarily set count to `6989`                             | 1 passed, 1 failed          |
| Refactor preserved output      | `pixi run pnpm run build && git diff --stat proj-codes.csv` | no diff                     |
| Python lint                    | `pre-commit run --all-files`                                | all hooks pass              |
| JS/YAML/MD format              | `pixi run pnpm run prettier:check`                          | all files clean             |
| Lockfile complete              | `pixi run pnpm install --frozen-lockfile`                   | succeeds                    |
| CI green                       | `gh pr checks`                                              | `lint` and `test` both pass |

## Follow-ups (explicitly not in this change)

- `.github/workflows/publish.yml` line 22 runs `pixi run pnpm ci`, which is not a valid
  pnpm command. Intended: `pnpm install --frozen-lockfile`.
- `.github/workflows/publish.yml` line 24 has `pixi run pnpm test` commented out. Now
  that tests exist, uncommenting it stops a bad build from publishing.
- Pin GitHub Actions by commit SHA rather than tag.
- eslint, if `index.js` grows beyond one export.
- zizmor GitHub Actions security auditing.
- Revisit `select = ["ALL"]` once real-world friction identifies rules worth ignoring.
