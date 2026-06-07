# QSM-045 Mock Server Import OpenAPI JSON

## Obiettivo

Introdurre nel `MockServerEditor` un flusso di import da file locale OpenAPI 3.x JSON che aggiunge in append le API definite nel file al mock server corrente.

La feature e limitata a:

- upload locale di file `.json`
- parsing OpenAPI 3.x
- append delle route importabili al mock server corrente
- persistenza immediata tramite il normale `update_mock_server`

Fuori scope:

- YAML
- Swagger 2.0
- fetch da URL
- sync futura
- estensione del runtime per supportare path parameters

## UX

Nella sezione `APIs` del `MockServerEditor` viene aggiunto un bottone `Import` accanto a `Add API`.

Il bottone apre un dialog Streamlit con:

- `file_uploader` per file `.json`
- preview sintetica dell'import
- conferma finale di append

La preview mostra almeno:

- numero API importabili
- numero duplicati saltati
- eventuali warning
- eventuali path templated rilevati
- eventuali errori bloccanti di parsing/validazione

Se il file non e valido o non e OpenAPI 3.x, l'import non e confermabile.

## Contratto Import

Nuovo servizio puro Python:

- `app/mock_servers/services/openapi_import_service.py`
- funzione principale `import_openapi_json(raw_bytes: bytes, existing_routes: set[tuple[str, str]]) -> OpenApiImportResult`

`OpenApiImportResult` espone almeno:

- `apis_to_append`
- `imported_count`
- `skipped_duplicates`
- `templated_paths`
- `warnings`
- `errors`

## Mapping OpenAPI -> Mock API

Per ogni operation HTTP supportata viene generata una route mock.

Campi mappati:

- `description`: `summary`, fallback `operationId`, fallback `METHOD path`
- `method`: method OpenAPI normalizzato uppercase
- `path`: path OpenAPI normalizzato come nel mock editor
- `params`: `{}`
- `headers`: `{}`
- `authorization`: `{}`
- `body`: `null`
- `body_type`: `any`
- `body_match`: `contains`
- `response_status`: `200` se presente, altrimenti prima `2xx`, altrimenti `default`, altrimenti fallback `200`
- `response_body`: primo example JSON disponibile nella response selezionata, fallback `{ "status": "ok" }`
- `response_headers`: `{"Content-Type": "application/json"}` solo quando `response_body` e object/list
- `pre_response_commands`: `[]`
- `response_operations`: `[]`
- `post_response_commands`: `[]`
- `priority`: `0`

L'ordine finale e in append rispetto alle API gia presenti nel mock server.

## Regole

Duplicati:

- se esiste gia una route con stesso `method + normalized path`, la route importata viene saltata
- se il file contiene duplicati interni, viene importata solo la prima occorrenza

Path templated:

- path come `/orders/{id}` vengono importati letteralmente
- il runtime attuale continuera a matchare la stringa letterale `/orders/{id}`
- il runtime non matchera `/orders/123` in questa versione

## Test Scope

Copertura prevista:

- JSON valido OpenAPI 3.x
- JSON non valido
- JSON valido ma non OpenAPI 3.x
- mapping `summary` / `operationId` / fallback `METHOD path`
- selezione response `200` / prima `2xx` / `default`
- fallback response body `{ "status": "ok" }`
- skip duplicati verso il mock server corrente
- skip duplicati interni al file
- rilevazione path templated con warning esplicito

Test manuale UI:

- apertura dialog `Import`
- preview coerente
- append reale delle API
- persistenza dopo reload
- nessuna modifica a queue, commands o configurazione server
