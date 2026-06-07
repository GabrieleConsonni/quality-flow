# QSM-047 — Test Suites refactor · Foundation (Phase 1)

> First slice of the Test Suites refactor (see [QFW-TEST-SUITE plan](../analisys/QFW-TEST-SUITE/QualityFlow%20-%20Test%20Suites%20·%20Implementation%20plan.md)).
> Status: **In corso** — Phase 1 (Foundation) implementata, validazione e2e da eseguire.

## Scope

Foundation per la migrazione del dominio **Test suites** dalla UI Streamlit alla nuova UI Angular (`quality-flow-ng-app`). Il piano completo si articola in 6 fasi; questa story copre la **Fase 1**.

### Backend (`quality-flow`)
- Migration Alembic `qsm_047_test_suites_foundation` che:
  - aggiunge a `suite_items`: `role`, `template_kind`, `template_config`, `data_driven`, `dataset_id`
  - aggiunge a `suite_item_executions`: `parent_execution_id`, `row_index`, `row_snapshot`
  - backfilla `role` dai vecchi `kind`+`hook_phase`
  - **collassa 4 hook → 2** (setup + teardown): i commands dei donor items vengono ri-parentati e ri-numerati nel target, donor items DELETED senza backup applicativo
  - aggiunge indici `idx_suite_items_role`, `idx_executions_parent`
- Nuovi enum: `SuiteItemRole` (test|setup|teardown), `TemplateKind` (custom|send_verify|mock_assert)
- Estensione `SuiteItemEntity` e `SuiteItemExecutionEntity` con le colonne nuove
- Estensione `CreateSuiteItemDto` con `role`, `template_kind`, `template_config`, `data_driven`, `dataset_id` + backward-compat (derivazione del `role` da `kind`+`hook_phase` se non passato esplicitamente)
- Nuovi endpoint REST:
  - `POST /elaborations/test-suite/{test_suite_id}/test` — append singolo test custom
  - `PUT /elaborations/test-suite/{test_suite_id}/test/{suite_item_id}` — update in-place; bulk replace dei commands in custom mode
  - `POST /elaborations/test-suite/{test_suite_id}/test/{suite_item_id}/convert-to-custom` — idempotente, in F1 sempre no-op
- Script `scripts/audit_before_each.py` per misurare il rischio del breaking change `beforeEach` prima della migration
- Test:
  - `test/integration/test_qsm_047_migration.py`: scenario completo upgrade+collapse, downgrade reversibile
  - `test/unit/test_qsm_047_suite_item_dto.py`: 9 test sui campi DTO nuovi
  - `test/integration/test_elaborations_api_inventory.py`: supported_paths aggiornati con i 3 nuovi endpoint

### Frontend (`quality-flow-ng-app`)
- Sidebar L1 ridotta a **3 voci attive in F1**: Home · Test Suites · Logs.
  Configurations e Datasources arriveranno con le rispettive fasi del refactor.
- Pulizia totale di Schedules · Brokers · Queues · DB Connections · Datasets · Mock Servers · JSON Arrays · Tools dalla nav L1 e dalle routes.
- Nuovo feature module `apps/quality-flow-ng-app/src/app/pages/test-suites/`:
  - `test-suites.routes.ts` con child routes (list, suite-editor)
  - `models/test-suite.model.ts`
  - `services/test-suite.service.ts` (HttpClient wrapper)
  - `suites-list/` (Mockup 1, F1 scope): DxDataGrid con search client-side, "+ New suite" popup, Run/Edit/Delete inline, empty+loading state, toast errori.
  - `suite-editor/` (Mockup 2 — solo custom mode in F1): caricamento via GET /test-suite/{id}, description editabile inline con save (PUT bulk), setup/teardown expander read-only, lista tests con "+ Add test" popup (custom kind+role), Run suite + Run test, Delete suite con confirm.
- E2E happy path Playwright in `e2e/tests/test-suites.smoke.spec.ts`.
- Nuove dipendenze in `package.json`: `@playwright/test ^1.58.2`, `monaco-editor ^0.54.0`, `ngx-monaco-editor-v2 ^20.0.0`, `jsondiffpatch ^0.7.3`.

### Documenti correlati
- `quality-flow/docs/SPEC.md` aggiornato (sezione hook 4→2).

## Breaking change documentato (`beforeEach`)

Lo schema legacy aveva 4 lifecycle hook: `before-all`, `before-each`, `after-each`, `after-all`. La semantica di `before-each`/`after-each` era "per test" (eseguiti N volte, una per test della suite).

Il refactor li collassa in 2 hook unici (`setup`, `teardown`), eseguiti **una sola volta** per suite. Le suite che usavano `before-each` per resettare lo stato fra un test e l'altro **perdono quel comportamento per-test** dopo la migration.

### Azione richiesta agli utenti che usano `before-each`
1. Eseguire l'audit pre-migration: `python scripts/audit_before_each.py` per ottenere la lista delle suite a rischio.
2. Per ognuna di esse, scegliere una delle due strategie:
   - **(A) Reset come primo step di ogni test**: copiare i command del `before-each` come primi step di ciascun test della suite (oggi la suite continua su test fallito, quindi il reset è esplicito);
   - **(B) Suite "reset test" iniziale**: aggiungere un test "Reset" come primo test della suite, contenente gli stessi command del `before-each`. Ogni test successivo eredita lo stato pulito.

Nessun backup applicativo dei dati hook viene conservato. Recovery affidato ai dump DB esterni.

## Fuori scope F1 (Fasi successive)

- **Template engine** (`send_verify`, `mock_assert`) — Fase 2
- **Step Editor dialog** completo + custom mode editing inline — Fase 3
- **Data-driven runtime** + parent/child execution + preview row — Fase 4
- **Execution view** dedicata + Quick Run drawer + SSE wiring in service condiviso — Fase 5
- **Decommissioning** della pagina Streamlit `Advanced suite settings` + telemetria — Fase 6

## Validazione

| Layer | Comando | Esito |
|---|---|---|
| Lint FE | `pnpm lint` | Pass (48 file, no finding) |
| TypeScript FE | `npx tsc --noEmit -p apps/quality-flow-ng-app/tsconfig.app.json` | Pass (exit 0) |
| Migration BE | `pytest test/integration/test_qsm_047_migration.py` | Da eseguire dopo Docker compose up |
| DTO BE | `pytest test/unit/test_qsm_047_suite_item_dto.py` | Da eseguire |
| E2E | `pnpm run e2e:run` con BE up + `pnpm run start:mock-auth` | Da eseguire |

## Note operative

- `pnpm install` necessario prima di eseguire lint/test/E2E (le 4 nuove dipendenze non sono ancora nel `pnpm-lock.yaml`).
- Sintassi Python `py_compile` verificata su tutti i file BE modificati/creati.
