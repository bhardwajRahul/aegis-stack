# Template Development Guide

This guide covers template development patterns for Aegis Stack's Cookiecutter templates.

## Template Architecture

### Template Structure
```
aegis/templates/cookiecutter-aegis-project/
├── cookiecutter.json                    # Template variables
├── hooks/
│   └── post_gen_project.py             # Template processing logic
└── {{cookiecutter.project_slug}}/      # Generated project structure
    ├── app/
    │   ├── components/
    │   │   ├── backend/                 # Always included
    │   │   ├── frontend/                # Always included
    │   │   ├── scheduler/               # Optional component
    │   │   └── worker/                  # Optional component
    │   ├── core/                        # Framework utilities
    │   ├── entrypoints/                 # Execution modes
    │   ├── integrations/                # App composition
    │   └── services/                    # Business logic (empty)
    ├── tests/
    ├── docker-compose.yml.j2            # Conditional services
    ├── Dockerfile.j2                    # Conditional entrypoints
    ├── pyproject.toml.j2                # Dependencies and configuration
    └── scripts/entrypoint.sh.j2         # Runtime dispatch
```

### Template Processing Flow
1. **Cookiecutter generates** base project structure using `cookiecutter.json`
2. **Post-generation hook** (`hooks/post_gen_project.py`) processes `.j2` files with Jinja2
3. **Component selection** includes/excludes files based on user choices
4. **Auto-formatting** runs `make fix` on generated project
5. **Cleanup** removes unused template files and `.j2` originals

## Cookiecutter Variables

### Core Variables (cookiecutter.json)
```json
{
    "project_name": "My Aegis Project",
    "project_slug": "{{ cookiecutter.project_name|lower|replace(' ', '-')|replace('_', '-') }}",
    "project_description": "A production-ready Python application",
    "author_name": "Your Name",
    "author_email": "your.email@example.com",
    "version": "0.1.0",
    "python_version": "3.11",
    "include_scheduler": "no",
    "include_worker": "no",
    "include_database": "no"
}
```

### Variable Usage in Templates
```jinja2
# In any .j2 file
{{ cookiecutter.project_name }}           # "My Aegis Project"
{{ cookiecutter.project_slug }}           # "my-aegis-project"
{{ cookiecutter.project_description }}    # Description text
{{ cookiecutter.author_name }}            # Author info
{{ cookiecutter.include_scheduler }}      # "yes" or "no"
```

## Jinja2 Template Patterns

### Conditional Content
```jinja2
{% if cookiecutter.include_scheduler == "yes" %}
# Scheduler-specific content
{% endif %}

{% if cookiecutter.include_worker == "yes" %}
# Worker-specific content
{% endif %}

{% if cookiecutter.include_database == "yes" %}
# Database-specific content
{% endif %}
```

### Conditional Files
File names can be conditional:
```
{% if cookiecutter.include_scheduler == "yes" %}scheduler.py{% endif %}
```

### Variable Substitution in Code
```python
# In .j2 files
CLI_NAME = "{{ cookiecutter.project_slug }}"
PROJECT_NAME = "{{ cookiecutter.project_name }}"
VERSION = "{{ cookiecutter.version }}"
```

### Dependencies Based on Components
```toml
# pyproject.toml.j2
dependencies = [
    "fastapi>=0.116.1",
    "flet>=0.28.3",
{% if cookiecutter.include_scheduler == "yes" %}
    "apscheduler>=3.10.0",
{% endif %}
{% if cookiecutter.include_worker == "yes" %}
    "arq>=0.26.1",
    "redis>=5.2.1",
{% endif %}
{% if cookiecutter.include_database == "yes" %}
    "sqlmodel>=0.0.14",
    "sqlalchemy>=2.0.0", 
    "aiosqlite>=0.19.0",
{% endif %}
]
```

## Post-Generation Hook Patterns

### Hook Responsibilities
The `hooks/post_gen_project.py` script:
1. **Processes .j2 files** - Renders Jinja2 templates with cookiecutter context
2. **Removes unused files** - Deletes component files when components not selected
3. **Cleans up directories** - Removes empty directories after file cleanup
4. **Auto-formats code** - Runs `make fix` to ensure generated code is clean

### Adding New Component Logic
```python
# In hooks/post_gen_project.py
if "{{ cookiecutter.include_new_component }}" != "yes":
    # Remove component-specific files
    remove_dir("app/components/new_component")
    remove_file("app/entrypoints/new_component.py")
    remove_file("tests/components/test_new_component.py")

# Database component logic
if "{{ cookiecutter.include_database }}" != "yes":
    remove_file("app/core/db.py")
    remove_sections_from_conftest("tests/conftest.py", ["database"])
```

