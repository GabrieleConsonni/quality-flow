# Quality Flow - Wave 1: Table Assert Core (MVP)

## Obiettivo

Introdurre le assert fondamentali su tabelle per coprire i casi più comuni di verifica dati senza SQL libero.

Focus:
- semplicità per tester
- sicurezza (no SQL arbitrario)
- output chiaro expected/actual

---

## Assert incluse

### 1. table_exists

#### Descrizione
Verifica che una tabella esista nel database.

#### Input
- connectionRef
- table
- schema opzionale

#### Output
- expected: true
- actual: true/false

---

### 2. row_count

#### Descrizione
Verifica che il numero di righe sia uguale al valore atteso.

#### Input
- connectionRef
- table
- filters opzionale
- expectedCount

#### Note
- filtri dichiarativi (no SQL)
- operatori whitelistati

---

### 3. row_exists

#### Descrizione
Verifica che una singola riga esista.

#### Input
- connectionRef
- table
- match: field -> value/valueFromVar

---

### 4. rows_exist

#### Descrizione
Verifica che più righe siano presenti.

#### Input
- connectionRef
- table
- rows oppure rowsFromVar
- keyColumns opzionale

---

### 5. row_not_exists

#### Descrizione
Verifica che una riga NON esista.

---

### 6. rows_not_exist

#### Descrizione
Verifica che un insieme di righe NON esista.

---

### 7. assert.table.intra_db_table_diff

#### Descrizione
Confronto tra due tabelle nello stesso DB.

#### Input
- connectionRef
- leftTable
- rightTable
- keyColumns
- compareColumns opzionale

#### Implementazione
- SQL nativo (JOIN / EXCEPT / FULL OUTER)

---

### 8. assert.table.inter_db_table_diff

#### Descrizione
Confronto tra tabelle su DB diversi.

#### Input
- leftConnectionRef
- rightConnectionRef
- leftTable
- rightTable
- keyColumns
- compareColumns opzionale

#### Implementazione
- estrazione dataset
- normalizzazione
- diff con Polars

---

## Output standard

```json
{
  "success": false,
  "actual": {
    "missingRows": 2,
    "extraRows": 1,
    "changedRows": 3,
    "matchingRows": 100
  }
}