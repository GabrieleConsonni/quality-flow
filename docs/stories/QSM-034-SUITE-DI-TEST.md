### Analisi
## Cambio terminologia
Cambiare test con test
Cambiare suite con suite
Togliere l’ordinamento dai test

## Hooks
Aggiungere before, beforeAll, aftereach e afterAll, al più uno per Suite.
Anche essi hanno operazioni configurabili

## Cambio elaborazione degli tests
Modificare l’elaborazione degli test come esecutore di operazioni in ordine.
Trasformare Data from db, data from json array etc…in operazioni.

## Operations
Suddividere le operazioni in input, output e assert.

- Per le operazioni di input è necessario salvare un nome di variabile di contesto locale\globale da cui leggere i dati.
- Per le operazioni di output è necessario salvare un nome di variabile di contesto locale in cui scrivere i dati.
- Per le operazioni di assert è possibile scegliere un nome di variabile di contesto locale\globale da cui confrontare i dati.

## Contesti
Ci sono un contesto globale e n contesti locali, uno per ogni test.
Il contesto globale è immutabile per i test, modificabile solo negli hooks.
I test sono atomici e non condividono i singoli contesti locali.
Le operazioni si scambiano dati solo tramite contesto locale.
I contesti locali vengono eliminati al termite del afterEach

## Workflow
L’esecuzione di una Suite di test avviene come di seguito:
- beforeAll <-- Se non eseguito da mock server crea il contesto globale
    - beforeEach <-- crea contesto locale ed esegue le sue operazioni
    - test <-- esegue le opearzioni in sequenza
    - afterEach <-- esegue le operazioni e distrugge contesto locale
- …altri test
- afterAll <-- esegue le operazioni e distrugge contesto globale

### PLAN

## Stato
- Stato: In corso
- Backend core: Completato
- UI core suite editor: Completato
- Test automatici: Parziali

## Implementazione
- sostituito il dominio `suite/test` con `test_suite/suite_item`
- rimossi gli endpoint pubblici `/elaborations/suite*` e `/elaborations/test*` dal bootstrap applicativo
- introdotti `test_suites`, `suite_items`, `suite_item_operations`, `test_suite_executions`, `suite_item_executions`, `suite_item_operation_executions`
- gli ex `testType` (`data`, `data-from-json-array`, `data-from-db`, `data-from-queue`, `sleep`) sono ora `operationType`
- `run-suite` e stato sostituito da `run-suite`

## Runtime
- introdotto workflow `beforeAll -> [beforeEach -> test -> afterEach]* -> afterAll`
- introdotti contesto `global` e contesto `local`
- gli hook possono scrivere nel contesto globale
- i test possono leggere il globale ma non possono modificarlo
- il resolver espone `$.global`, `$.local`, `$.event`, `$.artifacts` e mantiene `$.last`

## UI
- nuova navigazione `Test Suites` / `Suite Editor`
- rimosso il catalogo `tests`
- aggiunti 4 pannelli hook fissi
- i test sono embedded nella suite
- il dialog operazioni supporta i nuovi `operationType` e `run-suite`

## Verifica
- compilazione statica eseguita su backend e UI
- aggiunti test mirati per:
  - CRUD base test suite
  - happy path hook/test
  - blocco scrittura `global` durante i test
- nota ambiente locale: `pytest` non e installato nel runtime corrente, quindi i test aggiunti non sono stati eseguiti qui
