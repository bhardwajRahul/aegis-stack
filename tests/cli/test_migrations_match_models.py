"""The generated migrations and the generated models describe one schema.

Two oracles, both run inside the generated project's own venv because the
models are not importable from the aegis repo:

1. ``env.py``'s import block reaches every table. Autogenerate only sees
   what that block put in ``SQLModel.metadata``; a module it forgot is a
   table ``migrate-fix`` will never grow, silently.
2. Applying every generated revision in order, then comparing the database
   to the models with alembic's own ``compare_metadata``, yields nothing.
   This is the check the models-as-source migration generator will rely
   on, so it is pinned before that work starts.

``compare_metadata`` does not see ``ondelete`` or check constraints; the
structural parity test (#1054) covers those. This covers columns, types,
nullability, indexes and foreign-key presence, against a real Postgres
(the engine whose reflection is faithful, and where the finance schema exists).
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from .test_utils import run_project_command

pytestmark = [
    pytest.mark.slow,
    pytest.mark.postgres,
    pytest.mark.xdist_group("generated_stacks"),
]

STACKS = {
    "everything": (
        ["database[postgres]", "scheduler", "worker", "redis"],
        ["auth[org]", "ai[sqlite]", "insights", "payment", "blog", "comms"],
    ),
    "finance_auth": (["database[postgres]", "scheduler"], ["auth", "finance"]),
}


def _postgres_available() -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(("localhost", 5432)) == 0


PROBE = r"""
import json, os, re, sys, tempfile, importlib, pkgutil
from pathlib import Path
PW = os.environ.get("POSTGRES_TEST_PASSWORD", "postgres")
DB = os.environ["ORACLE_DB"]
ADMIN = f"postgresql://postgres:{PW}@localhost:5432/postgres"
URL = f"postgresql://postgres:{PW}@localhost:5432/{DB}"
os.environ["DATABASE_URL"] = URL
os.environ["DATABASE_URL_LOCAL"] = URL
os.environ["LOGFIRE_TOKEN"] = ""
from sqlalchemy import create_engine, text
with create_engine(ADMIN, isolation_level="AUTOCOMMIT").connect() as c:
    c.execute(text(f'DROP DATABASE IF EXISTS "{DB}"')); c.execute(text(f'CREATE DATABASE "{DB}"'))

# 1. what the registry (the only registrar, called by env.py) puts in metadata
from app.core.model_registry import import_all_models
import_all_models()
from sqlmodel import SQLModel
seen_by_env = set(SQLModel.metadata.tables)

# 2. every table-bearing module under app/
import app
for m in pkgutil.walk_packages(app.__path__, "app."):
    if ".models" in m.name or m.name.endswith(".usage"):
        try:
            importlib.import_module(m.name)
        except Exception as e:  # noqa: BLE001 - report, do not hide
            print("IMPORT-FAIL", m.name, type(e).__name__, str(e)[:80], file=sys.stderr)
all_tables = set(SQLModel.metadata.tables)

# 3. apply every generated revision, diff against the models
from alembic.config import Config
from alembic import command
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata
cfg = Config("alembic/alembic.ini") if Path("alembic/alembic.ini").exists() else Config("alembic.ini")
cfg.set_main_option("script_location", "alembic")
command.upgrade(cfg, "head")
with create_engine(URL).connect() as conn:
    ctx = MigrationContext.configure(conn, opts={"include_schemas": True, "compare_type": True})
    diffs = compare_metadata(ctx, SQLModel.metadata)
def _name(d):
    d = d[0] if isinstance(d, list) else d
    kind = d[0]
    if kind in ("add_table", "remove_table"):
        return f"{kind} {d[1].name}"
    if kind in ("add_column", "remove_column"):
        return f"{kind} {d[2]}.{d[3].name}"
    if kind == "modify_type":
        return f"{kind} {d[2]}.{d[3]} db={d[5]!r} model={d[6]!r}"
    if kind == "modify_nullable":
        return f"{kind} {d[2]}.{d[3]} db={d[5]} model={d[6]}"
    if kind.startswith("modify_"):
        return f"{kind} {d[2]}.{d[3]}"
    if kind in ("add_index", "remove_index"):
        ix = d[1]
        cols = ",".join(c.name for c in ix.columns)
        return f"{kind} {ix.table.name}({cols}) unique={bool(ix.unique)} name={ix.name}"
    if kind in ("add_fk", "remove_fk"):
        fk = d[1]; return f"{kind} {fk.table.name}({','.join(c.name for c in fk.columns)})->{fk.referred_table.name} name={fk.name}"
    if kind in ("add_constraint", "remove_constraint"):
        c = d[1]; return f"{kind} {c.table.name}.{c.name}"
    return f"{kind} {d[1:]}"[:120]
report = {"unseen_by_env": sorted(all_tables - seen_by_env), "diffs": sorted(_name(d) for d in diffs)}
if os.environ.get("ORACLE_DUMP"):
    Path(os.environ["ORACLE_DUMP"]).write_text(json.dumps(report, indent=1))
