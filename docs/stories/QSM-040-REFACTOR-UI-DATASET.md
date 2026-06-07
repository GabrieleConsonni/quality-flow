# QSM-040 - Refactor UI Dataset

## Stato
- Stato: In corso
- Area: UI Streamlit dataset
- Scope: solo `Datasets` e nuovo `DatasetPerimeterEditor`

## Obiettivo
Rendere piu leggibile e configurabile la UI dataset:
- lista dataset come expander collassati
- preview inline on-demand
- configurazione del perimeter in pagina dedicata

## Modifiche funzionali
### Datasets
- Ogni dataset e renderizzato come expander chiuso con descrizione nel titolo.
- Dentro l'expander sono mostrati:
  - `Database`
  - `Schema`
  - `Table/View`
- Le azioni disponibili sono:
  - `Preview` per mostrare o nascondere la preview inline del dataset
  - `Perimeter` per aprire `DatasetPerimeterEditor.py`
  - `Edit` per modificare descrizione e configurazione dataset
  - `Delete` diretto con richiesta di conferma

### DatasetPerimeterEditor
- Pagina hidden raggiungibile via `st.switch_page`.
- Layout:
  - bottone back verso `Datasets`
  - descrizione dataset e metadati oggetto
  - azione `Save and preview`
  - sezione `Selected columns`
  - riga con `Preview` e `Sort`
  - sezione `Filters`
- `Save and preview` salva il perimeter, invalida la cache preview, ricarica la preview e resta nella stessa pagina.

## Note tecniche
- Rifattorizzazione del modulo dataset al pattern `Page -> Container -> Service -> StateKeys`.
- Nessuna modifica alle API backend dataset.
- Il payload `perimeter` resta invariato:
  - `selected_columns`
  - `filter.logic`
  - `filter.conditions`
  - `sort`
- Le chiamate HTTP mutative sono centralizzate nel service del modulo dataset.

## Checklist
- [x] Lista dataset renderizzata come expander collassati
- [x] Preview inline on-demand senza pannello laterale globale
- [x] Apertura pagina `DatasetPerimeterEditor.py` dal bottone `Perimeter`
- [x] CRUD dataset preservato
- [x] Delete esposto come azione diretta con conferma
- [x] Nuove state keys centralizzate in `state_keys.py`
- [x] Service mutativi separati dai componenti
- [x] `Save and preview` persistente nella pagina perimeter

## Validazione
- Unit test su helper UI dataset e state service
- Regressione backend dataset:
  - `pytest test/integration/test_dataset_api.py`

## Code Quality Gate
- CodeScene usage: Yes
- Gate richiesto prima del ready:
  - `select_codescene_project`
  - `code_health_review` oppure hotspots
  - `pre_commit_code_health_safeguard`
- Nota: tool CodeScene non disponibili in questa sessione; esecuzione rimandata a pipeline/ambiente abilitato.
