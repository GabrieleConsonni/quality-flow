## 📄 Wave 2 — Advanced Table Assert

```md
# Quality Flow - Wave 2: Advanced Table Assert

## Obiettivo

Estendere le capacità di confronto senza introdurre SQL libero.

Focus:
- confronti tra dataset logici
- supporto a variabili e risultati intermedi
- copertura casi “query-like” senza query

---

## Assert incluse

### 1. result_equals

#### Descrizione
Confronta due sorgenti dati.

#### Source supportate
- table (con filtri)
- dataset
- variabile (jsonArray)

#### Input
- expectedSource
- actualSource
- keyColumns
- compareColumns

#### Output
- diff completo

---

### 2. result_contains

#### Descrizione
Verifica che actual contenga expected.

#### Uso
- subset check
- validazione parziale dati

---

### 3. aggregate_equals

#### Descrizione
Confronto su aggregati.

#### Aggregati supportati
- count
- sum
- min
- max
- distinct_count (futuro)

#### Input
- connectionRef
- table
- aggregate
- column opzionale
- filters
- expected / expectedFromVar

---

## Vantaggi

- evita SQL custom
- integra variabili test
- mantiene UX guidata

---

## Output standard

Identico a Wave 1 per consistenza.

---

## Priorità

Media

---

## Checklist

- [ ] implementare result_equals
- [ ] implementare result_contains
- [ ] implementare aggregate_equals
- [ ] supportare source multiple
- [ ] integrare con variabili contesto