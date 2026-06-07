# QF Extension SDK — Specifica Esecutiva

> Piano tecnico per la creazione di librerie Java e Python che consentono di esporre custom commands e verify a Quality Flow.
> Target: tool di vibe-coding (Cursor / Codex / Claude Code) e team di prodotto.
> Stato: approvato — pronto per implementazione Fase 1.

---

## 1. Obiettivo

Permettere a team di prodotto di implementare **custom commands** e **custom verify** specifici del loro dominio, esporli come microservizi, e integrarli in Quality Flow come se fossero comandi nativi.

QF li scopre tramite un registry, li esegue via API REST, e gestisce il ciclo di vita asincrono tramite RabbitMQ.

### Principi guida

- **Contract-first.** L'OpenAPI spec del SDK è la fonte di verità. Backend QF e SDK devono implementarla, non il contrario.
- **Input risolti da QF.** I binding (`constant_ref`, `runtime_value`, `literal`) vengono risolti dal runtime QF prima di chiamare l'extension. L'SDK riceve input già materializzati.
- **Snapshot al save.** `input_schema` e `extension_version` vengono frozen in `suite_item_commands` al momento del salvataggio. Il runtime usa lo snapshot, non la versione live.
- **Fail esplicito.** Extension irraggiungibile = test fallito con `EXTENSION_UNREACHABLE`, mai silent skip.
- **Versioning URL.** Breaking changes su `/v2/`. Oggi tutto è `/v1/`.

---

## 2. Architettura d'insieme

```
┌─────────────────────────────────────────────────────────────────┐
│                        Quality Flow Core                        │
│                                                                 │
│  Suite Editor ──► Command Palette ◄── Extension Registry        │
│      │                                       ▲                  │
│  Runtime Engine ──► Extension Dispatcher     │                  │
│      │                     │                 │                  │
│      │             ┌───────┴──────┐          │                  │
│      │             │  HTTP /v1/   │          │                  │
│      │             │  + RabbitMQ  │          │                  │
│      │             └───────┬──────┘          │                  │
│      ▼                     │                 │                  │
│  SSE Bridge ◄──────────────┘                 │                  │
└──────────────────────────────────────────────┼──────────────────┘
                                               │ POST /extensions/register
                    ┌──────────────────────────┘
                    ▼
         ┌─────────────────────┐      ┌─────────────────────┐
         │  Extension (Python) │      │  Extension (Java)   │
         │  qf-sdk             │      │  qf-sdk-spring      │
         │                     │      │                     │
         │  GET  /v1/commands  │      │  GET  /v1/commands  │
         │  POST /v1/execute   │      │  POST /v1/execute   │
         │  GET  /health       │      │  GET  /health       │
         └──────────┬──────────┘      └──────────┬──────────┘
                    │                            │
                    └────────────┬───────────────┘
                                 ▼
                         ┌──────────────┐
                         │  RabbitMQ    │
                         │  qf.events   │
                         │  (topic)     │
                         └──────────────┘
```

### Flusso principale

1. L'extension si avvia e chiama `POST /extensions/register` su QF.
2. QF chiama `GET /v1/commands` e popola il catalogo interno.
3. Il configuratore vede i custom command nel **Command Palette** del Suite Editor.
4. Al save del test, QF congela `input_schema` e `extension_version` nello snapshot.
5. A runtime, QF risolve i binding, valida gli input contro `input_schema_snapshot`, poi chiama `POST /v1/execute`.
6. Per command sincroni: risposta diretta. Per command asincroni: `status: accepted` + ascolto eventi RabbitMQ.
7. Gli eventi RabbitMQ vengono bridgati sullo stream SSE dell'esecuzione.

---

## 3. Modello dati QF — nuove tabelle

### `extensions`

