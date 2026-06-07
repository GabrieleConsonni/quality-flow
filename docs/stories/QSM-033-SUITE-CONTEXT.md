## Stato (2026-03-08)
- Stato: In corso
- Backend core: Completato
- UI configurazione avanzata (`pre/post/response` editor): Da fare

Implementato in questo avanzamento:
- RunContext runtime (`event`, `vars`, `last`, `artifacts`) + resolver `$ref/`$const/`$default/`$required
- Operazione `set-var`
- `run-suite` estesa con `suite_code`, `init_vars`, `invocation_id`
- Pipeline API runtime: `pre_response_operations` (sync), response dinamica, `post_response_operations` (async)
- Event envelope API/Queue + persistenza `mock_server_invocations`
- Persistenza suite run estesa: `invocation_id`, `vars_init_json`, `result_json`
- Assert estesi con `equals`, `actual/expected` risolti da contesto e artifacts persistiti
# QSM-0XX - Trigger â†’ Suite input tramite Run Context + Resolver

Obiettivo: gestire i dati provenienti da **API** o **Queue** (mock server) e passarli a **uno o piÃ¹ scenari** in modo deterministico, tracciabile e riusabile, introducendo:

* un **RunContext globale per ogni run**
* un **resolver di riferimenti dinamici (`$ref`)**
* una pipeline di operazioni **pre-response (sync)** e **post-response (async)** per le API
* possibilitÃ  di costruire **response dinamiche** basate sull'evento ricevuto.

---

# RunContext (contesto globale di esecuzione)

Ogni suite run e ogni invocazione API crea un contesto runtime isolato.

Struttura:

```json
{
  "run_id": "uuid",
  "event": {},
  "vars": {},
  "last": {
    "test_code": "",
    "data": {}
  },
  "artifacts": {}
}
```

Descrizione campi:

* **event** â†’ envelope dellâ€™evento che ha generato lâ€™esecuzione
* **vars** â†’ variabili condivise tra operazioni
* **last** â†’ ultimo output prodotto da uno test
* **artifacts** â†’ risultati assert / metadata run

Checklist implementazione:

* [ ] Definire modello `RunContext`
* [ ] Ogni `suite_run` crea il proprio `RunContext`
* [ ] Ogni test aggiorna `context.last`
* [ ] Le operazioni possono leggere da:

  * [ ] `context.last`
  * [ ] `context.vars`
  * [ ] `context.event`
* [ ] Gli assert salvano risultati in `context.artifacts`

---

# Event Envelope (API / Queue)

Tutti i trigger vengono normalizzati in un oggetto `event`.

Struttura:

```json
{
  "id": "uuid",
  "source": "api|queue",
  "mock_server_code": "",
  "trigger": {
    "code": "",
    "method": "",
    "queue_code": ""
  },
  "timestamp": "",
  "payload": {},
  "meta": {}
}
```

Meta possibili:

API:

```
meta.headers
meta.query
meta.path_params
```

Queue:

```
meta.message_attributes
meta.message_id
```

Checklist:

* [ ] Normalizzare tutte le API request in `event`
* [ ] Normalizzare tutti i messaggi queue in `event`
* [ ] Salvare `event_json` a DB per tracciabilitÃ 

---

# Resolver dinamico (`$ref`)

Per permettere configurazioni dinamiche si introduce un resolver.

Sintassi base:

```json
{ "$ref": "$.event.payload.orderId" }
```

Root disponibili:

```
$.event
$.vars
$.last
$.artifacts
```

Esempi:

```json
{ "$ref": "$.event.payload.customerId" }

{ "$ref": "$.vars.order_id" }

{ "$ref": "$.last.data.items[0].sku" }
```

Possibili estensioni future (non obbligatorie nella prima fase):

```
$const
$default
$required
$map
```

Checklist:

* [ ] Scegliere motore query (`JMESPath` consigliato)
* [ ] Implementare resolver ricorsivo
* [ ] Supportare `$ref`
* [ ] Supportare `$const`
* [ ] Gestire fallback default se `$ref` non trova valore

---

# Nuova operazione: `set_var`

Serve per salvare valori nel contesto.

Config esempio:

```json
{
  "type": "set_var",
  "key": "order_id",
  "value": { "$ref": "$.event.payload.orderId" }
}
```

Comportamento:

```
context.vars[key] = resolved(value)
```

Checklist:

* [ ] Implementare operazione `set_var`
* [ ] Validare config (`key` obbligatoria)
* [ ] Loggare valore risolto per debug

---

# Nuova operazione: `run_suite`

Permette di lanciare scenari da un trigger.

Config esempio:

```json
{
  "type": "run_suite",
  "suite_code": "SCN_PROCESS_ORDER",
  "init_vars": {
    "order_id": { "$ref": "$.event.payload.orderId" },
    "tenant": { "$ref": "$.event.meta.headers.x-tenant" }
  }
}
```

Comportamento:

* crea una nuova `suite_run`
* inizializza `vars` con `init_vars`
* esegue suite in modo **asincrono**

Checklist:

* [ ] Implementare operazione `run_suite`
* [ ] Supportare piÃ¹ `run_suite` per lo stesso trigger
* [ ] Risolvere `init_vars` al momento del trigger
* [ ] Salvare `vars_init_json` nella run
* [ ] Schedulare run asincrona

---

# Pipeline API: pre_response / post_response operations

Per i mock server API si introduce una pipeline divisa in due fasi.

## pre_response_operations (sincrone)

Operazioni eseguite **prima di generare la response HTTP**.

Scopo:

* preparare variabili
* valutare condizioni
* trasformare dati dell'evento

Esempio:

```json
"pre_response_operations": [
  {
    "type": "set_var",
    "key": "customer_type",
    "value": { "$ref": "$.event.payload.customer.type" }
  }
]
```

Vincoli:

* devono essere veloci
* non devono bloccare il server

Checklist:

* [ ] Supportare `pre_response_operations` nelle API
* [ ] Eseguire operazioni in sequenza
* [ ] Aggiornare `context.vars`

---

## Response Builder

La risposta API puÃ² essere costruita usando il resolver.

Esempio:

```json
"response": {
  "status": 200,
  "headers": {
    "content-type": "application/json"
  },
  "body": {
    "orderId": { "$ref": "$.event.payload.orderId" },
    "customer": { "$ref": "$.vars.customer_type" }
  }
}
```

Checklist:

* [ ] Implementare `ResponseBuilder`
* [ ] Supportare `$ref` in status, headers e body
* [ ] Usare resolver per generare response finale

---

## post_response_operations (asincrone)

Operazioni eseguite **dopo la risposta HTTP**.

Scopo:

* avviare scenari
* generare eventi
* effettuare side effects

Esempio:

```json
"post_response_operations": [
  {
    "type": "run_suite",
    "suite_code": "SCN_PROCESS_ORDER",
    "init_vars": {
      "payload": { "$ref": "$.event.payload" }
    }
  }
]
```

Checklist:

* [ ] Supportare `post_response_operations`
* [ ] Eseguire operazioni asincrone
* [ ] Collegare `invocation_id` alle suite run

---

# Persistenza

## mock_server_invocations

Campi:

```
id
mock_server_code
trigger_type
trigger_code
event_json
created_at
```

Checklist:

* [ ] Salvare ogni trigger API/Queue
* [ ] Collegare invocation con suite_runs

---

## suite_runs

Campi:

```
run_id
suite_code
invocation_id
status
vars_init_json
result_json
created_at
finished_at
```

Checklist:

* [ ] Salvare init vars
* [ ] Salvare artifacts finali

---

# Assert estesi

Gli assert devono poter leggere anche da `event` e `vars`.

Esempio JSON assert:

```json
{
  "type": "assert_json",
  "mode": "equals",
  "actual": { "$ref": "$.vars.response" },
  "expected": { "$ref": "$.event.payload.expectedResponse" }
}
```

Checklist:

* [ ] Supportare `$ref` per `actual`
* [ ] Supportare `$ref` per `expected`
* [ ] Default `actual = $.last.data`
* [ ] Salvare risultato in `artifacts`

---

# UI configurazione

Mock server UI deve supportare:

* configurazione `pre_response_operations`
* configurazione `response`
* configurazione `post_response_operations`

Checklist:

* [ ] Editor JSON configurazione response
* [ ] Supporto `$ref`
* [ ] Supporto `run_suite`
* [ ] Documentazione esempi

---

# CompatibilitÃ 

* [ ] Operazioni esistenti continuano a usare `last.data`
* [ ] Introduzione `RunContext` non rompe scenari esistenti
* [ ] Resolver usato solo dove configurato

---

# Test plan

* [ ] Test resolver `$ref`
* [ ] Test `set_var`
* [ ] Test `run_suite`
* [ ] Test pipeline API (pre â†’ response â†’ post)
* [ ] Test trigger queue
* [ ] Test assert con `vars/event`

---

# Output atteso

* [ ] API/Queue trigger genera `event`
* [ ] Event salvato come `mock_server_invocation`
* [ ] `pre_response_operations` preparano il contesto
* [ ] Response generata dinamicamente
* [ ] `post_response_operations` lanciano scenari asincroni
* [ ] Tutto tracciato tramite `invocation_id` e `run_id`

---


