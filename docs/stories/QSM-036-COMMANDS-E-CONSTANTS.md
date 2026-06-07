# CONTEXT, CONSTANTS e COMMANDS

Version: 1.0  
Target: Codex implementation  
Language: Python backend

# 1. Technical Overview

## CONTEXT: 
Rappresenta il contesto entro cui avvengono esecuzioni di test, commands e event trigger run.
Si suddivide gerarchicamente come :
- **runEnvelope**: generato da comando run context in api\queue mdi mock server
		{
			"run_id": "uuid",
			"event": {
				"id": "uuid",
				"mock_server_id": "",
				"listener_type": "api|queue",
				"listener_id":"",
				"trigger": {
					"code": "",
					"method": "",
					"queue_code": ""
				},
				"timestamp": "",
				"payload": {},
				"meta": {}
			},
			"constants": {}, <-- costanti in fase di lancio
		}
		Meta possibili:
			Rest API:
				meta.headers
				meta.query
				meta.path_params
			Queue:
				meta.message_attributes
				meta.message_id
- **global**: generato all'esecuzione dall'hook beforeAll della test suite
		{
			"runEnvelope": {} | None,
			"constants":{}
		}
- **local**: generato dall'esecuzione dell'hook before della test suite
		{
			"global":{},
			"constants":{}
		}
- **result_artifacts**:
		{
		}
			
## CONSTANTS:
Le costanti di contesto sono definibili con:
- **name**: sintassi json field 
- **type**: 
    - raw: tipi Python come number, str, dict etc.. ( dobbiamo cercare una nomeclatura tester friendly )
    - json
    - jsonArray è un id di jsonArray esistente 
    - dataset è un id di dataset esistente
    
- **context**: contesto di appartenenza
		runEnvelope
        global
		local
		result

## COMMANDS:
I commands sono entità eseguibili all'interno di determinati context. Sono divisi in famiglie: 
- **actions**: leggono variabili di contesto e inviano messaggi, scrivono tabelle etc.
- **context**: leggono sorgenti e aggiungono costanti al contesto di lavoro
- **asserts**: confrontano costanti di contesto con altre costanti e\o sorgenti di dati
	
### ACTION COMMANDS:
- **sendMessageQueue**: invia i dati contenuti in una costante in una coda.
	parametri:
		- coda SQS
		- template <-- il template per inviare il messaggio 
		- result target <-- costante del result context dove scrivere i risultati
- **saveTable**: salva i dati contenuti in una costante in una tabella interna a Quality Flow.
	parametri:
		- nome tabella
- **dropTable** : elimina una tabella interna di Quality Flow
- **cleanTable** : svuota una tabella interna di Quality Flow 
- **exportDataset**: salva i dati contenuti in una costante in una tabella esterna e l'aggiunge ai dataset presenti su Quality Flow.
	parametri:
	    - route della costante
	    - connessione
		- nome tabella
		- tipologia di export: drop\create, insert\update, append
		- mapping: se insert\update indicare quali elementi del 
		- descrizione data dataset
- **dropDataset**: elimina la tabella collegata al dataset e il dataset stesso
    parametri:
        - dataset id
- **cleanDataset**: svuola la tabella collegata al dataset 
    parametri:
        - dataset id
- **runSuite**: avvia una suite di test
	parametri:
		- id test suite
        - constants: [] <-- array di costanti attuali da salvare nel nuovo runEnvelope
		
### CONTEXT COMMANDS:
- **initConstant**: inizializza e salva una costante con i dati letti da una sorgente dati. Imposta il type in base al tipo sorgente. 
	parametri:
		- target <-- costante su cui sccrivere i dati
		- tipo di sorgente: 
			Raw : stringa, numero, date, datetime, dict
			JsonArray
				id di jsonArray salvato a db 
			SQSQueue
				id della SQSqueue esistente
				retry <-- numero tentativi in caso coda vuota
				wait_time_seconds
				max_messages <-- numero massimo di messaggi che si possono leggere
			Dataset 
				id del dataset
- **deleteConstant**: rimuove una costante 
    parametri:
        - target <-- la costante da salvare
				
### ASSERT:
Gli assert si dividono per il tipo di expect confrontato
- **jsonEquals( expected, actual)**: verifica che expected e actual siano uguali
		expected
			- json 
		actual 
			- costante del contesto
- **jsonEmpty\jsonNotEmpty(actual)**
		actual 
			- costante del contesto
- **jsonContains(expected, actual)**: nell'expected ci sono le properties e rispettivi valori dell'actual
		expected
			- json 
		actual 
			- costante del contesto
- **jsonArrayEquals( expected, actual)**: verifica che expected e actual siano uguali
		expected
			- id di jsonArray presente a db
		actual 
			- costante del contesto
- **jsonArrayEmpty\jsonArrayNotEmpty(actual)**
		actual 
			- costante del contesto
- **jsonArrayContains(expected, actual)**: nell'expected ci sono le properties e rispettivi valori dell'actual
		expected
			- json 
		actual 
			- costante del contesto
		

## SUDDIVISIONE COMMANDS:	

### MOCK SERVER :