```sql
CREATE TABLE extensions (
  id              uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
  extension_id    varchar(128) NOT NULL UNIQUE,   -- es. com.acme.crm-extension
  display_name    varchar(256) NOT NULL,
  base_url        varchar(512) NOT NULL,
  bearer_token    varchar(512) NULL,              -- cifrato a riposo (AES-256-GCM)
  version         varchar(32)  NULL,              -- popolato da /v1/commands
  tags            text[]       NOT NULL DEFAULT '{}',
  status          varchar(16)  NOT NULL DEFAULT 'registered',
                  -- registered | healthy | unhealthy | unreachable
  last_health_at  timestamptz  NULL,
  last_refresh_at timestamptz  NULL,
  auto_refresh    boolean      NOT NULL DEFAULT true,
  created_at      timestamptz  NOT NULL DEFAULT now(),
  updated_at      timestamptz  NOT NULL DEFAULT now()
);
```

### `extension_commands`

```sql
CREATE TABLE extension_commands (
  id                      uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
  extension_id            uuid         NOT NULL REFERENCES extensions(id) ON DELETE CASCADE,
  command_code            varchar(128) NOT NULL,
  command_type            varchar(16)  NOT NULL,  -- action | verify | transform
  display_name            varchar(256) NOT NULL,
  description             text         NULL,
  is_async                boolean      NOT NULL DEFAULT false,
  input_schema            jsonb        NOT NULL,
  output_schema           jsonb        NULL,
  result_constant_support boolean      NOT NULL DEFAULT false,
  async_config            jsonb        NULL,
  UNIQUE (extension_id, command_code)
);
```

### Modifica `suite_item_commands`

I command di tipo extension usano `command_type = 'extension'` con payload:

```json
{
  "extension_id": "com.acme.crm-extension",
  "command_code": "CRM_FETCH_ORDER",
  "input_schema_snapshot": { ... },
  "extension_version_snapshot": "1.2.0"
}
```

Lo snapshot garantisce che aggiornamenti dell'extension non rompano silenziosamente i test esistenti.

---

## 4. Contratto API dell'Extension — `/v1/commands`

`GET /v1/commands` — restituisce il catalogo completo.

```json
{
  "extension_id": "com.acme.crm-extension",
  "display_name": "CRM Commands",
  "version": "1.2.0",
  "commands": [
    {
      "command_code": "CRM_FETCH_ORDER",
      "command_type": "action",
      "display_name": "Fetch CRM Order",
      "description": "Recupera un ordine dal CRM per ID",
      "is_async": false,
      "input_schema": {
        "type": "object",
        "properties": {
          "order_id": { "type": "string", "description": "ID ordine CRM" },
          "env":      { "type": "string", "enum": ["prod", "staging"] }
        },
        "required": ["order_id"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "order":  { "type": "object" },
          "status": { "type": "string" }
        }
      },
      "result_constant_support": true
    },
    {
      "command_code": "CRM_VERIFY_ORDER_STATUS",
      "command_type": "verify",
      "display_name": "Verify Order Status",
      "description": "Verifica che lo stato ordine corrisponda al valore atteso",
      "is_async": false,
      "input_schema": {
        "type": "object",
        "properties": {
          "order_id":        { "type": "string" },
          "expected_status": { "type": "string" }
        },
        "required": ["order_id", "expected_status"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "passed":       { "type": "boolean" },
          "actual_value": { "type": "string" },
          "message":      { "type": "string" }
        }
      }
    },
    {
      "command_code": "CRM_BULK_PROCESS",
      "command_type": "action",
      "display_name": "Bulk Process Orders",
      "is_async": true,
      "async_config": {
        "event_exchange":         "qf.events",
        "event_routing_key_prefix": "ext.com-acme-crm-extension"
      },
      "input_schema": {
        "type": "object",
        "properties": {
          "batch_size": { "type": "integer", "default": 100 }
        }
      }
    }
  ]
}
```

**Valori di `command_type`:**

| Valore      | Semantica                                                       |
|-------------|-----------------------------------------------------------------|
| `action`    | Esegue un'operazione, può produrre output e `result_constant`   |
| `verify`    | Valuta una condizione, ritorna sempre `passed: bool + message`  |
| `transform` | Trasforma dati in ingresso — puro, nessun side effect           |

