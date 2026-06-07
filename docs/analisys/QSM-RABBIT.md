# Quality Flow — Piano operativo per integrazione broker Rabbit e publish da Mock Server

## 1. Obiettivo

Introdurre in Quality Flow un nuovo **broker type `rabbit`** per supportare la pubblicazione di messaggi tramite RabbitMQ.

L’integrazione deve permettere di:

* configurare broker RabbitMQ
* configurare una lista di **destination** riutilizzabili
* supportare destination Rabbit di tipo semplice e coerente con il dominio Quality Flow
* usare le destination dal **mock server** tramite una specifica **operation di pubblicazione**
* mantenere separati i concetti di connessione, destinazione e azione

## 2. Decisioni architetturali

### 2.1 Concetti da separare

#### Broker

Definisce **come collegarsi** a un sistema di messaging.

Esempi:

* `sqs`
* `elasticmq`
* `rabbit`

#### Destination

Definisce **dove inviare** o da dove leggere un messaggio.

Per Rabbit non conviene usare internamente il termine `channel`, perché in AMQP ha un significato tecnico diverso.

Nel modello interno di Quality Flow usare invece:

* `queue`
* `route`

In UI, se serve, è comunque possibile etichettare una destination Rabbit come **Canale Rabbit**.

#### Operation

Definisce **cosa fare** usando una destination.

Nel mock server la pubblicazione non deve essere una proprietà della destination, ma una operation esplicita.

---

### 2.2 Scelta per Rabbit

Per la prima fase supportare due tipi di destination:

#### `queue`

Rappresenta una queue RabbitMQ.
Utile per casi semplici e per possibili estensioni future lato consume/listen.

#### `route`

Rappresenta una destinazione logica Rabbit composta da:

* exchange
* exchange type
* routing key
* queue opzionale
* binding opzionali

Questa è la destination consigliata per il **publish**.

## 3. Broker Rabbit — parametri

### Parametri richiesti

* `host`
  Hostname o IP del broker RabbitMQ.

* `port`
  Porta AMQP, normalmente `5672`.

* `username`
  Username per autenticazione.

* `password`
  Password per autenticazione.

* `virtual_host`
  Virtual host RabbitMQ, tipicamente `/`.

### Parametri opzionali consigliati

* `ssl_enabled`
  Abilita TLS.

* `connection_timeout_ms`
  Timeout apertura connessione.

* `heartbeat_seconds`
  Heartbeat AMQP.

* `automatic_recovery`
  Tentativo di recovery automatico della connessione.

* `client_name`
  Nome logico del client per osservabilità/debug.

* `management_url`
  URL console management RabbitMQ.

* `metadata`
  Mappa di metadati liberi.

## 4. Destination Rabbit — elenco e significato

### 4.1 Destination type `queue`

Rappresenta una queue RabbitMQ.

#### Parametri

* `queue_name`
  Nome della queue.

* `durable`
  Se true, la queue sopravvive al riavvio broker.

* `exclusive`
  Se true, la queue è legata a una sola connessione.

* `auto_delete`
  Se true, la queue viene eliminata automaticamente quando non più usata.

* `auto_create`
  Se true, Quality Flow tenta di dichiarare la queue se non esiste.

* `arguments`
  Parametri avanzati Rabbit, per esempio TTL, DLX, max length.

#### Quando usarla

* casi semplici
* compatibilità mentale con il concetto attuale di coda
* future capacità di consume/listen

---

### 4.2 Destination type `route`

Rappresenta una route Rabbit logica adatta al publish.

#### Parametri

* `exchange_name`
  Nome exchange su cui pubblicare.

* `exchange_type`
  Tipo exchange: `direct`, `topic`, `fanout`, `headers`.

* `routing_key`
  Routing key usata in publish.

* `queue_name`
  Queue opzionale da dichiarare/bindare.

* `binding_keys`
  Lista chiavi di binding opzionali.

* `durable`
  Persistenza exchange.

* `queue_durable`
  Persistenza queue se presente.

* `auto_create`
  Se true, Quality Flow dichiara exchange, eventuale queue e binding mancanti.

* `arguments`
  Parametri avanzati.

#### Quando usarla

