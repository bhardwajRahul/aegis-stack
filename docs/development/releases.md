# Release Process

This guide covers the automated release process for Aegis Stack, including TestPyPI pre-flight testing and production PyPI publishing.

## Overview

Aegis Stack uses **tag-based automated releases** with PyPI Trusted Publishing:

- **Pre-release tags** (`v*.*.*-rc*`) → Automatically deploy to **TestPyPI** for testing
- **Production tags** (`v*.*.*`) → Automatically deploy to **production PyPI**

All you do is create and push tags - the rest is automated!

## Quick Start

### Release a New Version

```bash
# 1. Update version in pyproject.toml to "0.2.0rc1"
# 2. Commit the version change
git add pyproject.toml
git commit -m "Prepare v0.2.0-rc1"

# 3. Create and push release candidate tag
git tag v0.2.0-rc1
git push origin main --tags

# 4. Wait for GitHub Actions to deploy to TestPyPI (watch Actions tab)

# 5. Test the TestPyPI release
uvx --index-url https://test.pypi.org/simple/ aegis-stack --version
uvx --index-url https://test.pypi.org/simple/ aegis-stack init test-validation --no-interactive

# 6. If tests pass, update version to "0.2.0" and create production tag
git add pyproject.toml
git commit -m "Release v0.2.0"
git tag v0.2.0
git push origin main --tags

# 7. GitHub Actions automatically publishes to production PyPI!
```

## Detailed Release Process

### 1. Prepare Release Candidate

**Update version in `pyproject.toml`:**
```toml
[project]
name = "aegis-stack"
version = "0.2.0rc1"  # Note: rc1, rc2, etc. for release candidates
```

**Commit and tag:**
```bash
git add pyproject.toml
git commit -m "Prepare v0.2.0-rc1"
git tag v0.2.0-rc1
git push origin main --tags
```

**What happens automatically:**
1. GitHub Actions workflow triggers on `v*.*.*-rc*` tag
2. Runs `make check` (lint + typecheck + test)
3. Builds package with `uv build`
4. Publishes to **test.pypi.org** using Trusted Publishing
5. Creates GitHub Pre-release with testing instructions

### 2. Test from TestPyPI

