# Quality Flow

Quality Flow is a queue manager with a FastAPI backend. The new Angular UI lives in the sibling repo `quality-flow-ng-app` and is replacing the legacy Streamlit UI under `app/ui/` capability-by-capability (see [QSM-047](docs/stories/QSM-047-TEST-SUITES-FOUNDATION.md) and the [refactor plan](docs/analisys/QFW-TEST-SUITE/)).

## Prerequisiti

- Docker Desktop
- Python 3.13 (solo se vuoi eseguire tool/test fuori dai container)
- Node.js + pnpm (solo se avvii il FE Angular fuori dal container)

## ElasticMQ locale (opzionale)

Per avviare solo ElasticMQ in locale:

```bash
cd elasticmq
docker compose up -d
```

- SQS endpoint: `http://localhost:9324`
- Console web: `http://localhost:9325`

## Avvio stack (BE + FE insieme)

Dalla root del workspace `c:\sviluppo\devgit\alkrya`:

| Comando | Modalità FE | Watch | Quando usarlo |
|---|---|---|---|
| `qf-stack-dev.bat` | `mock-auth` (OIDC bypassato, `environment.mock.ts`) | sì, in foreground | uso quotidiano per il vibe-coding |
| `qf-stack-prod.bat` | `production` (OIDC reale, bundle ottimizzato) | no, build one-shot | smoke test del build di produzione locale prima del deploy |

Entrambi avviano lo stesso BE FastAPI (port 9082 + debugpy 5678) e l'nginx FE (port 4400). Lo stop è unico:

```bat
qf-stack-dev-stop.bat
```

> Il deploy cloud production reale usa `docker/docker-compose-prod.yml` con immagini dal registry e ENV completo (DATABASE_URL, VERSIONIMAGE, ...). I bat sopra sono per il workflow locale.

## Avvio solo BE (single repo)

```bash
docker compose -f docker-compose.yml up --build -d
docker compose -f docker-compose.yml down
```

## Repository Map

- `app/`: backend FastAPI + legacy Streamlit UI (in dismissione)
- `app/main.py`: entrypoint API
- `app/ui/QualityFlow.py`: entrypoint UI Streamlit legacy (verrà rimosso a fine refactor)
- `alembic/`: migrazioni database
- `docker/`: Dockerfile API + compose prod
- `elasticmq/`: compose e configurazione ElasticMQ locale
- `docs/`: documentazione funzionale e operativa
- `scripts/`: utility CLI (es. `scripts/audit_before_each.py`)

## Endpoint utili

- API FastAPI: `http://localhost:9082`
- Swagger: `http://localhost:9082/docs`
- OpenAPI JSON: `http://localhost:9082/openapi.json`
- Debugpy: `tcp://localhost:5678` (container `quality-flow`)
- FE Angular (via nginx): `http://localhost:4400`
- UI Streamlit legacy (solo se avviata manualmente): `streamlit run app/ui/QualityFlow.py`

## Environment Python

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Dipendenze

Installazione dipendenze ambiente Python locale:

```bash
pip install -r requirements.txt
```

Rigenerazione `docker-requirements.txt` da `requirements.in`:

```bash
docker compose -f docker-compose-compile-requirements.yml run --rm compiler
```

## Test

```bash
pytest test
```

Nota: i test usano Testcontainers (Docker richiesto).

## Alembic

Esempi comandi:

```bash
alembic revision --autogenerate -m "YYYYMMDDHH_desc"
alembic upgrade head
alembic downgrade -1
alembic current
alembic history
alembic heads
alembic branches
alembic show <revision>
```
