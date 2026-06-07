# QSM-024 - Modifiche SuiteEditor - editor operations

## Stato
- Stato: Completato
- Checklist: 6/6 completata

## Dettaglio sviluppo

### Modifiche SuiteEditor - editor operations

- [v] Nel container dello test sostituire il bottone `+ Add operation` con : 
    - [v] `+ Add new operation` -> apre dialog con code, description, operationType etc..
    - [v] `iconaImport Import operation` -> apre dialog con selectbox e preview dei dati dell'operation selezionato
- [v] Se nel dialog di aggiunta operation l'utente sceglie come operationType `PUBLISH` allora viene mostrata una selectbox su brokers configurati. 
      Scelto il broker si attiva seconda selectbox su queue del broker la parte template_id e template_params lo svilupperemo in un secondo momento.
- [v] Se nel dialog di aggiunta operation l'utente sceglie come operationType `SAVE_INTERNAL_DB` allora viene mostrata una textbox per il nome tabella.
- [v] Se nel dialog di aggiunta operation l'utente sceglie come operationType `SAVE_EXTERNAL_DB` allora viene mostrata una selectbox su dataset configurati

## Fonte
- Estratto da `docs/TASK.md`
