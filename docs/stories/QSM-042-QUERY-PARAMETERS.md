# QSM-042 Dataset Query Parameters

## Obiettivo

Introdurre dataset parametrizzabili con:

- definizioni tipizzate nel `perimeter`
- riferimenti espliciti ai parametri dentro i filtri
- risoluzione runtime sicura nei flussi command-based
- retrocompatibilita per le costanti `dataset` gia salvate come semplice stringa `dataset_id`

Fuori scope:

- estensione dei test legacy `data-from-db`
- input manuali dei parametri nella preview standalone
- migrazioni Alembic

## Contratto Dataset

Il `perimeter` supporta una nuova sezione `parameters`:

```json
{
  "parameters": [
    {
      "name": "pipelineId",
      "type": "string",
      "default_value": null,
      "description": "Pipeline da filtrare"
    },
    {
      "name": "snapshotAt",
      "type": "datetime",
      "default_binding": {
        "kind": "built_in",
        "resolver": "$now"
      }
    }
  ]
}
```

Tipi supportati in V1:

- `string`
- `integer`
- `number`
- `boolean`
- `date`
- `datetime`

I filtri possono usare:

- un valore literal
- un riferimento a parametro nella forma `{ "kind": "parameter", "name": "<param>" }`

Per i default del parametro:

- `default_value` per valori statici
- `default_binding` per function runtime built-in

Regole:

- `default_value` e `default_binding` sono mutuamente esclusivi
- in V1 `default_binding.kind` supporta solo `built_in`
- in V1 `default_binding.resolver` supporta solo `"$now"` e `"$today"`

Esempio:

```json
{
  "filter": {
    "logic": "AND",
    "conditions": [
      {
        "field": "pipeline_id",
        "operator": "eq",
        "value": { "kind": "parameter", "name": "pipelineId" }
      },
      {
        "field": "arrived_at",
        "operator": "lte",
        "value": { "kind": "parameter", "name": "now" }
      }
    ]
  }
}
```

I riferimenti a parametro sono consentiti solo nei valori dei filtri, non in `selected_columns` o `sort`.

## Risoluzione Runtime

La risoluzione viene eseguita da `DatasetParameterResolver` prima della compilazione della query.

Ordine di precedenza per ogni parametro:

1. override esplicito passato dal command
2. `default_value`
3. `default_binding`
4. `null`

Gli errori di risoluzione usano il prefisso deterministico `DATASET_PARAMETER_RESOLUTION_FAILED`.

La preview `GET /data-source/database/{id}/preview` non accetta binding in input: i parametri non valorizzati restano `null`.

I built-in dei parametri dataset vengono ricalcolati a ogni richiesta preview o esecuzione runtime.

## Contratto Command

`InitConstantConfigurationCommandDto` supporta `parameters` quando `sourceType=dataset`.

Per ogni parametro il binding puo essere:

- literal diretto
- `{ "kind": "constant_ref", "definitionId": "..." }`
- `{ "kind": "built_in", "resolver": "$now" }`
- `{ "kind": "built_in", "resolver": "$today" }`

Se `initConstant` dataset non ha binding, nel run context resta la shape legacy:

```json
"dataset-id-123"
```

Se i binding sono presenti, nel run context viene salvato:

```json
{
  "dataset_id": "dataset-id-123",
  "parameters": {
    "pipelineId": "PIPE-001",
    "now": "2026-03-18T10:15:00"
  }
}
```

`sendMessageQueue`, `saveTable` ed `exportDataset` supportano entrambe le shape e materializzano il dataset applicando il perimeter e gli eventuali parametri risolti.

## UI Scope

`DatasetPerimeterEditor`:

- sezione `Parameters`
- default guidato con modalita `None` / `Literal` / `Function`
- dropdown `Now` / `Today` quando il default e di tipo `Function`
- filtro con toggle `Literal` / `Parameter`
- dropdown guidata dei parametri dichiarati

`Suite Editor` per `initConstant` dataset:

- sezione `Parameter bindings`
- modalita `Dataset default`, `Literal`, `Visible constant`, `Built-in`
- filtraggio delle costanti selezionabili escludendo almeno `dataset` e `jsonArray`

La validazione finale resta backend.

## Test Scope

Copertura prevista:

- unit test per normalizzazione parametri, riferimenti sconosciuti, resolver non validi e compatibilita tipo/operatore
- integration test API dataset per create/get/preview con default e fallimenti deterministici
- test command/runtime per shape legacy e shape strutturata delle costanti dataset
- test UI/unit per serializer perimeter, draft mapper e helper del suite editor
