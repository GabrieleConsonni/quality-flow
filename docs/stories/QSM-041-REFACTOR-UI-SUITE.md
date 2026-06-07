# QSM-041 - Refactor UI Suite

## Stato
- Stato: Completato
- Area: UI Streamlit test suites
- Scope: solo `Suite Editor` e nuova pagina advanced settings

## Obiettivo
Rendere piu leggibile il `Suite Editor`, lasciando nella pagina principale il focus sui test e spostando la configurazione hook in una pagina dedicata.

## Modifiche funzionali
### Suite Editor
- La pagina principale mostra solo i test embedded della suite.
- Restano in header titolo suite, `Execution history`, bottone `Run` e gear `Advance settings`.
- Rimossi il `segmented_control` delle sezioni e i pannelli di riepilogo risultati esecuzione.
- Nei test il menu `:material/more_vert:` e stato spostato accanto a `Add assert`.

### AdvancedSuiteEditorSettings
- Nuova pagina hidden raggiungibile dal gear del `Suite Editor`.
- Layout con bottone back verso `Suite Editor`, titolo `Advanced settings` e sezioni fisse `Before suite`, `Before each test`, `After each test`, `After suite`.
- Ogni sezione espone la configurazione dei command hook con gli stessi dialog di add/edit/delete gia usati nel modulo suite.

### Command actions
- Le azioni del singolo command sono state separate in tre bottoni icona-only:
  - `settings` per modify
  - `swap_vert` per reorder
  - `close` per delete
- Il dialog di reorder mostra tutti i command della sezione corrente con lo stesso rendering compatto del page editor.
- Il salvataggio del reorder valida l'intera suite rispetto alla consistenza delle variabili e blocca l'operazione con messaggio breve in inglese se l'ordine non e valido.

## Note tecniche
- Refactor incrementale del modulo `test_suites` con split del rendering principale e della pagina advanced in container dedicati.
- Nessuna modifica al payload suite/hooks/operations e nessun impatto backend.
- Nuove chiavi centralizzate in `test_suites/services/state_keys.py` per la navigazione `Suite Editor` <-> `Advanced settings`.

## Checklist
- [x] Main editor focalizzato solo sui test
- [x] `Execution history` e `Run` preservati in header
- [x] Gear `Advance settings` aggiunto in header
- [x] Nuova pagina `AdvancedSuiteEditorSettings.py`
- [x] Hook `before/after` spostati nella pagina advanced
- [x] Menu `more_vert` del test spostato accanto a `Add assert`
- [x] Azioni command split in `modify / reorder / delete`
- [x] Dialog reorder con validazione variabili globale
- [x] Nessuna modifica al contratto backend suite

## Validazione
- Smoke check UI via compilazione/import:
  - `python -m compileall app/ui`
- Verifiche unitarie helper suite:
  - `pytest test/unit/test_suite_editor_command_helpers.py`

## Code Quality Gate
- CodeScene usage: Yes
- Gate richiesto prima del ready:
  - `select_codescene_project`
  - `code_health_review` oppure hotspots
  - `pre_commit_code_health_safeguard`
- Nota: tool CodeScene non disponibili in questa sessione; esecuzione rimandata a pipeline/ambiente abilitato.