---

## 5. Contratto API dell'Extension — `/v1/execute`

`POST /v1/execute` — esegue un singolo command o verify.

### Request

I binding vengono **risolti da QF** prima della chiamata. L'SDK riceve `inputs` già materializzati.

```json
{
  "execution_id": "uuid-qf-runtime",
  "command_code": "CRM_FETCH_ORDER",
  "run_envelope": {
    "global":           { "env": "staging" },
    "local":            { "customer_id": "C-001" },
    "result_constants": { "ORDER_ID": "ORD-123" }
  },
  "inputs": {
    "order_id": "ORD-123",
    "env":      "staging"
  }
}
```

### Response — command sincrono

```json
{
  "execution_id": "uuid-qf-runtime",
  "command_code": "CRM_FETCH_ORDER",
  "status": "success",
  "output": {
    "order":  { "id": "ORD-123", "status": "SHIPPED" },
    "status": "SHIPPED"
  },
  "result_constant_value": "SHIPPED",
  "duration_ms": 142,
  "error": null
}
```

### Response — command asincrono (`is_async: true`)

```json
{
  "execution_id": "uuid-qf-runtime",
  "command_code": "CRM_BULK_PROCESS",
  "status": "accepted",
  "correlation_id": "corr-abc-789",
  "error": null
}
```

QF attende gli eventi RabbitMQ filtrati per `correlation_id`. Timeout default: 60s → `EXTENSION_TIMEOUT`.

### Response — verify

```json
{
  "execution_id": "uuid-qf-runtime",
  "command_code": "CRM_VERIFY_ORDER_STATUS",
  "status": "success",
  "output": {
    "passed":       false,
    "actual_value": "PENDING",
    "message":      "Expected 'SHIPPED', got 'PENDING'"
  },
  "result_constant_value": null,
  "duration_ms": 88,
  "error": null
}
```

`passed: false` → QF marca il test come `failed` e mostra `message` nell'execution view.

### Codici errore standard

| `error_code`               | Causa                                                        |
|----------------------------|--------------------------------------------------------------|
| `EXTENSION_UNREACHABLE`    | L'extension non risponde (timeout TCP/HTTP)                  |
| `EXTENSION_TIMEOUT`        | Command asincrono: nessun evento RabbitMQ entro il timeout   |
| `INPUT_VALIDATION_FAILED`  | Gli input materializzati non passano validazione `input_schema_snapshot` |
| `COMMAND_NOT_FOUND`        | `command_code` non presente nel catalogo corrente            |
| `INTERNAL_ERROR`           | Errore non gestito lato extension                            |

---

## 6. Validazione `input_schema`

La validazione avviene in **due momenti distinti**:

**Design time** (save dello step nel Suite Editor): QF usa `input_schema` per generare il form e per validare i valori inseriti. Errori bloccano il salvataggio con messaggio inline sul campo.

**Runtime** (esecuzione del test): QF risolve i binding, valida il payload materializzato contro `input_schema_snapshot`. Se fallisce, il test viene marcato `failed` con `INPUT_VALIDATION_FAILED` prima ancora di chiamare l'extension.

Se `extension_version_snapshot` diverge dalla versione live, la UI mostra un warning passivo nell'editor: `⚠ Extension aggiornata a v1.3.0 — verifica gli input`.

---

## 7. Registry delle Extension in QF — router `/extensions`

| Endpoint                        | Metodo | Funzione                                    |
|---------------------------------|--------|---------------------------------------------|
| `/extensions`                   | GET    | Lista extension registrate con status       |
| `/extensions/register`          | POST   | Auto-registrazione da parte dell'extension  |
| `/extensions/{ext_id}`          | DELETE | Rimozione extension                         |
| `/extensions/{ext_id}/refresh`  | POST   | Forza refresh catalogo comandi              |
| `/extensions/{ext_id}/health`   | GET    | Stato health corrente                       |

### Payload di registrazione

