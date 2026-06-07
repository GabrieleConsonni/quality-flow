# Quality Flow - Wave 3: Dataset Assert

## Obiettivo

Introdurre una layer di assert astratto basato su dataset, indipendente dalla sorgente fisica.

Focus:
- riusabilità
- coerenza con modello dataset/perimeter/parameters
- integrazione con pipeline Quality Flow

---

## Concetto chiave

Il dataset è:
- una vista logica
- filtrata via perimeter
- parametrizzata runtime

Le assert operano su dataset materializzati.

---

## Assert incluse

### 1. dataset_equals

#### Descrizione
Confronta due dataset.

#### Input
- expectedDataset
- actualDataset
- keyColumns
- compareColumns

---

### 2. dataset_contains

#### Descrizione
Verifica che un dataset contenga un altro dataset.

---

### 3. dataset_row_count

#### Descrizione
Verifica il numero di righe dopo applicazione perimeter + parameters.

---

### 4. dataset_rows_exist

#### Descrizione
Verifica presenza righe tra dataset e tabella o tra dataset.

---

## Source supportate

- dataset (con perimeter)
- tabella
- variabile jsonArray
- risultato step

---

## Implementazione

Pipeline:

1. risoluzione dataset (perimeter + parameters)
2. materializzazione
3. normalizzazione
4. confronto via engine (Polars)

---

## Integrazione con sistema

- usa DatasetPerimeterCompiler :contentReference[oaicite:0]{index=0}
- usa DatasetParameterResolver :contentReference[oaicite:1]{index=1}
- integrato con initConstant :contentReference[oaicite:2]{index=2}

---

## Output

Allineato alle table assert:

```json
{
  "success": true,
  "actual": {
    "matchingRows": 50
  }
}