# CLI Core Development Guide

This guide covers CLI development patterns for Aegis Stack's core command system.

## Component System Architecture

### Component Registry (`components.py`)
The component system uses a centralized registry with typed component specifications:

```python
@dataclass
class ComponentSpec:
    """Specification for a component."""
    name: str
    description: str
    type: ComponentType
    requires: list[str] = field(default_factory=list)
    recommends: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

# Component registry
COMPONENTS: dict[str, ComponentSpec] = {
    "redis": ComponentSpec(
        name="redis",
        description="Redis server for caching and message queues",
        type=ComponentType.INFRASTRUCTURE,
    ),
    "worker": ComponentSpec(
        name="worker",
        description="Background task processing with arq",
        type=ComponentType.INFRASTRUCTURE,
        requires=["redis"],
    ),
    "scheduler": ComponentSpec(
        name="scheduler", 
        description="Scheduled task execution with APScheduler",
        type=ComponentType.INFRASTRUCTURE,
    ),
}
```

### Component Types
```python
class ComponentType(Enum):
    """Component types for organization."""
    INFRASTRUCTURE = "infrastructure"  # Redis, workers, databases
    SERVICE = "service"                # Future: API services, microservices
    INTEGRATION = "integration"        # Future: External integrations
```

## Dependency Resolution Patterns

### Dependency Resolver (`dependency_resolver.py`)
The dependency resolver handles component relationships and validation:

```python
class DependencyResolver:
    """Resolves component dependencies and validates selections."""
    
    @staticmethod
    def validate_components(components: list[str]) -> list[str]:
        """Validate component names and return errors."""
        errors = []
        for component in components:
            if component not in COMPONENTS:
                available = list(COMPONENTS.keys())
                # Suggest similar components
                suggestion = DependencyResolver._suggest_component(component, available)
                if suggestion:
                    errors.append(f"Unknown component '{component}'. Did you mean '{suggestion}'?")
                else:
                    errors.append(f"Unknown component '{component}'. Available: {', '.join(available)}")
        return errors

    @staticmethod
    def resolve_dependencies(selected: list[str]) -> list[str]:
        """Resolve all dependencies for selected components."""
        resolved = set(selected)
        
        # Add required dependencies
        queue = list(selected)
        while queue:
            component = queue.pop(0)
            if component in COMPONENTS:
                for required in COMPONENTS[component].requires:
                    if required not in resolved:
                        resolved.add(required)
                        queue.append(required)
        
        return sorted(resolved)
```

### Validation Patterns
```python
def validate_project_name(project_name: str) -> None:
    """Validate project name and raise typer.Exit if invalid."""
    import re
    
    # Check for invalid characters
    if not re.match(r"^[a-zA-Z0-9_-]+$", project_name):
        typer.echo("❌ Invalid project name. Only letters, numbers, hyphens, and underscores are allowed.", err=True)
        raise typer.Exit(1)
    
    # Check for reserved names
    reserved_names = {"aegis", "aegis-stack"}
    if project_name.lower() in reserved_names:
        typer.echo(f"❌ '{project_name}' is a reserved name.", err=True)
        raise typer.Exit(1)
    
    # Check length limit
    if len(project_name) > 50:
        typer.echo("❌ Project name too long. Maximum 50 characters allowed.", err=True)
        raise typer.Exit(1)
```

## Template Generation Logic

### Template Generator (`template_generator.py`)
The template generator converts component selections into cookiecutter context:

```python
class TemplateGenerator:
    """Generates template context from component selections."""
    
    def __init__(self, project_name: str, components: list[str]):
        self.project_name = project_name
        self.project_slug = self._generate_slug(project_name)
        self.components = components
    
    def get_template_context(self) -> dict[str, Any]:
        """Generate cookiecutter context from component selections."""
        return {
            "project_name": self.project_name,
            "project_slug": self.project_slug,
            "project_description": f"A production-ready Python application",
            "author_name": "Developer",
            "author_email": "dev@example.com",
            "version": "0.1.0",
            "python_version": "3.11",
            "include_scheduler": "yes" if "scheduler" in self.components else "no",
            "include_worker": "yes" if "worker" in self.components else "no",
            "include_database": "yes" if "database" in self.components else "no",
            "include_cache": "yes" if "cache" in self.components else "no",
        }
    
    def get_template_files(self) -> list[str]:
        """Get list of template files that will be generated."""
        files = []
        
        # Core files (always included)
        files.extend([
            "app/components/backend/main.py",
            "app/components/frontend/main.py",
            "app/core/config.py",
            "app/integrations/main.py",
        ])
        
        # Component-specific files
        if "scheduler" in self.components:
            files.extend([
                "app/components/scheduler/main.py",
                "app/entrypoints/scheduler.py",
                "tests/components/test_scheduler.py",
            ])
        
        if "worker" in self.components:
            files.extend([
                "app/components/worker/queues/system.py",
                "app/components/worker/tasks/system_tasks.py",
                "app/services/load_test.py",
                "tests/services/test_worker_health_registration.py",
            ])
        
        return sorted(files)
```

## CLI Command Structure

### Command Definitions (`__main__.py`)
Commands use Typer with proper validation and error handling:

