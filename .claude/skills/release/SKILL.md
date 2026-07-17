---
name: release
description: Use when cutting a release of the aegis-stack package. Covers the version-bump file set, the changelog cut, the three release gates, TestPyPI rc verification, and the tag-push mechanics that trigger the publish workflow.
---

# Release

Cuts a new version of the `aegis-stack` package itself (not a generated
project). Bumps the version string, cuts the changelog, runs three
independent gates, verifies an rc on TestPyPI, then tags for a real PyPI
publish and verifies again against the published package.

## When to use

Use when the task is "release a new version of aegis-stack" (bump the
version, publish to PyPI, cut a GitHub release).

Do NOT use for ordinary feature or fix work with no release attached, and do
NOT use for generated-project releases (those follow the target project's own
process, not this one).

## Files that change

Version bump (all five must be touched together; verify each file actually
contains the version string before editing it, since it is easy to assume a
file participates when it does not):

- `aegis/__init__.py`: `__version__ = "X.Y.Z"`.
- `pyproject.toml`: `version = "X.Y.Z"` under `[project]`.
- `copier.yml` (repo root): `_version: "X.Y.Z"`.
- `CHANGELOG.md`: the version also appears here as the new dated section
  heading (see the changelog cut step in Procedure).
- `uv.lock`: the `[[package]] name = "aegis-stack"` entry's own `version =
  "X.Y.Z"` field. This one is not hand-edited; the pre-commit `ty` hook
  rewrites it, so stage it in a second commit pass (see Procedure).

Every other match of the old version string in the repo is test data or an
unrelated coincidence; leave it alone.

Gate-relevant files (read, not edited, unless a gate fails):

- `Makefile` (repo root): `check`, `test-stacks-full`, `test-stacks-quick`
  targets.
- `tests/test_runtime_dependencies.py`: guards that `ruff` (and any other
  binary the updater shells out to at runtime) stays in
  `[project].dependencies`, not only a dev extra.
- `.github/workflows/release.yml`: the tag-triggered publish workflow (`v*.*.*-rc*`
  routes to TestPyPI, bare `v*.*.*` routes to PyPI); read this if tagging
  behavior is ever in question.

## Procedure

1. Confirm the target version and the previous released tag.
2. Bump the version string in all five files listed above. Open each file and
   grep for the old version string to confirm the edit landed; do not assume
   a file needs changing just because a prior release touched it.
3. Cut the changelog in `CHANGELOG.md`: identify which items under
   `[Unreleased]` actually shipped in this release (cross-check with `git log
   --first-parent <prev-tag>..HEAD` so nothing merged after the branch point
   is mis-attributed), rename that content into a new dated `[X.Y.Z] -
   YYYY-MM-DD` section, draft the section body from the PR history for this
   range, and leave a fresh, empty `## [Unreleased]` heading above it. This
   step is required and routinely forgotten; do not skip it.
4. Commit the version bump and changelog cut. If the pre-commit `ty` hook
   rewrites `uv.lock` during this commit, `git add uv.lock` and commit again
   so the lockfile's own version field matches.
5. Run the three gates (see Gates). Fix anything red before proceeding.
6. Tag the release commit as a release candidate: `git tag vX.Y.Z-rcN && git
   push origin vX.Y.Z-rcN`. This is what actually triggers the publish
   workflow; merging the version-bump PR alone publishes nothing.
7. Once the workflow is green, verify the rc via the TestPyPI upgrade-path
   recipe (see Gates, gate 3) run against the published rc rather than a
   local wheel.
8. If the rc verification finds a problem, fix it, bump to the next rc number
   (never reuse or re-tag a burned rc, see Pitfalls), and repeat from step 5.
9. Once an rc is clean, bump the version string from `X.Y.ZrcN` to the bare
   `X.Y.Z` in `aegis/__init__.py`, `pyproject.toml`, and `copier.yml` (the
   changelog section heading already says `X.Y.Z` from the cut; refresh
   `uv.lock` via `uv lock`), commit, and tag THAT
   commit: `git tag vX.Y.Z && git push origin vX.Y.Z`. Do not tag the rc
   commit itself: the publish workflow builds whatever version
   `pyproject.toml` carries, so tagging the rc commit as `vX.Y.Z` would
   publish an `X.Y.ZrcN` wheel under a final tag. This publishes to PyPI
   and drafts a GitHub release.
10. Post-publish, repeat the TestPyPI-style upgrade recipe once more against
    the now-published PyPI package (init the previous release, `update` to
    the new version) and grep the resulting project for conflict markers to
    confirm a clean upgrade path for real users.

## Gates

All three are required; each independently catches a class of failure the
others miss.

- `make check`: framework lint, typecheck, and pytest. Catches a
  constant/config change made without updating the test that asserts on it.
- `make test-stacks-full`: the full stack generation matrix (generate,
  install, lint, typecheck, pytest per stack combination). Catches template
  drift on stacks that no single local test generates on its own.
  `make test-stacks-quick` (base/everything/insights subset) is for iteration
  only; it never substitutes for the full run before a release.
- Production-mode wheel test: the repo's own test venv installs
  `--all-extras`, so a dependency that lives only in the dev extra looks fine
  locally but is missing from a real `uvx`/`pip` install. Before tagging,
  run `uv build`, then `uvx --from ./dist/aegis_stack-<ver>-py3-none-any.whl
  aegis update -y -p <fresh prev-release project> -t <repo> --to-version
  HEAD`, and assert zero conflict markers and a completed post-gen run.
  Confirm `tests/test_runtime_dependencies.py` exists and passes; it guards
  `ruff` specifically for this exact failure mode.

TestPyPI upgrade-path verification recipe (used in Procedure steps 7 and 10):

```bash
uvx --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    --index-strategy unsafe-best-match \
    aegis-stack@<prev-version> init test-upgrade-project --no-interactive -y

cd test-upgrade-project
uvx --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    --index-strategy unsafe-best-match \
    aegis-stack@<rc-version> update -y
```

## Pitfalls

- This procedure describes `git add`, `git commit`, `git tag`, and `git push`
  as the steps that must happen, but per the repo git policy the agent runs no
  git command without explicit user approval; stop and ask before each, the
  same as any other workflow.
- A burned rc version string (any rc that ever reached TestPyPI) can never be
  reused, even after deletion: PyPI/TestPyPI reject the filename permanently,
  and re-running the same tag replays the same HTTP 400. Always increment to
  the next rc number instead of re-tagging.
- Never pass `skip-existing` to the publish step: TestPyPI would then keep
  serving the stale build under that filename instead of failing loudly,
  and the smoke test would silently verify the wrong artifact.
- The release workflow triggers only on a tag push, not on a merge. Merging
  the version-bump PR into main publishes nothing; the actual publish and
  GitHub-release steps only run after `git push origin vX.Y.Z[-rcN]` against
  the merged commit.
- A dependency that lives only in the dev extra (`--all-extras` in the repo's
  own test venv) passes every local and CI test yet is silently absent from a
  real `uvx`/`pip` install; this is exactly what the production-mode wheel
  test gate exists to catch, so do not skip it even when the other two gates
  are green.
- `UV_PYTHON=3.11` is tool-only: it belongs in the release/CI/canary jobs
  that build and test this CLI, and must never be set globally in the stack
  matrix, because generated projects require Python >= 3.13. Pair it with
  `UV_LINK_MODE=copy` to avoid broken cache hardlinks.
- The changelog cut is easy to forget entirely since nothing fails loudly if
  it is skipped; verify the dated section exists and `[Unreleased]` is empty
  again before tagging, not just that the version files were bumped.
