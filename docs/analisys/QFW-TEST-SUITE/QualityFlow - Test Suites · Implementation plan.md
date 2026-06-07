# QualityFlow — Test Suites · Implementation plan

> Piano di implementazione Angular + DevExtreme del dominio **Test suites**.
> Si appoggia ai documenti di redesign (`QFW-SUITE-MOCK-REDESIGN.md`) e al brief mockup (`QFW-CLAUDE-DESIGN-MOCKUP-BRIEFS.md`), recependo tutte le decisioni concettuali consolidate in chat.

---

## 0. Snapshot delle decisioni consolidate

| Area | Decisione |
|---|---|
| Navigazione | Sidebar Level 1 only · 5 voci (Home · Configurations · Datasources · **Test suites** · Logs) |
| Branding | "QualityFlow" — Q e F in teal (`#2dd4bf`), resto bianco |
| Stack UI | Angular + DevExtreme + Monaco editor + SSE per esecuzioni live |
| Hook lifecycle | **4 → 2** (`setup` + `teardown`). `beforeEach` perso: documentare in release note |
| Test creation | **Template-first** · 3 template iniziali: `send_verify`, `mock_assert`, `custom` |
| Convert to Custom | One-way irreversibile · confirm dialog dedicato |
| Data-driven | Toggle trasversale su qualsiasi test, prefisso `${row.column}`, warning su >1000 righe |
| Save model | **Esplicito uniforme** — dialog modificano stato locale, persiste solo "Save" del Suite/Test editor |
| Run | Singolo test **sempre con setup+teardown**; nessuna interruzione (no Stop) |
| Drawer | Live + History condividono lo stesso componente |
| Execution view | Smart-default timeline (espansa solo nodi falliti) · JSON tree diff · Re-run = nuova execution |
| Test indipendenza | Test atomici — la suite continua su test fallito |
| Lingua copy | Inglese |

---

## 1. Modello dati (Backend / DB)

> Recepisce §4 di `QFW-SUITE-MOCK-REDESIGN.md`. Nessuna modifica al runtime esistente.

### 1.1 Migrazioni

```sql
-- 1) Suite items: template + role + data-driven
ALTER TABLE suite_items
  ADD COLUMN role             varchar(16)  NOT NULL DEFAULT 'test',  -- 'test' | 'setup' | 'teardown'
  ADD COLUMN template_kind    varchar(32)  NOT NULL DEFAULT 'custom',-- 'send_verify' | 'mock_assert' | 'custom'
  ADD COLUMN template_config  jsonb        NULL,
  ADD COLUMN data_driven      boolean      NOT NULL DEFAULT false,
  ADD COLUMN dataset_id       uuid         NULL REFERENCES json_payloads(id);

CREATE INDEX idx_suite_items_role ON suite_items(test_suite_id, role, position);

-- 2) Esecuzioni data-driven parent/child
ALTER TABLE suite_item_executions
  ADD COLUMN parent_execution_id uuid    NULL REFERENCES suite_item_executions(id),
  ADD COLUMN row_index           integer NULL,
  ADD COLUMN row_snapshot        jsonb   NULL;

CREATE INDEX idx_executions_parent ON suite_item_executions(parent_execution_id);
```

### 1.2 Migrazione hook 4 → 2 (one-shot)

Pseudocodice:

```
FOR suite IN test_suites:
  setup_steps    = concat(suite.beforeAll.commands, suite.beforeEach.commands)
  teardown_steps = concat(suite.afterEach.commands, suite.afterAll.commands)
  INSERT INTO suite_items (role='setup',    template_kind='custom', commands=setup_steps)
  INSERT INTO suite_items (role='teardown', template_kind='custom', commands=teardown_steps)
  DELETE FROM old hook rows
```

**Breaking change** da documentare: la semantica "per test" del `beforeEach` viene **collassata** in un setup unico → chi la usava per resettare stato fra test deve:
- spostare quel reset come **primo step di ogni test**, oppure
- creare un test "reset state" all'inizio della suite

