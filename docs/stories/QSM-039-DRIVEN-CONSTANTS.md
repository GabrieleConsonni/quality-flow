# QSM - Gestione Guidata delle Costanti nei Test Suite

## 🎯 Obiettivo

Introdurre una gestione **guidata, scope-aware e position-aware** delle costanti nei test suite e nei mock commands.

L’utente **non deve conoscere né usare resolver** (es: `$.local.constants.myJson`), ma deve poter:

* dichiarare costanti
* usarle nei comandi successivi tramite select guidate
* eliminarle
* riordinare i comandi in sicurezza

Il comportamento deve ricalcare la scrittura di codice:

> “Dichiaro una variabile → la uso → non posso usarla prima della dichiarazione”

---

## 🧠 Concetti Chiave

### 1. Visibilità per posizione

Una costante è visibile solo se:

* è stata dichiarata **prima** del comando corrente
* non è stata eliminata
* appartiene a uno scope accessibile
* appartiene a una sezione compatibile (before/test/after)

---

### 2. Scope logici (UI vs runtime)

| UI Label | Runtime     |
| -------- | ----------- |
| Run      | runEnvelope |
| Suite    | global      |
| Test     | local       |
| Result   | result      |

---

### 3. Tipi di costante

* `value` (ex raw)
* `json`
* `jsonArray`
* `dataset`

---

### 4. Tipi di command coinvolti

* `initConstant` → crea costante
* `deleteConstant` → elimina visibilità
* `action` → consuma costanti
* `assert` → consuma costanti
* `action con output` → può creare costanti (scope result)

---

## 🏗️ Architettura

### ✅ Scelta adottata

Persistenza separata delle costanti (symbol table)

---

## 🗄️ Data Model

### Tabella: `command_constant_definitions`

```sql
id UUID PK
suite_id UUID
suite_item_id UUID NULL
section_type VARCHAR  -- beforeAll, beforeEach, test, afterEach, afterAll
command_id UUID
command_order INT

name VARCHAR
context_scope VARCHAR -- runEnvelope, global, local, result
value_type VARCHAR -- raw, dataset, json, jsonArray

declared_at_order INT
deleted_at_order INT NULL

created_at TIMESTAMP
updated_at TIMESTAMP
```

---

### (V2) Tabella: `command_constant_references`

```sql
id UUID PK
command_id UUID
reference_role VARCHAR -- source, actual, expected, target, result
definition_id UUID

created_at TIMESTAMP
```

---

## 🔄 Lifecycle costante

### Creazione

* `initConstant`
  → crea record in `definitions`

---

### Utilizzo

* command usa `definition_id`
* NON salva resolver

---

### Eliminazione

* `deleteConstant`
  → aggiorna `deleted_at_order`

---

### Visibilità

Una costante è visibile se:

```text
declared_at_order < command_order
AND (deleted_at_order IS NULL OR deleted_at_order > command_order)
```

---

## 🧩 Form UI

### ❌ Prima

```text
$.local.constants.myJson
```

### ✅ Dopo

Select box:

```text
myJson — Test — json
orders — Suite — dataset
```

---

### Persistenza command

```json
{
  "sourceConstantRef": {
    "definitionId": "uuid"
  }
}
```

---

## 🔍 API

### Recupero costanti disponibili

```
GET /commands/{command_id}/available-constants?field=source
```

Filtro per:

* posizione
* scope
* tipo compatibile

---

### Reorder commands

```
POST /suite-items/{id}/commands/reorder
```

Body:

```json
{
  "orderedCommandIds": ["id1", "id2", "id3"]
}
```

---

## ⚙️ Logica Backend

### Funzione core

```python
get_visible_constants(section, command_order)
```

---

### Algoritmo

1. recupera tutte le definitions della sezione
2. filtra:

   * declared_at < order
   * not deleted
3. filtra per scope compatibile
4. filtra per tipo richiesto

---

## 🔁 Reorder (CRITICO)

### Processo

1. applica reorder in memoria
2. ricostruisce symbol table
3. valida tutte le referenze
4. commit o rollback

---

### ❌ Caso invalido

```text
initConstant A
sendMessageQueue (usa A)

→ sposto sendMessageQueue prima di initConstant
→ ERRORE → rollback
```

---

## 🚫 Regole di validazione

* non puoi usare costante non ancora dichiarata
* non puoi usare costante eliminata
* delete deve riferirsi a costante esistente
* no ridefinizione stessa costante nello stesso scope (V1)
* referenze devono essere sempre risolvibili

---

## 🧪 Compatibilità tipi

| Campo                    | Tipi ammessi    |
| ------------------------ | --------------- |
| sendMessageQueue.source  | raw, json, jsonArray, dataset |
| jsonNotEmpty.actual      | json            |
| jsonArrayNotEmpty.actual | jsonArray       |
| saveTable.source         | dataset         |
| deleteConstant.target    | qualsiasi       |

---

## 🔄 Scope propagation

| Sezione    | Può leggere        |
| ---------- | ------------------ |
| beforeAll  | run                |
| beforeEach | run, global        |
| test       | run, global, local |
| afterEach  | run, global, local |
| afterAll   | run, global        |

---

## 🚀 Roadmap implementativa

### V1 (MVP)

* [ ] creare tabella `command_constant_definitions`
* [ ] salvare definition su `initConstant`
* [ ] gestire `deleted_at_order`
* [ ] implementare `get_visible_constants`
* [ ] modificare UI → select guidate
* [ ] salvare `definitionId` nei command
* [ ] validazione create/update command
* [ ] implementare reorder con validazione globale
* [ ] bloccare reorder invalido
* [ ] vietare ridefinizione stessa costante

---

### V2

* [ ] introdurre `command_constant_references`
* [ ] dependency graph tra comandi
* [ ] refactor rename costante
* [ ] suggerimenti automatici
* [ ] linting editor

---

## 🧠 Scelte progettuali

### ❓ Perché non usare resolver?

* non user-friendly
* error-prone
* rompe UX guidata

---

### ❓ Perché usare `definitionId`?

* stabile
* evita problemi di rename
* elimina ambiguità

---

### ❓ Perché persistenza separata?

* performance
* validazione semplice
* base per evoluzioni future

---

## 🔮 Evoluzioni future

* autocomplete intelligente
* visualizzazione dependency graph
* debug runtime con tracing variabili
* supporto shadowing controllato
* esportazione test in DSL leggibile

---

## ✅ Risultato atteso

* UX guidata senza resolver
* comportamento prevedibile tipo codice
* editor robusto ai riordini
* base solida per evoluzioni avanzate

---

Se vuoi nel prossimo step possiamo:

* definire le **query SQL reali**
* oppure disegnare il **service Python (FastAPI)** per questa logica
* oppure fare un **mock UI flow completo Streamlit**
