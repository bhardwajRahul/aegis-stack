# Template Development Guide

This guide covers template development patterns for Aegis Stack's Copier templates.

## Template Architecture

### Template Structure
```
aegis/templates/copier-aegis-project/
└── {{ project_slug }}/              # Generated project structure
    ├── app/
    │   ├── components/
    │   │   ├── backend/             # Always included
    │   │   ├── frontend/            # Always included
    │   │   ├── scheduler/           # Optional component
    │   │   └── worker/              # Optional component
    │   ├── core/                    # Framework utilities
    │   ├── entrypoints/             # Execution modes
    │   ├── integrations/            # App composition
    │   └── services/                # Business logic (empty)
    ├── tests/
    ├── docker-compose.yml.jinja     # Conditional services
    ├── Dockerfile.jinja             # Conditional entrypoints
    ├── pyproject.toml.jinja         # Dependencies and configuration
    └── scripts/entrypoint.sh.jinja  # Runtime dispatch

copier.yml                           # Template configuration (at repo root)
```

### Template Processing Flow
1. **Copier generates** base project structure using `copier.yml`
2. **Jinja2 templates** (`.jinja` files) are rendered with context variables
3. **Component selection** includes/excludes files based on user choices
4. **Post-generation tasks** run via `aegis/core/post_gen_tasks.py`
5. **Auto-formatting** runs on generated project
6. **Cleanup** removes unused template files

## Copier Variables

### Core Variables (copier.yml)
```yaml
project_name:
  type: str
  help: "Name of your Aegis Stack project"
  default: "My Aegis Stack Project"

project_slug:
  type: str
  default: "{{ project_name.lower().replace(' ', '-').replace('_', '-') }}"

include_scheduler:
  type: bool
  help: "Include APScheduler for scheduled tasks?"
  default: false

include_worker:
  type: bool
  help: "Include worker for background jobs?"
  default: false

include_database:
  type: bool
  help: "Include SQLModel database with SQLite?"
  default: false
```

### Variable Usage in Templates
```jinja2
# In any .jinja file
{{ project_name }}           # "My Aegis Project"
{{ project_slug }}           # "my-aegis-project"
{{ project_description }}    # Description text
{{ author_name }}            # Author info
{{ include_scheduler }}      # true or false (boolean)
```

## Jinja2 Template Patterns

### Conditional Content
```jinja2
{% if include_scheduler %}
# Scheduler-specific content
{% endif %}

{% if include_worker %}
# Worker-specific content
{% endif %}

{% if include_database %}
# Database-specific content
{% endif %}
```

### Variable Substitution in Code
```python
# In .jinja files
CLI_NAME = "{{ project_slug }}"
PROJECT_NAME = "{{ project_name }}"
VERSION = "{{ version }}"
```

### Dependencies Based on Components
```toml
# pyproject.toml.jinja
dependencies = [
    "fastapi>=0.116.1",
    "flet>=0.28.3",
{% if include_scheduler %}
    "apscheduler>=3.10.0",
{% endif %}
{% if include_worker %}
    "arq>=0.26.1",
    "redis>=5.2.1",
{% endif %}
{% if include_database %}
    "sqlmodel>=0.0.14",
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.19.0",
{% endif %}
]
```

## Post-Generation Task Patterns

### Task Responsibilities
The `aegis/core/post_gen_tasks.py` script:
1. **Removes unused files** - Deletes component files when components not selected
2. **Cleans up directories** - Removes empty directories after file cleanup
3. **Auto-formats code** - Runs formatting to ensure generated code is clean

### Adding New Component Logic
```python
# In aegis/core/post_gen_tasks.py
if not include_new_component:
    # Remove component-specific files
    remove_dir("app/components/new_component")
    remove_file("app/entrypoints/new_component.py")
    remove_file("tests/components/test_new_component.py")

# Database component logic
if not include_database:
    remove_file("app/core/db.py")
```

## Template Development Workflow

### CRITICAL: Never Edit Generated Projects
**Always follow this pattern:**

1. **Edit template files** in `aegis/templates/copier-aegis-project/{{ project_slug }}/`
2. **Test template changes**: `make test-template`
3. **If tests fail**: Fix the **template files** (step 1), never the generated projects
4. **Repeat** until tests pass
5. **Clean up**: `make clean-test-projects`

### Adding New Template Files
```bash
# 1. Create template file
vim aegis/templates/copier-aegis-project/{{ project_slug }}/app/components/new_component.py

# 2. If using variables, make it a .jinja file
mv app/components/new_component.py app/components/new_component.py.jinja

# 3. Add conditional logic to post_gen_tasks if needed
vim aegis/core/post_gen_tasks.py

# 4. Test the changes
make test-template
```

### Modifying Existing Templates
```bash
# 1. Find the template file
find aegis/templates/ -name "*.py" -o -name "*.jinja" | grep component_name

# 2. Edit the template
vim aegis/templates/copier-aegis-project/{{ project_slug }}/path/to/file.jinja

# 3. Test immediately
make test-template-quick

# 4. Full validation
make test-template
```

## Template Testing Integration

### Template Validation Process
When you run `make test-template`:
1. **Generates fresh project** using current templates
2. **Processes .jinja files** through Copier
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
# In app/components/backend/startup/component_health.py.jinja
{% if include_worker %}
from app.components.worker.health import register_worker_health_checks
{% endif %}

async def register_component_health_checks() -> None:
    """Register health checks for all enabled components."""
{% if include_worker %}
    register_worker_health_checks()
{% endif %}
```

### Docker Service Configuration
```yaml
# docker-compose.yml.jinja
services:
  webserver:
    # Always included

{% if include_worker %}
  worker-system:
    build: .
    command: ["worker-system"]
    depends_on:
      - redis
{% endif %}

{% if include_scheduler %}
  scheduler:
    build: .
    command: ["scheduler"]
{% endif %}
```

## Template Debugging

### Common Template Issues
- **Jinja2 syntax errors** - Check bracket matching, endif statements
- **Missing variables** - Verify variable names in copier.yml
- **Conditional logic errors** - Test with different component combinations
- **File path issues** - Ensure proper directory structure

### Debugging Template Generation
```bash
# Generate project manually for debugging
uv run aegis init debug-project --output-dir ../debug --force --yes

# Check generated files
ls -la ../debug-project/

# Look for remaining .jinja files (should be none)
find ../debug-project/ -name "*.jinja"

# Check variable substitution
grep -r "{{ " ../debug-project/ || echo "No unreplaced variables"
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
- **No .jinja files** remain in generated projects
- **All variables replaced** - no `{{ ... }}` in final code
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