```python
@app.command()
def init(
    project_name: str = typer.Argument(..., help="Name of the new Aegis Stack project to create"),
    components: str | None = typer.Option(
        None,
        "--components", "-c",
        callback=validate_and_resolve_components,
        help="Comma-separated list of components (redis,worker,scheduler)",
    ),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", "-i/-ni",
        help="Use interactive component selection"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing directory if it exists"),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", help="Directory to create the project in"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Initialize a new Aegis Stack project with battle-tested component combinations."""
    
    # Validate project name first
    validate_project_name(project_name)
    
    # Show project configuration
    show_project_configuration(project_name, components, output_dir)
    
    # Confirm before proceeding
    if not yes and not typer.confirm("🚀 Create this project?"):
        typer.echo("❌ Project creation cancelled")
        raise typer.Exit(0)
    
    # Create project using cookiecutter
    create_project_with_cookiecutter(project_name, components, output_dir, force)
```

### Interactive Selection Patterns
```python
def interactive_component_selection() -> list[str]:
    """Interactive component selection with dependency awareness."""
    
    typer.echo("🎯 Component Selection")
    typer.echo("=" * 40)
    typer.echo("✅ Core components (backend + frontend) included automatically\\n")
    
    selected = []
    
    # Infrastructure components
    typer.echo("🏗️  Infrastructure Components:")
    if typer.confirm("  Add Redis (caching, message queues)?"):
        selected.append("redis")
    
    if "redis" in selected:
        if typer.confirm("  Add worker infrastructure (background tasks)?"):
            selected.append("worker")
    else:
        if typer.confirm("  Add worker infrastructure? (will auto-add Redis)"):
            selected.extend(["redis", "worker"])
    
    if typer.confirm("  Add scheduler infrastructure (scheduled tasks)?"):
        selected.append("scheduler")
    
    return selected
```

## CLI Error Handling Patterns

### Validation Callbacks
```python
def validate_and_resolve_components(
    ctx: typer.Context, param: typer.CallbackParam, value: str | None
) -> list[str] | None:
    """Validate and resolve component dependencies."""
    if not value:
        return None
    
    # Parse comma-separated string
    components_raw = [c.strip() for c in value.split(",")]
    
    # Check for empty components
    if any(not c for c in components_raw):
        typer.echo("❌ Empty component name is not allowed", err=True)
        raise typer.Exit(1)
    
    selected = [c for c in components_raw if c]
    
    # Validate components exist
    errors = DependencyResolver.validate_components(selected)
    if errors:
        for error in errors:
            typer.echo(f"❌ {error}", err=True)
        raise typer.Exit(1)
    
    # Resolve dependencies
    resolved = DependencyResolver.resolve_dependencies(selected)
    
    # Show dependency resolution
    auto_added = DependencyResolver.get_missing_dependencies(selected)
    if auto_added:
        typer.echo(f"📦 Auto-added dependencies: {', '.join(auto_added)}")
    
    return resolved
```

### Error Message Quality
```python
def show_helpful_error(component: str, available: list[str]) -> None:
    """Show helpful error message with suggestions."""
    # Suggest similar components using fuzzy matching
    suggestion = find_closest_match(component, available)
    
    if suggestion:
        typer.echo(f"❌ Unknown component '{component}'. Did you mean '{suggestion}'?", err=True)
    else:
        typer.echo(f"❌ Unknown component '{component}'.", err=True)
    
    typer.echo(f"   Available components: {', '.join(available)}", err=True)
    typer.echo("   Use 'aegis components' to see detailed information", err=True)
```

## CLI Development Best Practices

### Command Design
1. **Clear naming** - Use descriptive command and option names
2. **Helpful descriptions** - Provide clear help text for all commands
3. **Sensible defaults** - Choose good default values for options
4. **Progressive disclosure** - Show basic options first, advanced options with help
5. **Consistent patterns** - Use similar patterns across commands

### Validation Strategy
1. **Early validation** - Validate inputs as early as possible
2. **Clear error messages** - Provide actionable error messages
3. **Helpful suggestions** - Suggest corrections when possible
4. **Context-aware errors** - Show relevant information in errors
5. **Graceful degradation** - Handle edge cases gracefully

### User Experience
1. **Interactive guidance** - Provide interactive help when possible
2. **Visual feedback** - Use emojis and formatting for clarity
3. **Progress indication** - Show progress for long-running operations
4. **Confirmation prompts** - Ask before destructive operations
5. **Escape hatches** - Provide ways to cancel or undo operations

### Code Organization
1. **Separation of concerns** - Keep CLI logic separate from business logic
2. **Reusable functions** - Extract common patterns into functions
3. **Type safety** - Use proper type hints throughout
4. **Error handling** - Handle all possible error conditions
5. **Testing support** - Design code to be easily testable

## CLI Testing Patterns

### Command Testing
```python
def test_component_validation():
    """Test component validation logic."""
    # Valid components
    assert validate_components(["worker", "scheduler"]) == []
    
    # Invalid components
    errors = validate_components(["invalid"])
    assert "Unknown component 'invalid'" in errors[0]
    
    # Suggestions
    errors = validate_components(["schedul"])
    assert "Did you mean 'scheduler'?" in errors[0]
```

### Integration Testing
```python
def test_project_generation():
    """Test full project generation workflow."""
    with tempfile.TemporaryDirectory() as temp_dir:
        result = run_aegis_init(
            "test-project",
            ["worker"],
            Path(temp_dir)
        )
        
        assert result.success
        assert (result.project_path / "app" / "components" / "worker").exists()
        assert (result.project_path / "docker-compose.yml").exists()
```

This approach ensures the CLI is maintainable, user-friendly, and follows established patterns for command-line tool development.