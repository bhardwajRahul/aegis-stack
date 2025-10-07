# Testing Guide for Aegis Stack

This guide covers how to write tests and run tests for the Aegis Stack CLI tool development.

## Testing Philosophy

### Template-First Testing
**CRITICAL RULE: Never edit generated test projects directly!** 

Always follow this workflow:
1. Edit template files in `aegis/templates/cookiecutter-aegis-project/{{cookiecutter.project_slug}}/`
2. Run template tests to generate fresh projects
3. If tests fail, fix the **template files** (step 1), never the generated projects
4. Generated projects are temporary validation artifacts

### Dual CLI Testing
There are TWO different CLIs that need testing:
- **Aegis CLI** (`aegis init`) - Project generation (this repository)
- **Generated Project CLI** (`project-name health`) - Health monitoring (in generated projects)

### Testing Hierarchy
1. **Fast Tests** (`pytest tests/cli/`) - Unit tests, no project generation (~5 seconds)
2. **Template Tests** (`make test-template`) - Full project generation + validation (~30 seconds)
3. **Quality Checks** (`make check`) - Lint + typecheck + unit tests (~10 seconds)

## Current Test Commands

These are the **verified commands** that actually exist in the Makefile:

### Basic Testing
```bash
make test          # Run CLI unit tests (fast)
make check         # Run lint + typecheck + unit tests
```

### Template Testing (Critical for Template Changes)
```bash
make test-template                # Full template validation
make test-template-quick         # Fast template generation only
make test-template-with-components  # Test with scheduler component
make test-template-worker        # Test worker component specifically
make test-template-database      # Test database component specifically (v0.1.0)
make test-template-full          # Test all components (worker + scheduler)
make clean-test-projects         # Remove all generated test projects
```

### Parity Testing (Cookiecutter vs Copier Migration)
**NEW - Ticket #124: Ensure Copier generates identical output to Cookiecutter**

```bash
make test-parity                 # Run all parity tests
make test-parity-quick          # Quick test (base project only)
make test-parity-components     # Test all component combinations
make test-parity-services       # Test all service combinations
make test-parity-full           # Comprehensive kitchen-sink test
```

### Template Testing Workflow
After modifying any template files:
```bash
# 1. Quick feedback during development
make test-template-quick

# 2. Full validation before committing
make test-template

# 3. Test specific components if changed
make test-template-worker      # If worker templates changed
make test-template-full        # If multiple components changed

# 4. Cleanup when done
make clean-test-projects
```

## Writing New Tests

### Test File Organization
```
tests/cli/
├── test_cli_basic.py           # Fast tests (command parsing, help, validation)
├── test_cli_init.py            # Slow tests (project generation)
├── test_component_dependencies.py  # Component dependency logic
├── test_error_handling.py      # Error handling and edge cases
├── test_stack_generation.py    # Stack generation patterns
├── test_stack_validation.py    # Generated stack validation
└── test_utils.py               # Shared test utilities
```

### Fast vs Slow Test Patterns

**Fast Tests** (add to `test_cli_basic.py`):
```python
def test_new_validation(self) -> None:
    """Test new validation logic without project generation."""
    result = run_aegis_command("init", "test-project", "--components", "invalid")
    assert not result.success
    assert "invalid component" in result.stderr.lower()
```

**Slow Tests** (add to `test_cli_init.py`):
```python
def test_new_component_generation(self, temp_output_dir: Path) -> None:
    """Test full project generation with new component."""
    result = run_aegis_init(
        "test-new-component",
        ["new_component"],
        temp_output_dir
    )
    
    assert result.success
    assert_file_exists(result.project_path, "app/components/new_component.py")
```

### Test Utilities
Use the existing utilities in `test_utils.py`:
- `run_aegis_command()` - Run CLI commands without project generation
- `run_aegis_init()` - Full project generation with validation
- `assert_file_exists()` - Check generated file structure
- `check_error_indicators()` - Validate error messages

### When to Add Tests
- **New CLI commands** → Add to `test_cli_basic.py`
- **New components** → Add to `test_cli_init.py`
- **New validation logic** → Add to `test_error_handling.py`
- **New dependency patterns** → Add to `test_component_dependencies.py`

## Template Testing Deep Dive

### What Template Testing Does
1. **Generates fresh project** using current templates
2. **Sets up virtual environment** and installs dependencies
3. **Installs CLI script** (`uv pip install -e .`)
4. **Runs quality checks** (`make check` in generated project)
5. **Tests CLI functionality** (health commands, help text)

### Template Testing Locations
Generated test projects are created in parallel directories:
- `../test-basic-stack/` - Basic project (no components)
- `../test-component-stack/` - With scheduler component
- `../test-worker-stack/` - With worker component
- `../test-full-stack/` - With all components

