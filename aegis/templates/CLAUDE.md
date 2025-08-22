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
    "include_worker": "no"
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