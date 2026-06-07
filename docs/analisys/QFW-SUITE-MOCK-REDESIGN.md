# Quality Flow — Suite & Mock Redesign Plan

> Documento di redesign della costruzione test-suite e del trigger Mock→Suite.
> Target: UI Angular (in corso di migrazione da Streamlit). Backend FastAPI esistente.
> Audience: tool di vibe-coding (Cursor / Codex / Claude Code) e team di prodotto.

---

## 1. Obiettivo

Semplificare la costruzione di test-suite e il trigger dai Mock Server, mantenendo intatto il runtime esistente. L'utente medio deve poter creare un test funzionante in **meno di 60 secondi** scegliendo un template e compilando un form. L'utente avanzato deve poter accedere alla potenza dell'attuale modello (commands, sources, bindings, scope) tramite una modalità esplicita.

## 2. Principi guida

1. **Template-first.** L'unità di creazione di un test è la scelta di un template, non l'assemblaggio di command.
2. **Forma chiusa, contenuto aperto.** Ogni template ha step fissi e visibili (timeline read-only). Solo i campi sono editabili.
3. **Una sola via di evasione.** Si esce dal template solo via "Convert to Custom" (operazione one-way, irreversibile, con conferma).
4. **Mock = trigger, Suite = verifica.** I mock non contengono assert. I mock possono solo rispondere e/o lanciare una suite.
5. **Hook minimi.** `setup` e `teardown` a livello suite. Nient'altro.
6. **Snapshot immutabili al run.** Il modello attuale `suite_items` / `suite_item_commands` resta. I template generano command snapshot al save.
7. **Modalità avanzata visibile ma non invadente.** Toggle "Advanced" nel test editor; non una pagina separata.
8. **Estensibilità futura predisposta.** I template sono hard-coded ora ma il modello dati supporta `template_kind` come stringa libera + `template_config` JSONB.

## 3. Modello concettuale nuovo

### 3.1 Test Template

Un **Test Template** è una funzione documentata che produce uno o più step (command snapshot) a partire da un form di configurazione.

| `template_kind` | Cosa fa | Form principale | Step generati |
|---|---|---|---|
| `send_verify` | Invia messaggio su queue, attende, verifica | queue, payload, dataset opzionale, asserts | `sendMessageQueue` → `wait` → asserts |
| `mock_assert` | Verifica side-effect dopo trigger esterno | timeout, target (queue/db), asserts | `wait` → `receiveMessage`/`query` → asserts |
| `data_driven` (non template a sé) | Modificatore di test esistenti | — | gestito via toggle, vedi §3.4 |
| `custom` | Lista step libera (modello attuale) | nessun form, lista step editabile | quelli inseriti dall'utente |

**Nota:** `data_driven` non è un `template_kind` ma un attributo trasversale. Vedi §3.4.

### 3.2 Suite

Una suite contiene:
- `setup` (lista step, opzionale, eseguito 1 volta prima di tutti i test)
- `teardown` (lista step, opzionale, eseguito 1 volta dopo tutti i test, anche se i test falliscono)
- `tests[]` (lista ordinata di test, ognuno con un `template_kind`)

**Migrazione hook:** `beforeAll + beforeEach` → `setup`. `afterEach + afterAll` → `teardown`. Vedi §7.

### 3.3 Test

Ogni test ha:
- `name`, `description`
- `template_kind` (`send_verify | mock_assert | custom`)
- `template_config` (JSONB) — i campi del form template
- `data_driven` (boolean) — vedi §3.4
- `dataset_id` (nullable) — sorgente di iterazione se `data_driven = true`
- `commands[]` — snapshot generati al save (modello attuale invariato)
- `sources[]` — invariato (per `custom`); per template `send_verify`/`mock_assert` sono derivate

**Regola di edit:**
- In modalità base: editi solo `template_config`. Al save, i `commands[]` vengono **rigenerati** da zero.
- In modalità custom: editi `commands[]` direttamente. `template_kind` resta `custom`.
- Conversione template → custom: copia gli step generati come punto di partenza, setta `template_kind = custom`, abbandona `template_config`. **One-way.**

### 3.4 Data-driven (toggle)

Su qualsiasi test (qualunque `template_kind`), un toggle `Run for each row of dataset`:

- Quando ON, l'utente seleziona un `dataset_id`.
- A runtime, il test viene eseguito una volta per riga del dataset.
- I valori di riga sono accessibili nei campi del template tramite il prefisso `${row.<column>}`.
- Limite suggerito: warning se `count(rows) > 1000` (configurabile, hard limit a livello scheduler).
- L'esecuzione di un test data-driven produce N `suite_item_executions` figlie (una per iterazione) raggruppate sotto il parent.