Script di analisi pre-migrazione: contare quante suite hanno `beforeEach` non vuoto + loggare le suite a rischio.

### 1.3 Migrazione test esistenti

Tutti i `suite_items` esistenti con `role='test'` diventano automaticamente `template_kind='custom'`, `template_config=NULL`. I loro `suite_item_commands` restano invariati. **Zero perdita di funzionalità.**

---

## 2. Schemi `template_config` per template

### 2.1 `send_verify`

```jsonc
{
  "broker_id": "uuid",
  "queue_id": "uuid",
  "payload": {
    "kind": "json_inline | json_array_ref | dataset_ref",
    "value": "<json or uuid>"
  },
  "wait_ms": 500,
  "asserts": [
    {
      "target": "queue | database | none",
      "queue_id": "uuid?",
      "database_query": "string?",
      "operator": "equals | contains | matches_schema | exists",
      "expected": "<json | $ref>"
    }
  ]
}
```

### 2.2 `mock_assert`

```jsonc
{
  "trigger_hint": "string (info-only)",
  "wait_ms": 1000,
  "asserts": [ /* uguale a sopra */ ]
}
```

### 2.3 `custom`

`template_config = null` — i `suite_item_commands` sono la fonte di verità.

---

## 3. API (Backend)

### 3.1 Nuovi / modificati endpoint

| Method | Path | Note |
|---|---|---|
| `GET`  | `/elaborations/templates` | Metadati template (per chooser UI dinamica) |
| `POST` | `/elaborations/test-suite/{id}/test` | Crea test · accetta `template_kind` + `template_config` · backend genera commands snapshot |
| `PUT`  | `/elaborations/test-suite/{id}/test/{item_id}` | Update · rigenera commands se template; sostituisce commands se custom |
| `POST` | `/elaborations/test-suite/{id}/test/{item_id}/convert-to-custom` | Copia commands generati, scarta `template_config`, setta `template_kind=custom` · **idempotente** se già custom (no-op) |
| `POST` | `/elaborations/test-suite/{id}/hooks/{role}/commands` | CRUD step su setup/teardown (`role='setup'\|'teardown'`) |

### 3.2 Endpoint invariati

- Runtime mock (`/mock/{server_endpoint}/...`)
- SSE eventi runtime (`/elaborations/execution/{id}/events`)
- Schedulazioni (`/elaborations/test-suite-schedule`)
- CRUD broker/queue/datasource/logs

### 3.3 Template engine server-side

Modulo Python `app/templating/`:
- `template_registry.py` — registry dei `template_kind` validi
- `templates/send_verify.py` — funzione `generate_commands(config) -> list[Command]`
- `templates/mock_assert.py` — idem
- Test pytest: snapshot dei commands generati per ogni template

---

## 4. Frontend Angular — architettura

### 4.1 Feature module

```
src/app/features/test-suites/
├── pages/
│   ├── suites-list/                # Mockup 1
│   ├── suite-editor/               # Mockup 2
│   ├── test-editor/                # Mockup 4 + 5 (modalità switchata)
│   └── execution-view/             # Mockup 9
├── dialogs/
│   ├── new-test-dialog/            # Mockup 3
│   ├── step-editor-dialog/         # Mockup 6
│   └── convert-to-custom-dialog/   # Mockup 10
├── components/
│   ├── test-card/
│   ├── setup-teardown-expander/
│   ├── generated-steps-timeline/   # right pane in template mode
│   ├── variables-scope-panel/      # right pane in custom mode
│   ├── assert-row/
│   ├── payload-editor/             # wrapper Monaco
│   ├── quick-run-drawer/           # Mockup 11
│   ├── execution-timeline-tree/
│   └── json-diff-viewer/
├── services/
│   ├── test-suites.service.ts
│   ├── test-suite-execution.service.ts # gestisce SSE
│   ├── template-registry.service.ts
│   └── unsaved-changes.guard.ts
├── store/
│   └── suite-editor.store.ts       # stato locale + dirty flag
└── models/
    ├── test-suite.model.ts
    ├── test-template.model.ts
    └── execution.model.ts
```

