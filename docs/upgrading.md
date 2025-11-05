# Upgrading Aegis Stack Projects

This guide covers upgrading Aegis Stack projects and understanding the differences between template engines.

## Upgrading the CLI

### Recommended: uvx (No Installation)

```bash
# uvx always uses the latest version
uvx aegis-stack --version

# No upgrade needed - automatically uses latest
```

### Using uv tool

```bash
# Upgrade to latest version
uv tool upgrade aegis-stack

# Check version
uv tool run aegis-stack --version
```

### Using pip

```bash
# Upgrade to latest version
pip install --upgrade aegis-stack

# Check version
aegis --version
```

## Upgrading Generated Projects

### For Copier-Based Projects (Recommended)

Projects generated with `--engine copier` (default in v0.2.0+) can be updated automatically:

```bash
cd my-project

# Update to latest template version
aegis update

# Review changes and conflicts
# Accept/reject updates as needed

# Run tests to verify
make check
```

**What gets updated:**
- Template files (configuration, base components)
- Shared infrastructure code
- New features and improvements

**What's preserved:**
- Your custom business logic
- Modified template files (shows as conflicts)
- Database migrations
- Environment variables

### For Cookiecutter-Based Projects

Projects generated with v0.1.0 or `--engine cookiecutter` **cannot be automatically updated** using `aegis update`.

**Options for Cookiecutter projects:**

#### Option 1: Manual Updates (Recommended for Production)

Keep your existing project and manually adopt new features:

```bash
# Generate a new project with desired features to reference
aegis init reference-project --services auth,ai --components database,worker

# Manually copy desired features from reference-project to your project
# This gives you full control over what changes
```

**Pros:**
- Full control over what changes
- No risk of breaking existing code
- Good for production projects with customizations

**Cons:**
- Manual work required
- Need to understand what changed

#### Option 2: Migrate to Copier (Advanced)

Migrate your project to Copier template for future updateability:

```bash
# 1. Create new project with Copier
aegis init my-project-v2 --engine copier --services <your-services> --components <your-components>

# 2. Copy your custom code
cp -r my-project/app/services/* my-project-v2/app/services/
cp -r my-project/app/models/* my-project-v2/app/models/
# Copy other custom code...

# 3. Copy environment config
cp my-project/.env my-project-v2/.env

# 4. Migrate database
# If you have existing data, you'll need to handle migrations carefully

# 5. Test thoroughly
cd my-project-v2
make check
```

**Pros:**
- Future updates via `aegis update`
- Access to new component management features
- Modern template foundation

**Cons:**
- Significant upfront work
- Risk of data loss if not careful
- Requires thorough testing

#### Option 3: Continue with Cookiecutter

Stay with your Cookiecutter-based project:

```bash
# Continue generating new components with Cookiecutter
aegis init new-feature --engine cookiecutter --components database,worker

# Manually integrate desired pieces
```

**Pros:**
- No migration risk
- Keeps working setup
- Good for stable, production projects

**Cons:**
- No automatic updates
- Missing new Copier-only features (`aegis add/remove/update`)

## Template Engine Comparison

### Copier (Default in v0.2.0+)

**Capabilities:**
- ✅ `aegis update` - Update projects to latest templates
- ✅ `aegis add` - Add components post-generation
- ✅ `aegis remove` - Remove components post-generation
- ✅ Version tracking in `.copier-answers.yml`
- ✅ Smart conflict detection
- ✅ Template evolution support

**Best for:**
- New projects
- Projects that need flexibility
- Teams wanting latest features
- Projects with evolving requirements

**Generate a Copier project:**
```bash
aegis init my-project  # Copier is default
# or explicitly:
aegis init my-project --engine copier
```

### Cookiecutter (Legacy Support)

**Capabilities:**
- ✅ One-time project generation
- ❌ No `aegis update` support
- ❌ No `aegis add/remove` support
- ❌ No version tracking
- ❌ No template updates

**Best for:**
- Teams with existing Cookiecutter projects
- One-time generation needs
- Projects that won't change structure

**Generate a Cookiecutter project:**
```bash
aegis init my-project --engine cookiecutter
```

!!! warning "Cookiecutter Deprecation"
    Cookiecutter support is maintained for compatibility but is **not recommended for new projects**. Focus is on Copier features going forward.

## Version Compatibility

### CLI Version vs Template Version

The Aegis Stack CLI and generated project templates have separate versions:

- **CLI Version**: Version of the `aegis-stack` package (e.g., 0.2.0)
- **Template Version**: Version of the Copier template (tracked in project's `.copier-answers.yml`)

**Checking versions:**

```bash
# CLI version
aegis --version

# Template version (Copier projects only)
cat .copier-answers.yml | grep "_commit"
```

### Update Compatibility

**Copier projects** can be updated to newer template versions:

```bash
# Update to latest template
aegis update

# Update to specific template version (advanced)
aegis update --version 0.2.0
```

**Cookiecutter projects** have no update mechanism.

## Adding New Features to Existing Projects

### For Copier Projects

Use `aegis add` to add components:

```bash
cd my-project

# Add scheduler component
aegis add scheduler

# Add scheduler with SQLite persistence
aegis add scheduler --backend sqlite

# Add worker (automatically adds Redis)
aegis add worker

# Add database
aegis add database

# Add services (requires confirmation)
aegis add --services auth
aegis add --services ai
```

### For Cookiecutter Projects

**Manual integration required:**

1. Generate reference project with desired component
2. Manually copy component files
3. Update dependencies
4. Update configuration
5. Test thoroughly

Example:
```bash
# Generate reference with auth service
aegis init auth-reference --services auth --engine copier

# Manually copy files from auth-reference to your project
# This is manual and requires understanding the codebase
```

## Common Upgrade Scenarios

### Scenario 1: Add Auth to Existing Project

**Copier project:**
```bash
aegis add --services auth
# Automatically includes database, migrations, tests
```

**Cookiecutter project:**
```bash
# Generate reference project
aegis init auth-ref --services auth

# Manually copy:
# - app/services/auth/
# - app/components/backend/api/auth/
# - app/components/backend/api/deps.py
# - app/core/security.py
# - alembic/
# - tests/services/test_auth_*
# - tests/api/test_auth_*

# Update dependencies in pyproject.toml
# Run: uv sync
# Run: alembic upgrade head
```

### Scenario 2: Add Worker to Existing Project

**Copier project:**
```bash
aegis add worker
# Automatically adds Redis, updates docker-compose.yml
```

**Cookiecutter project:**
```bash
# Generate reference
aegis init worker-ref --components worker

# Manually copy:
# - app/components/worker/
# - Update docker-compose.yml
# - Update pyproject.toml
# - Update .env.example
```

### Scenario 3: Update to Latest Template

**Copier project:**
```bash
aegis update

# Review conflicts
# Run tests: make check
```

**Cookiecutter project:**
```bash
# No automatic update available
# Generate new project and manually merge improvements
```

## Best Practices

### For All Projects

1. **Always run tests after changes**: `make check`
2. **Commit before upgrading**: `git add . && git commit -m "Pre-upgrade checkpoint"`
3. **Review changes carefully**: Don't blindly accept updates
4. **Update dependencies**: `uv sync` after adding components
5. **Read CHANGELOG**: Understand what changed in new versions

### For Copier Projects

1. **Regular updates**: Run `aegis update` periodically for latest improvements
2. **Conflict resolution**: Review conflicts carefully, your changes may be important
3. **Version tracking**: Commit `.copier-answers.yml` changes
4. **Test after updates**: Always run full test suite

### For Cookiecutter Projects

1. **Document customizations**: Track what you've changed from template
2. **Periodic review**: Check CHANGELOG for new features worth manual adoption
3. **Consider migration**: Evaluate migrating to Copier for long-lived projects
4. **Reference projects**: Generate Copier projects to see new features

## Troubleshooting

### "aegis update" fails with conflicts

```bash
# Option 1: Accept all template changes
aegis update --force

# Option 2: Resolve conflicts manually
aegis update
# Edit conflicting files
# Choose between your version and template version
```

### "aegis add" fails with dependency errors

```bash
# Some components have dependencies
# Worker requires Redis - automatically added
# Auth requires Database - automatically added

# If you see errors:
1. Check error message for required components
2. Add missing components first
3. Run `uv sync` to update dependencies
```

### Template version mismatch warnings

```bash
# Your template might be older than CLI
# Update to latest:
aegis update

# Or continue with current template:
# Warnings are informational, not blocking
```

### Cookiecutter project shows "Not a Copier project"

```bash
# This is expected - Cookiecutter projects can't use aegis update/add/remove
# Options:
# 1. Continue with Cookiecutter (no automatic updates)
# 2. Migrate to Copier (see migration guide above)
```

## FAQ

### Can I switch from Cookiecutter to Copier mid-project?

Not automatically. You'll need to generate a new Copier project and manually migrate your code. See "Option 2: Migrate to Copier" above.

### Will Cookiecutter be removed?

Not in v0.2.x. Cookiecutter support is maintained for compatibility but deprecated. It may be removed in v0.3.0 or later with advance notice.

### Do I need to update my project?

No. Your existing project will continue to work. Updates are optional and provide:
- Latest improvements
- Bug fixes
- New features
- Better practices

### Can I roll back an update?

Yes, if you committed before updating:
```bash
git reset --hard HEAD~1  # Undo update commit
```

For safety, always commit before running `aegis update`.

### What happens to my custom code during updates?

Custom code in business logic files (services, models, your own modules) is preserved. Only template files are updated, and conflicts are clearly marked for manual resolution.

## See Also

- [Versioning Strategy](versioning.md) - Understand version compatibility
- [CLI Reference](cli-reference.md) - All aegis commands
- [Evolving Your Stack](evolving-your-stack.md) - Philosophy of post-generation changes
- [CHANGELOG](../CHANGELOG.md) - What's new in each version
