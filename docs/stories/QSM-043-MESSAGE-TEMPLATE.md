# QSM-043 - SendMessageQueue Message Template

## Stato
- Stato: Implementato parziale
- Scope consegnato: DTO/runtime `sendMessageQueue`, UI form base, preview campi, test automatici
- Vincolo architetturale: la preview usata dalla UI deve passare da endpoint API dedicato; la UI non puo importare direttamente `elaborations.services.operations.send_message_template_service`
- Note: `template_id` / `template_params` legacy restano supportati; il nuovo `message_template` ha precedenza quando presente

---

# 📄 QSM – SendMessageQueue: JSON Field Filtering

## 🎯 Obiettivo

Permettere all’utente di utilizzare un template per filtrare il source per `sendMessageQueue` e **decidere quali campi utilizzare** per il payload prima dell’invio.

Questo approccio:

* riduce la dimensione del payload
* evita l’invio di dati sensibili o inutili
* rende il messaggio più controllato e leggibile ([JSONViewerTool][1])

---

## 🧩 UX – Form per comando di tipo sendMessageQueue

### Quando `action = sendMessageQueue`

Mostrare una nuova sezione:

### **Message template (optional)**

Radio toggle 

#### se OFF(default)
 - non viene impostato e utilizzato un template

#### Se ON 
**sezione Message extract Preview e forEach** json + text field per root con validazione

forEach è obbligatorio se Message template attivo e tipo sorgente json\jsonArray, il default è $.
Se source è dataset è non attivo o invisibile 

Formattazione:  
 - $.path -> object\array
**Es path**
  field1.field2.field3
**Es di field semplice** 
  - text <- properties
  - text[*] <- array
**Es di path complesso (matrice)** 
  - field[*].nested[*]

**sezione Message to send preview** template json + preview template

Multiselect con i fields selezionati

Bottoni:
* `add all fields` -> aggiunge tutti i fields  
* `remove all fields` -> rimuove tutti i fields

Field costanti:
  Pulsante add che aggiunge:
    textfield nome | tipo | valore
    selectbox per scelta tipo che può essere : str, number, date, datetime, variabile, function
      textfield se tipo str, number, date, datetime
      selectbox se tipo variabile con variabile di contesto
      selectbox se tipo funcion con `now`, `today`

## Example

### Input

```json
{
  "body":{
    "envelope":{
      "campaign":"west"
    },
    "payload":[
      {
        "id":"xxx",
        "desc": "desc"
      }
    ]
  }
}
```

### Config forEach e template

forEach: "$.body"

fields:
- payload

### Output

```json
{
  "payload":[
      {
        "id":"xxx",
        "desc": "desc"
      }
  ]
}
```
---

## ⚙️ Comportamento runtime

### Flusso `sendMessageQueue` se Message template configurato

#### sorgente json
Dalla sorgente recuperare la porzione a partire da forEach
Se forEach è array la porzione estratta viene divisa in n json
Se forEach è composto la porzione viene esplosa seguendo la concatenazione del path
Es:

**Input**
```json
{
  "payload":[
      {
        "field":"xxx",
        "nested":[
          {
            "field2":"yyy"
          },
          {
            "field2":"zzz" 
          }
        ]
      },
      {
        "field":"aaa",
        "nested":[
          {
            "field2":"bbb"
          },
          {
            "field2":"ccc" 
          }
        ]
      }
  ]
}
```

forEach: "$.payload[*].nested[*]

**Output**
```json
[
  {
  "payload.field":"xxx",
  "field2":"yyy"
  },
  {
  "payload.field":"xxx",
  "field2":"zzz"
  },
  {
  "payload.field":"aaa",
  "field2":"bbb"
  },
  {
  "payload.field":"aaa",
  "field2":"ccc"
  }
]

```

Costruire un json semplice a partire dai fields e costanti configurati
Valorizzare:
  - i fields con i valori del sorgente 
  - le costanti con i valori immessi e le funzioni calcolate

#### sorgente jsonArray
Dalla sorgente recuperare ogni elemento dell'array ed eseguire le stesse operazioni del json

#### sorgente dataset
Dalla sorgente recuperare le righe a chunk e per ognuna delle righe del chunk construire
un json semplice a partire dai fields e costanti configurati
Valorizzare:
  - i fields con i valori del sorgente 
  - le costanti con i valori immessi e le funzioni calcolate

---

## ⚠️ Edge cases

* path inesistente → ignorato (no errore)
* campo già assente → ignorato
* nested non oggetto → ignorato

👉 comportamento resiliente

---