### 4.2 Routing

```
/test-suites
  ├── /              → suites-list
  ├── /:suiteId      → suite-editor
  │   └── /tests/:testId       → test-editor (mode dedotto da template_kind)
  └── /:suiteId/executions/:executionId  → execution-view
```

### 4.3 Pattern di state management

- **Editor pages** (suite-editor, test-editor): store locale con dirty flag + diff vs server snapshot
- **Save esplicito**: bottone Save nella toolbar → trigger PUT, su 200 reset dirty
- **Unsaved-changes guard**: confirm dialog "Discard changes?" su navigation
- **Dialog (Step Editor / New Test / Convert)**: emettono evento `applied(payload)` raccolto dallo store del parent → **non chiamano API direttamente**

### 4.4 DevExtreme widgets in uso

| Pagina | Widget DX |
|---|---|
| Suites list | `dx-data-grid` (table mode) · `dx-tile-view` (card mode) · `dx-text-box` · `dx-select-box` · `dx-toast` (snackbar) |
| Suite editor | `dx-sortable` (drag tests) · `dx-accordion` (Setup/Teardown) · `dx-popup` (Schedule dialog) |
| Test editor template | `dx-form` (parziale) · `dx-radio-group` (payload source) · `dx-tag-box` (preset wait) |
| Test editor custom | `dx-sortable` (steps) · `dx-tab-panel` (Variables/Constants/Envelope) |
| Step editor dialog | `dx-popup` · `dx-text-box` (search) |
| Execution view | `dx-tree-list` (timeline tree) · `dx-data-grid` (iterations) |

Monaco editor integrato custom (wrapper Angular) per:
- payload editor (JSON syntax + autocompletion `${row.*}`)
- database query editor (SQL syntax)
- expected value editor (JSON)

---

## 5. Componenti chiave — note implementative

### 5.1 `generated-steps-timeline`

Input: `template_kind` + `template_config` + `dataset_id?` + `previewRow?`.
Logica:
- Chiama `POST /elaborations/templates/preview` (endpoint helper) che restituisce gli step generati **senza salvare**
- Aggiornamento **al blur** dei field del form (debounce 250ms)
- Se `data_driven=true` e dataset disponibile, mostra valori risolti con `row[0]`

### 5.2 `payload-editor` (Monaco wrapper)

- Modalità `language=json`
- Autocompletion provider che suggerisce `${row.<column>}` se il padre è in `data_driven`
- Validazione live (JSON schema base + custom rule sui `${...}` placeholder)
- Persistenza: `[(value)]` two-way su `template_config.payload.value`

### 5.3 `step-editor-dialog`

Phase 1 — kind chooser:
- Lista lineare raggruppata (Producers / Consumers / Assertions / Control)
- Search bar (filtro client-side per nome e descrizione)
- Filtri contestuali: passa `availableKinds: string[]` da chi apre il dialog (es. setup di una suite esclude `runSuite` riflessivo)
- Conferma con doppio click oppure pulsante "Continue"

Phase 2 — kind-specific form:
- Mappa `kind → ComponentRef` (ngComponentOutlet)
- Validazione reactive-forms · Save disabilitato finché invalido
- Edit: Phase 1 **skippata** (kind bloccato)
- Esc / click outside → confirm "Discard changes?" se dirty

### 5.4 `execution-timeline-tree`

- `dx-tree-list` con `dataStructure: tree`
- Smart default: pre-espande solo nodi `status='failed'` + nodo `current` se running
- Toolbar: search (filtra per name) · toggle "Only failed" · bottoni Expand all / Collapse all · shortcut `f` e `c`
- Data-driven: parent node con banner riassunto "N/M passed" · link "Show all iterations" apre dialog dedicata con `dx-data-grid` paginata