**Compatibilità con template:** in `send_verify`, il payload può referenziare `${row.email}` etc. In `mock_assert`, gli expected possono dipendere da `${row.*}`. In `custom`, le `${row.*}` sono variabili runtime nello scope `local`.

### 3.5 Mock Server — modello "When called, do…"

Per ogni endpoint API mock e per ogni queue mock binding, l'utente sceglie **un solo behavior** tra:

| Behavior | Descrizione | Mappa su modello esistente |
|---|---|---|
| `reply_only` | Risponde con la response configurata, niente altro | `pre_response_commands = []`, `post_response_commands = []` |
| `reply_and_run_suite` | Risponde + lancia una suite in background | `post_response_commands = [{ kind: "runSuite", suite_id }]` |
| `advanced` | Espone le 3 fasi (pre/response/post) come oggi | invariato |

**Vincolo:** in `reply_and_run_suite` non si possono aggiungere altri command. Solo `runSuite` con un `suite_id`. Niente assert, niente save, niente set variable.

**Per le queue mock:** stessa logica. `reply_only` non ha senso (niente reply su queue), quindi i behavior sono `ack_only`, `ack_and_run_suite`, `advanced`.

## 4. Modello dati — modifiche

### 4.1 Tabella `suite_items` — nuove colonne

```sql
ALTER TABLE suite_items
  ADD COLUMN template_kind     varchar(32) NOT NULL DEFAULT 'custom',
  ADD COLUMN template_config   jsonb       NULL,
  ADD COLUMN data_driven       boolean     NOT NULL DEFAULT false,
  ADD COLUMN dataset_id        uuid        NULL REFERENCES json_payloads(id);
```

- `template_kind` valori validi attuali: `send_verify | mock_assert | custom`. Aperto in futuro.
- `template_config` schema dipende da `template_kind` (vedi §5).
- I `commands` (`suite_item_commands`) restano la **fonte di verità** per il runtime. Il `template_config` è solo la "ricetta" per rigenerarli.

### 4.2 Tabella `test_suites` — hook

```sql
-- Niente nuove colonne. Setup/teardown sono suite_items con un kind speciale.
ALTER TABLE suite_items
  ADD COLUMN role varchar(16) NOT NULL DEFAULT 'test';
-- valori: 'test' | 'setup' | 'teardown'
```

In alternativa (se la tabella suite_items ha già un campo `kind` per hook): unificare i 4 vecchi hook nei 2 nuovi via migrazione (§7).

### 4.3 Tabella `mock_server_apis` e `mock_server_queues` — behavior

```sql
ALTER TABLE mock_server_apis
  ADD COLUMN behavior        varchar(32) NOT NULL DEFAULT 'reply_only',
  ADD COLUMN linked_suite_id uuid        NULL REFERENCES test_suites(id);

ALTER TABLE mock_server_queues
  ADD COLUMN behavior        varchar(32) NOT NULL DEFAULT 'ack_only',
  ADD COLUMN linked_suite_id uuid        NULL REFERENCES test_suites(id);
```

In `advanced` mode, `linked_suite_id` resta nullable e i `*_commands` esistenti governano la pipeline.

### 4.4 Esecuzioni data-driven

```sql
ALTER TABLE suite_item_executions
  ADD COLUMN parent_execution_id uuid    NULL REFERENCES suite_item_executions(id),
  ADD COLUMN row_index           integer NULL,
  ADD COLUMN row_snapshot        jsonb   NULL;
```

- Quando un test data-driven gira, si crea un parent `suite_item_execution` con `row_index = NULL` (riepilogo) + N child con `row_index = 0..N-1` e `row_snapshot` = riga usata.
- L'UI raggruppa i child sotto il parent nella execution view.

## 5. Schemi `template_config` per template

### 5.1 `send_verify`

```json
{
  "queue_id": "uuid",
  "payload": {
    "kind": "json_inline | json_array_ref | dataset_ref",
    "value": { ... } | "uuid"
  },
  "wait_ms": 500,
  "asserts": [
    {
      "target": "queue | database | none",
      "queue_id": "uuid?",
      "database_query": "string?",
      "expected": { ... },
      "operator": "equals | contains | matches_schema | exists"
    }
  ]
}
```

### 5.2 `mock_assert`

```json
{
  "trigger_hint": "string (info-only, es. 'Chiama POST /orders')",
  "wait_ms": 1000,
  "asserts": [
    {
      "target": "queue | database",
      "queue_id": "uuid?",
      "database_query": "string?",
      "expected": { ... },
      "operator": "equals | contains | matches_schema | exists"
    }
  ]
}
```

### 5.3 `custom`

```json
null
```

(I command vivono in `suite_item_commands`, il template_config non si usa.)

## 6. API — modifiche

### 6.1 Nuovi/modificati endpoint