* publish verso Rabbit
* routing realistico
* configurazione semplificata lato utente
* integrazione mock server

## 5. Parametri avanzati consigliati per `arguments`

### Queue arguments utili

* `x-message-ttl` — TTL dei messaggi in coda
* `x-expires` — scadenza della queue
* `x-dead-letter-exchange` — exchange di dead letter
* `x-dead-letter-routing-key` — routing key di dead letter
* `x-max-length` — lunghezza massima della queue
* `x-max-priority` — priorità massima supportata

### Nota

Non è necessario supportare tutta la matrice Rabbit nella prima fase. È sufficiente mantenere `arguments` come mappa libera serializzabile.

## 6. Modello dati consigliato

## 6.1 Broker

```json
{
  "id": "rabbit-local",
  "type": "rabbit",
  "name": "Rabbit Local",
  "connection": {
    "host": "localhost",
    "port": 5672,
    "username": "guest",
    "password": "guest",
    "virtual_host": "/",
    "ssl_enabled": false,
    "connection_timeout_ms": 5000,
    "heartbeat_seconds": 30,
    "automatic_recovery": true,
    "client_name": "quality-flow"
  }
}
```

## 6.2 Destination `queue`

```json
{
  "id": "orders-queue",
  "broker_id": "rabbit-local",
  "type": "queue",
  "name": "Orders Queue",
  "config": {
    "queue_name": "orders.q",
    "durable": true,
    "exclusive": false,
    "auto_delete": false,
    "auto_create": true,
    "arguments": {}
  }
}
```

## 6.3 Destination `route`

```json
{
  "id": "orders-created",
  "broker_id": "rabbit-local",
  "type": "route",
  "name": "Orders Created",
  "config": {
    "exchange_name": "orders.events",
    "exchange_type": "topic",
    "routing_key": "orders.created",
    "queue_name": "orders-created.q",
    "binding_keys": ["orders.created"],
    "durable": true,
    "queue_durable": true,
    "auto_create": true,
    "arguments": {}
  }
}
```

## 7. Mock server — scelta funzionale

Il mock server deve avere:

* una **lista di destination** disponibili
* una **operation** dedicata per pubblicare messaggi

### Decisione

La destination è configurazione.
La publish è comportamento.

Questo permette di:

* riusare le destination
* avere più publish operation verso la stessa destination
* separare routing e payload
* estendere facilmente il modello ad altri broker

## 8. Operation `publish_message`

### Parametri consigliati

* `destination_id`
  Riferimento alla destination configurata.

* `payload`
  Payload statico opzionale.

* `payload_ref`
  Riferimento al contesto per ottenere il payload dinamicamente.

* `payload_type`
  `json`, `text`, `bytes`.

* `content_type`
  MIME type, es. `application/json`.

* `content_encoding`
  Es. `utf-8`.

* `headers`
  Header custom del messaggio.

* `routing_key_override`
  Override opzionale della routing key configurata nella destination.

* `exchange_override`
  Override opzionale dell’exchange.

* `delivery_mode`
  `1` non persistente, `2` persistente.

* `priority`
  Priorità messaggio.

* `correlation_id`
  Identificativo di correlazione.

* `message_id`
  Identificativo univoco del messaggio.

* `timestamp`
  Timestamp del messaggio.

* `expiration`
  TTL del singolo messaggio.

* `reply_to`
  Destinazione di risposta.

* `mandatory`
  Flag AMQP per segnalare routing obbligatorio.

* `enabled`
  Abilitazione operation.

* `on_error`
  Strategia errore: `fail`, `warn`, `ignore`.

## 9. Esempio operation `publish_message`

```json
{
  "type": "publish_message",
  "name": "Publish order created event",
  "destination_id": "orders-created",
  "payload_ref": "$response.body",
  "payload_type": "json",
  "content_type": "application/json",
  "content_encoding": "utf-8",
  "headers": {
    "eventType": "ORDER_CREATED",
    "source": "mock-server"
  },
  "delivery_mode": 2,
  "correlation_id": "$context.correlationId",
  "on_error": "fail",
  "enabled": true
}
```

## 10. Risoluzione runtime

### Regole di risoluzione