### 5.5 `quick-run-drawer`

- Wrapper `dx-popup` con `position: right` · larghezza 480
- Sottoscritto a SSE `/elaborations/execution/{id}/events`
- Compatto: 1 riga per step principale (setup / test×N / teardown), niente sub-step
- Footer link "Open full execution view →" → `execution-view`
- **Riusato anche per Execution history**: input `mode: 'live' | 'history'` con differenze minime di copy + sorgente dati

### 5.6 `json-diff-viewer`

Libreria: `jsondiffpatch` per il calcolo del diff.
Rendering custom:
- View di default: **tree con path evidenziati**, value rimossi in rosso, value attesi in verde
- Toggle "Side-by-side text" (Monaco diff editor) come secondaria

---

## 6. Rollout in fasi

> Allineato al rollout `QFW-SUITE-MOCK-REDESIGN.md` §8, ma calato sulle decisioni del mockup.

### Fase 1 — Foundation (BE + shell Angular)
- Migrazione DB: nuove colonne + hook 4→2 + script analisi pre-migrazione
- Endpoint CRUD test con `template_kind=custom` (parità funzionale con oggi)
- `convert-to-custom` no-op
- Frontend: feature module scaffolding + routing + Sidebar Level 1 con voce "Test suites"
- **Demo target**: Suites list + Suite editor in modalità custom (parità Streamlit)

### Fase 2 — Template engine
- Backend: template engine + endpoint `GET /templates` + `POST /test` con `template_kind=send_verify|mock_assert`
- Frontend:
  - `new-test-dialog` (template chooser)
  - `test-editor` modalità template per `send_verify` e `mock_assert`
  - `generated-steps-timeline` con preview server-side
- **Demo target**: creazione test funzionante in <60s con Send & Verify

### Fase 3 — Custom mode + Step editor
- Frontend:
  - `test-editor` modalità custom
  - `step-editor-dialog` (kind chooser + form per ogni kind)
  - `variables-scope-panel`
  - `convert-to-custom-dialog`
- **Demo target**: utente avanzato monta un test custom end-to-end

### Fase 4 — Data-driven
- Backend: runtime loop per riga + persistenza parent/child execution
- Frontend:
  - Toggle "Run for each row" nei due editor
  - Banner riassunto + expand iterazioni nella execution view
  - Preview row 0 nella timeline template-mode
- **Demo target**: test data-driven su 50 righe, debug iterazione fallita

### Fase 5 — Execution view + Quick run drawer
- Frontend:
  - `execution-view` completa (timeline + detail panel + diff)
  - `quick-run-drawer` (live + history)
  - SSE integration in service condiviso
- **Demo target**: lancio suite con drawer live + drill-down su fallimento

### Fase 6 — Polish & deprecation
- Rimozione pagina `Advanced suite settings` (Streamlit)
- Rimozione codice 4-hook legacy
- Telemetria: `test_created` (template_kind, data_driven), `mock_behavior_set` (behavior), `template_convert_to_custom`
- Accessibilità: pass WCAG AA, focus visibili, shortcuts (`f`, `c`, Esc)
- Empty/loading/error states per ogni schermata
- Mobile: collapse sidebar < 1024px, 2 colonne → 1 (scrollabile)

---

## 7. Definition of Done per fase

- **Backend**: pytest pass, copertura modulo nuovo ≥ 80%, snapshot tests per template engine
- **Frontend**: lint + unit pass, E2E happy-path per ogni schermata (Cypress / Playwright)
- **Docs**: `SPEC.md` aggiornato, release notes con breaking changes
- **Telemetria**: eventi tracciati ed esposti in dashboard interna

---

## 8. Rischi e mitigazioni

