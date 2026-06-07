# Quality Flow - Functional Specification

## 1. Project Overview
Quality Flow e un'applicazione per gestire broker SQS, queue e payload JSON, con funzioni di test, invio/ricezione/ack messaggi e orchestrazione scenari.

L'applicazione e composta da:
- Backend FastAPI (`app/main.py`)
- UI Streamlit multipage (`app/ui/Quality Flow.py`)

## 2. Scope Funzionale
La soluzione copre:
- configurazione broker SQS (ElasticMQ/Amazon)
- configurazione connessioni database (Postgres/Oracle/MSSQL)
- configurazione mock server API/queue con trigger asincroni
- gestione queue per broker
- operazioni runtime su queue (test connessione, send, receive, ack)
- gestione datasource 
    - JSON array
    - dataset (table/view da database)
- gestione scenari di test
    - creazione di scenari composti da test e operazioni
    - esecuzione singola o multipla di scenari
    - esecuzione singola di scenari in modalità debug
    - schedulazione ricorrente delle suite di test
- visualizzazione log applicativi
- import configurazione mock server da file OpenAPI JSON

## 3. Routing UI
Pagine disponibili:
- `Home`
- `Configurations` 
    - `Brokers`
    - `Database Connections`
    - `Mock Servers`
        - `Mock Server Editor`
- `SQS Brokers` 
    - `Queues`
        - `Queue details`
- `Datasources`
    - `Json Array`
    - `Dataset`
        - `DatasetPerimeterEditor` (hidden page)
- `Test suites`
    - `Test Suites`
        - `Suite Editor`
        - `Advanced suite settings`
    - `Test Suite Schedules`
- `Logs`
- `Tools`


## 4. Specifiche per Pagina

### 4.1 Brokers
Obiettivi:
- visualizzare elenco broker configurati
- consentire inserimento/modifica/cancellazione broker
- aprire la pagina `Queues` del broker selezionato

Dati principali mostrati:
- code
- description
- tipo connessione/configurazione

### 4.2 Database Connections
Obiettivi:
- elenco connessioni database
- CRUD connessioni (Postgres/Oracle/MSSQL)
- test connessione configurata

### 4.3 Queues
Obiettivi:
- mostrare le queue del broker selezionato
- visualizzare metriche queue (messaggi, ultimo aggiornamento)
- aggiungere/modificare/cancellare queue
- navigare al `Queue details` della singola queue

### 4.4 Queue details
Header:
- metrica `Approximante number of messages`
- metrica `Not visible messages`
- azioni `Refresh` e `Test connection`

Tab disponibili:
- `Send`
- `Receive`

Funzioni `Send`:
- create/edit json-array body (dialog `Write json-array`)
- select datasource da JSON array salvati
- save json-array nel datasource
- send messages alla queue
- view results invio

Funzioni `Receive`:
- ricezione messaggi dalla queue
- preview JSON messaggi ricevuti
- ack messages (PUT su endpoint queue messages)
- extract json-array da messaggi ricevuti e salvataggio datasource
- clean preview

### 4.5 Json Array
Obiettivi:
- elenco datasource JSON array
- aggiunta/modifica/cancellazione item
- preview payload JSON

### 4.6 Dataset
Obiettivi:
- elenco dataset tabellari
- CRUD datasource database
- scelta tabella/view da connessione tramite dialog con tree tables/views
- preview dati tabella/view configurata
- UI principale con expander collassati per dataset e preview inline on-demand
- configurazione del perimeter in pagina dedicata `DatasetPerimeterEditor`
- supporto a dataset parametrizzabili tramite `perimeter.parameters`
- i filtri del perimeter possono usare valori literal oppure riferimenti espliciti a parametri `{ "kind": "parameter", "name": "..." }`
- i parametri supportano i tipi `string`, `integer`, `number`, `boolean`, `date`, `datetime`
- i parametri dataset supportano `default_value` per literal statici oppure `default_binding` con shape `{ "kind": "built_in", "resolver": "$now|$today" }`; i due campi sono mutuamente esclusivi
- i built-in dei parametri dataset vengono ricalcolati a ogni preview/esecuzione usando il clock del processo applicativo
- la preview dataset non accetta input manuali dei parametri: i parametri non valorizzati restano `null`

