# QSM-038 - Dataset Perimeter

## Stato
- Stato: Completato
- Area: Backend + UI Streamlit dataset
- Scope: perimetro dataset per preview e runtime

## Obiettivo
Introdurre il concetto di `perimeter` del dataset per controllare projection, filter e sort in modo sicuro e riusabile.

## Modifiche funzionali
### Backend
- Nuovo campo `perimeter` persistito sui dataset.
- Validazione server-side del payload `perimeter` su CRUD dataset.
- Compiler dedicato per trasformare il perimetro in query SQL parametrica.
- Applicazione del perimetro sia nella preview dataset sia nel runtime delle operation che leggono dataset.

### UI
- Editor dedicato `DatasetPerimeterEditor` raggiungibile dalla pagina `Datasets`.
- Configurazione di `selected_columns`, `filter.logic`, `filter.conditions` e `sort`.
- Salvataggio del perimeter con refresh della preview dataset.

## Note tecniche
- Nessun SQL libero lato utente.
- Colonne, filtri e sort sono validati contro il metadata dell'oggetto database.
- Le query generate usano sempre binding parametrico.

## Checklist
- [x] Persistenza campo `perimeter`
- [x] Normalizzazione/validazione server-side
- [x] `DatasetPerimeterCompiler`
- [x] Preview dataset con perimeter applicato
- [x] Runtime dataset integrato con perimeter
- [x] Pagina UI `DatasetPerimeterEditor`
- [x] Test sicurezza/validazione compiler
- [x] Test API dataset con perimeter

## Validazione
- Integration test:
  - `pytest test/integration/test_qsm_038_migration.py`
  - `pytest test/integration/test_dataset_api.py`
- Alembic/runtime test:
  - `pytest test/alembic/services/test_dataset_perimeter_compiler.py`
  - `pytest test/alembic/services/test_command_executors.py`
