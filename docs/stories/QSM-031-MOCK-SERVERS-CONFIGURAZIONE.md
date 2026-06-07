# QSM-031 - Mock servers - configurazione

## Stato
- Stato: Completato
- Checklist: 3/3 completata

## Dettaglio sviluppo

### Mock servers - configurazione

I mock server sono dei server attivabili su quality-flow per eseguire test in modo asincrono.
    - ogni server può avere:
        - code e desc
        - endpoint
        - più api configurabili 
        - più code su cui rimanere in ascolto
    - le api possono essere configurate come in postman:
        - tipo di metodo GET,PUT, etc..
        - url
        - params
        - headers
        - body
    - le code si riferiscono alle code esistenti su quality-flow
    - ad ogni coda\api associata ad un server possono essere associate le operazioni di quality-flow
    - aggiungere un'altra operazione `run suite`
        - impostare lo suite da eseguire
    - una volta creato un mock server è possibile attivarlo\spengerlo
    - l'attivazione di un mock server mette in ascolto le api e le code
    - all'invocazione di api\coda partono le operazioni ad esse associate
- [x] Aggiungere una pagina `Mock Servers` in configurations
- [x] Aggiungere una sezione `Mock Servers` nel sidebar e mettervi tutti i servers configurati
- [x] Aggiungere relativa anagrafica a db per persistenza dei mock server
    - mock_servers: code, desc json configurazione
    - mock_server_apis: code, desc e json della configurazione
    - ms_api_operations: prendere a riferimento test_operations
    - mock_server_queues: code, desc e id della queue
    - ms_queue_operations: prendere a riferimento test_operations

## Fonte
- Estratto da `docs/TASK.md`
