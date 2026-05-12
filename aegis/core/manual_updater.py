"""
Manual project update mechanism (Copier-lite).

This module provides manual component addition/removal without relying on
Copier's git-dependent update mechanism. It directly renders Jinja2 templates
and copies files to the target project.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Any

import typer
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from pydantic import BaseModel, Field

from aegis.config.shared_files import SHARED_TEMPLATE_FILES
from aegis.constants import AnswerKeys, ComponentNames, StorageBackends
from aegis.i18n import t

from .component_files import get_component_files, get_copier_defaults, get_template_path
from .copier_manager import is_copier_project, load_copier_answers
from .plugins.template_resolver import get_plugin_template_root
from .verbosity import verbose_print

# Constants
COPIER_ANSWERS_FILE = ".copier-answers.yml"
COPIER_ANSWERS_HEADER = (
    "# Changes here will be overwritten by Copier; NEVER EDIT MANUALLY\n"
)
PROJECT_SLUG_PLACEHOLDER = "{{ project_slug }}"
JINJA_EXTENSION = ".jinja"

# Files with conditional content that should be regenerated when components change.
# These files are not user-editable and contain Jinja conditionals that depend on
# which components/services are enabled.
REGENERATE_ON_COMPONENT_CHANGE = {
    "app/components/backend/api/deps.py",
    "app/components/backend/api/routing.py",
}


def _is_empty_stub(path: Path) -> bool:
    """Return True if the file at ``path`` has no meaningful Python content.

    Files left behind by a previous init where the owning service's
    templates were gated off render as 0-byte or whitespace-only files.
    ``add_component`` should treat them as fresh rather than preserve
    them as "user files." See issue #686 — Failure A.
    """
    if path.name == "__init__.py":
        return False
    try:
        return not path.read_text().strip()
    except (OSError, UnicodeDecodeError):
        # OSError: races with linting/formatting tools rewriting the file.
        # UnicodeDecodeError: file is binary or non-UTF-8 — treat as
        # non-empty so we never mistake unreadable content for a stub.
        return False


# Directories that should never be swept. Some contain authored content
# that may legitimately be empty (alembic version stubs), some contain
# tooling artefacts (.venv, .git, __pycache__).
_SWEEP_SKIP_DIRS = frozenset(
    {
        ".venv",
        ".git",
        "__pycache__",
        "node_modules",
        "versions",  # alembic/versions
        "__snapshots__",
    }
)


def sweep_empty_stubs(project_path: Path) -> list[str]:
    """Delete 0-byte / whitespace-only ``.py`` files under ``project_path``.

    Whole-file Jinja gates (``{% if include_X %}...{% endif %}``) render
    empty files at init time when the gate is False. Those stubs are
    invisible to per-component manifests, so a later ``add-service``
    won't touch them and the project crashes at import time. This sweep
    is the safety net: any empty ``.py`` that survives generation is
    not authored content, so we delete it. See issue #686 — Failure A.

    ``__init__.py`` files are preserved (empty is the *expected* state
    for a package marker). Skips ``.venv``, ``.git``, ``__pycache__``,
    ``node_modules``, ``alembic/versions/`` (one-line stubs are valid
    there), and snapshot directories. Removes any parent directory that
    becomes empty as a result.

    Returns the list of deleted paths, relative to ``project_path``.
    """
    deleted: list[str] = []
    affected_parents: set[Path] = set()

    for path in project_path.rglob("*.py"):
        # Symlinks are not ours to delete — skip.
        if path.is_symlink():
            continue
        if any(
            part in _SWEEP_SKIP_DIRS for part in path.relative_to(project_path).parts
        ):
            continue
        if not _is_empty_stub(path):
            continue
        try:
            path.unlink()
        except OSError:
            continue
        deleted.append(str(path.relative_to(project_path)))
        affected_parents.add(path.parent)

    # Walk parents bottom-up; an emptied dir may empty its own parent.
    for parent in sorted(affected_parents, key=lambda p: len(p.parts), reverse=True):
        current = parent
        while current != project_path and current.exists():
            try:
                if any(current.iterdir()):
                    break
                current.rmdir()
            except OSError:
                break
            current = current.parent

    return deleted


# Files with Jinja conditionals that depend on auth level (basic/rbac/org).
# Must be regenerated when upgrading auth level.
REGENERATE_ON_AUTH_LEVEL_CHANGE = {
    "app/models/user.py",
    "app/models/org.py",
    "app/core/security.py",
    "app/services/auth/auth_service.py",
    "app/services/auth/org_service.py",
    "app/services/auth/membership_service.py",
    "app/services/auth/invite_service.py",
    "app/components/backend/api/auth/router.py",
    "app/components/backend/api/orgs/router.py",
    "app/components/backend/api/orgs/__init__.py",
    "app/components/backend/api/deps.py",
    "app/components/frontend/dashboard/modals/auth_modal.py",
    "app/components/frontend/dashboard/modals/auth_users_tab.py",
    "app/components/frontend/dashboard/modals/auth_orgs_tab.py",
    "tests/services/test_org_integration.py",
    "tests/api/test_org_endpoints.py",
}


class UpdateResult(BaseModel):
    """Result of a component update operation."""

    component: str = Field(description="Component that was updated")
    files_modified: list[str] = Field(
        default_factory=list, description="Files that were created/modified"
    )
    files_deleted: list[str] = Field(
        default_factory=list, description="Files that were deleted"
    )
    files_skipped: list[str] = Field(
        default_factory=list, description="Files that already existed and were skipped"
    )
    shared_files_updated: list[str] = Field(
        default_factory=list, description="Shared template files that were regenerated"
    )
    shared_files_backed_up: list[str] = Field(
        default_factory=list,
        description="Shared files that were backed up before update",
    )
    shared_files_need_manual_merge: list[str] = Field(
        default_factory=list, description="Shared files that need manual merging"
    )
    success: bool = Field(description="Whether the operation succeeded")
    error_message: str | None = Field(
        default=None, description="Error message if operation failed"
    )


class ManualUpdater:
    """
    Manual project updater that bypasses Copier's update mechanism.

    This class provides component addition/removal by:
    1. Reading current state from .copier-answers.yml
    2. Rendering Jinja2 templates with updated context
    3. Copying rendered files to project
    4. Updating .copier-answers.yml
    5. Running post-generation tasks
    """

    def __init__(self, project_path: Path):
        """
        Initialize updater for a project.

        Args:
            project_path: Path to the Aegis Stack project

        Raises:
            FileNotFoundError: If project is not a Copier-generated project
        """
        if not is_copier_project(project_path):
            raise FileNotFoundError(
                f"Project at {project_path} was not generated with Copier"
            )

        self.project_path = project_path
        self.template_path = get_template_path()

        # Backfill missing answer keys with copier.yml defaults before any
        # rendering. Without this, undefined variables (e.g. ollama_mode missing
        # from older projects) cause Jinja2 conditionals to inject unrelated
        # component code. See: #504
        copier_defaults = get_copier_defaults()
        self.answers = {**copier_defaults, **load_copier_answers(project_path)}

        # Heal answer-file drift before any shared-file regen consumes
        # ``self.answers``. Without this, a project whose
        # ``.copier-answers.yml`` is missing flags for an already-
        # installed service (e.g. ``include_insights``) regenerates
        # ``app/core/config.py`` with the wrong shape and drops env-
        # bound Settings fields. See issue #686 — Failure B.
        #
        # Only fill keys that are absent from the *persisted* answers
        # file. An explicit ``include_database: false`` written by
        # Copier must not be flipped to True just because the project
        # happens to have an ``alembic/`` dir hanging around — that
        # would over-promote and break the normal add-component path.
        persisted_keys = set(load_copier_answers(project_path).keys())
        reconciled = {
            k: v
            for k, v in self.reconcile_answers_from_disk().items()
            if k not in persisted_keys
        }
        if reconciled:
            self.answers = {**self.answers, **reconciled}
            self._save_answers(self.answers)

        # Setup Jinja2 environment
        # Template files are at: template/{{ project_slug }}/...
        # We need to point to the template root
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_path)),
            trim_blocks=False,  # Preserve newlines after blocks (matches Copier default)
            lstrip_blocks=False,  # Preserve whitespace for parity
        )

    def add_component(
        self,
        component: str,
        additional_data: dict[str, Any] | None = None,
        *,
        run_post_gen: bool = True,
    ) -> UpdateResult:
        """
        Add a component to the project.

        Args:
            component: Component name (e.g., "scheduler", "worker")
            additional_data: Additional configuration data (e.g., scheduler_backend)
            run_post_gen: When False, skip the trailing ``uv sync`` + ``make fix``
                pass. Used by orchestrators (the plugin resolver flow) that batch
                multiple installs and want to amortise post-gen across the whole
                operation by calling :meth:`run_post_generation_tasks` once at
                the end.

        Returns:
            UpdateResult with files modified/skipped

        Raises:
            ValueError: If component is already enabled or no files found
        """
        files_modified: list[str] = []
        files_skipped: list[str] = []
        shared_files_updated: list[str] = []
        shared_files_backed_up: list[str] = []
        shared_files_need_manual_merge: list[str] = []

        try:
            # Check if already enabled
            include_key = AnswerKeys.include_key(component)
            if self.answers.get(include_key) is True:
                # Allow auth level upgrades (basic → rbac → org)
                is_auth_upgrade = (
                    component == AnswerKeys.SERVICE_AUTH
                    and additional_data
                    and AnswerKeys.AUTH_LEVEL in additional_data
                )
                if not is_auth_upgrade:
                    raise ValueError(f"Component '{component}' is already enabled")

            # Merge additional data
            update_data = additional_data or {}
            update_data[include_key] = True

            # Update answers with new component
            updated_answers = {**self.answers, **update_data}

            # Get files for this component
            backend_variant = (
                update_data.get(AnswerKeys.SCHEDULER_BACKEND)
                if component == ComponentNames.SCHEDULER
                else None
            )
            component_files = get_component_files(component, backend_variant)

            # Some components (like Redis) have no template files - they only
            # configure Docker services and dependencies via shared files
            rendered_files: dict[Path, str] = {}

            if not component_files:
                verbose_print(
                    f"   Component '{component}' has no template files "
                    f"(configured via shared files only)"
                )
                # Continue to regenerate shared files even if no component files
            else:
                # Render and copy each file for this component
                typer.secho(
                    f"   {t('updater.processing_files', count=len(component_files))}",
                    fg=typer.colors.CYAN,
                )
                for file_path in component_files:
                    # Convert relative path to template path
                    # copier_files: "app/components/scheduler"
                    # template_file: "{{ project_slug }}/app/components/scheduler.jinja"
                    template_file = f"{PROJECT_SLUG_PLACEHOLDER}/{file_path}"

                    # Try with .jinja extension first, then without
                    content = self._render_template_file(template_file, updated_answers)

                    if content is not None:
                        # Output path in project
                        output_path = self.project_path / file_path
                        rendered_files[output_path] = content
                    else:
                        typer.secho(
                            f"   Warning: Template not found for: {file_path}",
                            fg=typer.colors.YELLOW,
                        )

                # Copy files to project
                for output_path, content in rendered_files.items():
                    # Create parent directories
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    relative_path = str(output_path.relative_to(self.project_path))

                    # Check for conflicts
                    if output_path.exists():
                        # Some files have conditional content and must be regenerated
                        is_auth_upgrade = (
                            additional_data
                            and AnswerKeys.AUTH_LEVEL in additional_data
                            and relative_path in REGENERATE_ON_AUTH_LEVEL_CHANGE
                        )
                        # Existing-but-empty files are empty stubs left behind
                        # by an earlier init where this service's templates
                        # were gated off. They're not user content, so
                        # treat them as fresh and write the rendered body.
                        # See issue #686 — Failure A.
                        is_empty_stub = _is_empty_stub(output_path)
                        if (
                            relative_path in REGENERATE_ON_COMPONENT_CHANGE
                            or is_auth_upgrade
                            or is_empty_stub
                        ):
                            output_path.write_text(content)
                            verbose_print(f"   Regenerated: {relative_path}")
                            files_modified.append(relative_path)
                            continue

                        # For other files, skip existing to preserve user changes
                        verbose_print(f"   Skipping existing file: {relative_path}")
                        files_skipped.append(relative_path)
                        continue

                    # Write file
                    output_path.write_text(content)
                    verbose_print(f"   Created: {relative_path}")
                    files_modified.append(relative_path)

            # Regenerate shared template files with updated component configuration
            (
                shared_files_updated,
                shared_files_backed_up,
                shared_files_need_manual_merge,
            ) = self._regenerate_shared_files(updated_answers)

            # Update .copier-answers.yml
            self._save_answers(updated_answers)

            # Sweep any empty .py stubs left by whole-file Jinja gates.
            # Must run AFTER shared-file regen — regen may legitimately
            # turn a previously-empty file into a populated one (e.g.
            # auth's deps.py going from gated-off to gated-on). See
            # issue #686 — Failure A.
            files_deleted = sweep_empty_stubs(self.project_path)

            if run_post_gen:
                self.run_post_generation_tasks()

            return UpdateResult(
                component=component,
                files_modified=files_modified,
                files_skipped=files_skipped,
                files_deleted=files_deleted,
                shared_files_updated=shared_files_updated,
                shared_files_backed_up=shared_files_backed_up,
                shared_files_need_manual_merge=shared_files_need_manual_merge,
                success=True,
            )

        except Exception as e:
            return UpdateResult(
                component=component,
                files_modified=files_modified,
                files_skipped=files_skipped,
                success=False,
                error_message=str(e),
            )

    def add_service(
        self,
        service: str,
        additional_data: dict[str, Any] | None = None,
        *,
        run_post_gen: bool = True,
    ) -> UpdateResult:
        """Install a service: write its files, then run its migrations.

        Services are stored alongside components in the registry, so the
        file-rendering half of the install reuses :meth:`add_component`.
        What's different is the **migration tail**: services that ship
        a ``MIGRATION_SPECS`` entry (auth, ai-with-sqlite, insights, ...)
        need ``alembic`` bootstrapped, a versioned migration generated,
        and the migration applied. Without this tail the service's
        answer flag is set but its tables don't exist, and the project
        boots into a SQLAlchemy ``OperationalError`` on first request.

        ``add_service_command`` does this manually inline; this method
        gives the resolver flow (``aegis add <plugin>`` resolving
        ``required_services``) the same treatment without re-implementing
        the migration sequence.

        Args:
            service: Service name (e.g., ``"auth"``, ``"insights"``).
            additional_data: Optional config dict (auth level, AI
                backend, etc.). Pass ``None`` for the defaults a
                transitive plugin dep gets.
            run_post_gen: When False, skip the trailing ``uv sync`` +
                ``make fix`` pass — caller will run them once at the
                end of a batched operation.

        Returns the same :class:`UpdateResult` shape as
        :meth:`add_component`. Migration steps are best-effort: if
        bootstrap or generation raises, the result still reports
        success for the file install (the user can re-run migrations
        manually). A failed ``run_migrations`` is logged but doesn't
        fail the install — matching how ``add_service_command`` handles
        the same case.
        """
        # Lazy import — keeps ``ManualUpdater`` from pulling the
        # migration_generator surface (and its alembic deps) at module
        # load time. Only services-with-migrations exercise this path.
        from .migration_generator import (
            MIGRATION_SPECS,
            bootstrap_alembic,
            generate_migration,
            service_has_migration,
        )
        from .post_gen_tasks import run_migrations

        result = self.add_component(service, additional_data, run_post_gen=False)
        if not result.success:
            return result

        if service in MIGRATION_SPECS:
            alembic_dir = self.project_path / "alembic"
            if not alembic_dir.exists():
                bootstrap_alembic(self.project_path, self.jinja_env, self.answers)
            if not service_has_migration(self.project_path, service):
                generate_migration(self.project_path, service)
            # run_migrations failure is non-fatal — match
            # add_service_command's behaviour. The user can ``alembic
            # upgrade head`` manually later.
            run_migrations(self.project_path, include_migrations=True)

        if run_post_gen:
            self.run_post_generation_tasks()
        return result

    def remove_component(self, component: str) -> UpdateResult:
        """
        Remove a component from the project.

        Args:
            component: Component name to remove

        Returns:
            UpdateResult with files deleted

        Raises:
            ValueError: If component is not enabled
        """
        files_deleted: list[str] = []

        try:
            # Check if enabled
            include_key = AnswerKeys.include_key(component)
            if not self.answers.get(include_key):
                raise ValueError(f"Component '{component}' is not enabled")

            # Get files for this component
            backend_variant = (
                self.answers.get(AnswerKeys.SCHEDULER_BACKEND)
                if component == ComponentNames.SCHEDULER
                else None
            )
            component_files = get_component_files(component, backend_variant)

            # Delete each file
            deleted_paths: list[Path] = []

            for file_path in component_files:
                full_path = self.project_path / file_path

                if full_path.exists():
                    relative_path = str(full_path.relative_to(self.project_path))

                    if full_path.is_dir():
                        shutil.rmtree(full_path)
                        verbose_print(f"   Removed directory: {relative_path}")
                    else:
                        full_path.unlink()
                        verbose_print(f"   Removed file: {relative_path}")

                    files_deleted.append(relative_path)
                    deleted_paths.append(full_path)

            # Clean up empty parent directories
            for file_path in deleted_paths:
                parent = file_path.parent
                try:
                    if parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
                        relative_parent = str(parent.relative_to(self.project_path))
                        verbose_print(f"   Removed empty directory: {relative_parent}")
                except OSError:
                    # Directory not empty or other error, skip
                    pass

            # Update answers
            updated_answers = {**self.answers, include_key: False}

            # Also reset backend variant if removing scheduler
            if component == ComponentNames.SCHEDULER:
                updated_answers[AnswerKeys.SCHEDULER_BACKEND] = StorageBackends.MEMORY
                updated_answers[AnswerKeys.SCHEDULER_WITH_PERSISTENCE] = False

            # Update .copier-answers.yml before regenerating shared files
            self._save_answers(updated_answers)

            # Regenerate shared template files with component removed
            (
                shared_files_updated,
                shared_files_backed_up,
                shared_files_need_manual_merge,
            ) = self._regenerate_shared_files(updated_answers)

            # Run post-generation tasks to clean up dependencies
            self.run_post_generation_tasks()

            return UpdateResult(
                component=component,
                files_deleted=files_deleted,
                shared_files_updated=shared_files_updated,
                shared_files_backed_up=shared_files_backed_up,
                shared_files_need_manual_merge=shared_files_need_manual_merge,
                success=True,
            )

        except Exception as e:
            return UpdateResult(
                component=component,
                files_deleted=files_deleted,
                success=False,
                error_message=str(e),
            )

    def _extract_env_vars(self, content: str) -> dict[str, str]:
        """
        Extract environment variable names and values from .env.example content.

        Args:
            content: Content of .env.example file

        Returns:
            Dictionary mapping variable names to their values (or empty string if commented)
        """
        env_vars: dict[str, str] = {}

        for line in content.split("\n"):
            line = line.strip()

            # Skip blank lines
            if not line:
                continue

            # Handle commented variable definitions FIRST (e.g., "# REDIS_URL=...")
            if line.startswith("# ") and "=" in line:
                var_line = line[2:].strip()  # Remove "# " prefix
                if "=" in var_line:
                    var_name = var_line.split("=")[0].strip()
                    var_value = var_line.split("=", 1)[1].strip()
                    env_vars[var_name] = var_value
                continue

            # Skip other comment-only lines (section headers, descriptions, etc.)
            if line.startswith("#"):
                continue

            # Handle active variable definitions (e.g., "REDIS_URL=...")
            if "=" in line:
                var_name = line.split("=")[0].strip()
                var_value = line.split("=", 1)[1].strip()
                env_vars[var_name] = var_value

        return env_vars

    def _regenerate_shared_files(
        self, updated_answers: dict[str, Any]
    ) -> tuple[list[str], list[str], list[str]]:
        """
        Regenerate shared template files with updated answers.

        Shared files (docker-compose.yml, pyproject.toml, etc.) contain
        conditional logic for components and must be regenerated when
        components are added or removed.

        Args:
            updated_answers: Updated Copier answers with component changes

        Returns:
            Tuple of (updated_files, backed_up_files, need_manual_merge_files)
        """
        shared_files_updated: list[str] = []
        shared_files_backed_up: list[str] = []
        shared_files_need_manual_merge: list[str] = []

        print(f"\n{t('updater.updating_shared')}")
        for shared_file, policy in SHARED_TEMPLATE_FILES.items():
            template_file = f"{PROJECT_SLUG_PLACEHOLDER}/{shared_file}"
            output_path = self.project_path / shared_file

            # Skip if file doesn't exist (shouldn't happen for shared files)
            if not output_path.exists():
                continue

            # For .env.example, extract variables before and after to show diff
            old_env_vars: dict[str, str] = {}
            if shared_file == ".env.example":
                old_content = output_path.read_text()
                old_env_vars = self._extract_env_vars(old_content)

            # Render template with updated answers
            content = self._render_template_file(template_file, updated_answers)

            if content is None:
                continue  # Template not found

            if policy.get("backup"):
                # Create backup before overwriting
                backup_path = output_path.with_suffix(output_path.suffix + ".backup")
                shutil.copy(output_path, backup_path)
                verbose_print(f"   Backed up: {shared_file}")
                shared_files_backed_up.append(shared_file)

            if policy.get("overwrite"):
                # Regenerate with updated answers
                output_path.write_text(content)
                verbose_print(f"   Updated: {shared_file}")
                shared_files_updated.append(shared_file)

                # Show environment variable changes for .env.example
                if shared_file == ".env.example":
                    new_env_vars = self._extract_env_vars(content)
                    added_vars = {
                        k: v for k, v in new_env_vars.items() if k not in old_env_vars
                    }

                    if added_vars:
                        verbose_print("   New environment variables:")
                        for var_name, var_value in sorted(added_vars.items()):
                            verbose_print(f"      • {var_name}={var_value}")

            elif policy.get("warn"):
                # Only warn if file actually has changes that need manual merge
                existing_content = output_path.read_text()
                if content != existing_content:
                    print(f"   Manual merge required: {shared_file}")
                    shared_files_need_manual_merge.append(shared_file)

        return (
            shared_files_updated,
            shared_files_backed_up,
            shared_files_need_manual_merge,
        )

    def _render_template_file(
        self, template_file: str, context: dict[str, Any]
    ) -> str | None:
        """
        Render a Jinja2 template file.

        Args:
            template_file: Template file path (relative to template root)
            context: Jinja2 context variables

        Returns:
            Rendered content, or None if template not found
        """
        # Render .jinja templates through Jinja2.
        try:
            template = self.jinja_env.get_template(f"{template_file}{JINJA_EXTENSION}")
            return template.render(context)
        except TemplateNotFound:
            pass

        # Non-.jinja files are copied verbatim — same contract Copier uses.
        # Rendering them through Jinja2 breaks any source that legitimately
        # contains brace syntax (Python f-string {{...}} escapes, Alpine/HTMX
        # attributes, CSS in inline strings, etc.).
        raw_path = self.template_path / template_file
        if raw_path.is_file():
            return raw_path.read_text()
        return None

    def install_plugin_template_tree(self, plugin_module_name: str) -> list[str]:
        """Render the plugin's template tree into the project.

        Plugins ship a ``<package>/templates/{{ project_slug }}/...``
        directory parallel to aegis-stack's own. This method locates
        that tree via :func:`aegis.core.plugins.template_resolver.get_plugin_template_root`,
        renders every ``*.jinja`` file through a fresh Jinja2 environment
        rooted at the plugin's templates dir (so ``include`` / ``extends``
        resolve against the plugin's tree, not aegis-stack's), and writes
        the rendered output at the corresponding relative path under
        ``self.project_path``.

        The render context is the project's current ``self.answers``,
        so plugin templates can branch on the same project state that
        aegis-stack templates do (``include_database``, ``database_engine``,
        etc.).

        Returns the list of relative paths written. Empty list when the
        plugin ships no templates (pure-code plugin).

        Existing files are overwritten. Per-file conflict policy lives at
        the calling level (``aegis add`` in round 8b); for now this is
        used by tests and by future ``aegis add`` once it lands.

        **Filesystem-only.** Uses ``Path.rglob`` and ``FileSystemLoader``
        on the resolver's returned path, which requires a real on-disk
        directory. Zipped wheels are not supported today — see
        ``aegis.core.plugins.template_resolver`` for the rationale.
        """
        template_root = get_plugin_template_root(plugin_module_name)
        if template_root is None:
            return []

        # Plugin templates mirror aegis-stack's: every file is nested
        # under ``{{ project_slug }}/`` so the rendered path is naturally
        # rooted at the project tree.
        project_slug_dir = template_root / PROJECT_SLUG_PLACEHOLDER
        if not project_slug_dir.is_dir():
            return []

        plugin_env = Environment(
            loader=FileSystemLoader(str(template_root)),
            trim_blocks=False,
            lstrip_blocks=False,
        )

        files_written: list[str] = []
        for source_file in sorted(project_slug_dir.rglob(f"*{JINJA_EXTENSION}")):
            # Path relative to the project slug dir → relative path
            # inside the target project. Strip the ``.jinja`` suffix
            # since the rendered file shouldn't keep it.
            rel_inside_slug = source_file.relative_to(project_slug_dir)
            out_rel = rel_inside_slug.with_suffix("")
            out_path = self.project_path / out_rel

            # Jinja2 needs the template name relative to the loader's
            # root (template_root, not project_slug_dir) so it can
            # resolve includes against sibling files.
            template_name = str(source_file.relative_to(template_root))
            template = plugin_env.get_template(template_name)
            content = template.render(self.answers)

            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content)
            files_written.append(str(out_rel))

        return files_written

    def remove_plugin(self, spec: Any) -> UpdateResult:
        """Uninstall a plugin from the project.

        Mirror of :meth:`add_plugin`:

        1. Drop the plugin's ``_plugins[i]`` entry from answers and
           persist.
        2. Regenerate shared template files so the plugin's wiring no
           longer appears in routes / cards / modals / etc.
        3. Apply :class:`FileManifest` cleanup to remove the plugin's
           own files from the project tree.
        4. Run post-generation tasks (``uv sync`` to drop deps).

        Migrations are intentionally NOT rolled back — matches the
        existing ``aegis remove-service`` behaviour. Database tables
        belonging to the plugin remain in place; users can drop them
        manually via ``alembic downgrade`` if desired.

        Returns an :class:`UpdateResult`. ``success=False`` with a
        clear error message if the plugin isn't currently installed.
        """
        from .file_manifest import apply_cleanup_path, iter_cleanup_paths
        from .plugins.composer import PLUGINS_ANSWER_KEY

        files_deleted: list[str] = []
        try:
            # Normalise legacy entries — pre-Round-8 ``_plugins`` data
            # could be a list of strings (``"plugin>=1.0"``); only
            # dict-shaped entries carry a ``name`` field. Filter to the
            # safe shape before reading / rewriting.
            raw_plugins = self.answers.get(PLUGINS_ANSWER_KEY) or []
            existing_plugins: list[dict[str, Any]] = [
                p for p in raw_plugins if isinstance(p, dict)
            ]
            if not any(p.get("name") == spec.name for p in existing_plugins):
                raise ValueError(
                    f"Plugin {spec.name!r} is not installed in this project"
                )

            # Drop the plugin from answers + persist before any disk
            # cleanup. If the cleanup fails the answers still reflect
            # reality; a re-run picks up where we left off.
            updated_plugins = [
                p for p in existing_plugins if p.get("name") != spec.name
            ]
            updated_answers = {**self.answers, PLUGINS_ANSWER_KEY: updated_plugins}
            self._save_answers(updated_answers)

            # Shared file regen — plugin's wiring is no longer in
            # ``_plugins``, so loops emit nothing for it.
            (
                shared_updated,
                shared_backed_up,
                shared_manual_merge,
            ) = self._regenerate_shared_files(updated_answers)

            # Plugin's own files. ``FileManifest.iter_cleanup_paths``
            # with ``selected=False`` walks the manifest as if the
            # plugin were never selected, yielding everything to
            # delete.
            for rel_path in iter_cleanup_paths(spec, selected=False):
                target = self.project_path / rel_path
                if not target.exists():
                    continue
                apply_cleanup_path(self.project_path, rel_path)
                files_deleted.append(rel_path)

            self.run_post_generation_tasks()

            return UpdateResult(
                component=spec.name,
                files_deleted=files_deleted,
                shared_files_updated=shared_updated,
                shared_files_backed_up=shared_backed_up,
                shared_files_need_manual_merge=shared_manual_merge,
                success=True,
            )
        except Exception as e:
            return UpdateResult(
                component=spec.name,
                files_deleted=files_deleted,
                success=False,
                error_message=str(e),
            )

    def add_plugin(
        self,
        spec: Any,
        plugin_module_name: str,
        plugin_options: dict[str, Any] | None = None,
        *,
        run_post_gen: bool = True,
    ) -> UpdateResult:
        """Install a plugin into the project.

        Higher-level than :meth:`install_plugin_template_tree` —
        this is the full ``aegis add <plugin>`` operation:

        1. Serialise the plugin spec into a ``_plugins[i]`` entry
           (predicates evaluated against the merged opts dict, see
           ``plugin_composer``).
        2. Append it to ``self.answers["_plugins"]`` and persist.
        3. Regenerate shared template files so the new plugin loops
           emit imports / wiring for this plugin.
        4. Drop the plugin's own template tree into the project.
        5. Run post-generation tasks (``uv sync`` + format), unless the
           caller asked to defer them via ``run_post_gen=False``.

        Returns an :class:`UpdateResult` describing the surface area
        that changed. Existing plugin entries with the same name are
        replaced (idempotent).

        ``run_post_gen=False`` is used by the resolver flow in
        ``aegis add`` — it batches multiple component / service /
        plugin installs and runs ``uv sync`` + ``make fix`` exactly
        once at the end (avoids the N+1 sync that nesting would
        otherwise produce).
        """
        from .plugins.composer import PLUGINS_ANSWER_KEY, serialize_plugin_to_answer

        files_modified: list[str] = []
        try:
            # Normalise legacy entries — see ``remove_plugin`` for the
            # full rationale. Same filter; same intent.
            raw_plugins = self.answers.get(PLUGINS_ANSWER_KEY) or []
            existing_plugins: list[dict[str, Any]] = [
                p for p in raw_plugins if isinstance(p, dict)
            ]
            # Idempotent: same plugin name replaces an existing entry
            # rather than duplicating. Plugin authors who want re-add
            # semantics use ``aegis remove`` + ``aegis add`` explicitly.
            existing_plugins = [
                p for p in existing_plugins if p.get("name") != spec.name
            ]

            entry = serialize_plugin_to_answer(
                spec,
                plugin_options=plugin_options,
                project_answers=self.answers,
            )
            existing_plugins.append(entry)

            updated_answers = {**self.answers, PLUGINS_ANSWER_KEY: existing_plugins}

            # Persist BEFORE regenerating shared files so subsequent
            # ManualUpdater operations (and tests) see the plugin in
            # answers from disk.
            self._save_answers(updated_answers)

            # Shared file regen — uses ``self.answers`` (now includes
            # the new plugin) so ``{% for p in _plugins %}`` loops emit
            # this plugin's wiring entries.
            (
                shared_updated,
                shared_backed_up,
                shared_manual_merge,
            ) = self._regenerate_shared_files(updated_answers)
            files_modified.extend(shared_updated)

            # Plugin's own template tree.
            plugin_files = self.install_plugin_template_tree(plugin_module_name)
            files_modified.extend(plugin_files)

            # Post-gen — uv sync picks up the plugin's pyproject deps,
            # make fix re-formats anything we touched. Skipped when the
            # caller (resolver flow) is batching installs and will run
            # post-gen once at the end.
            if run_post_gen:
                self.run_post_generation_tasks()

            return UpdateResult(
                component=spec.name,
                files_modified=files_modified,
                shared_files_updated=shared_updated,
                shared_files_backed_up=shared_backed_up,
                shared_files_need_manual_merge=shared_manual_merge,
                success=True,
            )
        except Exception as e:
            return UpdateResult(
                component=spec.name,
                files_modified=files_modified,
                success=False,
                error_message=str(e),
            )

    def _save_answers(self, answers: dict[str, Any]) -> None:
        """
        Save updated answers to .copier-answers.yml.

        Args:
            answers: Updated answers dictionary
        """
        import yaml

        answers_file = self.project_path / COPIER_ANSWERS_FILE

        # Preserve metadata
        answers_with_meta = {
            **answers,
            "_commit": answers.get("_commit", "None"),
            "_src_path": answers.get("_src_path", str(self.template_path)),
        }

        with open(answers_file, "w") as f:
            f.write(COPIER_ANSWERS_HEADER)
            yaml.safe_dump(
                answers_with_meta, f, default_flow_style=False, sort_keys=False
            )

        self.answers = answers

    def reconcile_answers_from_disk(self) -> dict[str, Any]:
        """Infer ``include_*`` / ``auth_level`` flags from filesystem markers.

        Some legacy projects have a ``.copier-answers.yml`` that is
        missing flags for services that are actually installed on disk
        (we've seen this with ``include_insights`` and its sub-flags).
        When that happens, ``_regenerate_shared_files`` renders shared
        templates with the wrong gating and drops env-bound Settings
        fields, which causes Pydantic ``extra_forbidden`` crashes on
        boot. See issue #686 — Failure B.

        This method walks well-known marker paths and returns a dict
        of flags to set ``True`` (or, for ``auth_level``, the inferred
        level). It only ever **promotes** — never demotes a flag that
        is already ``True`` in answers — because file presence is a
        strong "installed" signal but absence isn't a reliable "not
        installed" signal (a service could have been partially removed
        manually).
        """
        proj = self.project_path
        inferred: dict[str, Any] = {}

        def has_file(*relative: str) -> bool:
            full = proj
            for part in relative:
                full = full / part
            return full.is_file()

        def has_nonstub_dir(*relative: str) -> bool:
            full = proj
            for part in relative:
                full = full / part
            if not full.is_dir():
                return False
            for child in full.rglob("*.py"):
                if child.name == "__init__.py":
                    continue
                try:
                    if child.read_text().strip():
                        return True
                except (OSError, UnicodeDecodeError):
                    continue
            return False

        # Services
        if has_file("app", "services", "auth", "auth_service.py"):
            inferred[AnswerKeys.AUTH] = True
        if has_file("app", "services", "ai", "ai_service.py"):
            inferred[AnswerKeys.AI] = True
        if has_nonstub_dir("app", "services", "insights"):
            inferred[AnswerKeys.INSIGHTS] = True
        if has_nonstub_dir("app", "services", "blog"):
            inferred[AnswerKeys.BLOG] = True
        if has_nonstub_dir("app", "services", "payment"):
            inferred[AnswerKeys.PAYMENT] = True
        if has_nonstub_dir("app", "services", "comms"):
            inferred[AnswerKeys.COMMS] = True

        # Components
        if (proj / "alembic").is_dir() or has_nonstub_dir("app", "models"):
            inferred[AnswerKeys.DATABASE] = True
        if has_nonstub_dir("app", "components", "scheduler"):
            inferred[AnswerKeys.SCHEDULER] = True
        if has_nonstub_dir("app", "components", "worker"):
            inferred[AnswerKeys.WORKER] = True
        if has_nonstub_dir("app", "components", "backend", "observability"):
            inferred[AnswerKeys.OBSERVABILITY] = True
        if has_nonstub_dir("app", "components", "backend", "ingress"):
            inferred[AnswerKeys.INGRESS] = True

        # Auth level — only meaningful if auth itself is installed.
        # RBAC is gated by inline ``{% if include_auth_rbac %}`` blocks
        # in existing files rather than a dedicated module, so we sniff
        # ``def require_role`` in the rendered auth_service.py — that
        # symbol is only emitted when RBAC is on. Org is detected via
        # the org_service.py module (whole-file gated).
        if inferred.get(AnswerKeys.AUTH) or self.answers.get(AnswerKeys.AUTH):
            auth_svc = proj / "app" / "services" / "auth" / "auth_service.py"
            has_require_role = False
            if auth_svc.is_file():
                try:
                    has_require_role = "def require_role" in auth_svc.read_text()
                except (OSError, UnicodeDecodeError):
                    has_require_role = False
            if has_file("app", "services", "auth", "org_service.py"):
                inferred[AnswerKeys.AUTH_LEVEL] = "org"
                inferred[AnswerKeys.AUTH_ORG] = True
                inferred[AnswerKeys.AUTH_RBAC] = True
            elif has_require_role:
                inferred[AnswerKeys.AUTH_LEVEL] = "rbac"
                inferred[AnswerKeys.AUTH_RBAC] = True

        # Auth OAuth marker — file may exist as a non-stub when oauth was wired
        if has_file("app", "components", "backend", "api", "auth", "oauth.py"):
            oauth_path = (
                proj / "app" / "components" / "backend" / "api" / "auth" / "oauth.py"
            )
            try:
                if oauth_path.read_text().strip():
                    inferred[AnswerKeys.AUTH_OAUTH] = True
            except (OSError, UnicodeDecodeError):
                pass

        # Insights sub-flags
        collectors_dir = proj / "app" / "services" / "insights" / "collectors"
        if collectors_dir.is_dir():
            for source, key in (
                ("github", AnswerKeys.INSIGHTS_GITHUB),
                ("pypi", AnswerKeys.INSIGHTS_PYPI),
                ("plausible", AnswerKeys.INSIGHTS_PLAUSIBLE),
                ("reddit", AnswerKeys.INSIGHTS_REDDIT),
            ):
                if (collectors_dir / f"{source}_collector.py").is_file():
                    inferred[key] = True

        return inferred

    def run_post_generation_tasks(self) -> None:
        """
        Run post-generation tasks (uv sync, make fix).

        Public so callers that batch multiple ``add_*`` operations
        (e.g. the plugin resolver flow in ``aegis add``) can defer
        sync/format with ``run_post_gen=False`` per call and invoke
        this exactly once at the end of the whole operation.

        This ensures:
        - Dependencies are updated
        - Code is auto-formatted
        - Imports are organized
        """
        print(f"\n{t('updater.running_postgen')}")

        # Run uv sync to update dependencies
        try:
            subprocess.run(
                ["uv", "sync", "--all-extras"],
                cwd=self.project_path,
                check=True,
                capture_output=True,
            )
            print(f"   {t('updater.deps_synced')}")
        except subprocess.CalledProcessError as e:
            print(f"   Warning: Failed to sync dependencies: {e}")

        # Run make fix to auto-format code
        try:
            subprocess.run(
                ["make", "fix"],
                cwd=self.project_path,
                check=True,
                capture_output=True,
            )
            print(f"   {t('updater.code_formatted')}")
        except subprocess.CalledProcessError:
            typer.echo(
                "   "
                + typer.style("Warning:", fg=typer.colors.YELLOW)
                + " "
                + typer.style("make fix", fg=typer.colors.CYAN)
                + " had issues. Run it manually to see details."
            )


def add_component_manual(
    project_path: Path,
    component: str,
    additional_data: dict[str, Any] | None = None,
) -> None:
    """
    Convenience function to add a component to a project.

    Args:
        project_path: Path to the Aegis Stack project
        component: Component name
        additional_data: Additional configuration data
    """
    updater = ManualUpdater(project_path)
    updater.add_component(component, additional_data)


def remove_component_manual(project_path: Path, component: str) -> None:
    """
    Convenience function to remove a component from a project.

    Args:
        project_path: Path to the Aegis Stack project
        component: Component name
    """
    updater = ManualUpdater(project_path)
    updater.remove_component(component)