| Rischio | Mitigazione |
|---|---|
| Perdita `beforeEach` rompe suite esistenti | Script di analisi pre-migrazione + release note + tutorial migrazione |
| Template troppo rigidi → fuga in custom | Telemetria `template_kind` distribution. Se custom > 40% → ripensare template (aggiungere `db_verify`, `chain`, ...) |
| Data-driven con dataset enormi | Warning UI > 1000 righe + hard limit lato scheduler (configurabile) |
| Confusione "Save esplicito" vs "Step dialog salva al volo" | **Risolto in chat**: tutti i dialog modificano stato locale, save unico del parent |
| Monaco editor pesante in bundle | Lazy load del modulo Monaco solo nei `test-editor` |
| SSE su browser non supportato | Fallback polling 2s, già pattern noto nel backend |

---

## 9. Estensibilità futura (non bloccante)

- **Template aggiuntivi**: `db_verify` (query + assert senza send), `chain` (N invii sequenziali), `replay_log`, `chaos_inject`
- **Template engine dinamico**: `GET /templates` ritorna JSON Schema → UI renderizza form dinamicamente (oggi è hard-coded Angular)
- **Marketplace template** (utente o community-defined)
- **Re-run failed only** nella Execution view (oggi: Re-run = nuova esecuzione completa)
- **Execution stop** (oggi: non supportato)
- **Data-driven con paginazione esecuzioni** (oggi: tutte le iterazioni serializzate)

---

## 10. Schermate fuori scope di questo dominio

Coperte da altri brief/specifiche, non incluse qui:
- Home dashboard (esecuzioni storiche · grafici · filtri)
- Configurations (Brokers, Connections, Mock servers)
- Datasources (Dataset, Json Array)
- Logs
- Schedules editor (esiste, linkato da Suites list e Suite editor)
- Mock Server editor con behavior selector — separato, prossimo brief

---

## Appendice A — Mapping decisioni → componenti

| Decisione concettuale | Dove vive |
|---|---|
| Sidebar L1 only + breadcrumb topbar | Shell app + `Topbar` component |
| Inline edit titolo (icona matita) | `EditableInlineText` component (riusato in Suite + Test editor) |
| Drag handle + kebab "Move to top/bottom" | `dx-sortable` wrapper + `kebabMenuItems` configurabile |
| Schedule chip persistente solo se attiva | `ScheduleChip` in `SuiteEditorHeader` (conditional render) |
| Timeline read-only sticky | `position: sticky` su `generated-steps-timeline` |
| Auto-preview row 0 in data-driven | Effetto in `suite-editor.store` quando `data_driven=true` |
| JSON tree diff con path | `json-diff-viewer` con jsondiffpatch + tree renderer custom |
| Toggle Only failed + shortcut `f` | `hostListener` sul `execution-view` + UI button |
| Confirm "Discard changes?" su navigate | `UnsavedChangesGuard` con `CanDeactivate` |
| Snackbar "Suite is running" su Run da kebab | `dx-toast` invocato da `suites-list` |

---

## Appendice B — Esempio E2E happy path

**Goal:** un utente nuovo crea una suite con un test data-driven Send & Verify e la lancia.

1. Sidebar → `Test suites`
2. Suites list → `+ New suite` → dialog nome/descrizione → arrivo a Suite Editor vuoto
3. `+ Add test` → New Test dialog → seleziono `Send & Verify` → Continue
4. Test Editor template mode:
   - Broker = `amazon-akeron` · Queue = `customer-events`
   - Payload Inline JSON (Monaco): `{"id": "${row.id}", "email": "${row.email}"}`
   - Wait = 500ms (chip preset)
   - + Add assertion: Queue · `customer-events-ack` · exists
   - Toggle Iteration ON · Dataset = `customers` (50 rows)
   - Timeline a destra mostra 4 step con riga 0 risolta
   - **Save** (toolbar)
5. Breadcrumb → torno al Suite Editor → vedo la test card · `▶ Run suite`
6. Quick Run drawer si apre · setup → 50 iterazioni → teardown · Success
7. Link "Open full execution view →" → Execution view con timeline gerarchica e banner "50/50 passed"