**Wait for deployment** - Check the [Actions tab](https://github.com/lbedner/aegis-stack/actions) for workflow completion.

**Test installation and basic functionality:**
```bash
# Test version command
uvx --index-url https://test.pypi.org/simple/ aegis-stack --version
# Should output: aegis-stack, version 0.2.0rc1

# Test project generation
uvx --index-url https://test.pypi.org/simple/ aegis-stack init test-validation --no-interactive

# Validate generated project
cd test-validation
make check  # Should pass all tests

# Test with components
cd ..
uvx --index-url https://test.pypi.org/simple/ aegis-stack init test-with-scheduler --components scheduler --no-interactive
cd test-with-scheduler
make check

# Clean up
cd ..
rm -rf test-validation test-with-scheduler
```

**Testing checklist:**
- ✅ `aegis-stack --version` works
- ✅ `aegis init` generates project successfully
- ✅ Generated project passes `make check`
- ✅ Components work correctly
- ✅ CLI entry point is functional
- ✅ No import errors or missing dependencies

### 3. Handle Test Results

**If tests pass** → Proceed to production release (Step 4)

**If tests fail** → Fix issues and create new RC:
```bash
# Fix the issue in code
git add .
git commit -m "Fix: <description>"

# Create new RC tag (increment rc number)
# Update version to "0.2.0rc2" in pyproject.toml
git add pyproject.toml
git commit -m "Prepare v0.2.0-rc2"
git tag v0.2.0-rc2
git push origin main --tags

# Repeat testing from step 2
```

### 4. Promote to Production

**Once TestPyPI testing is successful:**

```bash
# Update version in pyproject.toml to final version
# Change "0.2.0rc1" → "0.2.0"
git add pyproject.toml
git commit -m "Release v0.2.0"

# Create production tag (NO -rc suffix!)
git tag v0.2.0
git push origin main --tags
```

**What happens automatically:**
1. GitHub Actions workflow triggers on `v*.*.*` tag (without -rc)
2. Runs `make check` (lint + typecheck + test)
3. Builds package with `uv build`
4. Publishes to **pypi.org** using Trusted Publishing
5. Generates Sigstore attestations (supply chain security)
6. Creates GitHub Release with changelog
7. Attaches distribution files to release

### 5. Verify Production Release

```bash
# Wait 2-3 minutes for PyPI propagation

# Test production installation
uvx aegis-stack --version
# Should output: aegis-stack, version 0.2.0

# Verify PyPI page
open https://pypi.org/project/aegis-stack/
```

## Tag Naming Conventions

### Pre-Release Tags (TestPyPI)

- `v0.2.0-rc1` - Release candidate 1
- `v0.2.0-rc2` - Release candidate 2
- `v1.0.0-beta1` - Beta release
- `v1.0.0-alpha1` - Alpha release

Any tag containing `-rc`, `-beta`, or `-alpha` goes to TestPyPI.

### Production Tags (PyPI)

- `v0.2.0` - Minor version release
- `v1.0.0` - Major version release
- `v0.2.1` - Patch release

Clean version tags (no suffix) go to production PyPI.

## PyPI Trusted Publishing Setup

### One-Time Configuration Required

You must configure Trusted Publishers on **both** TestPyPI and production PyPI.

### TestPyPI Setup

1. Go to https://test.pypi.org/manage/account/publishing/
2. Click "Add a new pending publisher"
3. Fill in:
   - **PyPI Project Name**: `aegis-stack`
   - **Owner**: `lbedner`
   - **Repository name**: `aegis-stack`
   - **Workflow name**: `release.yml`
   - **Environment name**: `release-test`
4. Save

### Production PyPI Setup

1. Go to https://pypi.org/manage/account/publishing/
2. Click "Add a new pending publisher"
3. Fill in:
   - **PyPI Project Name**: `aegis-stack`
   - **Owner**: `lbedner`
   - **Repository name**: `aegis-stack`
   - **Workflow name**: `release.yml`
   - **Environment name**: `release`
4. Save

!!! note "Pending vs Active Publishers"
    Publishers start as "pending" and become "active" after the first successful publish.

### Why Trusted Publishing?

- ✅ **No API tokens** - Uses OpenID Connect (OIDC) authentication
- ✅ **Zero credential management** - No secrets to rotate or leak
- ✅ **Automatic attestations** - Built-in supply chain security (Sigstore)
- ✅ **Industry standard** - Recommended by PyPI and Python Packaging Authority

## Workflow Details

### What the Workflow Does

The [release workflow](https://github.com/lbedner/aegis-stack/blob/main/.github/workflows/release.yml) consists of three jobs:

**1. Build Job** (runs for all tags)
```yaml
- Checkout code
- Install uv
- Run make check (quality gates)
- Build package: uv build
- Upload dist/ as artifact
```

**2. TestPyPI Job** (runs only for `-rc*` tags)
```yaml
- Download dist/ artifact
- Publish to test.pypi.org
- Create GitHub Pre-release
- Add testing instructions to release notes
```

**3. PyPI Job** (runs only for production tags)
```yaml
- Download dist/ artifact
- Publish to pypi.org with attestations
- Extract changelog from CHANGELOG.md
- Create GitHub Release
- Attach dist/ files
```

### Quality Gates

All releases (TestPyPI and PyPI) must pass:
- ✅ `ruff check` (linting)
- ✅ `mypy` (type checking)
- ✅ `pytest` (test suite)

If any check fails, the release is aborted.

## Troubleshooting

### Workflow fails on "make check"

**Problem**: Tests, linting, or type checks fail during build.

**Solution**: Run locally before tagging:
```bash
make check
# Fix any issues, then commit and tag
```

### "Publishing to PyPI failed"

**Problem**: Trusted Publishing not configured correctly.

**Solution**:
1. Verify Trusted Publisher configuration on PyPI
2. Ensure workflow name is exactly `release.yml`
3. Ensure environment name matches (`release-test` or `release`)
4. Check workflow permissions include `id-token: write`

### Can't install from TestPyPI

**Problem**: `uvx --index-url https://test.pypi.org/simple/ aegis-stack` fails with dependency errors.

**Reason**: TestPyPI doesn't have all dependencies (like `click`, `cookiecutter`, etc.).

**Solution**: Install with fallback to production PyPI:
```bash
uvx --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    aegis-stack
```

!!! warning "TestPyPI Limitation"
    TestPyPI is isolated from production PyPI. Most dependencies won't be available, but the package itself will install and work for testing.

### Tag already exists

**Problem**: Trying to push a tag that already exists.

**Solution**: Delete and recreate the tag:
```bash
# Delete local tag
git tag -d v0.2.0

# Delete remote tag (use with caution!)
git push origin :refs/tags/v0.2.0

# Create new tag
git tag v0.2.0
git push --tags
```

### Want to skip TestPyPI for hotfix

**Problem**: Need to release emergency fix, don't want to wait for RC testing.

**Solution**: Create production tag directly:
```bash
# Update version to "0.2.1" (no rc suffix)
git tag v0.2.1
git push --tags
# Goes straight to production PyPI
```

Use this only for critical hotfixes - normal releases should always go through TestPyPI first.

## Best Practices

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **Major** (1.0.0): Breaking changes
- **Minor** (0.2.0): New features, backwards compatible
- **Patch** (0.2.1): Bug fixes, backwards compatible

### Changelog Maintenance

Update `CHANGELOG.md` before each release:
```markdown
## [0.2.0] - 2025-01-15

### Added
- New feature X
- Support for Y

### Changed
- Improved Z performance

### Fixed
- Bug in ABC component
```

The workflow automatically extracts this section for GitHub Release notes.

### Release Cadence

- **RC tags**: Create as many as needed for testing
- **Production tags**: Only after successful RC validation
- **Hotfixes**: Use patch versions (0.2.1) for critical fixes

### Testing Discipline

Always test from TestPyPI before production:
1. Install from TestPyPI (`uvx --index-url ...`)
2. Test all major features
3. Generate projects with different component combinations
4. Run `make check` on generated projects
5. Only then promote to production

## Security

### Attestations

Production PyPI releases include **Sigstore attestations** (PEP 740):
- Cryptographic proof of what was built
- Who built it (GitHub Actions OIDC identity)
- When it was built (timestamp)
- Verifiable by anyone

View attestations on PyPI: https://pypi.org/project/aegis-stack/#files

### Token Security

No API tokens are used or stored. The workflow uses **short-lived OIDC tokens**:
- Generated during workflow execution
- Valid for only 15 minutes
- Automatically expire after use
- Cannot be leaked or stolen

## FAQ

### Q: Can I trigger releases manually?

A: No, releases are tag-based only. Create a tag to trigger a release.

### Q: Can I cancel a release in progress?

A: Yes, stop the GitHub Actions workflow from the Actions tab before it reaches the publish step.

### Q: What if TestPyPI publish succeeds but PyPI fails?

A: Fix the issue, delete the production tag, and recreate it after fixing.

### Q: Do I need to update CHANGELOG.md?

A: Recommended but optional. The workflow will extract changelog sections if they exist.

### Q: Can I test the workflow without publishing?

A: Use [`act`](https://github.com/nektos/act) to run workflows locally (complex setup required), or create a test tag and cancel before publish step.

## Additional Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [Sigstore Attestations (PEP 740)](https://peps.python.org/pep-0740/)
- [Semantic Versioning](https://semver.org/)
