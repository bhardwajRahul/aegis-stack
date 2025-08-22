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
make test-template-full          # Test all components (worker + scheduler)
make clean-test-projects         # Remove all generated test projects
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

## Test Development Best Practices

1. **Run fast tests frequently** (`make test`) during development
2. **Run template tests before commits** (`make test-template`)
3. **Test component combinations** when adding new components
4. **Use `make test-template-quick`** for rapid iteration
5. **Clean up test projects** (`make clean-test-projects`) regularly
6. **Never edit generated projects** - always fix templates
7. **Check both CLIs** - generation and generated project functionality