1. La operation recupera `destination_id`
2. La destination risolve `broker_id`
3. Il broker fornisce i parametri di connessione
4. Il driver Rabbit costruisce la publish request
5. Gli eventuali override nella operation hanno precedenza sulla destination
6. Il payload viene serializzato in base a `payload_type`

### Precedenze consigliate

* `exchange_override` > `destination.config.exchange_name`
* `routing_key_override` > `destination.config.routing_key`
* `payload` esplicito > `payload_ref`

## 11. Validazioni minime

### Broker

* `type` deve essere `rabbit`
* `host` obbligatorio
* `port` obbligatorio e numerico
* `username` obbligatorio
* `password` obbligatorio
* `virtual_host` obbligatorio

### Destination `queue`

* `queue_name` obbligatorio

### Destination `route`

* `exchange_name` obbligatorio
* `exchange_type` obbligatorio
* `routing_key` opzionale solo se `exchange_type = fanout`, altrimenti consigliato obbligatorio

### Operation `publish_message`

* `destination_id` obbligatorio
* almeno uno tra `payload` e `payload_ref`
* `payload_type` coerente con il payload
* `on_error` limitato ai valori previsti

## 12. API / DTO suggeriti

## 12.1 Broker DTO

```python
class RabbitBrokerConnection(BaseModel):
    host: str
    port: int = 5672
    username: str
    password: str
    virtual_host: str = "/"
    ssl_enabled: bool = False
    connection_timeout_ms: int = 5000
    heartbeat_seconds: int = 30
    automatic_recovery: bool = True
    client_name: str | None = None
    management_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## 12.2 Destination DTO

```python
class RabbitQueueDestinationConfig(BaseModel):
    queue_name: str
    durable: bool = True
    exclusive: bool = False
    auto_delete: bool = False
    auto_create: bool = True
    arguments: dict[str, Any] = Field(default_factory=dict)


class RabbitRouteDestinationConfig(BaseModel):
    exchange_name: str
    exchange_type: Literal["direct", "topic", "fanout", "headers"]
    routing_key: str | None = None
    queue_name: str | None = None
    binding_keys: list[str] = Field(default_factory=list)
    durable: bool = True
    queue_durable: bool = True
    auto_create: bool = True
    arguments: dict[str, Any] = Field(default_factory=dict)
```

## 12.3 Publish DTO

```python
class PublishMessageOperation(BaseModel):
    type: Literal["publish_message"]
    name: str | None = None
    destination_id: str
    payload: Any | None = None
    payload_ref: str | None = None
    payload_type: Literal["json", "text", "bytes"] = "json"
    content_type: str | None = "application/json"
    content_encoding: str | None = "utf-8"
    headers: dict[str, Any] = Field(default_factory=dict)
    exchange_override: str | None = None
    routing_key_override: str | None = None
    delivery_mode: int | None = 2
    priority: int | None = None
    correlation_id: str | None = None
    message_id: str | None = None
    timestamp: str | None = None
    expiration: str | None = None
    reply_to: str | None = None
    mandatory: bool = False
    enabled: bool = True
    on_error: Literal["fail", "warn", "ignore"] = "fail"