```json
{
  "extension_id": "com.acme.crm-extension",
  "base_url":     "http://crm-extension-service:8080",
  "bearer_token": "tok-secret-xyz",
  "tags":         ["crm", "orders"],
  "auto_refresh": true
}
```

### Health polling

QF fa polling su `GET /health` ogni 60 secondi. Dopo 3 fallimenti consecutivi lo status passa a `unreachable`. La UI mostra il badge nella pagina Extensions (sotto Configurations).

### Autenticazione

QF inietta `Authorization: Bearer <token>` su ogni chiamata verso l'extension. Il `bearer_token` è cifrato a riposo (AES-256-GCM). Le extension girano in rete Docker interna (trust implicito): nessuna autenticazione richiesta verso QF.

---

## 8. Protocollo RabbitMQ — elaborazioni asincrone

**Exchange:** `qf.events` (topic)

### Eventi Extension → QF

| Routing key               | Payload fields                                                  |
|---------------------------|-----------------------------------------------------------------|
| `ext.{ext_id}.started`    | `correlation_id, execution_id, command_code, ts`                |
| `ext.{ext_id}.progress`   | `correlation_id, execution_id, percent, message`                |
| `ext.{ext_id}.completed`  | `correlation_id, execution_id, status, output, result_constant_value, duration_ms` |
| `ext.{ext_id}.failed`     | `correlation_id, execution_id, error_code, error_message, ts`   |

### Esempio evento `completed`

```json
{
  "routing_key": "ext.com-acme-crm-extension.completed",
  "payload": {
    "correlation_id":         "corr-abc-789",
    "execution_id":           "uuid-qf-runtime",
    "command_code":           "CRM_BULK_PROCESS",
    "status":                 "success",
    "output":                 { "processed": 1500, "failed": 3 },
    "result_constant_value":  null,
    "duration_ms":            12400,
    "ts":                     "2026-05-10T14:32:11Z"
  }
}
```

QF consumer ascolta `ext.#`, filtra per `correlation_id`, aggiorna lo stato dell'esecuzione e pubblica sul canale SSE. In **Fase 1** gli eventi SSE sono transienti (in-memory). In **Fase 2** verranno persistiti in `execution_events`.

---

## 9. SDK Python — struttura e API pubblica

### Struttura moduli

```
qf-sdk-python/
├── qf_sdk/
│   ├── __init__.py        # esporta: QFExtension, RunContext, VerifyResult, CommandResult
│   ├── _app.py            # QFExtension: registra command/verify, costruisce FastAPI app
│   ├── _context.py        # RunContext: ctx.input(), ctx.set_result_constant()
│   ├── _models.py         # Pydantic: ExecuteRequest, ExecuteResponse, CommandDescriptor
│   ├── _server.py         # FastAPI con /v1/commands, /v1/execute, /health
│   ├── _register.py       # POST /extensions/register su QF all'avvio
│   ├── _schema.py         # type hints Python → JSON Schema
│   └── async_/
│       ├── __init__.py
│       └── publisher.py   # AsyncEventPublisher (aio-pika — dipendenza opzionale)
├── examples/
│   └── crm_extension/
│       └── main.py
└── pyproject.toml
```

### Esempio d'uso

