# QSM-048 — Test Suites refactor · Template Engine (Phase 2)

> Seconda slice del refactor Test Suites (segue [QSM-047 Foundation](QSM-047-TEST-SUITES-FOUNDATION.md)).
> Status: **In corso** — implementazione completata, validazione e2e da eseguire.

## Scope

Phase 2 del piano [QFW-TEST-SUITE](../analisys/QFW-TEST-SUITE/QualityFlow%20-%20Test%20Suites%20·%20Implementation%20plan.md). Introduce il **template engine** server-side che converte un `template_config` in una snapshot di `suite_item_commands`, più la UI Angular **template-first** (New Test dialog + Test Editor template-mode + timeline preview).

### Backend (`quality-flow`)

#### Runtime extension (prerequisito)
- Nuovi `CommandCode`: `RECEIVE_QUEUE = "receiveQueue"` e `QUERY_DATABASE = "queryDatabase"`.
- Nuovi DTO Pydantic `ReceiveQueueConfigurationCommandDto` (queue_id, max_messages, retry, wait_time_seconds, target, resultConstant) e `QueryDatabaseConfigurationCommandDto` (connection_id, query, target, resultConstant).
- `ConfigurationCommandTypes` esteso, `convert_to_config_command_type` riconosce i due nuovi codes.
- `CommandContract` registrato per i due nuovi codes (writes_to runEnvelope/local/result).
- Nuovi executor: `ReceiveQueueOperationExecutor` (riceve fino a N messaggi con retry/wait + scrive nel target), `QueryDatabaseOperationExecutor` (esegue SQL via `create_sqlalchemy_engine`).
- `_EXECUTOR_MAPPING` aggiornato in `command_executor_composite.py`.

#### Template engine
- Nuovo pacchetto `app/templating/`:
  - `base.py`: `TemplateMeta`, `TemplateProtocol`, eccezioni `UnknownTemplateError` / `InvalidTemplateConfigError`.
  - `template_registry.py`: singleton `_TemplateRegistry` con `register`, `is_supported`, `get`, `list_templates`, `generate_commands`. Bootstrap automatico dei built-in al primo import.
  - `templates/send_verify.py`: produce `[setVariable → sendMessageQueue → sleep → (receiveQueue|queryDatabase → assertX)*]`.
  - `templates/mock_assert.py`: produce `[sleep → (receiveQueue|queryDatabase → assertX)+]` (≥1 assert obbligatorio).
- Operatori F2 supportati: `equals` → JSON_EQUALS, `exists` → JSON_NOT_EMPTY. `contains` / `matches_schema` rimandati a F2.5.
- Payload kind F2 supportato: `json_inline`. `json_array_ref` / `dataset_ref` arrivano in Fase 4 (data-driven).

#### Endpoint
- `GET /elaborations/templates` — metadata dei template registrati (per il New Test dialog dinamico).
- `POST /elaborations/templates/preview` — genera la snapshot senza salvare (per la timeline read-only).
- `POST /elaborations/test-suite/{id}/test` e `PUT /elaborations/test-suite/{id}/test/{item_id}` — quando `template_kind != custom` ignorano `dto.commands` e invocano `template_registry.generate_commands(template_kind, template_config)` per produrre lo snapshot persistito.
- `POST /elaborations/test-suite/{id}/test/{item_id}/convert-to-custom` — ora non più no-op puro: se l'item è basato su template, snapshot dei commands generati, poi `template_kind=custom` + `template_config=None`.
- Supported_paths nell'inventory test aggiornato.

#### Test
- `test/unit/test_templating_registry.py`: 6 test sul registry.
- `test/unit/test_templating_send_verify.py`: 9 test snapshot dei commands.
- `test/unit/test_templating_mock_assert.py`: 5 test snapshot.
- `test/integration/test_elaborations_api_inventory.py`: include `/templates` e `/templates/preview` nei supported_paths.
- **NON eseguito in F2** (lasciato per slice di test runtime end-to-end dedicata): pytest runtime per `ReceiveQueueOperationExecutor` e `QueryDatabaseOperationExecutor` (richiede Testcontainers ElasticMQ + Postgres).

### Frontend (`quality-flow-ng-app`)