```

## 13. Implementazione tecnica suggerita

### 13.1 Layer da introdurre

* repository/config layer per broker Rabbit
* repository/config layer per destination Rabbit
* driver Rabbit dedicato
* service di risoluzione destination → broker
* executor operation `publish_message`
* supporto UI per broker e destination

### 13.2 Componenti runtime

#### RabbitClient

Responsabilità:

* apertura connessione
* apertura channel AMQP tecnico interno
* dichiarazione exchange/queue/binding se `auto_create = true`
* pubblicazione messaggi
* gestione errori e chiusura risorse

#### DestinationResolver

Responsabilità:

* caricare destination
* verificare coerenza tipo/broker
* restituire config runtime pronta per il publish

#### PublishMessageExecutor

Responsabilità:

* leggere operation
* risolvere payload
* risolvere destination
* costruire proprietà messaggio
* invocare RabbitClient
* tracciare risultato ed errori

## 14. Persistenza ed execution log

Per ogni publish conviene salvare almeno:

* broker id
* destination id
* tipo destination
* exchange effettivo
* routing key effettiva
* payload serializzato o riferimento al payload
* headers
* esito publish
* timestamp
* eventuale errore

Questo è utile per debugging degli scenari e del mock server.

## 15. UX/UI suggerita

### Broker form Rabbit

Campi:

* host
* port
* username
* password
* virtual host
* ssl enabled
* heartbeat
* timeout
* automatic recovery
* client name

### Destination form Rabbit

Scelta tipo:

* Queue
* Route

#### Form Queue

* name
* queue name
* durable
* exclusive
* auto delete
* auto create
* arguments

#### Form Route

* name
* exchange name
* exchange type
* routing key
* queue name opzionale
* binding keys
* durable
* queue durable
* auto create
* arguments

### Mock server operation form

* destination
* payload / payload ref
* payload type
* content type
* headers
* routing key override
* correlation id
* on error

## 16. Scope prima fase

### In scope

* broker type `rabbit`
* destination type `queue`
* destination type `route`
* operation `publish_message`
* publish da mock server
* serializzazione payload `json` e `text`
* supporto headers custom
* auto create exchange/queue/binding
* logging esecuzione

### Fuori scope per ora

* consume/listen da Rabbit
* subscribe continuativa
* UI avanzata per arguments Rabbit specializzati
* gestione ack/nack
* gestione retry policy avanzata
* DLQ wizard
* topology browser Rabbit

## 17. Roadmap successiva

### Fase successiva possibile

* listen/consume da queue Rabbit
* trigger scenario da messaggio Rabbit
* supporto exchange standalone
* supporto binding espliciti
* supporto headers exchange avanzato
* supporto bytes/binary payload completo
* test helpers per request/reply pattern

## 18. Checklist operativa

### Analisi e modello

* [ ] introdurre `rabbit` tra i broker type supportati
* [ ] introdurre destination type `queue`
* [ ] introdurre destination type `route`
* [ ] definire schema persistente broker Rabbit
* [ ] definire schema persistente destination Rabbit
* [ ] definire schema operation `publish_message`
* [ ] definire regole di validazione

### Backend runtime

* [ ] implementare client Rabbit dedicato
* [ ] implementare connessione con parametri broker
* [ ] implementare dichiarazione queue opzionale
* [ ] implementare dichiarazione exchange opzionale
* [ ] implementare binding opzionale
* [ ] implementare publish con headers e properties
* [ ] implementare serializzazione `json`
* [ ] implementare serializzazione `text`
* [ ] implementare gestione errori `fail/warn/ignore`
* [ ] implementare log tecnico publish

### Mock server

* [ ] aggiungere lista destination configurabili
* [ ] aggiungere operation `publish_message`
* [ ] integrare risoluzione `payload_ref`
* [ ] integrare override routing key
* [ ] integrare persistenza risultato operation

### API

* [ ] esporre CRUD broker Rabbit
* [ ] esporre CRUD destination Rabbit
* [ ] esporre schema operation `publish_message`
* [ ] aggiornare endpoint di validazione configurazioni

### UI

* [ ] aggiungere broker Rabbit nel form broker
* [ ] aggiungere form destination Queue
* [ ] aggiungere form destination Route
* [ ] aggiungere selection destination nel mock server
* [ ] aggiungere editor headers publish
* [ ] aggiungere editor payload type
* [ ] aggiungere campi override publish

### Test

* [ ] test unitari validazione broker Rabbit
* [ ] test unitari validazione destination Queue
* [ ] test unitari validazione destination Route
* [ ] test unitari operation `publish_message`
* [ ] test integrazione publish verso Rabbit reale o containerizzato
* [ ] test errore connessione broker
* [ ] test errore destination non trovata
* [ ] test serializzazione payload JSON
* [ ] test override routing key
* [ ] test auto create topology

## 19. Decisione finale raccomandata

Per la prima implementazione adottare questo assetto:

* **Broker type**: `rabbit`
* **Destination types**: `queue`, `route`
* **Mock server operation**: `publish_message`

### Motivazione

Questa soluzione:

* resta coerente con il dominio Quality Flow
* evita l’ambiguità tecnica del termine `channel`
* consente una UX semplice
* è estendibile in futuro senza rompere il modello
* consente di aggiungere in seguito consume/listen e binding espliciti
