# QSM - API Commands Input References

## Stato
- Stato: Proposed
- Area: Backend FastAPI + UI Streamlit + runtime commands
- Scope: command di tipo API con input guidati e risoluzione unificata dei valori (inclusa authentication)

---

# 1. Obiettivo

Introdurre nei command di tipo API la possibilità di valorizzare:

- query parameters
- headers
- path parameters
- request body
- authentication

usando in modo guidato una delle seguenti sorgenti:

- literal inline
- variabili runtime del test
- built-in runtime functions
- data sources `jsonArray`
- data sources `dataset`

L’obiettivo è evitare resolver raw scritti a mano dall’utente e mantenere coerenza con il modello Quality Flow basato su:

- runtime context annidato `runEnvelope / global / local / result`
- data sources dichiarative separate dai valori runtime
- variabili selezionabili in modo guidato tramite reference stabili

---

# 2. Principi di design

## 2.1 Nessun resolver raw lato UI
L’utente non deve mai scrivere sintassi come:
- `$.local.constants.myVar`

## 2.2 Dataset e jsonArray non sono variabili runtime
Sono `sources` dichiarative e vengono materializzate solo a runtime.

## 2.3 Un solo meccanismo di risoluzione
Tutti gli input (inclusa auth) passano da un unico resolver.

## 2.4 Auth non è un caso speciale
L’autenticazione è trattata come:
> un insieme strutturato di parametri HTTP (header/query)

---

# 3. Modello concettuale

## 3.1 Distinzione tra valore finale e reference

Ogni valore è definito tramite una `reference`:

```json
{
  "kind": "literal | runtime_value | source | source_field | built_in"
}