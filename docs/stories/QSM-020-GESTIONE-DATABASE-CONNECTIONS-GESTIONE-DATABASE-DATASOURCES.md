# QSM-020 - Gestione database connections / Gestione database datasources

## Stato
- Stato: Completato
- Checklist: 6/6 completata

## Dettaglio sviluppo

### Gestione database connections

- [x] Aggiungere una pagina sotto Configurations per la gestione delle connessioni a db
- [x] la crud Ã¨ uguale a quella dei brokers eccezion fatta per `open queues`
- [x] Al momento gestiamo solo connessioni Postgres, aggiungi Oracle e MSSQL

### Gestione database datasources

- [x] Aggiungere una pagina sotto datasources per la gestione dei sorgenti di tipo db (tabelle)
- [x] la crud Ã¨ uguale a quella fatta per Json array eccezzion fatta per la parte sinistra in cui vediamo la preview della tabella configurata
- [x] quando aggiungiamo una tabella si apre un dialog in cui:
 - si sceglie code e descrizione
 - si sceglie la connessione
 - viene mostrato un tree in cui ci sono tabelle e views
 - scelta la tabella\view si clicca `add` e viene creato il db datasource

## Fonte
- Estratto da `docs/TASK.md`
