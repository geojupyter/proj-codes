# Minimal CI: data test + linting

Date: 2026-08-14

## Problem

`proj-codes` has no CI. Two gaps:

1. **No verification of the generated data.** `generate.py` produces `proj-codes.json`
   (gitignored, built at publish time) and `proj-codes.csv`. Nothing checks that the
   build actually produced a sane dataset. A partial or degraded PROJ database would
   publish silently.
2. **No linting.** The repo follows no enforced style, and `generate.py` is unchecked
   Python.

Tracked by the upstream issue asking to "test that it functions properly": check the
expected number of rows, and check that WGS 84 is present and identical to expected.

## Goals

- Assert the generated dataset has the expected number of CRS entries.
- Assert `EPSG:4326` (WGS 84) is present and exactly matches the expected record.
- Lint with the tools jupytergis uses, insofar as they are relevant to this repo, at
  the strictest available settings.
- Stay minimal. Add complexity later, only when a need appears.

## Non-goals

- eslint. `index.js` is a single re-export line; the config and dependency cost is not
  yet justified.
- zizmor GitHub Actions auditing.
- Broad per-CRS assertions, snapshot tests of the whole dataset, or a matrix across
  Python/Node versions.
- Fixing `publish.yml` (see Follow-ups).

## Design

### Data test

`test/proj-codes.test.js`, run by the built-in Node test runner (`node --test`). No new
runtime or dev dependencies.

The test imports `../index.js` rather than reading `proj-codes.json` directly. This
covers the actual published surface: if the JSON import attribute export breaks, or the
package's `exports` map regresses, the test fails alongside a genuinely bad
`generate.py`.

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import projCodes from '../index.js';