### File Removal Patterns
```python
# Remove individual files
remove_file("app/components/scheduler.py")
remove_file("tests/components/test_scheduler.py")

# Remove entire directories
remove_dir("app/components/worker")
```

## Template Development Workflow

### CRITICAL: Never Edit Generated Projects
**Always follow this pattern:**

1. **Edit template files** in `aegis/templates/cookiecutter-aegis-project/{{cookiecutter.project_slug}}/`
2. **Test template changes**: `make test-template`
3. **If tests fail**: Fix the **template files** (step 1), never the generated projects
4. **Repeat** until tests pass
5. **Clean up**: `make clean-test-projects`

### Adding New Template Files
```bash
# 1. Create template file
vim aegis/templates/cookiecutter-aegis-project/{{cookiecutter.project_slug}}/app/components/new_component.py

# 2. If using variables, make it a .j2 file
mv app/components/new_component.py app/components/new_component.py.j2

# 3. Add conditional logic to hook if needed
vim hooks/post_gen_project.py

# 4. Test the changes
make test-template
```

### Modifying Existing Templates
```bash
# 1. Find the template file
find aegis/templates/ -name "*.py" -o -name "*.j2" | grep component_name

# 2. Edit the template
vim aegis/templates/cookiecutter-aegis-project/{{cookiecutter.project_slug}}/path/to/file.j2

# 3. Test immediately
make test-template-quick

# 4. Full validation
make test-template
```

## Template Testing Integration

### Template Validation Process
When you run `make test-template`:
1. **Generates fresh project** using current templates
2. **Processes .j2 files** through post-generation hook
3. **Installs dependencies** in generated project
4. **Runs quality checks** (lint, typecheck, tests)
5. **Tests CLI installation** and functionality

### Template-Specific Test Commands
```bash
make test-template                # Test basic project generation
make test-template-with-components # Test with scheduler component
make test-template-worker         # Test worker component
make test-template-full           # Test all components
```

### Auto-Fixing in Templates
The template system automatically:
- **Fixes linting issues** in generated code
- **Formats code** with ruff
- **Ensures proper imports** and structure
- **Validates type annotations**

## Common Template Patterns

### Configuration Management
```python
# Use in templates for environment-dependent values
from app.core.config import settings

# Template generates proper imports
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL
```

### Component Registration
```python
# Backend component registration
# In app/components/backend/startup/component_health.py.j2
{% if cookiecutter.include_worker == "yes" %}
from app.components.worker.health import register_worker_health_checks
{% endif %}

async def register_component_health_checks() -> None:
    """Register health checks for all enabled components."""
{% if cookiecutter.include_worker == "yes" %}
    register_worker_health_checks()
{% endif %}
```

### Docker Service Configuration
```yaml
# docker-compose.yml.j2
services:
  webserver:
    # Always included
    
{% if cookiecutter.include_worker == "yes" %}
  worker-system:
    build: .
    command: ["worker-system"]
    depends_on:
      - redis
{% endif %}

{% if cookiecutter.include_scheduler == "yes" %}
  scheduler:
    build: .
    command: ["scheduler"]
{% endif %}
```

## Template Debugging

### Common Template Issues
- **Jinja2 syntax errors** - Check bracket matching, endif statements
- **Missing cookiecutter variables** - Verify variable names in cookiecutter.json
- **Conditional logic errors** - Test with different component combinations
- **File path issues** - Ensure proper directory structure

### Debugging Template Generation
```bash
# Generate project manually for debugging
uv run aegis init debug-project --output-dir ../debug --force --yes

# Check generated files
ls -la ../debug-project/

# Look for remaining .j2 files (should be none)
find ../debug-project/ -name "*.j2"

# Check variable substitution
grep -r "cookiecutter\." ../debug-project/ || echo "No unreplaced variables"
```

### Testing Individual Components
```bash
# Test specific component combinations
make test-template-worker         # Just worker component
make test-template-with-components # Just scheduler component
make test-template-full           # All components

# Clean up between tests
make clean-test-projects
```

## Template Quality Standards

### Code Generation Requirements
- **No .j2 files** remain in generated projects
- **All variables replaced** - no `{{ cookiecutter.* }}` in final code
- **Proper imports** - only import what's needed based on components
- **Type annotations** - all generated code must be properly typed
- **Linting passes** - generated code passes ruff checks
- **Tests included** - component tests generated with components

### Component Isolation
- **Independent components** - each component can be enabled/disabled
- **Clean dependencies** - components only depend on what they need
- **Proper cleanup** - unused files removed when components disabled
- **No broken imports** - imports only exist when dependencies available