print(json.dumps(report))
"""


BASELINE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "schema_drift_baseline.json"
)


def _baseline() -> dict[str, list[str]]:
    return json.loads(BASELINE.read_text()) if BASELINE.exists() else {}


def _write_baseline(stack: str, drift: list[str]) -> None:
    data = _baseline()
    data[stack] = sorted(drift)
    BASELINE.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")


def _real_drift(diffs: list[str]) -> list[str]:
    """Drop what is not schema drift; everything left is the porting list.

    - An FK the database names (``*_fkey``) and the model leaves unnamed is
      the same FK: ``add_fk``/``remove_fk`` pairs with one signature cancel.
    - Likewise an index with the same table, columns and uniqueness under
      a different name.
    - Postgres reports SQLModel's ``AutoString`` (VARCHAR without length)
      against the revisions' ``TEXT``; identical semantics on Postgres.
    - A unique *index* in the database and a ``UniqueConstraint`` on the
      model over the same columns: Postgres implements the constraint as
      exactly that index. Same behaviour, different declaration style.
    """
    import re

    def _sig(pattern: str, entry: str) -> str:
        match = re.search(pattern, entry)
        assert match is not None, entry
        return match.group(1)

    def _sig2(pattern: str, entry: str) -> tuple[str, str]:
        match = re.search(pattern, entry)
        assert match is not None, entry
        return match.group(1), match.group(2)

    def fk_sig(entry: str) -> str:
        return _sig(r"fk (\S+\(.*?\)->\S+)", entry)

    def ix_sig(entry: str) -> str:
        return _sig(r"index (\S+\(.*?\) unique=\w+)", entry)

    fk_add = {fk_sig(e) for e in diffs if e.startswith("add_fk ")}
    fk_rem = {fk_sig(e) for e in diffs if e.startswith("remove_fk ")}
    ix_add = {ix_sig(e) for e in diffs if e.startswith("add_index ")}
    ix_rem = {ix_sig(e) for e in diffs if e.startswith("remove_index ")}
    # unique index (db) vs unique constraint (model) over the same columns
    uq_ix_cols = {
        _sig2(r"index (\S+)\((.*?)\) unique=True", e)
        for e in diffs
        if e.startswith("remove_index ") and "unique=True" in e
    }
    cons_names = {
        _sig2(r"add_constraint (\S+)\.(\S+)", e)
        for e in diffs
        if e.startswith("add_constraint ")
    }
    out = []
    for e in diffs:
        if e.startswith("remove_index ") and "unique=True" in e:
            table, cols = _sig2(r"index (\S+)\((.*?)\) unique=True", e)
            if (table, cols) in uq_ix_cols and any(t == table for t, _ in cons_names):
                continue
        if e.startswith("add_constraint "):
            table, _ = _sig2(r"add_constraint (\S+)\.(\S+)", e)
            if any(t == table for t, _ in uq_ix_cols):
                continue
        if e.startswith(("add_fk ", "remove_fk ")) and fk_sig(e) in fk_add & fk_rem:
            continue
        if (
            e.startswith(("add_index ", "remove_index "))
            and ix_sig(e) in ix_add & ix_rem
        ):
            continue
        if (
            e.startswith("modify_type ")
            and "db=TEXT()" in e
            and "model=AutoString()" in e
        ):
            continue
        out.append(e)
    return sorted(out)


@pytest.mark.parametrize("stack", sorted(STACKS))
def test_generated_revisions_rebuild_the_models_schema(
    project_factory, stack: str
) -> None:
    if not _postgres_available():
        pytest.skip("PostgreSQL not available on localhost:5432")
    components, services = STACKS[stack]
    project: Path = project_factory(components=components, services=services)
    # The cache copy carries a venv whose interpreter links are only valid
    # at the cache's own path; sync a fresh one here (as the db fixtures do).
    shutil.rmtree(project / ".venv", ignore_errors=True)
    sync = run_project_command(
        ["uv", "sync", "--extra", "dev"], project, timeout=600, step_name="sync"
    )
    assert sync.success, sync.stderr[-800:]
    run = run_project_command(
        ["uv", "run", "python", "-c", PROBE],
        project,
        timeout=600,
        step_name="oracle",
        env_overrides={
            "VIRTUAL_ENV": "",
            "ORACLE_DB": f"aegis-oracle-{stack}",
            "ORACLE_DUMP": os.environ.get("ORACLE_DUMP_DIR", "")
            and f"{os.environ['ORACLE_DUMP_DIR']}/oracle-{stack}.json",
        },
    )
    assert run.success, run.stdout[-1500:] + run.stderr[-1500:]
    report = json.loads(run.stdout.strip().splitlines()[-1])
    assert report["unseen_by_env"] == [], (
        f"{stack}: tables env.py never imports (autogenerate is blind to them): "
        f"{report['unseen_by_env']}"
    )
    drift = _real_drift(report["diffs"])
    known = _baseline().get(stack, [])
    if os.environ.get("SCHEMA_DRIFT_BASELINE_UPDATE"):
        _write_baseline(stack, drift)
        pytest.skip(f"baseline rewritten with {len(drift)} entries for {stack}")
    new = sorted(set(drift) - set(known))
    gone = sorted(set(known) - set(drift))
    if gone:
        print(
            f"{stack}: {len(gone)} baseline entries no longer occur - prune them:\n  "
            + "\n  ".join(gone)
        )
    assert not new, (
        f"{stack}: NEW drift between generated revisions and models "
        f"({len(known)} known entries tolerated):\n  " + "\n  ".join(new)
    )