#### Dipendenze
- Aggiunte e installate: `@playwright/test ^1.58.2`, `monaco-editor 0.54.0`, `ngx-monaco-editor-v2 20.3.0`, `jsondiffpatch 0.7.6`. Monaco non ancora wired (vedi scope F2).

#### Models + service
- `pages/test-suites/models/test-suite.model.ts`: aggiunti `TemplateMeta`, `TemplateAssertTarget/Operator`, `TemplateAssertSpec`, `SendVerifyConfig`, `MockAssertConfig`, `TemplateConfig`, `TemplatePreviewRequest`, `PreviewedCommand`, `TemplatePreviewResponse`.
- `pages/test-suites/services/test-suite.service.ts`: aggiunti `listTemplates()` e `previewTemplate(payload)`.

#### Componenti
- `pages/test-suites/dialogs/new-test-dialog/`: Mockup 3 — 3 card (Send & Verify, Mock & Assert, Custom), click+doppio click, Continue disabled finché niente è selezionato.
- `pages/test-suites/test-editor/test-editor.component.{ts,html,scss}`: Mockup 4 minimale — form template-specific a sinistra, timeline sticky a destra, header con chip kind + Save/Cancel.
- `pages/test-suites/test-editor/components/generated-steps-timeline.component.{ts,html,scss}`: chiama `previewTemplate` con debounce 250ms al change degli input, gestisce loading/error/empty.
- Suite Editor aggiornato: `+ Add test` apre il New Test dialog (custom continua col popup descrizione semplice).
- Routes nuove: `/test-suites/:suiteId/tests/new?template_kind=...` e `/test-suites/:suiteId/tests/:suiteItemId`.

#### Scope F2 (rispetto al piano)
- Payload editor: `<dx-text-area>` JSON con validazione JSON.parse. **Monaco editor wrapper rimandato a F2.5** (richiede lazy load + worker setup non triviale).
- Asserts editor: blocco inline con i 4 field condizionali. Operatori UI: `equals`, `exists`.
- Iteration toggle (data-driven): NON in F2 (Fase 4).
- Run test / Convert to custom: non aggiunti al Test Editor in F2 (Convert resta no-op come da decisione utente; Run è in Suite Editor).

### E2E
- `e2e/tests/test-suites-template.smoke.spec.ts` (tag `@qfw @smoke @template`): happy path Send & Verify end-to-end (apri suites list → crea suite → New Test dialog → Send & Verify → fill form → attendi timeline a 5 step → Save → verifica back to suite editor).

## Validazione

| Layer | Comando | Esito |
|---|---|---|
| Lint FE | `pnpm lint` | Pass (51 file, no finding) |
| TypeScript FE | `npx tsc --noEmit -p apps/quality-flow-ng-app/tsconfig.app.json` | Pass (exit 0) |
| Unit BE templating | `pytest test/unit/test_templating_*.py` | Da eseguire (sintassi py_compile OK) |
| Inventory BE | `pytest test/integration/test_elaborations_api_inventory.py` | Da eseguire |
| Runtime BE receive/query | (test runtime dedicati) | **Non scritti in F2** — slice separata raccomandata |
| E2E template smoke | `pnpm run e2e:run` con stack up | Da eseguire |

## Out of scope F2 (Fasi successive)

- **F2.5 (mini-slice opzionale)**: Monaco editor wrapper, operatori `contains` / `matches_schema`, payload `json_array_ref` / `dataset_ref` non-data-driven, run E2E runtime per receive/query.
- **Fase 3**: Step Editor dialog (Mockup 6), custom mode editing inline (Mockup 5), Convert to Custom dialog (Mockup 10).
- **Fase 4**: data-driven runtime + UI (Iteration toggle, parent/child execution, preview row 0).
- **Fase 5**: Execution View (Mockup 9), Quick Run drawer (Mockup 11), SSE service condiviso.
- **Fase 6**: rimozione Streamlit `Advanced suite settings`, telemetria.

## Note operative

- Per testare manualmente: `qf-stack-dev.bat` (mock-auth) → http://localhost:4400 → Test Suites → crea suite → "+ Add test" → Send & Verify → compila → Save.
- Convert-to-custom è ora attivo: invocato su un test send_verify/mock_assert, snapshotta i commands generati e cambia il `template_kind` in `custom` (one-way, come da Mockup 10 — il dialog di confirm UX verrà aggiunto in Fase 3).