- pre-response
	- initConstant
	- jsonEquals
	- jsonEmpty
	- jsonNotEmpty
	- jsonContains
	- jsonArrayEquals
	- jsonArrayEmpty
	- jsonArrayNotEmpty
	- jsonArrayContains

- post-response
	- sendMessageQueue
	- saveTable
	- exportTable
	- saveTable
	- dropTable
	- cleanTable
	- exportDataset
	- dropDataset
	- cleanDataset
	- runSuite	
		

### TEST SUITE:

- HOOKS:	
	- initConstant
	- deleteConstant
	- saveTable
	- dropTable
	- cleanTable
	- exportDataset
	- dropDataset
	- cleanDataset
	
- TEST
    - initConstant
	- sendMessageQueue
	- saveTable
	- exportTable
	- saveTable
	- dropTable
	- cleanTable
	- exportDataset
	- dropDataset
	- cleanDataset
	- jsonEquals
	- jsonEmpty
	- jsonNotEmpty
	- jsonContains
	- jsonArrayEquals
	- jsonArrayEmpty
	- jsonArrayNotEmpty
	- jsonArrayContains
	

## TEST SUITE CONSTANTS:
I fase di costruzione di un test le costanti create devono essere visibili e persistite.
Le costanti si riferiscono sempre ad un contesto: run, global, local, result.

Es:
- l'utente crea una initConstant in beforeAll con name B
- l'utente crea una initConstant in test con name A
- l'utente crea l'assert equals
- il sistema propone A e B come costante 

I context, actions e assert commands dentro hooks\test si riferiscono ai relativi contesti con i seguenti permessi: 
	- hooks: visibilita di contesto run e globale. 
		per beforeAll\afterAll scrittura su global
		per before scrittura su local dopo la creazione
		after lettura da local prima della sua distruzione.  
    - test: visibilità di contesto run, globale e locale. Scrittura solo locale. 

# PLAN

## Stato
- Stato: In corso
- Modalita: hard cut completo
- Compatibilita pubblica legacy `operation*`: rimossa

## Contratto pubblico
- payload suite item: `operations` -> `commands`
- payload mock API: `pre_response_operations` -> `pre_response_commands`
- payload mock API: `post_response_operations` -> `post_response_commands`
- payload mock queue: `operations` -> `commands`
- ogni cfg comando espone:
  - `commandCode`
  - `commandType` con valori `context | action | assert`
- rimossi dal contratto pubblico:
  - `operationType`
  - `set-var`
  - `set-response-status`
  - `set-response-header`
  - `set-response-body`
  - `build-response-from-template`
  - `response_operations`

## Runtime e contesto
- modello runtime annidato:
  - `runEnvelope`
  - `global`
  - `local`
  - `result`
- `runEnvelope`, `global` e `local` espongono blocchi `constants`
- `result` raccoglie artifacts assert e output tecnici dei command
- il mock runtime esegue:
  - `pre_response_commands`
  - response statica/dinamica da config route
  - `post_response_commands`
- il canale `mock.response` viene rimosso

## Refactor commands esistenti
- `data`, `data-from-json-array`, `data-from-db`, `data-from-queue` -> `initConstant`
- `publish` -> `sendMessageQueue`
- `save-internal-db` -> `saveTable`
- `save-external-db` -> `exportDataset`
- `run-suite` -> `runSuite`
- `assert` -> family assert con `commandCode` specifico:
  - `jsonEquals`
  - `jsonEmpty`
  - `jsonNotEmpty`
  - `jsonContains`
  - `jsonArrayEquals`
  - `jsonArrayEmpty`
  - `jsonArrayNotEmpty`
  - `jsonArrayContains`
- `sleep` resta action con naming command

## Commands da aggiungere
- `deleteConstant`
- `dropTable`
- `cleanTable`
- `dropDataset`
- `cleanDataset`

## Persistenza
- rename tabelle e servizi attivi:
  - `suite_item_operations` -> `suite_item_commands`
  - `suite_item_operation_executions` -> `suite_item_command_executions`
  - `ms_api_operations` -> `ms_api_commands`
  - `ms_queue_operations` -> `ms_queue_commands`
- introdurre colonne:
  - `command_code`
  - `command_type`
- eliminare `operation_type`
- mantenere `configuration_json`

## Policy scope
- hook: `context` + `action`
- test: `context` + `action` + `assert`
- mock `pre_response`: `context` + `assert`
- mock `post_response`: solo `action`
- eccezione concordata: `deleteConstant` ammesso anche nei test

## runSuite
- `runSuite` usa `constants: string[]`
- precedence risoluzione costanti:
  - `local.constants`
  - `global.constants`
  - `runEnvelope.constants`

## Verifica
- test migrazione Alembic rename/backfill
- test CRUD suite/mock con soli `commands`
- test resolver nuovo contesto `runEnvelope/global/local/result`
- test `initConstant`, `deleteConstant`, `runSuite.constants`
- test commands action mancanti
- test regressione suite runtime e mock runtime

## Gate qualita
- CodeScene usage: Yes
- tools richiesti prima del ready:
  - `select_codescene_project`
  - `code_health_review`
  - `pre_commit_code_health_safeguard`
