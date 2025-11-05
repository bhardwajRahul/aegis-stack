# Versioning Strategy

Aegis Stack follows [Semantic Versioning](https://semver.org/) (SemVer) with clear policies for version numbers, compatibility, and support.

## Version Number Format

Aegis Stack uses `MAJOR.MINOR.PATCH` versioning:

```
v0.2.0
│ │ │
│ │ └─ PATCH: Bug fixes, no new features
│ └─── MINOR: New features, backwards compatible
└───── MAJOR: Breaking changes, incompatible API changes
```

### Examples

- **v0.1.0** → **v0.1.1**: Patch (bug fix only)
- **v0.1.1** → **v0.2.0**: Minor (new features, backwards compatible)
- **v0.9.0** → **v1.0.0**: Major (breaking changes or API redesign)

## What Changes Affect Which Version Number

### MAJOR (Breaking Changes)

Increment MAJOR version when making **incompatible changes**:

- ❌ Removing CLI commands or options
- ❌ Changing required arguments or flags
- ❌ Removing or renaming components
- ❌ Changing generated project structure significantly
- ❌ Removing support for template engines (e.g., removing Cookiecutter)
- ❌ Changing configuration file formats incompatibly
- ❌ Removing supported Python versions

**User Impact**: May require code changes or migration steps.

**Communication**:
- Document in CHANGELOG under "Breaking Changes"
- Provide migration guide
- Announce in release notes
- Consider deprecation warnings in prior MINOR release

### MINOR (New Features)

Increment MINOR version when adding **backwards-compatible features**:

- ✅ Adding new CLI commands (`aegis add`, `aegis remove`, `aegis update`)
- ✅ Adding new components (database, worker, scheduler)
- ✅ Adding new services (auth, AI)
- ✅ Adding new CLI options or flags
- ✅ Adding new template engine support
- ✅ Enhancing existing features without breaking them
- ✅ Adding new documentation
- ✅ Performance improvements

**User Impact**: New capabilities available, existing code unaffected.

**Communication**:
- Document in CHANGELOG under "Added"
- Highlight in release notes
- Update documentation

### PATCH (Bug Fixes)

Increment PATCH version for **backwards-compatible bug fixes**:

- 🐛 Fixing template generation bugs
- 🐛 Fixing CLI command errors
- 🐛 Fixing type checking issues
- 🐛 Fixing documentation errors
- 🐛 Fixing test failures
- 🐛 Dependency security updates (if no API changes)
- 🐛 Minor performance improvements

**User Impact**: Fixes without new features or breaking changes.

**Communication**:
- Document in CHANGELOG under "Fixed"
- May not require formal release notes for minor patches

## CLI Version vs Template Version

Aegis Stack has **two separate versioning tracks**:

### CLI Version

The version of the `aegis-stack` Python package:

```bash
aegis --version
# Output: aegis-stack, version 0.2.0
```

**What it controls:**
- Command-line interface behavior
- Project generation logic
- Component management (add/remove/update)
- Dependency resolution

**How to upgrade:**
```bash
# Using uvx (always latest)
uvx aegis-stack --version

# Using uv tool
uv tool upgrade aegis-stack

# Using pip
pip install --upgrade aegis-stack
```

### Template Version

The version of the Copier/Cookiecutter templates used to generate projects:

```bash
# Copier projects
cat .copier-answers.yml | grep "_commit"

# Cookiecutter projects
# No version tracking
```

**What it controls:**
- Generated project structure
- Component implementations
- Configuration defaults
- Documentation templates

**How to upgrade:**
```bash
# Copier projects only
cd my-project
aegis update
```

### Version Relationship

**CLI and template versions are synchronized** for releases:

| Release | CLI Version | Template Version | Compatibility |
|---------|-------------|------------------|---------------|
| v0.1.0  | 0.1.0       | 0.1.0            | ✅ Matched |
| v0.2.0  | 0.2.0       | 0.2.0            | ✅ Matched |

However, they can diverge:
- **Newer CLI, older template**: `aegis update` available to upgrade project
- **Older CLI, newer template**: Not possible (can't generate future templates)

## Compatibility Policy

### Python Version Support

Aegis Stack follows Python's release cadence:

- **Supported**: Python 3.11+ (currently 3.13 tested)
- **Dropped**: When Python version reaches end-of-life
- **Added**: New Python versions supported in MINOR releases

**Deprecation policy:**
- Announce removal of Python version 6 months before dropping
- Removal is a MAJOR version change if it affects users

### Dependency Compatibility

**Generated projects**:
- Use latest stable versions of dependencies at generation time
- Dependencies pinned with compatible ranges (e.g., `fastapi>=0.100,<0.200`)
- Major dependency updates may require project regeneration or manual updates

**CLI dependencies**:
- Updated in PATCH releases for security fixes
- Updated in MINOR releases for new features
- MAJOR dependency changes may trigger MAJOR version bump if breaking

### Template Engine Compatibility

**Current support** (v0.2.0):
- ✅ Copier (default, recommended)
- ✅ Cookiecutter (legacy, maintained)

**Future plans**:
- Cookiecutter may be deprecated in v0.3.0 with advance warning
- Removal would be MAJOR version change (v1.0.0 or v0.3.0 with migration guide)

### Backwards Compatibility Guarantee

**What's guaranteed:**
- MINOR and PATCH releases won't break existing usage
- CLI commands won't be removed without MAJOR version bump
- Template structure changes are MINOR if backwards-compatible

**What's NOT guaranteed:**
- Internal implementation details
- Undocumented behavior
- Development/testing utilities
- Generated project internals (user's responsibility after generation)

## Update Support Policy

### Automatic Updates (Copier Projects)

**Supported update paths:**
```
v0.1.0 → v0.2.0 ✅ (aegis update)
v0.2.0 → v0.2.1 ✅ (aegis update)
v0.2.0 → v0.3.0 ✅ (aegis update)
v0.2.0 → v1.0.0 ⚠️ (aegis update with migration guide)
```

**Major version updates** may require manual intervention:
- Review migration guide
- Resolve complex conflicts
- Update custom code

### Manual Updates (Cookiecutter Projects)

**No automatic updates** - manual migration required:
- Generate new project
- Copy custom code
- Update dependencies
- Migrate data if needed

See [Upgrading Guide](upgrading.md) for details.

### Support Timeline

**Active support:**
- Latest MINOR version receives PATCH updates
- Previous MINOR version receives security PATCH updates for 3 months

**Example** (assuming v0.3.0 is latest):
- v0.3.x: ✅ Active support (all fixes)
- v0.2.x: ✅ Security fixes only (3 months)
- v0.1.x: ❌ No support (upgrade to v0.2.x or v0.3.x)

**MAJOR version support:**
- Latest MAJOR version: Active support
- Previous MAJOR version: Security fixes for 6 months after new MAJOR release

## Breaking Change Policy

### Definition

A change is breaking if it requires users to:
- Modify existing code
- Change command usage
- Migrate data or configuration
- Update dependencies incompatibly

### Communication Timeline

**Deprecation process:**

1. **MINOR Release N**: Deprecation warning added
   ```bash
   # Example: v0.2.0 warns about Cookiecutter deprecation
   aegis init my-project --engine cookiecutter
   # Warning: Cookiecutter support will be removed in v0.3.0
   ```

2. **MINOR Release N+1**: Continued warnings, migration guide published
   ```bash
   # Example: v0.2.1 continues warnings, docs updated
   ```

3. **MAJOR Release**: Feature removed
   ```bash
   # Example: v0.3.0 removes Cookiecutter
   aegis init my-project --engine cookiecutter
   # Error: Cookiecutter not supported. Use --engine copier
   ```

**Minimum deprecation period:** 3 months or 1 MINOR version, whichever is longer.

### Emergency Breaking Changes

**Security or critical bugs** may require immediate breaking changes:
- Released as MAJOR version (even if small change)
- Clearly documented in CHANGELOG and security advisory
- Migration guide provided

## Version Planning

### v0.x.x (Pre-1.0)

**Current phase:** Active development and stabilization

- MINOR versions may introduce significant new features
- Breaking changes possible but minimized
- Deprecation warnings used when practical
- Focus on feature completion and API stabilization

### v1.0.0 Goals

**Requirements for v1.0.0:**
- Stable CLI API
- Proven template architecture
- Comprehensive documentation
- Production usage validation
- Strong backwards compatibility commitment
- Component ecosystem maturity

**Not required for v1.0.0:**
- Feature completeness (new features can be MINOR)
- All possible components (can add more post-1.0)

### Post-1.0 Stability

**After v1.0.0:**
- Stronger backwards compatibility guarantees
- Longer deprecation periods (6+ months)
- More conservative breaking changes
- LTS version consideration

## How We Version

### Release Process

1. **Determine version number** based on changes (MAJOR.MINOR.PATCH)
2. **Update CHANGELOG.md** with changes
3. **Update version in `pyproject.toml`** and template
4. **Create release candidate** tag (v0.2.0-rc1)
5. **Test on TestPyPI**
6. **Create final release** tag (v0.2.0)
7. **Publish to PyPI**
8. **Create GitHub Release** with changelog

### Version Bumping

**Automated:**
```bash
# Using version bump script (v0.2.0+)
python scripts/bump-version.py 0.2.0
```

**Manual:**
```toml
# pyproject.toml
[project]
version = "0.2.0"
```

```yaml
# aegis/templates/copier-aegis-project/copier.yml
_version: "0.2.0"
```

### Pre-release Versions

**Format:** `MAJOR.MINOR.PATCH-PRERELEASE`

**Types:**
- **Alpha**: `v0.2.0-alpha1` - Early testing, unstable
- **Beta**: `v0.2.0-beta1` - Feature complete, testing needed
- **RC**: `v0.2.0-rc1` - Release candidate, final testing

**Usage:**
```bash
# Install pre-release
pip install aegis-stack==0.2.0rc1

# Test pre-release
uvx aegis-stack@0.2.0rc1 init test-project
```

## FAQ

### When will v1.0.0 be released?

When the API is stable, well-tested, and production-proven. No specific date set - quality over speed.

### Can I use v0.x.x in production?

Yes! v0.x.x versions are production-ready but may have breaking changes between MINOR versions. Pin your version and test updates before deploying.

### How long are versions supported?

- Latest MINOR: Full support
- Previous MINOR: Security fixes for 3 months
- Older MINOR: No support (upgrade recommended)

### What if I need a feature from a new version?

**Copier projects:**
```bash
aegis update  # Get latest template
```

**Cookiecutter projects:**
- Generate new project to see feature
- Manually integrate if needed
- Or migrate to Copier

### Will my generated project break when I upgrade the CLI?

No. Generated projects are independent. Upgrading the CLI doesn't affect existing projects unless you run `aegis update` (Copier projects only).

### How do I know if an update has breaking changes?

1. Check CHANGELOG.md "Breaking Changes" section
2. Review migration guide (if provided)
3. Test in development environment first
4. Look for MAJOR version number changes (v1.0.0 → v2.0.0)

## See Also

- [CHANGELOG](../CHANGELOG.md) - Version history and changes
- [Upgrading Guide](upgrading.md) - How to upgrade projects
- [Semantic Versioning](https://semver.org/) - Official SemVer spec
- [Release Process](development/releases.md) - How releases are created
