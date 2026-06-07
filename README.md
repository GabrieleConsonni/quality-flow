# Quality Flow — backend

**Quality Flow** is a platform for **API / integration testing and data quality**.
It lets teams define **test suites** that exercise real integrations — sending and
receiving messages on queues, querying databases and JSON datasources, calling HTTP
and mock servers — then run them, assert on the results, and inspect detailed
execution timelines.

This repository is the **backend**: an async **FastAPI** service (Python 3.13) plus
the data model, migrations and execution engine. The modern Angular UI lives in the
sibling repo [`quality-flow-ng-app`](https://github.com/GabrieleConsonni/quality-flow-ng-app)
and is progressively replacing the legacy Streamlit UI under `app/ui/`.

## Key concepts

- **Suite** — an ordered set of stages: **Setup → Tests → Teardown**. Schedulable.
- **Test** — built from a template (*Send & Verify*, *Mock & Assert*) or as a fully
  **custom** list of steps.
- **Step / Operation** — a single action, grouped by intent:
  - **Producers** — send messages to a queue / call an endpoint
  - **Consumers** — receive and read from a queue
  - **Assertions** — verify payloads, including JSON-array assertions
  - **Control** — variables, constants, set-variable, run-envelope, flow control
- **Datasource** — a database connection or JSON-array source used to feed/verify tests.
- **Broker / Queue** — messaging connection (Amazon SQS, ElasticMQ for local dev).
- **Mock server** — a configurable HTTP stub, importable from an OpenAPI / JSON spec.
- **Execution** — a recorded run with a hierarchical timeline, resolved values and JSON diffs.
- **Template engine** — parametrizes tests so a single definition resolves per-row at run time.

## Architecture

Modular FastAPI app under `app/`, one package per domain (each with `api/`,
`models/`, `services/`):

| Module | Responsibility |
|---|---|
| `app/brokers` | Queue/broker connections and send/receive (Amazon SQS, ElasticMQ) |
| `app/data_sources` | Database & JSON-array datasources, connection configs, parameter resolution |
| `app/elaborations` | Suite/test/operation modeling, command DTOs, the execution engine |
| `app/json_utils` | JSON manipulation, assertions and diffing helpers |
| `app/mock_servers` | Mock HTTP servers, OpenAPI/JSON import |
| `app/logs` | Execution logs and run history |
| `app/middleware` | Cross-cutting concerns including multi-tenant resolution |
| `app/config` | Settings and environment configuration |
| `app/ui` | Legacy Streamlit UI (being retired — kept as a functional reference) |

- **Async stack:** FastAPI + AsyncPG (PostgreSQL), Pydantic v2 for validation,
  Polars for data processing.
- **Multi-tenant:** tenant database routing is configured per environment
  (see `application-*.yaml`); the DB schema is `quality_flow_service` — always
  qualify table names.
- **Migrations:** Alembic.
- **Testing:** Pytest + Testcontainers (Docker required).

## Tech stack

Python 3.13 · FastAPI · AsyncPG / PostgreSQL · Pydantic v2 · Polars ·
SQS (Amazon / ElasticMQ) · Alembic · Pytest + Testcontainers.

Dependencies are pinned with **pip-compile** (`requirements.in` → `requirements.txt`,
`docker-requirements.txt`).

## Prerequisites

- Docker Desktop
- Python 3.13 (only to run tools/tests outside containers)
- Node.js + pnpm (only to run the Angular FE outside its container)

## Run — backend only

```bash
docker compose -f docker-compose.yml up --build -d
docker compose -f docker-compose.yml down
```

## Run — full stack (backend + frontend)

From the workspace root, `qf-stack-dev.bat` starts the FastAPI backend
(port **9082**, debugpy **5678**) together with the Angular FE behind nginx
(port **4400**, OIDC bypassed). Stop with `qf-stack-dev-stop.bat`.

> Cloud production deploys use `docker/docker-compose-prod.yml` with registry images
> and a full ENV (`DATABASE_URL`, `VERSIONIMAGE`, …).

## Local ElasticMQ (optional)

```bash
cd elasticmq && docker compose up -d
```

- SQS endpoint: `http://localhost:9324`
- Web console: `http://localhost:9325`

## Useful endpoints

- API: `http://localhost:9082`
- Swagger UI: `http://localhost:9082/docs`
- OpenAPI JSON: `http://localhost:9082/openapi.json`
- Debugpy: `tcp://localhost:5678`
- Frontend (via nginx): `http://localhost:4400`
- Legacy Streamlit UI (manual): `streamlit run app/ui/QualityFlow.py`

## Python environment

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Regenerate `docker-requirements.txt` from `requirements.in`:

```bash
docker compose -f docker-compose-compile-requirements.yml run --rm compiler
```

## Tests

```bash
pytest test
```

> Tests use Testcontainers, so Docker must be running.

## Database migrations (Alembic)

```bash
alembic revision --autogenerate -m "YYYYMMDDHH_desc"
alembic upgrade head
alembic downgrade -1
alembic current
alembic history
```

## Repository map

- `app/` — FastAPI backend (and legacy Streamlit UI under `app/ui/`)
- `app/main.py` — API entry point
- `alembic/` — database migrations
- `api_quality_flow/` — API client collection (requests, environments)
- `docker/` — Dockerfile (API) and production compose
- `elasticmq/` — local ElasticMQ compose & config
- `docs/` — functional and operational documentation
- `scripts/` — CLI utilities

## Related repositories

- **Frontend:** [`quality-flow-ng-app`](https://github.com/GabrieleConsonni/quality-flow-ng-app) — Angular UI.
