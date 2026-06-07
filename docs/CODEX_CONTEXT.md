# Quality Flow - Contesto Progetto per Codex

## Panoramica
Quality Flow e un'applicazione per test e orchestrazione di flussi su broker SQS, datasource e test suite.
Il progetto e composto da:
- backend FastAPI
- UI Streamlit multipage

Domini principali:
- broker/queue (send, receive, ack, metriche)
- datasource JSON array e datasource tabellari database
- test suite (hook + test + operation) con esecuzioni persistite
- schedulazione ricorrente delle suite di test
- mock server API/queue con attivazione runtime e import OpenAPI JSON
- logs applicativi

## Stack tecnologico
- Python 3.13
- FastAPI + Pydantic
- SQLAlchemy 2 + Alembic
- PostgreSQL
- ElasticMQ (SQS locale)
- Streamlit
- Docker / Docker Compose
- Testcontainers (test backend)

## Mappa repository
- `app/` codice backend + UI
- `app/main.py` entrypoint API FastAPI
- `app/ui/Quality Flow.py` entrypoint UI Streamlit
- `alembic/` migrazioni DB
- `elasticmq/` compose/config ElasticMQ locale
- `docker/` Dockerfile API/UI
- `docs/` documentazione
  - `docs/SPEC.md` specifica funzionale
  - `docs/stories/STORIES_INDEX.md` indice storie
  - `docs/stories/` storie QSM
  - `docs/bugs/` bug log (formato `QSMB-XXX`)

## Entry point e bootstrap
In `app/main.py` all'avvio:
1. carica `.env`
2. esegue migrazioni Alembic
3. inizializza ElasticMQ (`init_elasticmq`)
4. registra router API
5. a startup bootstrap dei mock server attivi (`MockServerRuntimeRegistry.bootstrap_active_servers()`) e avvio scheduler runtime (`bootstrap_scheduler_runtime()`)
6. a shutdown arresto scheduler runtime (`shutdown_scheduler_runtime()`)

## UI Streamlit
Entry point: `app/ui/Quality Flow.py`

Pagine principali:
- `app/ui/pages/Home.py`
- `app/ui/pages/Brokers.py`
- `app/ui/pages/DatabaseConnections.py`
- `app/ui/pages/Datasets.py`
- `app/ui/pages/DatasetPerimeterEditor.py`
- `app/ui/pages/MockServers.py`
- `app/ui/pages/MockServerEditor.py`
- `app/ui/pages/Queues.py`
- `app/ui/pages/QueueDetails.py`
- `app/ui/pages/JsonArray.py`
- `app/ui/pages/TestSuites.py`
- `app/ui/pages/TestEditor.py`
- `app/ui/pages/AdvancedSuiteEditorSettings.py`
- `app/ui/pages/TestSuiteSchedules.py`
- `app/ui/pages/SuiteEditor.py` (alias legacy)
- `app/ui/pages/Logs.py`
- `app/ui/pages/Tools.py`

Organizzazione UI modulare gia presente in package dedicati:
- `app/ui/brokers`
- `app/ui/database_connections`
- `app/ui/database_datasources`
- `app/ui/elaborations_shared` (componenti condivisi test/command editing)
- `app/ui/home` (servizi home page)
- `app/ui/json_arrays`
- `app/ui/mock_servers`
- `app/ui/test_suites`
- `app/ui/queues`

Note UI test suite:
- `app/ui/pages/TestEditor.py` e la pagina attiva per il dettaglio/edit del singolo test.
- `app/ui/pages/SuiteEditor.py` resta alias legacy di compatibilita e non deve ricevere nuova logica.
- Il rendering page-specific del test editor vive in `app/ui/test_suites/components/test_editor_component.py`.
- `app/ui/test_suites/components/suite_editor_component.py` contiene helper condivisi della feature, non rendering dedicato a una pagina specifica.
- La UI Streamlit comunica con la logica applicativa backend solo tramite API FastAPI e wrapper `app/ui/**/services/api_service.py`; i componenti UI non devono importare servizi di dominio come `elaborations.services.*`.

## Router API principali
- `/broker`
  - connessioni broker
  - queue del broker
  - messaggi queue (send/receive/ack/test)
- `/data-source`
  - json-array datasource
  - database table datasource
- `/database`
  - database connections + test + metadata oggetti + preview
- `/elaborations`
  - test suites
  - preview template `sendMessageQueue` per editor UI
  - suite_items / suite_item_commands (snapshot)
  - test suite executions
  - test suite schedules (CRUD + activate/deactivate + run-now)
  - SSE runtime: `/elaborations/execution/{execution_id}/events`
- `/mock-server`
  - CRUD mock server + activate/deactivate
  - import OpenAPI JSON
- runtime mock API
  - route dinamiche sotto `/mock/{server_endpoint}/...`
- `/logs`
- `/json_utils`
- `/public`
  - configurazione IDP (`/public/idp-config`)

## Modello dati (alto livello)
- `json_payloads` configurazioni JSON tipizzate
- `queues` configurazioni queue per broker
- `test_suites` anagrafica suite
- `suite_items` snapshot funzionale di test e hook
- `suite_item_commands` snapshot funzionale operation sull'item
- `test_suite_executions`, `suite_item_executions`, `suite_item_command_executions`
- `mock_servers`, `mock_server_apis`, `ms_api_commands`
- `mock_server_queues`, `ms_queue_commands`
- `test_suite_schedules` schedulazioni ricorrenti suite
- `command_constant_definitions` symbol table costanti per suite e mock commands
- `logs`

Nota: il runtime suite e mock usa snapshot contestuali (`suite_items`/`suite_item_commands`, `ms_api_commands`, `ms_queue_commands`), senza catalogo condiviso `commands`.

## Configurazione ambiente
Valori esempio `.env`:
```env
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db>
HOST_IP=<host>
```

Non inserire credenziali reali nei documenti.

## Avvio e stop
Stack completo (BE + FE Angular) dalla root del workspace:
```bat
qf-stack-dev.bat        :: FE in mock-auth, watch in foreground (uso quotidiano)
qf-stack-prod.bat       :: FE production build one-shot (smoke test pre-deploy)
qf-stack-dev-stop.bat   :: down dei container (vale per entrambi)
```

Solo BE quality-flow:
```bash
docker compose -f docker-compose.yml up --build -d
docker compose -f docker-compose.yml down
```

## Servizi e URL utili
Dal compose dev:
- API `quality-flow`: `http://localhost:9082`
- Debugpy API: `tcp://localhost:5678`
- FE Angular (via nginx del FE compose): `http://localhost:4400`
- UI Streamlit legacy (avvio manuale, in dismissione): `streamlit run app/ui/QualityFlow.py`

Altri endpoint:
- Swagger: `http://localhost:9082/docs`
- OpenAPI: `http://localhost:9082/openapi.json`

ElasticMQ locale (opzionale, compose dedicato in `elasticmq/`):
- SQS endpoint: `http://localhost:9324`
- Console: `http://localhost:9325`

## Test
Comando principale:
```bash
pytest test
```

I test usano Testcontainers, quindi Docker deve essere disponibile.

## Regole operative docs
Quando cambia il comportamento funzionale o il piano di lavoro:
- aggiornare `docs/SPEC.md`
- aggiornare `docs/stories/QSM-*.md`
- aggiornare `docs/stories/STORIES_INDEX.md` se cambiano le storie
- aggiornare `docs/CODEX_CONTEXT.md` se cambia il contesto progetto