### Template Validation Checks
- No `.j2` files remain in generated projects
- All `{{ cookiecutter.* }}` variables are replaced
- Generated code passes linting and type checking
- CLI scripts install and run correctly
- Component-specific files exist when components selected

### Testing Template Changes
```bash
# 1. Make template changes
vim aegis/templates/cookiecutter-aegis-project/{{cookiecutter.project_slug}}/app/...

# 2. Test quickly
make test-template-quick

# 3. Check the generated project
cd ../test-basic-stack
make check  # Should pass

# 4. If issues found, fix templates (not generated project!)
cd ../aegis-stack
vim aegis/templates/...  # Fix the template

# 5. Re-test
make test-template

# 6. Clean up when satisfied
make clean-test-projects
```

## Debugging Test Failures

### Template Generation Failures
```bash
# Check permissions and cleanup
chmod -R +w ../test-basic-stack 2>/dev/null || true
rm -rf ../test-basic-stack

# Check cookiecutter template syntax
uv run aegis init debug-test --output-dir ../debug --force --yes
```

### CLI Installation Issues
```bash
# In generated project, if CLI script fails
cd ../test-basic-stack

# Method 1: Recreate virtual environment
rm -rf .venv
uv sync --extra dev --extra docs
uv pip install -e .

# Method 2: Use uv run instead of direct CLI
uv run test-basic-stack --help  # Should always work
```

### Virtual Environment Corruption
```bash
# Generated project virtual environment issues
cd ../test-basic-stack
chmod -R +w .venv 2>/dev/null || true
rm -rf .venv
env -u VIRTUAL_ENV uv sync --extra dev --extra docs
env -u VIRTUAL_ENV uv pip install -e .
```

### Permission Problems
```bash
# If test projects can't be removed
chmod -R +w ../test-*-stack 2>/dev/null || true
rm -rf ../test-*-stack

# Or use the makefile target
make clean-test-projects
```

### Common Issues
- **"command not found"** → CLI script not installed, use `uv run project-name`
- **Template syntax errors** → Check Jinja2 syntax in `.j2` files
- **Linting failures** → Template tests auto-fix most issues
- **Permission denied** → Use `chmod -R +w` before cleanup

## Database Testing Patterns (v0.1.0+)

### Database Component Testing
The database component includes comprehensive testing infrastructure:

**Test Files Generated:**
- `tests/conftest.py` - Database fixtures with transaction rollback
- `tests/cli/test_database_runtime.py` - Database integration tests
- Health check integration tests

**Testing Philosophy:**
- **In-memory databases** for test speed
- **Transaction rollback** for test isolation
- **Real database operations** to validate ORM setup
- **Health check integration** to ensure monitoring works

### Database Test Patterns
```python
# Test database connectivity and basic operations
def test_database_session_management(db_session):
    """Test basic database session operations."""
    # Tests use real SQLModel operations
    # Transaction rollback ensures clean state

# Test health check integration  
def test_database_health_check():
    """Test database component health monitoring."""
    # Validates file existence, connectivity, metadata
```

**Key Testing Approach:**
- **No mock models** - Only test infrastructure until real models exist
- **Session management validation** - Ensure context managers work
- **Health integration testing** - Database monitoring functions correctly
- **Future expansion ready** - Fixtures ready for User/Auth service testing

### Template Testing for Database
```bash
# Test database component in isolation
make test-template-database

# Generated project includes:
# - app/core/db.py with session management
# - tests/conftest.py with database fixtures  
# - Health check integration
# - Clean project passes all quality checks
```

## Parity Testing (Cookiecutter → Copier Migration)

**Ticket #124** - Comprehensive testing ensuring Copier generates 100% identical output to Cookiecutter during the migration period.

### What Parity Testing Does

Parity tests generate projects with BOTH Cookiecutter and Copier, then compare them byte-for-byte:

1. **Generates with Cookiecutter** - Uses existing template
2. **Generates with Copier** - Uses new template
3. **Compares directories** - File structure, contents, permissions
4. **Reports differences** - Detailed diff output for debugging

### Parity Test Matrix

The parity test suite covers all critical combinations:

```python
# tests/test_template_parity.py

test_parity_base_project()              # Base (backend + frontend only)
test_parity_with_scheduler_memory()     # Scheduler (memory backend)
test_parity_with_scheduler_sqlite()     # Scheduler (sqlite backend)
test_parity_with_worker()               # Worker component
test_parity_with_database()             # Database component
test_parity_with_all_components()       # Worker + Scheduler + Database
test_parity_with_auth_service()         # Auth service
test_parity_with_ai_service()           # AI service
test_parity_kitchen_sink()              # Everything enabled
```

