# QSM - Refactor Sources, Commands e Dataset Perimeters

## Stato
Aggiornamento 2026-03-28:
- Slice attiva: batch-first
- Stato implementazione: in progress
- Rename applicato: `initConstant/deleteConstant` -> `setVariable/deleteVariable`
- Contratto batch: `sources + commands`
- Queue rimossa come source batch
- Hard cut dati suite/mock incompatibili tramite migration distruttiva

## Scope della slice corrente
- include solo suite batch
- include data sources `dataset` e `jsonArray`
- include perimeter locale per dataset source
- esclude trigger streaming e refactor completo del runtime mock

- Stato: Proposed
- Modalità: hard cut concettuale
- Area: Backend FastAPI + UI Streamlit + runtime suite/mock
- Obiettivo: separare in modo netto le sorgenti dichiarative dai valori runtime e ridefinire il ruolo del dataset perimeter

---

# 1. Obiettivo

Ristrutturare il modello di costruzione ed esecuzione dei test in Quality Flow introducendo quattro concetti distinti:

1. **Data Sources**
   sorgenti dichiarative disponibili in hook o test

2. **Commands**
   valori effettivi presenti nel contesto di esecuzione

3. **Streaming Triggers**
   eventi esterni che avviano test event-driven

4. **Local Dataset Perimeter**
   perimetro locale della source dataset, copiato dal dataset base ma poi indipendente

L’obiettivo è eliminare l’ambiguità attuale in cui `dataset`, `jsonArray` e `queue` sono trattati come se fossero tutti “variabili”, mentre in realtà rappresentano concetti diversi.

---

# 2. Problemi del modello attuale

## 2.1 Dataset e jsonArray non sono vere variabili runtime
Oggi dataset e jsonArray sono gestiti dentro il concetto di costante/variabile, ma semanticamente rappresentano soprattutto:
- riferimenti a sorgenti dati persistite
- input dichiarativi per command successivi
- configurazioni riusabili

Non sono quindi assimilabili a:
- un literal
- un json runtime
- un output prodotto da un command

## 2.2 Le queue come source nei test batch creano confusione
Usare una queue come `sourceType` in `initConstant` mescola due concetti diversi:
- leggere dati in un test batch
- reagire a un evento esterno

La queue è più correttamente un **trigger di streaming** dentro il mock runtime.

## 2.3 Il termine “constant” o “variable” è troppo ampio
Lato UX il termine unico porta a confondere:
- dati dichiarati a design-time
- dati letti o prodotti a runtime
- trigger di avvio della suite

## 2.4 Il perimeter del dataset oggi è solo base globale
Oggi il dataset ha un perimeter persistito e riusabile, ma nel contesto suite serve poter:
- partire da quel perimeter
- copiarlo nel punto d’uso
- cambiarlo anche radicalmente
- eventualmente promuovere la variante locale a nuovo dataset

---

# 3. Nuovo modello concettuale

## 3.1 Data Sources
Le Data Sources sono dichiarazioni disponibili a livello di:
- hook
- test

Tipi supportati in V1:
- `dataset`
- `jsonArray`

Caratteristiche:
- non sono command
- non hanno ordine di esecuzione
- non producono side effects
- non vengono “lanciate”
- sono solo dichiarazioni consumabili dai command

## 3.2 Commands
I Commands restano il contenuto vero del contesto di esecuzione.

Tipi consigliati:
- `value`
- `json`
- output tecnici / result artifacts
- functions
  - `now`
  - `today`

Caratteristiche:
- esistono nel runtime
- sono letti/scritti dai command
- hanno scope
- seguono il lifecycle del run

## 3.3 Streaming Triggers
I trigger rappresentano gli eventi esterni che fanno partire un test streaming.

Tipi supportati:
- API mock trigger
- Queue mock trigger

Caratteristiche:
- non sono data source
- non sono Commands creati dall’utente
- popolano `runEnvelope.event`
- avviano l’esecuzione della suite o del test streaming

## 3.4 Dataset Base vs Dataset Source Locale
Il dataset catalogato è un template riusabile.
Quando viene aggiunto come source in un hook o in un test:
- il suo perimeter viene copiato
- la source riceve un proprio perimeter locale
- da quel momento il perimeter locale è indipendente dal dataset di origine

