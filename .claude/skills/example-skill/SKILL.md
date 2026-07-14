---
name: example-skill
description: Use when you need the canonical shape of an Aegis Stack skill, or as the copy-from starting point for a new skill. Demonstrates every required section; not a real workflow.
---

# Example skill

This skill exists to validate and demonstrate the house format defined in
`.claude/skills/README.md`. It is a template, not a real workflow. Copy this
directory, rename it, and replace the placeholder content.

## When to use

Use when starting a new skill and you want a known-good skeleton to fill in, or
when you need to see how the required sections fit together.

Do NOT use for real work. This skill performs no framework change; it only
shows the format.

## Files that change

Grouped by role. A real skill lists exact repo-relative paths here so an agent
opens them without searching. Placeholder example:

- Registry: `aegis/services/registry.py`
- CLI: `aegis/cli/<command>.py`
- Template: `aegis/templates/copier-aegis-project/{{ project_slug }}/...`
- Tests: `tests/<area>/test_<thing>.py`
- Docs: `docs/<page>.md`
- i18n: `aegis/i18n/en.py`

## Procedure

1. Write the failing test first (TDD): add the case to the relevant
   `tests/...` file and confirm it fails for the right reason.
2. Make the change in the registry, CLI, and template files listed above.
3. Backport any change made in a generated project into its template under
   `aegis/templates/`, so it survives the next `aegis init`.
4. Update docs and i18n keys touched by the change.
5. Run the gates below and fix anything red.

## Gates

- `make check` (lint, typecheck, test) must pass.
- `make test-template` must pass when the change touches templates.

## Pitfalls

- Template changes read from the committed git state, not the working tree, so
  an uncommitted template edit will not show up in a freshly generated project.
- A vague frontmatter `description` means the skill never loads, because the
  description is the only thing an agent reads when deciding to use it.