```python
from qf_sdk import QFExtension, RunContext, VerifyResult

app = QFExtension(
    extension_id="com.acme.crm-extension",
    display_name="CRM Commands",
    qf_base_url="http://quality-flow:9082",
    bearer_token="tok-secret-xyz",
)

@app.command(
    code="CRM_FETCH_ORDER",
    display_name="Fetch CRM Order",
    description="Recupera un ordine dal CRM",
)
async def fetch_order(ctx: RunContext) -> dict:
    order_id = ctx.input("order_id")            # già materializzato da QF
    env      = ctx.input("env", default="prod")
    result   = await crm_client.get_order(order_id, env)
    ctx.set_result_constant(result["status"])   # espone il valore per resultConstant
    return result

@app.verify(
    code="CRM_VERIFY_ORDER_STATUS",
    display_name="Verify Order Status",
)
async def verify_order_status(ctx: RunContext) -> VerifyResult:
    order_id = ctx.input("order_id")
    expected = ctx.input("expected_status")
    actual   = await crm_client.get_status(order_id)
    return VerifyResult(
        passed=(actual == expected),
        actual_value=actual,
        message=f"Expected '{expected}', got '{actual}'"
    )

# command asincrono (richiede: pip install qf-sdk[async])
@app.command(
    code="CRM_BULK_PROCESS",
    display_name="Bulk Process Orders",
    is_async=True,
)
async def bulk_process(ctx: RunContext) -> None:
    batch_size   = ctx.input("batch_size", default=100)
    correlation  = ctx.correlation_id
    await ctx.publish_started()
    results = await crm_client.bulk(batch_size, progress_cb=ctx.publish_progress)
    await ctx.publish_completed(output=results)

# Avvia il server, espone /v1/commands /v1/execute /health,
# e chiama POST /extensions/register su QF
app.run(host="0.0.0.0", port=8080)
```

### Configurazione (`pyproject.toml` deps)

```toml
[project]
name = "qf-sdk"
dependencies = ["fastapi", "pydantic>=2", "httpx", "uvicorn"]

[project.optional-dependencies]
async = ["aio-pika"]
```

---

## 10. SDK Java — struttura e API pubblica

### Struttura moduli

```
qf-sdk-java/
├── qf-sdk-core/                        # nessuna dipendenza Spring/RabbitMQ
│   └── src/main/java/io/qualityflow/sdk/
│       ├── QFCommand.java              # @interface: code, displayName, description, asyncMode
│       ├── QFVerify.java               # @interface: code, displayName, description
│       ├── RunContext.java             # interface: input(name), setResultConstant(value)
│       ├── CommandResult.java          # factory: success(output), failure(code, msg)
│       ├── VerifyResult.java           # factory: of(passed).withActual().withMessage()
│       └── ExtensionDescriptor.java   # POJO serializzato per /v1/commands
├── qf-sdk-spring/
│   └── src/main/java/io/qualityflow/sdk/spring/
│       ├── QFExtensionAutoConfiguration.java  # @Configuration + @EnableConfigurationProperties
│       ├── QFExtensionProperties.java          # extension-id, base-url, qf-base-url, rabbit.*
│       ├── CommandController.java              # @RestController: /v1/commands, /v1/execute, /health
│       ├── CommandRegistry.java                # classpath scan su @QFCommand/@QFVerify
│       ├── RunContextImpl.java                 # implementazione con inputs ricevuti da QF
│       ├── RabbitEventPublisher.java           # RabbitTemplate wrapper per async events
│       └── QFRegistrationRunner.java           # ApplicationRunner → POST /extensions/register
└── qf-sdk-examples/
    └── crm-extension/                          # Spring Boot app di esempio funzionante
```

### Esempio d'uso

```java
@Component
public class CrmCommands {

    @QFCommand(
        code        = "CRM_FETCH_ORDER",
        displayName = "Fetch CRM Order",
        description = "Recupera un ordine dal CRM"
    )
    public CommandResult fetchOrder(RunContext ctx) {
        String orderId = ctx.input("order_id");
        String env     = ctx.input("env", "prod");
        Order  order   = crmClient.getOrder(orderId, env);
        return CommandResult.success(order)
            .withResultConstant(order.getStatus());
    }

    @QFVerify(
        code        = "CRM_VERIFY_ORDER_STATUS",
        displayName = "Verify Order Status"
    )
    public VerifyResult verifyOrderStatus(RunContext ctx) {
        String orderId  = ctx.input("order_id");
        String expected = ctx.input("expected_status");
        String actual   = crmClient.getStatus(orderId);
        return VerifyResult.of(actual.equals(expected))
            .withActual(actual)
            .withMessage("Expected '%s', got '%s'", expected, actual);
    }

    @QFCommand(
        code        = "CRM_BULK_PROCESS",
        displayName = "Bulk Process Orders",
        asyncMode   = true
    )
    public void bulkProcess(RunContext ctx) {
        int batchSize = ctx.inputInt("batch_size", 100);
        ctx.publishStarted();
        // elaborazione con callback progresso
        crmClient.bulk(batchSize, pct -> ctx.publishProgress(pct, "Processing..."));
        ctx.publishCompleted(Map.of("processed", 1500, "failed", 3));
    }
}
```