### File Organization
- **Consistent structure** - follow established patterns
- **Logical grouping** - related files in same directories
- **Clear naming** - descriptive file and directory names
- **Proper permissions** - executable files marked as executable

## Template Parity Patterns (Cookiecutter ↔ Copier Migration)

### Overview
Aegis Stack maintains two parallel template engines during migration:
- **Cookiecutter** (legacy) - Uses `cookiecutter.json` + `.j2` files + post-generation hooks
- **Copier** (modern) - Uses `copier.yml` + `.jinja` files + built-in tasks

Both engines MUST generate byte-for-byte identical projects. The `tests/test_template_parity.py` suite verifies this across all component/service combinations.

### Critical Pattern #1: Whitespace Control

**Problem**: Jinja2's `{%-` strips ALL preceding whitespace, including intentional blank lines.

**Rule**: Copier templates must match Cookiecutter's whitespace preservation.

```jinja2
# ❌ WRONG - Copier template (strips blank lines)
from app.core.log import logger

{%- if include_auth %}
from app.models.user import User
{% endif %}

# ✅ CORRECT - Matches Cookiecutter
from app.core.log import logger

{% if include_auth %}
from app.models.user import User
{% endif %}
```

**When This Matters**: When conditional blocks are skipped (e.g., `include_auth = false`), the `{%-` strips the blank line, creating a mismatch.

**Detection**: If parity tests show line number differences or unexpected blank lines, search for `{%-` in Copier templates.

```bash
# Find all whitespace control usage
grep -n '{%-' aegis/templates/copier-aegis-project/**/*.jinja

# Compare with Cookiecutter equivalent
grep -n '{%' aegis/templates/cookiecutter-aegis-project/**/*.j2
```

### Critical Pattern #2: Type Mismatches (Boolean vs String)

**Problem**: Cookiecutter uses strings (`"yes"/"no"`), Copier uses native booleans (`true/false`).

**Rule**: Copier templates must use boolean logic, not string comparisons.

```jinja2
# ❌ WRONG - Copier template comparing boolean to string
{% if include_worker == "yes" %}
from app.components.worker import WorkerConfig
{% endif %}

# ✅ CORRECT - Boolean comparison
{% if include_worker %}
from app.components.worker import WorkerConfig
{% endif %}
```

**Common Mistakes**:
```jinja2
# Cookiecutter (strings)
{% if cookiecutter.include_auth == "yes" %}
{% if cookiecutter.include_scheduler == "yes" and cookiecutter.include_database == "yes" %}

# Copier (booleans)
{% if include_auth %}
{% if include_scheduler and include_database %}
```

**Detection**: If conditional content is missing from Copier output, check for string comparisons against boolean variables.

### Critical Pattern #3: Service Dependency Auto-Resolution

**Problem**: Services declare `required_components` but templates must honor these dependencies.

**Architecture**:
```python
# aegis/core/services.py
SERVICES = {
    "auth": ServiceSpec(
        name="auth",
        required_components=["backend", "database"],  # Auth needs database!
    ),
}

# aegis/core/template_generator.py
# ✅ CORRECT - Auto-add service dependencies
for service_name in self.selected_services:
    if service_name in SERVICES:
        service_spec = SERVICES[service_name]
        all_components.extend(service_spec.required_components)
```

**Impact**: When `--services auth` is used, database component must be automatically enabled. Without this, alembic migrations fail with `ModuleNotFoundError: No module named 'sqlmodel'`.

**Testing**:
```bash
# Auth service should auto-enable database
make test-parity  # Includes test_parity_with_auth_service
```

### Critical Pattern #4: File Exclusion Consistency

**Problem**: Both templates must exclude the same files based on component selection.

**Rule**: Exclusions must match in both `copier.yml` and `hooks/post_gen_project.py`.

```yaml
# copier.yml exclusions
_exclude:
  # Scheduler memory backend exclusions
  - "{% if scheduler_backend == 'memory' -%}{{ project_slug }}/app/services/scheduler{% endif %}"
  - "{% if scheduler_backend == 'memory' -%}{{ project_slug }}/tests/services/test_scheduled_task_manager.py{% endif %}"
```

```python
# hooks/post_gen_project.py
if "{{ cookiecutter.scheduler_backend }}" == "memory":
    remove_dir("app/services/scheduler")
    remove_file("tests/services/test_scheduled_task_manager.py")
```

**Detection**: If parity tests show file existence differences, check exclusion rules in both templates.

### Parity Testing Workflow

**Running Parity Tests**:
```bash
make test-parity              # All 9 parity tests
make test-parity-quick        # Base project only
make test-parity-components   # All component combinations
make test-parity-services     # All service combinations
```

