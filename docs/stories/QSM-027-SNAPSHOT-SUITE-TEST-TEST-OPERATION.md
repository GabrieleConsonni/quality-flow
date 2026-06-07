# QSM-027 - Snapshot suite_test / test_operation

## Stato
- Stato: Completato
- Checklist: 5/5 completata

## Dettaglio sviluppo

### Snapshot suite_test / test_operation

- [x] `suite_tests` e `test_operations` aggiornati a modello snapshot (code/type/configuration_json)
- [x] dialog add test/operation: aggiunto `Add only`
- [x] dialog add test/operation lato sinistro: aggiunto `Delete` sotto `Add`
- [x] Suite Editor renderizza dettagli da `suite_tests` / `test_operations`
- [x] Runtime esecuzione test/operation basato su snapshot suite (senza lookup da anagrafica)

Nota evolutiva:
- il catalogo condiviso `operations` e' stato poi rimosso; l'aggiunta operation e' ora solo locale al contesto che la contiene.

## Fonte
- Estratto da `docs/TASK.md`
