# QSM-037 - Scheduler

## Stato
- Stato: Completato
- Area: Backend + UI Streamlit test suites
- Scope: schedulazione ricorrente delle suite di test

## Obiettivo
Introdurre la schedulazione delle test suite sopra il runtime gia esistente, senza creare un motore di esecuzione separato.

## Modifiche funzionali
### Backend
- Nuova entita `test_suite_schedules` con stato attivo/disattivo, frequenza interval, finestra `start_at/end_at`, `next_run_at`, `last_run_at`, `last_status`, `last_execution_id`, `last_error_message`.
- Nuovi endpoint `/elaborations/test-suite-schedule` per CRUD, `activate`, `deactivate` e `run-now`.
- Runtime scheduler avviato all'avvio applicazione, con polling periodico e trigger delle suite dovute.
- Trigger schedulato integrato nel `runEnvelope` con metadata `trigger.type = schedule`.
- Policy overlap `skip if running` per evitare esecuzioni parallele della stessa suite.

### UI
- Nuova pagina `Test Suite Scheduler` accessibile dall'area `Test`.
- Lista schedulazioni con filtro per suite, stato, prossima esecuzione e ultima esecuzione.
- Dialog di creazione/modifica schedule con frequenza `minutes/hours/days`, attivazione e finestra temporale opzionale.
- Azioni rapide `Run now`, `Activate/Deactivate`, `Edit`, `Delete`.

## Note tecniche
- La schedulazione riusa `execute_test_suite_by_id` e non altera il contratto delle suite.
- Il calcolo `next_run_at` resta centralizzato nel service scheduler.
- Le esecuzioni schedulate aggiornano `last_status` in base allo stato effettivo dell'execution.

## Checklist
- [x] Persistenza schedule con metadati runtime
- [x] API CRUD schedule
- [x] Endpoint `activate` / `deactivate`
- [x] Endpoint `run-now`
- [x] Runtime scheduler bootstrap/shutdown
- [x] Trigger suite con metadata `schedule`
- [x] Pagina UI `Test Suite Scheduler`
- [x] Test mirati su service/API/runtime scheduler

## Validazione
- Unit test:
  - `pytest test/unit/test_test_suite_schedule_service.py`
- Integration/alembic test:
  - `pytest test/integration/test_elaborations_api_inventory.py`
  - `pytest test/alembic/services/test_test_suite_scheduler_service.py`