Quindi:
- **dataset** = template di partenza
- **dataset source** = copia editabile locale nel test/hook

---

# 4. Decisioni architetturali

## 4.1 Dataset e jsonArray escono dal concetto di variabile
`dataset` e `jsonArray` non devono più essere modellati come normali variabili/costanti runtime.

Diventano:
- `Data Sources` dichiarative

## 4.2 Le sources non hanno ordine
Le sources:
- vengono dichiarate
- sono tutte disponibili nella sezione in cui vivono
- non partecipano al reorder dei command
- non fanno parte della symbol table position-aware dei Commands

## 4.3 Le queue non sono più source dei test batch
Le queue non devono più essere selezionabili come source generica di un test batch.

Restano supportate in:
- broker
- queue management
- mock runtime
- listener queue dei mock server

## 4.4 Le queue diventano trigger di streaming
Una queue deve essere usata per:
- ascoltare un evento
- creare un `runEnvelope.event`
- avviare un test streaming

## 4.5 Nessun merge del perimeter
Quando una source dataset viene creata da un dataset base:
- il perimeter base viene copiato
- non si calcola alcun merge con il dataset originario
- il perimeter della source è autonomo

## 4.6 Save as new dataset
Una source dataset locale può essere promossa a nuovo dataset persistito nel catalogo dataset.

---

# 5. Nuova tassonomia

## 5.1 Batch Test
Un batch test è eseguito:
- manualmente da UI
- via API
- via scheduler
- via `runSuite`

Input possibili:
- data sources dichiarative
- Commands iniziali
- built-in runtime
- parameter bindings delle dataset sources

## 5.2 Streaming Test
Uno streaming test è eseguito a seguito di:
- trigger API mock
- trigger queue mock

Input principali:
- `runEnvelope.event`
- `runEnvelope.meta`
- data sources dichiarative locali
- Commands derivati dal trigger

---

# 6. Nuovo modello dati suite

## 6.1 Principio
Ogni sezione di suite deve distinguere chiaramente tra:
- `sources`
- `commands`

## 6.2 Sezioni interessate
- `beforeAll`
- `beforeEach`
- `test`
- `afterEach`
- `afterAll`

## 6.3 Shape proposta