test('contains the expected number of CRS codes', () => {
  assert.equal(Object.keys(projCodes).length, 6990);
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

`package.json` gains `"test": "node --test"`, replacing the current
`echo "Error: no test specified" && exit 1`. No change to the `files` array is needed —
it lists only `index.js` and `proj-codes.json`, so `test/` is excluded from the published
tarball automatically.

Both expected values were verified locally by running `pixi run python generate.py`
against the pinned `pyproj >=3.7.2,<4`:

- count: `6990` (consistent with `proj-codes.csv`: 6991 lines = 1 header + 6990 rows)
- `EPSG:4326`: the four-field record above

**The count is asserted exactly, not as a floor.** The number is a function of the
installed PROJ database, so a `pyproj` upgrade will fail this test. That is the intended
behavior: the failure prompts a deliberate review of what changed, and the constant is
bumped on purpose. A floor threshold (`>= 6000`) would stay silent if several hundred
codes quietly disappeared.

Because `proj-codes.json` is gitignored, the test requires a build first. CI runs
`pnpm run build` before `pnpm test`.

### Linting

**`.pre-commit-config.yaml`** — the jupytergis hooks that apply here, at the same pinned
revisions:

- `pre-commit/pre-commit-hooks` v6.0.0: `forbid-new-submodules`, `end-of-file-fixer`,
  `check-case-conflict`, `check-added-large-files` (`--maxkb=5000`), `check-json`,
  `check-toml`, `check-yaml` (`--allow-multiple-documents`), `debug-statements`,
  `check-builtin-literals`, `trailing-whitespace` (excluding `proj-codes.csv`)

Two hook arguments are load-bearing, both discovered by running the hooks rather than by
reading jupytergis's config:

- `check-yaml` needs `--allow-multiple-documents` because `pnpm-lock.yaml` is genuinely a
  multi-document YAML file (`---` at lines 1 and 199).
- `trailing-whitespace` must exclude `proj-codes.csv`. `EPSG:10551` is named
  `"DKMSL depth "` — with a trailing space — in the EPSG database. Without the exclusion
  the hook strips it, which both falsifies the published data and creates permanent
  churn: every build re-adds the space, every hook run removes it.
- `astral-sh/ruff-pre-commit` v0.15.20: `ruff` (`--fix --show-fixes
--exit-non-zero-on-fix`) and `ruff-format`

Dropped as inapplicable: `rstcheck` (no `.rst` files), `validate-cff` (no
`CITATION.cff`), `nbstripout` (no notebooks), `requirements-txt-fixer` (no
`requirements.txt`).

Also gives local git hooks for free via `pre-commit install`.

**`pyproject.toml`** (new, minimal) — ruff configuration only:

```toml
[tool.ruff.lint]
select = ["ALL"]
ignore = ["COM812", "D203", "D213"]
```

Per the "start strictest, loosen as needed" preference, jupytergis's ~90 ignores are
dropped. The three that remain are not a loosening — each resolves a conflict internal to
ruff, and removing them produces warnings rather than stricter linting:

- `COM812` — ruff-format warns that this rule conflicts with the formatter.
- `D203` — mutually exclusive with `D211`, which `ALL` also selects.
- `D213` — mutually exclusive with `D212`, which `ALL` also selects.

Beyond these, no rule is ignored until real friction justifies it.

Adding `pyproject.toml` alongside `pixi.toml` is safe: pixi prefers `pixi.toml` when both
are present, so the new file is read only by ruff.

**Prettier** — `.prettierrc` copied verbatim from jupytergis:

```json
{
  "singleQuote": true,
  "trailingComma": "all",
  "arrowParens": "avoid",
  "endOfLine": "auto"
}
```

Run as a pnpm devDependency with a `prettier:check` script, matching how jupytergis
invokes it. It is deliberately _not_ a pre-commit hook: `pre-commit/mirrors-prettier` is
archived and should not be a new dependency.

**`.prettierignore`** is required, covering `node_modules/`, `.pixi/`, `pixi.lock`,
`pnpm-lock.yaml`, `proj-codes.json`, and `proj-codes.csv`. Both lockfiles are YAML, so
without this prettier rewrites them — and `pixi.lock` is additionally marked `-diff
linguist-generated=true` in `.gitattributes`. `proj-codes.json` is a multi-megabyte
generated file present locally after any build.

### CI workflow

One new file, `.github/workflows/ci.yml`. Triggers on push to `main` and on
`pull_request`. Top-level `permissions: {}`, and every checkout uses
`persist-credentials: false`, following jupytergis's hardening convention.

Two jobs, both on `ubuntu-latest`:

| job    | steps                                                                                                      |
| ------ | ---------------------------------------------------------------------------------------------------------- |
| `lint` | checkout → `pre-commit/action` → pnpm setup → `pnpm install --frozen-lockfile` → `pnpm run prettier:check` |
| `test` | checkout → `setup-pixi` → `pixi install` → `pixi run pnpm run build` → `pixi run pnpm test`                |

The `test` job needs no `pnpm install`: the build is `python generate.py`, and
`node --test` requires no dependencies. pixi already provides Python, pyproj, Node, and
pnpm.

The jobs are independent and run in parallel. They live in one file because there are
only two of them; splitting per concern (as jupytergis does) is a reasonable later step
if the count grows.

## Expected first-run consequences

These are anticipated, not surprises:

- `select = ["ALL"]` flags exactly 9 findings in `generate.py`, all measured rather than
  predicted: `D100`/`D103` missing docstrings, `ANN201` missing return annotations (×2),
  `I001` unsorted imports, `PTH123` `open()` → `Path.open()` (×2), and `W292` no trailing
  newline. `INP001` does **not** fire on a root-level script. Fix all 9 rather than adding
  ignores.
- `end-of-file-fixer` and `trailing-whitespace` will modify files that currently lack a
  trailing newline (`generate.py` is one). Expect a small mechanical formatting change
  before CI is first green.
- Prettier will reformat exactly three existing files: `index.js` (the one-line export
  wraps to four lines), `README.md` (blank line after a heading, trailing whitespace and
  newline, and `[-122.2730, ...]` → `[-122.273, ...]` inside a JS code fence), and
  `publish.yml` (double-quoted YAML strings become single-quoted). `package.json` is
  already clean.

## Testing the change itself

Verify locally before pushing:

1. `pre-commit run --all-files` — passes (after the fixes above).
2. `pnpm run prettier:check` — passes.
3. `pixi run pnpm run build && pixi run pnpm test` — 2 tests pass.
4. Deliberately break it: change the expected count to `6989` and confirm the test
   fails. A test that has never failed has not been tested.

Then confirm both CI jobs pass on the pull request.

## Follow-ups (not in this change)

- `publish.yml` line 22 runs `pixi run pnpm ci`, which is not a valid pnpm command
  (intended: `pnpm install --frozen-lockfile`).
- `publish.yml` line 24 has `pixi run pnpm test` commented out. Once tests exist,
  uncommenting it prevents publishing a bad build.
- eslint, if `index.js` grows.
- zizmor GitHub Actions security auditing.
- Loosening `select = ["ALL"]` with a targeted ignore list once the noisy rules are
  known.

## Local environment note

pixi 0.65.0 cannot read the committed `pixi.lock` format and silently regenerates it on
`pixi install`. Run `pixi self-update` before working locally, or check `git status`
afterward and restore the file.
