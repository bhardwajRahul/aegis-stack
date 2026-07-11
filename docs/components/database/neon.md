# Neon

[Neon](https://neon.tech) is serverless Postgres. In Aegis Stack, `database[neon]` runs your FastAPI app against Neon's cloud in production, with autoscaling, scale-to-zero, and database branching, while development keeps the same local Postgres container as any other PostgreSQL stack.

```bash
aegis init my-project --components "database[neon]"
```

Neon is not a separate engine. `database[neon]` is the **postgres** engine hosted on Neon, so every Python model, migration, and query is identical to a self-hosted PostgreSQL stack. See the [Database component](../database.md) for the engine itself: models, sessions, migrations, and testing.

## How It Works

- **Development** runs the same local `postgres:16` container as a plain PostgreSQL stack (zero credentials, fully offline).
- **Production** runs no database container at all: the app points `DATABASE_URL` at Neon's pooled endpoint, injected as a secret.
- The generated connection code detects a Neon host (`*.neon.tech`) at runtime and applies Neon's pooler-safe connection settings only then, so one codebase runs against the local container in development and Neon in production.
- No extra Python dependencies: the standard `asyncpg` and `psycopg2` drivers connect over TCP. There is no Neon-specific Python driver.

## Pooled and Direct Endpoints

Neon exposes two connection endpoints per database, and the generated project uses both:

```bash
# App runtime uses the POOLED endpoint (note the -pooler host)
DATABASE_URL=postgresql://user:pass@ep-xxxx-pooler.region.aws.neon.tech/dbname

# Migrations use the DIRECT (unpooled) endpoint
DATABASE_URL_UNPOOLED=postgresql://user:pass@ep-xxxx.region.aws.neon.tech/dbname
```

Runtime traffic goes through the pooled endpoint. Migrations run over the direct endpoint automatically, because Neon's pooler (PgBouncer in transaction mode) is unsafe for DDL and session-level features. You set both variables once; the project picks the right one per task.

## Setup

1. Create a Neon account and project (free tier available).
2. Copy both connection strings from the Neon console: the pooled one (its host contains `-pooler`) and the direct one.
3. Set `DATABASE_URL` (pooled) and `DATABASE_URL_UNPOOLED` (direct) as production secrets in your deployment environment.

Development needs none of this: `make serve` runs the local container with zero configuration.

## Switching an Existing Project

The provider is chosen at `aegis init` today. `aegis add` and `aegis update` cannot yet move an existing PostgreSQL project between the local container and Neon, because the Neon connection handling is generated into the project rather than toggled at runtime. Provider switching on a living project is planned.

Until then, the practical path is to generate a fresh `database[neon]` project and move your models across. The data itself is standard PostgreSQL: `pg_dump` from the container, restore into Neon.

## When to Choose Neon

- Serverless and autoscaling deployments
- Per-PR / preview database branches
- Teams that would rather not operate a database server

One trade-off to know: scale-to-zero adds cold-start latency to the first request after an idle period. If that is unacceptable, or you would rather run and back up your own PostgreSQL service in every environment, use the local container instead: see [Hosting PostgreSQL: container or Neon](../database.md#hosting-postgresql-container-or-neon).