**Test Matrix** (9 comprehensive tests):
1. `test_parity_base_project` - Backend + frontend only
2. `test_parity_with_scheduler_memory` - Scheduler (memory backend)
3. `test_parity_with_scheduler_sqlite` - Scheduler (sqlite backend)
4. `test_parity_with_worker` - Worker component
5. `test_parity_with_database` - Database component
6. `test_parity_with_all_components` - Worker + scheduler + database
7. `test_parity_with_auth_service` - Auth service (auto-enables database)
8. `test_parity_with_ai_service` - AI service
9. `test_parity_kitchen_sink` - Everything enabled

**What Parity Tests Verify**:
- File structure (same files exist in both outputs)
- File contents (byte-for-byte identical after normalization)
- File permissions (executables marked correctly)
- Template variable substitution (no unreplaced `{{ ... }}`)

**Normalization Process**:
Both outputs are auto-formatted with `ruff` before comparison to eliminate cosmetic differences like import ordering.

### Debugging Parity Failures

**Step 1: Identify the failure**
```bash
make test-parity 2>&1 | grep "FAILED"
# Example: test_parity_with_auth_service FAILED
```

**Step 2: Focus on ONE mismatch**
Parity test output shows specific differences:
```
📝 Content mismatches:
   alembic/env.py:
      Cookiecutter: line 24: ...
      Copier:       line 24: from app.models.user import User  # noqa: E402,F401...
```

**Step 3: Generate both projects manually**
```bash
# Cookiecutter
cd /tmp
aegis init ck-test --services auth --no-interactive --yes --force

# Copier
copier copy --trust --defaults \
  --data project_slug="cp-test" \
  --data include_auth=true \
  aegis/templates/copier-aegis-project /tmp/cp-test
```

**Step 4: Compare specific files**
```bash
diff -u /tmp/ck-test/alembic/env.py /tmp/cp-test/cp-test/alembic/env.py

# Check line numbers
sed -n '20,30p' /tmp/ck-test/alembic/env.py
sed -n '20,30p' /tmp/cp-test/cp-test/alembic/env.py
```

**Step 5: Identify the pattern**
- Blank line difference? → Check for `{%-` in Copier template
- Missing content? → Check for boolean vs string comparison
- Wrong imports? → Check service dependency resolution
- Missing file? → Check exclusion rules

**Step 6: Fix the template**
Always fix the **template files**, never the generated projects:
```bash
vim aegis/templates/copier-aegis-project/{{ project_slug }}/alembic/env.py.jinja
# Change {%- if to {% if
```

**Step 7: Re-test**
```bash
make test-parity
# Should show one more test passing
```

### Common Parity Issues

**Issue**: 56 import ordering differences
**Cause**: Different ruff versions or incomplete normalization
**Fix**: Ensure `uv sync --all-extras` runs before `make fix` in Copier tasks

**Issue**: Alembic migration fails with "No module named 'sqlmodel'"
**Cause**: Auth service enabled without database component
**Fix**: TemplateGenerator must auto-add service dependencies

**Issue**: File has 6 lines in Copier, 113 lines in Cookiecutter
**Cause**: Boolean comparison bug (e.g., `include_scheduler == "yes"` when it's `true`)
**Fix**: Change to `include_scheduler` (boolean logic)

**Issue**: Blank line mismatch at line N
**Cause**: Copier uses `{%-` where Cookiecutter uses `{%`
**Fix**: Remove `-` to preserve whitespace

### Best Practices

**When Adding New Templates**:
1. Create in Cookiecutter first (`.j2` files)
2. Copy to Copier and convert (`.jinja` files)
3. Update variables: `cookiecutter.var` → `var`
4. Update conditionals: `== "yes"` → boolean logic
5. Check whitespace: `{%-` → `{%` (usually)
6. Run `make test-parity` to verify

**When Modifying Existing Templates**:
1. Edit **BOTH** Cookiecutter and Copier templates
2. Keep the same logic, just adapt syntax
3. Run `make test-parity` to catch drift
4. Never assume templates are in sync

**When Services Change**:
1. Update `aegis/core/services.py` with new dependencies
2. Verify TemplateGenerator respects them
3. Add parity test case if needed
4. Document new service dependencies

### Success Criteria

Parity is achieved when:
```bash
make test-parity
# 9 passed in ~70 seconds
```

All tests MUST pass before:
- Merging template changes
- Releasing new Aegis Stack versions
- Switching from Cookiecutter to Copier as primary engine

**Zero tolerance for drift** - Any parity failure indicates a real problem that will affect users.