- `POST /elaborations/test-suite/{id}/test` — accetta payload con `template_kind` + `template_config`. Genera `suite_item_commands` lato server.
- `PUT /elaborations/test-suite/{id}/test/{item_id}` — stessa logica, rigenera command in template mode.
- `POST /elaborations/test-suite/{id}/test/{item_id}/convert-to-custom` — copia gli step come custom, setta `template_kind = custom`, scarta `template_config`. Idempotente solo se già custom (no-op).
- `GET /elaborations/templates` — ritorna metadata dei template disponibili (per UI dinamica).
- `POST /mock-server/{id}/api` — accetta `behavior` + `linked_suite_id`.
- `POST /mock-server/{id}/queue` — accetta `behavior` + `linked_suite_id`.

### 6.2 Endpoint invariati

- Runtime mock (`/mock/{server_endpoint}/...`)
- SSE eventi runtime (`/elaborations/execution/{id}/events`)
- Schedulazioni (`/elaborations/test-suite-schedule`)
- CRUD broker, queue, datasource, logs

## 7. Migrazione (one-shot)

### 7.1 Hook 4 → 2

Pseudo-codice migrazione:

```python
for suite in test_suites:
    setup_steps    = collect(suite.beforeAll) + collect(suite.beforeEach)
    teardown_steps = collect(suite.afterEach) + collect(suite.afterAll)
    create_suite_item(suite, role='setup', commands=setup_steps)
    create_suite_item(suite, role='teardown', commands=teardown_steps)
    delete_old_hooks(suite)
```

**Breaking change da comunicare:** la semantica `beforeEach`/`afterEach` (1 volta per test) viene persa. Chi la usava per resettare stato fra test deve esplicitarlo nel primo step di ogni test (o in un test "reset" data-driven). **Documentare in release note.**

### 7.2 Test esistenti

Tutti i test esistenti diventano `template_kind = custom` automaticamente. `template_config = NULL`. I loro `suite_item_commands` restano invariati. Nessuna perdita.

### 7.3 Mock esistenti

Tutti i mock esistenti diventano `behavior = advanced` automaticamente. La pipeline a 3 fasi resta visibile per loro. Quando l'utente li edita, può scegliere di "Simplify to reply_only/reply_and_run_suite" se la pipeline è compatibile (heuristic check: solo 1 `runSuite` in post → `reply_and_run_suite`; pipeline vuota → `reply_only`; altrimenti `advanced`).

## 8. Piano di rollout in fasi

### Fase 1 — Foundation (backend)
- Migrazione DB (colonne nuove, default sicuri).
- Migrazione hook 4→2.
- Endpoint `POST /test` con `template_kind = custom` (parità con oggi via Angular).
- Endpoint `convert-to-custom` (no-op se già custom).
- Test backend: snapshot template `custom` invariato.

### Fase 2 — Templates (backend + UI base)
- Template engine server-side (`send_verify`, `mock_assert`).
- Endpoint `GET /templates`.
- UI Angular: dialog "New Test" con scelta template (3 card: Send & Verify, Mock & Assert, Custom).
- UI Angular: form-builder per `send_verify` e `mock_assert`.
- UI Angular: timeline read-only degli step generati.

### Fase 3 — Data-driven
- Toggle nel test editor.
- Runtime: loop di esecuzione + parent/child execution.
- UI execution view: raggruppamento parent/child con expand.

### Fase 4 — Mock simplificato
- UI Angular: selettore "When called, do…" sull'endpoint API e queue mock.
- Backend: validazione behavior + linked_suite_id.
- Heuristic "Simplify" su mock esistenti.

### Fase 5 — Hook semplificati
- UI Angular: expander `Setup` / `Teardown` in cima al Suite Editor.
- Rimozione pagina `Advanced suite settings`.

### Fase 6 — Polish & deprecation
- Rimozione codice legacy 4-hook.
- Telemetria: % test creati per template, % mock per behavior.
- Estendibilità: documentare come aggiungere un nuovo `template_kind`.

## 9. Definizione "Advanced mode" nel Test Editor

Toggle in alto a destra `Advanced ⓘ`. Quando OFF (default):
- Form del template visibile, campi editabili.
- Timeline read-only sotto il form.
- Pulsante "Convert to Custom" in fondo.

Quando ON (solo se `template_kind = custom`):
- Lista step editabile (add/remove/reorder).
- Pannello "Variables" con scope (`global`, `local`, `runEnvelope`, `result.constants`).
- Pannello "Sources" (dataset, jsonArray) collassato di default.

I template `send_verify` e `mock_assert` non hanno modalità Advanced — solo "Convert to Custom".

## 10. Estensibilità futura (non implementare ora, ma non bloccare)

