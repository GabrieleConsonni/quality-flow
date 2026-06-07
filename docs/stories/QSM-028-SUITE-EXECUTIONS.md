# QSM-028 - Suite executions

## Stato
- Stato: Completato
- Checklist: 11/11 completata

## Dettaglio sviluppo

### Suite executions

- Ã¨ necessario persistere a db le esecuzioni degli scenari e vederli sia in suite editor che in home page
- l'esecuzione mostra righe di testata con il nome dello suite e l'esito globale e il datetime
- la riga di testata Ã¨ ampliabile con il dettaglio degli test con esito e datetime
- gli test contengono le operazioni con esito e datetime
- [x] creare la struttura a db `suite_executions`, `suite_test_executions`, `test_operation_executions`
- [x] modificare l'elaborazione degli scenari\test\operatzioni in modo che registrino le esecuzioni
- [x] Aggiungere una home page
    - [x] Aggiungere sezione `Test suite executions` in cui mettere solo gli scenari exectution e bottone che naviga allo suiteEditor relativo
- [x] Modifiche alla suite editor
    - [x] Dividere lo sceario editor in due parti: la parte di sinistra con gli scenari executions, la parte di destra come adesso.
    - [x] Gli scenari hanno ordine dal piÃ¹ recente al piÃ¹ vecchio
    - [x] Aggiungere `bottone di cancellazione` e `bottone icona cerca`
    - [x] Alla selezione del `bottone cerca`, gli indicatori dello suite: test, operation si aggiornano con i risultati dell'esecuzione. 
    - [x] in basso ad ogni test\operazione mettere (eventualmenten) il messaggio di errore come feedback.
    - [x] quando viene lanciato uno suite\test\test gli indicatori e i messaggi di feedback si svuotano\puliscono  

## Fonte
- Estratto da `docs/TASK.md`