### Configurazione (`application.yml`)

```yaml
qf:
  sdk:
    extension-id:  com.acme.crm-extension
    display-name:  CRM Commands
    qf-base-url:   http://quality-flow:9082
    bearer-token:  tok-secret-xyz
    auto-register: true
    rabbit:
      enabled:    true
      exchange:   qf.events
      host:       rabbitmq
      port:       5672
```

---

## 11. Integrazione Suite Editor

### Command Palette

Sezione **Custom Commands** nel dialog `Add step`. Supporta:
- Ricerca per `display_name`, `command_code`, `tags`, `extension_id`
- Raggruppamento per extension con header collassabile
- Badge `verify` / `action` / `async` per ogni command
- Badge `⚠ versione aggiornata` se l'extension è cambiata dopo lo snapshot

### Form generazione automatica

QF genera il form dei parametri da `input_schema` (JSON Schema → widget). Tipi supportati in Fase 1:

| JSON Schema type | Widget generato                |
|------------------|-------------------------------|
| `string`         | Input text                    |
| `string` + `enum`| Dropdown select               |
| `integer`        | Input numerico                |
| `boolean`        | Toggle                        |
| `object`         | JSON editor (inline)          |

Ogni parametro supporta i binding già noti: `literal`, `constant_ref`, `runtime_value`, `built_in ($now/$today)`.

### Visualizzazione risultati

I verify custom appaiono nell'execution view con la stessa icona check/error dei verify nativi. Il campo `message` viene mostrato nel dettaglio esecuzione. I progress event asincroni alimentano la progress bar del drawer.

---

## 12. Fasi di implementazione

### Fase 1 — Foundation (backend + SDK base)

Obiettivo: custom commands sincroni funzionanti end-to-end. Nessun async.

- Definizione OpenAPI spec SDK (fonte di verità condivisa).
- Migrazione DB: tabelle `extensions` e `extension_commands`.
- Router FastAPI `/extensions` (CRUD + register + refresh + health).
- Dispatcher runtime: risoluzione binding → validazione schema → `POST /v1/execute` → parse response.
- Gestione errori: `EXTENSION_UNREACHABLE` (fail test), `INPUT_VALIDATION_FAILED`, `COMMAND_NOT_FOUND`.
- SDK Python: `QFExtension`, decoratori `@app.command`/`@app.verify`, `RunContext`, `FastAPI` automatico, auto-register.
- SDK Java Core: `@QFCommand`, `@QFVerify`, `RunContext`, `CommandResult`, `VerifyResult`.
- SDK Java Spring: `CommandController`, `CommandRegistry` (classpath scan), `QFRegistrationRunner`.
- Suite Editor: lettura comandi da extension, snapshot in `suite_item_commands`, form da `input_schema`.
- Test backend: pytest con extension mock (Testcontainers).

**Definition of done Fase 1:** test sincrono con command e verify custom funzionanti; snapshot corretto; fail esplicito se extension irraggiungibile; coverage nuova ≥ 80%.

### Fase 2 — Async + RabbitMQ

Obiettivo: command asincroni con eventi RabbitMQ → SSE.

- Consumer QF su `ext.#` con routing per `correlation_id`.
- Bridge RabbitMQ → SSE stream esistente (`/elaborations/execution/{id}/events`).
- Timeout per command asincroni (default 60s, configurabile per extension).
- SDK Python: `AsyncEventPublisher` (aio-pika).
- SDK Java: `RabbitEventPublisher` (RabbitTemplate).
- Health polling QF ogni 60s su `/health` extension.
- UI: pagina **Extensions** sotto Configurations (lista + status badge + last health).

