---
name: add-model-and-migration
description: Use when adding or changing a database model in this project. Covers the SQLModel table definition, the alembic autogenerate migration flow, and the query rules that keep access performant.
---

# Add model and migration

Database tables are SQLModel classes, and every schema change is captured by an
alembic migration. The model and the migration are two separate artifacts:
changing the model without generating a migration drifts the running schema from
the code.

## When to use

Use when adding a table, adding or changing a column, or adding an index.

Do NOT use for query-only changes that touch no schema (no migration needed), or
for non-database state.

## Files that change

- `app/services/`: models live in a service package as `models.py` (SQLModel
  classes with `table=True`).
- `app/core/model_registry.py`: imports every `models` module under
  `app/models/` and `app/services/<service>/models`, so alembic, `migrate-fix`
  and the tests all see the same tables. Nothing to edit; a table defined
  outside those paths is invisible, and `tests/test_model_registry.py` fails.
- `alembic/versions/`: the generated revision lands here.

## Procedure

1. Write the failing test first (the query or behavior that needs the new
   column or table). Confirm it fails for the right reason.
2. Define or edit the SQLModel class in the service's `models.py`.
3. Keep the class under the service's `models` module or package; the model
   registry imports it, so autogenerate sees it with no further wiring.
4. Derive the migration from the model with
   `uv run python -m app.cli.migrate_gen <service>` (what `aegis add` runs), or
   with alembic autogenerate directly. Open the new file in `alembic/versions/`
   and confirm it contains the intended change and nothing spurious.
5. Confirm nothing drifted: `uv run python -m app.cli.migrate_gen --check`
   replays every revision onto a scratch database and prints what still
   differs from the models. Empty output is the goal, and
   `tests/test_model_registry.py` asserts it.
6. Run the gates and fix anything red.

## Gates

- `make check`: lint, typecheck, and test.

## Pitfalls

- Never query inside a loop (N+1): batch with `WHERE id IN (...)` or eager-load
  relationships with `selectinload()` or `joinedload()`, or the query count
  grows with the row count.
- A table defined outside `app/models/` or `app/services/<service>/models`
  is invisible to autogenerate, because only the registry's paths are imported;
  `tests/test_model_registry.py` reports exactly which module.
- The SQLModel class and the migration are independent; editing one without the
  other leaves the schema and the code out of sync with no error until runtime.