### 4.7 Test Suites
Obiettivi:
- selezionare suite
- aggiunta/cancellazione item
- eseguire la suite selezionata
- navigare al `Suite Editor` della singola suite


### 4.8 Suite Editor
Obiettivi:
- aggiungere test embedded e operazioni alla suite
- configurare i 2 hook lifecycle `setup` e `teardown` direttamente nel Suite Editor (collassati dai 4 hook legacy `beforeAll`/`beforeEach`/`afterEach`/`afterAll` con la migration qsm_047; vedi [QSM-047](stories/QSM-047-TEST-SUITES-FOUNDATION.md) per il breaking change su `beforeEach`).
- eseguire singoli test o l'intera suite
- visualizzare stato ultima esecuzione di hook/test/operazioni (check/error/idle)
- mostrare avanzamento esecuzione suite in tempo reale (test eseguiti / totali)
- mantenere in header `Execution history`, `Run`, e (legacy Streamlit) `Advanced settings` — la pagina `Advanced suite settings` viene dismessa con la Phase 6 del refactor
- il dialog `Add command` supporta:
  - un solo submit locale che aggiunge snapshot contestuale all'item
  - ogni command espone sempre `commandCode` e `commandType`
  - ogni hook/test distingue `sources` dichiarative e `commands` eseguibili
  - i Commands batch usano `setVariable` e `deleteVariable`
  - `setVariable` supporta solo `value`, `json`, `function`
  - `dataset` e `jsonArray` batch sono `sources`, non Commands
  - i command consumer batch usano `inputRef` con `kind = runtimeValue|source`
  - gli assert batch usano `actualRef` e `expectedRef`
  - i command che producono output tecnici possono dichiarare `resultConstant`
  - il runtime usa `runEnvelope/global/local/result.constants` come scope risolvibili
  - le dataset sources batch persistono un `perimeter` locale indipendente dal dataset catalogato
  - i binding supportati per dataset source sono: valore literal, `{ "kind": "constant_ref", "definitionId": "..." }`, `{ "kind": "built_in", "resolver": "$now|$today" }`
  - `sendMessageQueue`, `saveTable` ed `exportDataset` materializzano le righe a runtime sia da Commands sia da data sources batch
  - le queue non sono selezionabili come batch source

Modello dati suite:
- `test_suites`, `suite_items` e `suite_item_commands` contengono i dettagli funzionali usati in esecuzione.
- `command_constant_definitions` mantiene la symbol table persistita per suite e mock commands.
- La suite non dipende piu da `test_id`/`command_id` in runtime e non usa cataloghi condivisi di command.
- Da qsm_047 in poi: `suite_items` espone `role` (`test|setup|teardown`), `template_kind` (`custom|send_verify|mock_assert`), `template_config` (JSONB), `data_driven` (bool), `dataset_id` (FK `json_payloads.id`). I valori `kind`+`hook_phase` legacy restano popolati per backward-compat del runtime; `role` è il discriminante autoritativo del codice nuovo. `suite_item_executions` espone inoltre `parent_execution_id`, `row_index`, `row_snapshot` per le esecuzioni data-driven (Fase 4).
- Da QSM-048 in poi: nuovi `CommandCode` runtime `receiveQueue` (riceve fino a N messaggi da una queue, scrive in target+resultConstant) e `queryDatabase` (esegue SQL arbitraria su una connection, scrive in target+resultConstant). Vengono emessi dal template engine `send_verify` e `mock_assert` per popolare l'`actualRef` degli assert. Endpoint nuovi: `GET /elaborations/templates`, `POST /elaborations/templates/preview`.