```json
{
  "beforeAll": {
    "sources": [],
    "commands": []
  },
  "beforeEach": {
    "sources": [],
    "commands": []
  },
  "tests": [
    {
      "id": "test-1",
      "code": "verify-orders",
      "sources": [],
      "commands": []
    }
  ],
  "afterEach": {
    "sources": [],
    "commands": []
  },
  "afterAll": {
    "sources": [],
    "commands": []
  }
}
````

---

# 7. Modello delle sources

## 7.1 Source comune

```json
{
  "sourceCode": "ordersSource",
  "sourceType": "dataset"
}
```

Regole:

* `sourceCode` obbligatorio
* univoco nella sezione
* usato come riferimento stabile lato UI e payload
* non dipende dalla posizione

## 7.2 JsonArray source

```json
{
  "sourceCode": "expectedMessages",
  "sourceType": "jsonArray",
  "jsonArrayId": "ja-001"
}
```

## 7.3 Dataset source

```json
{
  "sourceCode": "ordersForTest",
  "sourceType": "dataset",
  "datasetId": "ds-orders",
  "perimeter": {
    "selected_columns": ["order_id", "status"],
    "filter": {
      "logic": "AND",
      "conditions": [
        {
          "field": "status",
          "operator": "eq",
          "value": "READY"
        }
      ]
    },
    "sort": [
      {
        "field": "order_id",
        "direction": "asc"
      }
    ],
    "parameters": [
      {
        "name": "pipelineId",
        "type": "string",
        "default_value": null
      }
    ]
  },
  "parameterBindings": {
    "pipelineId": {
      "kind": "built_in",
      "resolver": "$today"
    }
  },
  "sourceOrigin": {
    "type": "dataset_copy",
    "copiedFromDatasetId": "ds-orders"
  }
}
```

---

# 8. Dataset perimeter: semantica definitiva

## 8.1 Dataset base

Il dataset persistito nel catalogo ha:

* configurazione sorgente database
* perimeter base
* eventuali parameter definitions

Esempio:

```json
{
  "id": "ds-orders",
  "description": "Orders base dataset",
  "configuration": {
    "connectionId": "db-1",
    "schema": "public",
    "objectName": "orders"
  },
  "perimeter": {
    "selected_columns": ["order_id", "status", "created_at"],
    "filter": {
      "logic": "AND",
      "conditions": [
        {
          "field": "status",
          "operator": "eq",
          "value": "READY"
        }
      ]
    },
    "sort": [
      {
        "field": "created_at",
        "direction": "desc"
      }
    ],
    "parameters": [
      {
        "name": "pipelineId",
        "type": "string",
        "default_value": null
      }
    ]
  }
}
```

## 8.2 Creazione di una dataset source

Quando l’utente seleziona un dataset nel test o nell’hook:

1. il sistema legge il dataset base
2. copia il suo `perimeter`
3. crea una source locale con `datasetId` e `perimeter` copiato
4. l’utente modifica il perimeter locale

## 8.3 Nessun merge

Il perimeter locale della source:

* non viene mergeato col base perimeter a runtime
* non viene ricalcolato partendo dal dataset base
* è già il perimeter definitivo da eseguire

## 8.4 Modificabilità libera

L’utente può:

* lasciare il perimeter copiato invariato
* aggiungere filtri
* togliere filtri
* cambiare colonne
* cambiare sort
* cambiare parametri
* sostituire completamente il perimetro

## 8.5 Save as new dataset

Da una dataset source locale l’utente può:

* salvare il suo perimeter corrente come nuovo dataset

Il nuovo dataset:

* eredita configurazione database della source/dataset originario
* salva il perimeter corrente della source
* riceve un nuovo `datasetId`
* entra nel catalogo dei dataset disponibili

---

# 9. Perché copy-on-use invece di merge

## 9.1 Motivi

Il merge introduce ambiguità:

* sostituzione o concatenazione dei filtri
* override o intersection delle colonne
* priorità sul sort
* regole non immediate lato UX

## 9.2 Vantaggi del copy-on-use

Il copy-on-use è:

* più semplice da spiegare
* più prevedibile
* più flessibile
* più coerente con il comando “Save as new dataset”
* migliore per i tester

Formula mentale:

* scelgo un dataset
* ne copio il perimetro
* lo modifico come voglio
* se serve lo salvo come nuovo dataset

---

# 10. Runtime model aggiornato

## 10.1 Runtime context

Il runtime resta composto da:

* `runEnvelope`
* `global`
* `local`
* `result`

## 10.2 Cosa entra nel runtime

Nel runtime entrano solo:

* valori runtime veri
* output tecnici
* artifacts
* dati evento streaming
* risultati dei command

## 10.3 Cosa NON entra come “variabile”

Le `sources` non devono essere trattate come costanti runtime standard.

Possono essere:

* risolte dal command quando servono
* tracciate in debug/log
* referenziate dai command

Ma non vanno inserite automaticamente nella symbol table come variabili normali.

---

# 11. Risoluzione input dei command

## 11.1 Principio

I command che leggono un input devono poter dichiarare se accettano:

* `source`
* `runtime value`
* entrambi

## 11.2 Resolver unificato

Introdurre una funzione unica:

```python
resolve_input_reference(ref, execution_context) -> ResolvedInput
```

Capacità:

* risolvere una source dichiarativa
* risolvere un runtime value
* capire il tipo risultante
* materializzare il dato quando necessario

## 11.3 Risoluzione di una dataset source

Se l’input è una source dataset:

1. leggere `datasetId`
2. usare il `perimeter` presente nella source
3. risolvere eventuali `parameterBindings`
4. compilare query
5. eseguire query
6. restituire dataset materializzato

## 11.4 Risoluzione di una jsonArray source

Se l’input è una source jsonArray:

1. leggere `jsonArrayId`
2. caricare il contenuto persistito
3. restituire il payload array

## 11.5 Risoluzione di un runtime value

Se l’input è un runtime value:

1. leggere la definition/reference
2. recuperare il valore dal contesto
3. applicare eventuali validazioni di tipo

## 11.6 Risoluzione di un runtime function

Se l’input è un runtime function:

1. leggere la definition/reference
2. calcolare il valore della funzione

---

# 12. Dataset parameters nel nuovo modello

## 12.1 I parametri restano nel perimeter

Il perimeter continua a supportare:

* `parameters`
* riferimenti `{ "kind": "parameter", "name": "..." }` nei valori dei filtri
* built-in come `$now` e `$today`

## 12.2 Nella dataset source si copia anche `parameters`

Quando il perimeter del dataset base viene copiato nella source:

* vengono copiate anche le `parameter definitions`

## 12.3 La source può cambiare anche i parametri

Poiché il perimeter locale è indipendente, la source può:

* cambiare `parameters`
* cambiare `filter`
* cambiare `selected_columns`
* cambiare `sort`

## 12.4 I binding runtime restano separati

Le `parameterBindings` della source non appartengono al dataset catalogato.
Appartengono alla source di quel test/hook.

Esempio:

```json
{
  "parameterBindings": {
    "pipelineId": {
      "kind": "constant_ref",
      "definitionId": "..."
    },
    "snapshotAt": {
      "kind": "built_in",
      "resolver": "$now"
    }
  }
}
```

---

# 13. Command model aggiornato

## 13.1 Command da mantenere

* `sendMessageQueue`
* `saveTable`
* `dropTable`
* `cleanTable`
* `exportDataset`
* `dropDataset`
* `cleanDataset`
* `runSuite`
* assert family

## 13.2 Context commands da rivedere

`initConstant` non deve più essere usato per:

* `dataset`
* `jsonArray`
* `queue`

Può restare solo per veri Commands:

* `value`
* `json`
* `function` (built-in o custom)

Rinominare:

* `initConstant` -> `setVariable`
* `deleteConstant` -> `deleteVariable`
*  tutti i formati UI `Initialize variable` -> `Set variable`



## 13.3 Delete runtime value

`deleteConstant` deve diventare concettualmente:

* delete runtime value
* non deve cancellare data sources dichiarative

Consiglio rename futuro:

* `deleteConstant` -> `deleteVariable`
* tutti i formati UI `Delete constant` -> `Delete variable`

---

# 14. Compatibilità input per command

## 14.1 sendMessageQueue

Input ammessi:

* source `dataset`
* source `jsonArray`
* runtime `json`

## 14.2 saveTable

Input ammessi:

* source `dataset`
* source `jsonArray`
* runtime `json`

La semantica specifica dipende dal tipo di input:
* dataset: materializza dataset e salva come tabella
* jsonArray: salva ogni item come riga di tabella
* json: salva json come singola riga di tabella
* in caso di json o jsonArray, è necessario specificare anche lo schema della tabella da creare con mappatura dei campi

## 14.3 exportDataset

Input ammessi:

* source `dataset`
* jsonArray: salva ogni item come riga di tabella
* json: salva json come singola riga di tabella
* in caso di json o jsonArray, è necessario specificare anche lo schema della tabella da creare con mappatura dei campi

## 14.4 jsonArrayEquals

Input ammessi:

* source `jsonArray`
* eventuale runtime jsonArray futuro

## 14.5 jsonEquals

Input ammessi:

* runtime `json`
* json inline per expected

---

# 15. Queue: nuova collocazione

## 15.1 Dove restano supportate

Le queue restano supportate in:

* brokers
* queue management
* queue details
* mock server queue binding
* runtime send/receive/ack
* trigger mock queue

## 15.2 Dove non devono più stare

Le queue non devono più stare in:

* source declarations di hook/test
* `initConstant` come sorgente batch
* catalogo data sources del suite editor

## 15.3 Nuova semantica

Una queue è:

* un endpoint di messaggistica
* un trigger streaming
* una destinazione di action
* non una data source batch dichiarativa

---

# 16. Streaming test e runEnvelope.event

## 16.1 Trigger API

Per trigger API il runtime deve valorizzare:

```json
{
  "runEnvelope": {
    "event": {
      "listener_type": "api",
      "trigger": {
        "code": "api-trigger-code",
        "method": "POST"
      },
      "payload": {},
      "meta": {
        "headers": {},
        "query": {},
        "path_params": {}
      }
    }
  }
}
```

## 16.2 Trigger Queue

Per trigger queue il runtime deve valorizzare:

```json
{
  "runEnvelope": {
    "event": {
      "listener_type": "queue",
      "trigger": {
        "code": "queue-trigger-code",
        "queue_code": "orders-queue"
      },
      "payload": {},
      "meta": {
        "message_attributes": {},
        "message_id": "..."
      }
    }
  }
}
```

## 16.3 Conseguenza

Il test streaming usa:

* `runEnvelope.event`
* eventuali source declarations locali
* eventuali Commands derivati dai command

---

# 17. Persistenza: proposta

## 17.1 Suite payload

Introdurre in ogni sezione:

* `sources`
* `commands`

## 17.2 Dataset source

Persistire direttamente nella source:

* `datasetId`
* `perimeter`
* `parameterBindings`
* `sourceOrigin`

## 17.3 JsonArray source

Persistire:

* `jsonArrayId`

## 17.4 Commands

La symbol table position-aware deve restare solo per i Commands.

Non deve includere:

* dataset sources
* jsonArray sources

---

# 18. Symbol table: nuova responsabilità

## 18.1 Prima

La symbol table gestiva:

* value
* json
* jsonArray
* dataset

## 18.2 Dopo

La symbol table deve gestire solo:

* `value`
* `json`
* eventuali result Commands

## 18.3 Motivazione

Le data sources:

* non hanno ordine
* non nascono da command
* non vengono cancellate con `deleteConstant`
* non hanno dipendenza position-aware

Quindi devono stare fuori dalla symbol table dei command runtime.

---

# 19. Scope delle sources

## 19.1 Rule

Le sources sono dichiarate per sezione.

## 19.2 Ambiti

* `beforeAll.sources`
* `beforeEach.sources`
* `test.sources`
* `afterEach.sources`
* `afterAll.sources`

## 19.3 Visibilità consigliata

Per evitare ambiguità, ogni sezione vede:

* le proprie sources
* eventuali `suiteSources` globali se introdotte in V2

Per V1 consiglio di **non propagare implicitamente** le sources tra sezioni diverse.

Motivo:

* è più semplice
* evita coupling nascosto
* evita casi difficili in UI

---

# 20. UI: nuovo modello editor

## 20.1 Terminologia

Sostituire le etichette generiche con due blocchi distinti:

* **Data Sources**
* **Commands**

## 20.2 Data Sources editor

In hook o test, l’utente deve poter:

* aggiungere una source dataset
* aggiungere una source jsonArray
* modificarne configurazione
* eliminarla

Le sources devono essere mostrate come elenco dichiarativo:

* non ordinabile
* non position-aware
* con codice univoco e tipo

## 20.3 Commands editor

Separare la gestione dei valori runtime:

* `Set variable`
* `Set json`
* `Delete variable`

## 20.4 Dataset source editor flow

Flow suggerito:

1. click `Add data source`
2. scelta tipo `Dataset`
3. select dataset catalogato
4. salvataggio source
5. copia automatica del perimeter nella source

In fase di modifica del dataset source:
1. eventuale edit del dataset source
2. (Edit local perimeter)
   a. editor del perimeter locale
   b. salvataggio source

## 20.5 Azioni dataset source

Azioni utili:

* `Reset from dataset`
* `Save as new dataset`
* `Preview source`
* `Edit local perimeter`

## 20.6 JsonArray source editor flow

1. click `Add data source`
2. scelta tipo `JSON Array`
3. select jsonArray catalogato
4. salvataggio source

---

# 21. UI: dataset perimeter locale

## 21.1 Principio

La source dataset deve mostrare chiaramente:

* dataset di origine
* perimeter locale corrente
* differenza tra origine e copia locale

## 21.2 Layout suggerito

Lo stesso presente in dataset DatasetPerimeterEditor:

Azioni aggiuntive: 

* `Reset from dataset`
* `Save as new dataset`

## 21.3 Save as new dataset dialog

Campi:

* dataset code / id
* description
* conferma riuso configurazione connessione/schema/object
* conferma salvataggio del perimeter locale corrente

---

# 22. API changes

## 22.1 Suite API

Aggiornare il contratto suite per supportare:

* `sources`
* `commands`

## 22.2 Data source DTO

Introdurre DTO dedicati:

```json
{
  "sourceCode": "orders",
  "sourceType": "dataset",
  "datasetId": "..."
}
```

```json
{
  "sourceCode": "expected",
  "sourceType": "jsonArray",
  "jsonArrayId": "..."
}
```

## 22.3 Dataset source with local perimeter

Supportare payload con:

* `perimeter`
* `parameterBindings`
* `sourceOrigin`

## 22.4 Save as new dataset

Nuovo endpoint o riuso endpoint dataset create:

```text
POST /data-source/database
```

Body derivato da una dataset source locale:

* stessa configurazione database
* nuovo perimeter
* nuova descrizione

---

# 23. Migrazione dal modello attuale

## 23.1 Da migrare

I vecchi `initConstant` con:

* `sourceType = Dataset`
* `sourceType = JsonArray`

devono essere migrati in `sources` dichiarative.

## 23.2 Da dismettere

I vecchi `initConstant` con:

* `sourceType = SQSQueue`

devono essere rifiutati nel nuovo editor e segnati come non supportati nel modello nuovo.

## 23.3 Compatibilità temporanea

Durante la migrazione puoi mantenere:

* lettura legacy
* serializzazione nuova

Ma il target finale deve essere:

* niente dataset/jsonArray/queue in `initConstant`

---

# 24. Esempio completo

## 24.1 Suite con data sources e Commands

```json
{
  "beforeEach": {
    "sources": [
      {
        "sourceCode": "readyOrders",
        "sourceType": "dataset",
        "datasetId": "ds-orders",
        "perimeter": {
          "selected_columns": ["order_id", "status"],
          "filter": {
            "logic": "AND",
            "conditions": [
              {
                "field": "status",
                "operator": "eq",
                "value": "READY"
              }
            ]
          },
          "sort": [
            {
              "field": "order_id",
              "direction": "asc"
            }
          ],
          "parameters": [
            {
              "name": "pipelineId",
              "type": "string",
              "default_value": null
            }
          ]
        },
        "parameterBindings": {
          "pipelineId": {
            "kind": "built_in",
            "resolver": "$today"
          }
        },
        "sourceOrigin": {
          "type": "dataset_copy",
          "copiedFromDatasetId": "ds-orders"
        }
      }
    ],
    "commands": [
      {
        "commandCode": "setValue",
        "commandType": "context",
        "configuration": {
          "target": "targetQueue",
          "valueType": "value",
          "value": "orders-queue"
        }
      }
    ]
  },
  "tests": [
    {
      "id": "test-1",
      "code": "send-ready-orders",
      "sources": [
        {
          "sourceCode": "expectedPayloads",
          "sourceType": "jsonArray",
          "jsonArrayId": "ja-expected-orders"
        }
      ],
      "commands": [
        {
          "commandCode": "sendMessageQueue",
          "commandType": "action",
          "configuration": {
            "queueRef": {
              "runtimeValueName": "targetQueue"
            },
            "sourceRef": {
              "kind": "source",
              "sourceCode": "readyOrders"
            },
            "templateMode": "jsonArray-first-item"
          }
        },
        {
          "commandCode": "jsonArrayEquals",
          "commandType": "assert",
          "configuration": {
            "expectedRef": {
              "kind": "source",
              "sourceCode": "expectedPayloads"
            },
            "actualRef": {
              "kind": "result",
              "path": "sendMessageQueue.renderedPayloads"
            }
          }
        }
      ]
    }
  ]
}
```

---

# 25. Validazioni backend

## 25.1 Sources

* `sourceCode` obbligatorio
* `sourceCode` univoco nella sezione
* `sourceType` ammesso solo `dataset | jsonArray`
* `datasetId` obbligatorio se `sourceType=dataset`
* `jsonArrayId` obbligatorio se `sourceType=jsonArray`

## 25.2 Dataset source

* `perimeter` obbligatorio dopo la copia
* validazione completa del perimeter
* validazione parameter definitions
* validazione parameter bindings

## 25.3 Commands

* compatibilità tipo tra command e input reference
* divieto di usare una source inesistente
* divieto di usare Commands incompatibili
* `deleteConstant` non applicabile alle sources

## 25.4 Queue

* vietato `queue` come sourceType
* vietato `initConstant`/`setValue` con `queue` come sorgente dati batch

---

# 26. Test plan

## 26.1 Backend domain

* test creazione source dataset da dataset base
* test copia perimeter
* test indipendenza del perimeter locale
* test reset from dataset
* test save as new dataset
* test source jsonArray

## 26.2 Runtime

* test `resolve_input_reference` su source dataset
* test `resolve_input_reference` su source jsonArray
* test materializzazione dataset con perimeter locale
* test parameter bindings su dataset source
* test command che leggono source dataset
* test command che leggono source jsonArray
* test rifiuto queue come source batch

## 26.3 Streaming

* test trigger API -> `runEnvelope.event`
* test trigger queue -> `runEnvelope.event`
* test runSuite streaming avviata da mock queue
* test `ACK` queue invariato nel mock runtime

## 26.4 UI

* test editor Data Sources
* test distinzione Data Sources / Commands
* test flow `Add dataset source`
* test flow modifica perimeter locale
* test flow `Save as new dataset`
* test flow `Reset from dataset`
* test flow `Add jsonArray source`

## 26.5 Migrazione

* test migrazione legacy `initConstant(dataset)` -> `sources`
* test migrazione legacy `initConstant(jsonArray)` -> `sources`
* test blocco legacy `initConstant(queue)`

---

# 27. Roadmap implementativa

## Fase 1 - Modello e persistenza

* [ ] introdurre `sources` nelle sezioni suite
* [ ] definire DTO `dataset source` e `jsonArray source`
* [ ] persistere `perimeter` locale nella dataset source
* [ ] persistere `parameterBindings` locali
* [ ] introdurre `sourceOrigin`

## Fase 2 - Runtime

* [ ] introdurre `resolve_input_reference`
* [ ] separare risoluzione source vs runtime value
* [ ] materializzare dataset source usando il perimeter locale
* [ ] integrare parameter resolver sul perimeter locale
* [ ] rimuovere queue come source batch

## Fase 3 - Commands

* [ ] limitare `initConstant` ai soli Commands
* [ ] valutare rename `initConstant` -> `setValue`
* [ ] aggiornare `sendMessageQueue`
* [ ] aggiornare `saveTable`
* [ ] aggiornare `exportDataset`
* [ ] aggiornare assert che consumano jsonArray source

## Fase 4 - UI

* [ ] introdurre blocco `Data Sources`
* [ ] separare blocco `Commands`
* [ ] creare editor dataset source con copia perimeter
* [ ] aggiungere `Reset from dataset`
* [ ] aggiungere `Save as new dataset`
* [ ] aggiornare dialog command input compatibili

## Fase 5 - Migrazione

* [ ] migrare legacy dataset/jsonArray initConstant
* [ ] bloccare nuovo inserimento queue source
* [ ] introdurre warning sui casi legacy

## Fase 6 - Test e hardening

* [ ] unit test domain/runtime
* [ ] integration test suite API
* [ ] regression test mock runtime
* [ ] regression test dataset API
* [ ] test UI Streamlit

---

# 28. Decisioni finali

## Da fare

* `dataset` e `jsonArray` diventano `Data Sources`
* le `sources` non hanno ordine
* le `sources` sono dichiarate a livello hook/test
* le queue non sono più sources batch
* le queue restano trigger streaming
* il dataset source usa un perimeter copiato e locale
* nessun merge base/override
* la source può essere salvata come nuovo dataset

## Da evitare

* continuare a trattare dataset/jsonArray come normali costanti
* mantenere queue come source type nei test batch
* merge automatici del perimeter
* dipendenze nascoste tra sources e order dei command
* modifica implicita del dataset originale quando si modifica una source locale

---

# 29. Frase guida di design

**Le data sources definiscono da dove arrivano i dati, i Commands rappresentano i dati effettivamente presenti durante l’esecuzione, e i trigger streaming definiscono perché il test è partito.**

---

# 30. Sintesi finale

Nuovo modello:

* `dataset/jsonArray` = sorgenti dichiarative
* `value/json` = valori runtime
* `queue` = trigger o destinazione di messaging, non source batch
* `dataset perimeter` = base copiata localmente nella source
* `dataset source` = configurazione autonoma, editabile e promuovibile a nuovo dataset

```

Se vuoi, nel passo successivo posso trasformarlo in una **versione ancora più operativa per Codex**, con:
- JSON schema dei DTO
- elenco endpoint API da toccare
- struttura classi/service Python da introdurre.
```
