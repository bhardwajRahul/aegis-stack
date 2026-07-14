# CLAUDE.md

Guidance for Claude Code working in this repository. This file carries only
always-true rules and a skills index. Task procedures live in `.claude/skills/`
and load on demand; see the index at the bottom.

## Hard rules

### No git operations without explicit request
Never run `git add`, `commit`, `push`, or create PRs, and do not run
`git status`/`diff`/`log` as preparation, unless the user explicitly asks. Wait
for explicit approval before any git operation.

### TDD: failing test first
Write the failing test before the implementation, always. Confirm it fails for
the right reason, then implement.

### Templates are the source of truth; backport immediately
`aegis/templates/copier-aegis-project/{{ project_slug }}/` is what ships;
generated projects (often a scratch `my-app/`) are prototypes. Any change made
in a generated project MUST be backported to its template in the same session,
or it is lost on the next `aegis init`. Full workflow: the template-dev skill.

### Scope control
Fix exactly what is asked. No scope creep, no unrequested test suites, minimal
viable change, and verify it works.

### DRY
Before writing new code, look for existing logic used elsewhere; prefer a single
shared function over duplicating it.

## Coding standards

- Types are mandatory: every function fully annotated, including return types
  (`-> None` if none) and parameters (`ctx: dict[str, Any]`). Use `str | None`,
  `dict[str, Any]`, `list[str]` (modern generics), never `Optional`/`Dict`/`List`.
- Functions: small and focused (~20 lines), descriptive names, guard clauses,
  prefer pure functions.
- Errors: specific exception types (never bare `except:`), meaningful messages,
  `from None` where apt, log at the right level. Never silently swallow an error.
- No N+1 queries: never query inside a loop; batch with `WHERE id IN (...)` or
  eager-load with `selectinload()`/`joinedload()`.

## Components vs services

Components (`app/components/`) are infrastructure (backend, frontend, worker,
scheduler, database, redis) and define WHEN/WHERE. Services (`app/services/`)
are business logic (auth, AI, payment, blog, finance) and define WHAT. Both ride
the shared plugin-spec machinery.

## Code navigation

Prefer the language server (Pyright) over grep for symbols: `findReferences`,
`goToDefinition`, `hover`, `documentSymbol`. Use grep/glob for text patterns,
non-Python files, or when the LSP is unavailable.

## Daily commands

- `make check` - lint + typecheck + test; run before considering work done
- `make test-template` - generate and validate a project after template changes
- `make test-stacks-quick` - fast multi-stack smoke (base, everything, insights)

The Makefile documents the rest (per-component template tests, the full stack
matrix, release targets).

## Skills index

Procedures load on demand from `.claude/skills/<name>/SKILL.md` when the task
matches the skill's description. Reach for:

- `add-service` - add a new business-capability service to the framework
- `add-component` - add a new component, or a variant axis on an existing one
- `i18n` - add or translate locale strings (en.py first, parity across locales)
- `add-cli-command` - add a command to the `aegis` tool CLI
- `release` - cut a version or rc release (bump, gates, TestPyPI, tagging)
- `template-dev` - modify templates, or backport a change from a generated project

See `.claude/skills/README.md` for the skill format; `example-skill` is the
copy-from template.