Pagina `Advanced suite settings` (legacy, in dismissione con Phase 6):
- hidden page raggiungibile dal gear del `Suite Editor` Streamlit
- contiene le sezioni hook `Before suite`, `Before each test`, `After each test`, `After suite`
- riusa lo stesso contratto di command/hook della suite
- Stato attuale: dopo qsm_047 le 4 fasi sono state collassate in 2 (`setup` + `teardown`), perciò la pagina mostra solo i 2 hook unici. Verrà rimossa dal nuovo Suite Editor Angular (`quality-flow-ng-app`).


### 4.9 Logs
Obiettivi:
- visualizzare i log
- filtrare log per livello, tipo, subject, messaggio e intervallo data
- pulire log vecchi per numero giorni

### 4.10 Mock Servers
Obiettivi:
- creare/modificare/cancellare mock server con endpoint dedicato
- configurare API mock (`method`, `path`, params/headers/body, response)
- configurare queue binding verso queue esistenti
- associare command a trigger API e queue (incluso `runSuite`)
- attivare/disattivare runtime mock server
- importare route da file OpenAPI 3.x JSON

Import OpenAPI JSON:
- bottone `Import` nella sezione APIs del `MockServerEditor`
- file upload `.json` con parsing OpenAPI 3.x
- preview sintetica: numero API importabili, duplicati saltati, warning, path templated rilevati, errori
- append mode: le route importate vengono aggiunte alle API esistenti
- duplicate detection: skip route con stesso `method + normalized path`
- path templated (es. `/orders/{id}`) importati letteralmente; il runtime matcha la stringa letterale
- mapping OpenAPI → mock route: `description` da summary/operationId/fallback `METHOD path`, response da primo example JSON o fallback `{ "status": "ok" }`

Comportamento runtime:
- route runtime sotto prefisso fisso `/mock/{server_endpoint}/...`
- pipeline command API:
  - `pre_response_commands` (sync, senza side effects)
  - response statica/dinamica da configurazione route
  - `post_response_commands` (async, side effects consentiti)
- i command mock e suite condividono la stessa risoluzione costanti `definitionId -> command_constant_definitions -> scope runtime`
- risposta API mock immediata, operazioni eseguite in background
- listener queue avviati solo quando il server e attivo
- su trigger queue viene eseguito `ACK` sempre (anche in caso errore operazioni)

### 4.11 Test Suite Schedules
Obiettivi:
- elenco schedulazioni con filtro per suite, stato, prossima esecuzione e ultima esecuzione
- CRUD schedulazioni con frequenza configurabile (`minutes`, `hours`, `days`)
- finestra temporale opzionale (`start_at`, `end_at`)
- azioni rapide: `Run now`, `Activate/Deactivate`, `Edit`, `Delete`
- policy overlap: `skip if running` per evitare esecuzioni parallele della stessa suite
- trigger schedulato integrato nel `runEnvelope` con metadata `trigger.type = schedule`
- aggiornamento automatico `last_status`, `last_execution_id`, `last_error_message` dopo ogni esecuzione

## 5. API Funzionali Principali
- `/broker/connection` CRUD broker connection
- `/broker/{broker_id}/queue` CRUD queue e operazioni queue/messages
- `/data-source/json-array` CRUD JSON array datasource
- `/data-source/database` CRUD datasource database
- `/database/connection` CRUD connessioni database + test + metadata objects/preview
- `/elaborations/test-suite` elenco/gestione test suite ed esecuzione
- `/elaborations/test-suite/{test_suite_id}/test/{suite_item_id}/execute` esecuzione asincrona del singolo test
- `/elaborations/execution/{execution_id}/events` stream SSE eventi runtime esecuzione
- `/mock-server` CRUD configurazione mock server + activate/deactivate
- `/mock/{server_endpoint}/{path}` runtime mock API dispatcher
- `/elaborations/test-suite-schedule` CRUD schedulazioni + activate/deactivate + run-now
- `/logs/` elenco log
- `/logs/{days}` pulizia log
- `/json_utils/` utility elaborazione JSON
- `/public/idp-config` configurazione Identity Provider

## 6. Vincoli Operativi
- Avvio standard via Docker Compose.
- UI dipende da `QUALITY_FLOW_API_BASE_URL`.
- I test backend usano Docker/Testcontainers.

