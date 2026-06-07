# QSM-032 - Mock server modifiche alla ui della configurazione

## Stato
- Stato: Da fare
- Checklist: 0/7 completata

## Dettaglio sviluppo

### Mock server modifiche alla ui della configurazione

- Nella pagina `MockServers` 
    - [ ] rimuovere riepilogo api, queues etc..
    - [ ] rimuovere bottone refresh
    - [ ] sostituire bottone play con un toggle per attivazione\disattivazione server 
    - [ ] mettere bottone ... (verticali) con dialog per modifica e cancellazione
        - nella modifica è possibile cambiare descrizione e endpoint e cancellare il server
        - la modifica è abilitata solo se il server è disattivato 
    - [ ] il bottone ruota meccanica naviga verso una nuova pagina `MockServerEditor` che è quella messa sotto la sezione `Mock Servers`
    - [ ] Spostare la sezione `Mock Servers` sotto la sezione Test prima di `Logs & Tools`
- Nella pagina `MockServerEditor` simile allo suite
 - [ ] layout
    - titolo Descrizione mock server
    - subheader endpoint
    - toggle attiva\disattiva
    - divider
    - sezione api come test suite: 
        - per ogni api expander e bottone modifica e cancellazione, nota: non mettere indicatore
        - dentro expander 
            - selectbox per tipo api | url 
            - tabs: params, authorization, headers, body
            - sezione operazioni come in test
    
    - divider
    - sezione queue come test suite: 
        - per ogni queue expander e bottone modifica e cancellazione, nota: non mettere indicatore
        - dentro expander  
            - descrizione broker | descrizione coda 
        - sezione operazioni come in test

## Fonte
- Estratto da `docs/TASK.md`
