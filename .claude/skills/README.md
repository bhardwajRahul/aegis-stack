# Skill conventions

Skills are on-demand procedural knowledge for coding agents. Claude Code loads
`.claude/skills/<name>/SKILL.md` when a task matches the skill's frontmatter
`description`. Skills keep recurring workflows (add a service, add a component,
i18n, CLI commands, releases, template development) out of always-loaded context
and out of one developer's session memory, so any agent with this repo can
execute the work.

This document is the house format. It is a conventions reference, not a skill
itself, so it has no frontmatter and never loads as a skill.

## Layout

- One skill per directory: `.claude/skills/<kebab-name>/SKILL.md`.
- The directory name is the skill name and must be kebab-case.
- `SKILL.md` opens with YAML frontmatter carrying exactly two keys:

  ```yaml
  ---
  name: add-service
  description: Use when adding a new service to the framework. Covers the registry, CLI, template, test, and docs files that must change together.
  ---
  ```

- `name` matches the directory name.
- `description` states the trigger in plain language ("Use when ..."), because
  it is the only text an agent reads when deciding whether to load the skill. A
  vague description means the skill never fires. Lead with the trigger, then say
  what the skill covers.
- Supporting files (checklists, scripts, snippets) may live beside `SKILL.md` in
  the same directory. Reference them by relative path from the skill directory.

## Required sections

Every `SKILL.md` body has these sections, in this order, with these exact H2
headings:

1. `## When to use`
   State the trigger conditions, then state when NOT to use the skill so it is
   not loaded for adjacent-but-different work.

2. `## Files that change`
   Exact repo-relative paths, grouped by role. Use whichever of these groups
   apply: registry, CLI, template, tests, docs, i18n. List the real paths, not
   descriptions of them, so an agent can open them without searching.

3. `## Procedure`
   Numbered steps. TDD-first: the failing test comes before the implementation.
   Each step is an action, not a discussion.

4. `## Gates`
   The `make` targets that must pass before the work counts as done (for
   example `make check`, `make test-template`). Name the exact targets.

5. `## Pitfalls`
   Known traps, one sentence each, including the why. A pitfall without its
   reason is not actionable.

Omit a section only when it genuinely does not apply; do not reorder them.

## Style rules

- Imperative voice: "Add the route", not "You should add the route".
- Compact. Prefer a path or a command over a paragraph describing one.
- No emojis.
- No em-dashes; use commas, parentheses, or rewrite.
- Repo-relative paths only. Never absolute paths, never user- or
  machine-specific references (home directories, personal project locations,
  local ports chosen by one machine).

## Portability rule

A skill describes the repo contract: the files, commands, and gates that define
the work. It never describes one person's environment.

Skills destined for generated projects (see Milestone 2) additionally carry:

- No internal codenames.
- No aegis-stack issue references.

Write every skill as if a stranger's agent, in a fresh checkout on an unknown
machine, will run it. If a line only makes sense on one machine or to one
person, it does not belong in a skill.

## Example

`.claude/skills/example-skill/SKILL.md` is a filled-in skeleton that exercises
every required section. Copy it as the starting point for a new skill, then
replace the placeholder content.
