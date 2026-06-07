# QSM-030 - JsonArray Assert operations

## Stato
- Stato: Completato
- Checklist: 10/10 completata

## Dettaglio sviluppo

### JsonArray Assert operations

- [x] aggiungere una nuova operation di tipo assert. Essa ha due field generali.
    - Error message
    - evaluetedObjectType: `Json\Data`, `Table`, etc ... (ampliabile)
- [x] per il tipo `Json\Data` Ã¨ possibile configurare:
    - [x] `NotEmpty` <-- verifica che i dati non siano vuoti
    - [x] `Empty` <-- verifica che i dati siano vuoti
    - [x] `SchemaValidation` <-- verifica che i dati in formato json rispettino uno schema
        - impostare lo schema per la verifica
    - [x] `Contains` <-- verifica che i dati siano contenuti nel json array impostato
        - impostare il json array expected
        - impostare un array di keys per fare il confronto
    - [x] `JsonArrayEquals` <-- verifica che i dati siano uguali al json array impostato
        - impostare il json array expected
- [x] introdurre una family `assert` con un evalutor orchestratore\composite + strategy interne simile a quanto fatto per test_executor (NotEmptyData, EmptyData, ecc.).
- [x] modificare il dialog delle operazioni per integrare questa funzionalitÃ 
- [x] integrare i test esistenti

## Fonte
- Estratto da `docs/TASK.md`
