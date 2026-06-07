# QSM-035 - Operations (Suite + Mock)

## Stato
- Stato: In corso
- Scope funzionale: solo runtime `test suite + mock server`
- Fuori scope: runtime legacy `suite/test` (compatibilita mantenuta, nessuna nuova feature dedicata)

## Analisi AS-IS
- Runtime suite gia presente con lifecycle `beforeAll -> beforeEach -> test -> afterEach -> afterAll`.
- Runtime mock gia presente con `pre_response_operations` e `post_response_operations`.
- `run_context` e resolver dinamico gia disponibili (`$.event`, `$.global`, `$.local`, `$.last`, `$.artifacts`).
- Mancava un contratto centralizzato e validabile per operation (`supported_scopes`, `reads_from`, `writes_to`, ecc.).
- Mancava enforcement policy uniforme per scope runtime.
- Input operations senza target esplicito obbligatorio nel payload legacy.
- Action operations senza output target standard.
- Response mock costruita principalmente da configurazione statica (`response_status/headers/body`) senza family operation dedicata.

## Matrice Gap
| Requisito QSM-035 | Stato attuale | Azione |
| --- | --- | --- |
| Contratto operation centralizzato | Assente | Introdotto registry con descriptor (`family`, `supported_scopes`, `reads_from`, `writes_to`, `produces_result`, `side_effects`, `async_allowed`, `failure_mode`) |
| Validazione scope-driven | Parziale | Introdotto validator pre-execution in pipeline operation |
| Regola hard: test non scrive global | Solo `set-var` | Enforcement centralizzato su target path + writer context |
| Regola hard: mock pre-response no side effects/async | Assente | Enforcement su descriptor (`side_effects`, `async_allowed`) |
| Input target esplicito | Assente | Campo `target` aggiunto ai DTO input + UI |
| Action result target opzionale | Assente | Campo `result_target` aggiunto ai DTO action + writer runtime |
| Mock response operations | Assente | Nuova family `mock-response` + dispatcher scope `mock.response` |

## Decisioni congelate
1. `operationType` resta la chiave pubblica di compatibilita nel primo incremento.
2. Policy applicata su scope runtime: `test`, `hook.*`, `mock.preResponse`, `mock.response`, `mock.postResponse`.
3. Global context immutabile durante `test`.
4. Trigger operation (`run-suite`) propaga dati solo via `init_vars` esplicito.
5. Compat mode attivo: payload legacy senza `target/result_target` continua a funzionare.

## Roadmap fasi
### Fase 1 - Contratto e policy runtime
- Aggiungere registry contratti operation.
- Aggiungere scope resolver runtime e policy validator pre-execution.
- Applicare enforcement sui call-site suite/mock.

### Fase 2 - Evoluzione DTO operation
- Estendere DTO input con `target`.
- Estendere DTO action/trigger con `result_target`.
- Mantenere parser retrocompatibile (`snake_case`/`camelCase` + alias legacy).

### Fase 3 - Mock response family
- Aggiungere operation:
  - `set-response-status`
  - `set-response-header`
  - `set-response-body`
  - `build-response-from-template`
- Integrare fase `mock.response` nel dispatcher.
- Mantenere fallback su response statica legacy.

### Fase 4 - UI e validazione configurazione
- Estendere editor operation (shared) con campi `target` e `resultTarget`.
- Estendere mock editor con tab `Response` operations.
- Validare `operationType` e payload minimi lato UI.

### Fase 5 - Test e regressione
- Unit test su policy scope x contract.
- Unit test su target path/parser e writer runtime.
- Integration test su flow mock `pre -> response -> post`.
- Regression test su operation legacy.

## Checklist validazione
- [ ] `test` non puo scrivere `$.global.*`.
- [ ] `mock.preResponse` blocca operation con `side_effects=true`.
- [ ] `mock.preResponse` blocca operation con `async_allowed=true`.
- [ ] Input operation con `target` scrive nel contesto dichiarato.
- [ ] Action operation con `result_target` salva output tecnico.
- [ ] Assert non modifica business context (`global/local`).
- [ ] `mock.response` puo costruire status/header/body via operation.
- [ ] Fallback response legacy invariato se `response_operations` assenti.

## Test plan
- `pytest test/alembic/services/test_operation_policy_validator.py`
- `pytest test/alembic/services/test_operation_executors.py`
- `pytest test/alembic/services/test_mock_server_runtime.py`
- `pytest test/alembic/services/test_test_suite_runtime.py`

## Qualita e gate
- CodeScene usage: Yes (refactor cross-module).
- Gate richiesto prima del ready:
  - `select_codescene_project`
  - `code_health_review` (o hotspots)
  - `pre_commit_code_health_safeguard`
- Nota: tool CodeScene non disponibili in questa sessione, gate da eseguire in pipeline/ambiente abilitato.