**Definition of done Fase 2:** command asincrono completa il ciclo started → progress → completed con aggiornamento SSE live; health badge corretto in UI.

### Fase 3 — DX e robustezza

Obiettivo: experience developer eccellente, distribuzione pubblica.

- JSON Schema → form Streamlit automatico (tipi annidati, `oneOf`, `anyOf`).
- Warning UI se `extension_version_snapshot` diverge dalla versione live.
- Persistenza eventi SSE in tabella `execution_events` (Fase 2 li tiene in-memory).
- Publish PyPI: `qf-sdk` (Python).
- Publish Maven Central: `io.qualityflow:qf-sdk-core`, `io.qualityflow:qf-sdk-spring`.
- Documentazione con esempio CRM completo funzionante (Docker Compose incluso).
- Test di integrazione con extension mock in Testcontainers.

---

## 13. Decisioni architetturali fissate

| Decisione                      | Scelta                                                                      |
|-------------------------------|-----------------------------------------------------------------------------|
| Autenticazione QF → Extension | Bearer token (iniettato da QF su ogni chiamata)                             |
| Autenticazione Extension → QF | Nessuna (rete Docker interna, trust implicito)                              |
| Persistenza eventi SSE         | Fase 1-2: transienti in-memory. Fase 3: tabella `execution_events`          |
| Validazione `input_schema`     | Design time (save) + runtime (pre-call) entrambi                            |
| Extension irraggiungibile      | Test fallisce con `EXTENSION_UNREACHABLE`                                   |
| Versioning API                 | URL-based: oggi `/v1/`. Breaking changes su `/v2/`                          |
| Risoluzione binding            | Effettuata da QF prima di chiamare l'extension (inputs già materializzati)  |

---

## 14. Out of scope

- Plugin marketplace o template community.
- Autenticazione OAuth2 / mTLS tra QF e extension.
- UI visual builder per `input_schema` (form generato automaticamente, non editabile graficamente).
- Refactor del formato `command_constant_definitions` esistente.
- Migrazione Streamlit → Angular (direttiva separata).
- Versionamento dei command catalog (non si mantiene storico delle versioni passate).

---

## Appendice A — Esempio flusso completo sincrono

**Step configuratore:**
1. Suite Editor → Add step → Custom Commands → cerca "Fetch CRM Order".
2. Form: `order_id = ${result.constants.ORDER_ID}`, `env = staging`.
3. Save.

**Cosa succede al save:**
- QF congela `input_schema_snapshot` e `extension_version_snapshot = 1.2.0`.
- `suite_item_commands` contiene lo snapshot con `command_type = 'extension'`.

**Cosa succede a runtime:**
1. QF risolve `${result.constants.ORDER_ID}` → `"ORD-123"`.
2. QF valida `{ "order_id": "ORD-123", "env": "staging" }` contro `input_schema_snapshot`. OK.
3. QF chiama `POST http://crm-service:8080/v1/execute` con `Authorization: Bearer tok-secret-xyz`.
4. Extension risponde `{ "status": "success", "output": { ... }, "result_constant_value": "SHIPPED" }`.
5. QF registra l'esecuzione, aggiorna lo scope `result.constants`.

## Appendice B — Esempio flusso completo asincrono

**A runtime:**
1. QF chiama `POST /v1/execute` → risposta `{ "status": "accepted", "correlation_id": "corr-xyz" }`.
2. QF si iscrive al consumer RabbitMQ filtrando per `corr-xyz`.
3. Extension pubblica `ext.com-acme-crm-extension.started` → QF bridga su SSE → progress bar nel drawer.
4. Extension pubblica (opzionale) `ext.com-acme-crm-extension.progress` con `percent: 45`.
5. Extension pubblica `ext.com-acme-crm-extension.completed` → QF chiude l'esecuzione con `success`.
6. Se nessun evento in 60s → QF marca il test `failed` con `EXTENSION_TIMEOUT`.