- `template_kind` è una stringa. Domani si può aggiungere `replay_log`, `chaos_inject`, `load_test`, etc.
- `GET /templates` ritorna meta dinamici → l'UI Angular renderizza form dinamici da JSON Schema.
- I template definiti dall'utente vivranno in una tabella `user_templates` con `template_config_schema` (JSON Schema) e una funzione `generate_commands` (Python o expression).
- Il toggle `data_driven` rimarrà trasversale a tutti i template futuri.

## 11. Rischi e mitigazioni

| Rischio | Mitigazione |
|---|---|
| Utenti che usano `beforeEach` perdono funzionalità | Release note esplicita + script di analisi pre-migrazione che logga i casi |
| Template troppo rigidi → utenti frustrati passano a custom | Telemetria: se >40% va in custom subito, rivedere template |
| Data-driven con dataset enormi | Hard limit + warning UI + paginazione execution view |
| Mock `advanced` resta usato in massa (nessuno migra) | OK by design, è retrocompatibile. Niente da migrare a forza. |
| Convert-to-custom per errore | Conferma esplicita con testo "this cannot be undone" |

## 12. Definition of Done per ogni fase

- Backend: tutti i test pytest passano, copertura nuova ≥80%.
- UI Angular: ogni schermo ha storybook + test E2E per il flusso felice.
- Docs: `SPEC.md` aggiornato, `STORIES_INDEX.md` aggiornato, release note.
- Telemetria: evento `test_created` con `template_kind` e `data_driven`, evento `mock_behavior_set` con `behavior`.

## 13. Out of scope (per non scope-creep)

- Editor visuale flowchart degli step.
- Versionamento dei template.
- Marketplace di template community.
- Refactor del formato `command_constant_definitions` (resta com'è).
- Refactor scheduler (resta com'è).
- Migrazione end-to-end di Streamlit a Angular (questa è una direttiva separata).

---

## Appendice A — Mapping vecchio → nuovo

| Concetto attuale | Concetto nuovo | Note |
|---|---|---|
| `suite_items` con role `test` | `suite_items` con `role=test` + `template_kind` | Default `custom` per migrati |
| `suite_items` con role hook | `suite_items` con `role=setup\|teardown` | Aggregati 4→2 |
| `suite_item_commands` | invariato | Snapshot generati o manuali |
| `command_constant_definitions` | invariato | Symbol table immutata |
| `sources` (dataset/jsonArray batch) | invariato per `custom`; derivati per template | Template li produce internamente |
| `pre_response_commands` / `post_response_commands` (mock) | nascosti dietro `behavior` | Solo `advanced` li mostra |
| Pagina `Advanced suite settings` | Rimossa | Setup/teardown in Suite Editor |
| 4 hook | 2 hook | Migrazione one-shot |

## Appendice B — Esempio: creazione "Send & Verify" data-driven

**Step utente:**
1. Suite Editor → "Add test" → card "Send & Verify".
2. Form:
   - Queue: `customer-events`
   - Payload: JSON inline `{"id": "${row.id}", "email": "${row.email}"}`
   - Wait: `500ms`
   - Assert: target=`queue`, queue=`customer-events-ack`, operator=`exists`
3. Toggle "Run for each row" → ON, dataset = `customers`.
4. Save.

**Cosa succede lato server:**
1. `POST /elaborations/test-suite/{id}/test` con `template_kind=send_verify`, `template_config={...}`, `data_driven=true`, `dataset_id=...`.
2. Backend genera 3 `suite_item_commands`:
   - `sendMessageQueue` con payload templated.
   - `wait` 500ms.
   - `receiveMessage` + assert.
3. Salva snapshot.

**Cosa succede a runtime:**
1. Scheduler/manual run avvia il test.
2. Runtime carica `customers` (50 righe).
3. Crea parent `suite_item_execution` (row_index=NULL).
4. Per ogni riga: crea child execution, popola `${row.*}` in scope `local`, esegue i 3 command, registra esito.
5. Parent execution = aggregato (success se tutti i child success).

## Appendice C — Esempio: Mock con trigger Suite

**Step utente:**
1. Mock Server Editor → endpoint `POST /orders` → "When called, do…": `Reply and run suite`.
2. Response statica: `{"orderId": "123", "status": "accepted"}`.
3. Linked suite: `Order Verification Suite`.
4. Save.

**Cosa succede lato server:**
1. `mock_server_apis.behavior = 'reply_and_run_suite'`, `linked_suite_id = ...`.
2. `pre_response_commands = []`, `post_response_commands = [{ kind: "runSuite", suite_id }]` (generati dal backend).

**Cosa succede a runtime:**
1. Chiamata `POST /mock/.../orders` → response immediata.
2. Background: esegue `Order Verification Suite` con `runEnvelope.trigger.type = 'mock_api'`, `runEnvelope.trigger.api_id`.
3. Esito visibile in execution history della suite.