### Running Parity Tests

**CURRENT STATE**: Parity tests are currently **SKIPPED** in CI/CD because the Copier template migration is incomplete. The test infrastructure is ready, but the Copier template needs conditional `_exclude` patterns added before tests can pass.

```bash
# Tests are skipped by default (won't block CI/CD)
uv run pytest tests/test_template_parity.py -v
# Result: 9 skipped

# To run parity tests (will fail until Copier template is fixed)
uv run pytest tests/test_template_parity.py -v --run-skipped

# Or use make targets (also skipped by default)
make test-parity-quick          # Base project only
make test-parity-components     # All component combinations
make test-parity-services       # All service combinations
make test-parity                # Full matrix (all tests)
make test-parity-full           # Kitchen sink (everything)
```

**To enable tests** (after fixing Copier template):
Remove the `@pytest.mark.skip` decorator from `TestTemplateParity` class in `tests/test_template_parity.py`

### Reading Parity Test Failures

When parity tests fail, you get detailed diff reports:

```
❌ PARITY TEST FAILURE
================================================================================
Cookiecutter: /tmp/cookiecutter-test-XXX
Copier:       /tmp/copier-test-XXX

📁 Files missing in Copier output:
   - .env

📁 Extra files in Copier output:
   + .copier-answers.yml

📝 Content mismatches:
   README.md:
      Cookiecutter: line 3: test-base project documentation...
      Copier:       line 3: {{ project_name }} project documentation...

🔒 Permission mismatches:
   scripts/entrypoint.sh:
      Cookiecutter: executable
      Copier:       not executable

================================================================================
```

### Common Parity Issues

**Missing variable substitution:**
```jinja
{# WRONG - Copier doesn't know about cookiecutter #}
{{ cookiecutter.project_name }}

{# RIGHT - Copier uses direct variable names #}
{{ project_name }}
```

**File permission mismatches:**
- Cookiecutter's post-generation hook sets permissions
- Copier needs permissions set in template or via tasks

**Acceptable differences:**
- `.copier-answers.yml` - Copier tracking file (ignored)
- `uv.lock` revision differences - Lock file variations (expected)
- `__pycache__` files - Generated artifacts (filtered out)

### Parity Testing During Migration

**Phase 1: Parallel Implementation (Current)**
- Both templates exist side-by-side
- Parity tests ensure identical output
- Fix Copier template when tests fail

**Phase 2: Parity Validation (Ticket #124)**
- All tests passing (100% parity)
- CI blocks merges if parity breaks
- Ready for switchover

**Phase 3: Copier Primary (Ticket #125+)**
- Switch `aegis init` to use Copier
- Keep Cookiecutter for comparison
- Eventually remove after confidence period

### Parity Test Development

When adding new components/services:

```python
def test_parity_with_new_component(self) -> None:
    """Test parity with new component."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Generate with both engines
        ck_path = generate_with_cookiecutter(
            project_name="test-new",
            components=["new_component"],
            output_dir=temp_path / "cookiecutter",
        )
        cp_path = generate_with_copier(
            project_name="test-new",
            components=["new_component"],
            output_dir=temp_path / "copier",
        )

        # Compare outputs
        result = compare_projects(ck_path, cp_path)

        # Assert parity
        assert result.is_identical, result.get_failure_report()
```

### Debugging Parity Failures

```bash
# 1. Run failing test with verbose output
uv run pytest tests/test_template_parity.py::TestTemplateParity::test_parity_base_project -vv

# 2. Check generated projects (they're in temp dirs, but you can modify test to keep them)
# Modify test temporarily:
temp_dir = "/tmp/parity-debug"  # Instead of TemporaryDirectory()

# 3. Compare manually
diff -r /tmp/parity-debug/cookiecutter/test-base /tmp/parity-debug/copier/test-base

# 4. Fix the Copier template (NOT the generated project!)
vim aegis/templates/copier-aegis-project/...

# 5. Re-run parity test
make test-parity-quick
```

## Test Development Best Practices

1. **Run fast tests frequently** (`make test`) during development
2. **Run template tests before commits** (`make test-template`)
3. **Run parity tests when touching templates** (`make test-parity-quick`)
4. **Test component combinations** when adding new components
5. **Use `make test-template-quick`** for rapid iteration
6. **Clean up test projects** (`make clean-test-projects`) regularly
7. **Never edit generated projects** - always fix templates
8. **Check both CLIs** - generation and generated project functionality
9. **Parity tests are critical** - Don't skip them during Copier migration