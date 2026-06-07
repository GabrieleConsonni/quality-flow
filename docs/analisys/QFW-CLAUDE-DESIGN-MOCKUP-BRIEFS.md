# Quality Flow — Mockup Briefs (Suite & Mock Redesign)

> Brief schermo per schermo da incollare in Claude Design / V0 / Figma AI.
> Una sezione = un mockup. Ogni sezione è autoconclusiva.
> Stile target: Angular Material o equivalente, layout web desktop-first (UI è uno strumento di test interno, non mobile).
> Tono visivo: pulito, denso di informazione ma respirato, no decorazioni gratuite, gerarchia tipografica chiara.

---

## Convenzioni globali (da applicare a tutti gli schermi)

- **Layout:** sidebar sinistra fissa con navigazione (`Home`, `Brokers`, `Datasources`, `Test Suites`, `Mock Servers`, `Schedules`, `Logs`, `Tools`). Header in alto con breadcrumb e azioni globali.
- **Palette:** neutri grigi per superfici, un accento blu per azioni primarie, verde per success/run, rosso per errori, giallo ambra per warning, viola tenue per data-driven.
- **Stati esecuzione (badge/icone):**
  - `idle` — cerchio vuoto grigio
  - `running` — spinner blu
  - `success` — check verde
  - `failed` — x rossa
  - `skipped` — slash grigio
- **Componenti ricorrenti:** card, table con riga espandibile, dialog modal, drawer laterale, tab orizzontali, expander collassabile, breadcrumb.
- **Tipografia:** sans-serif sistema, monospace per JSON/codice, dimensioni 13-14px base, 11px per metadati.
- **Empty states:** illustrazione minimale + frase + CTA primaria.
- **Loading states:** skeleton row, mai spinner full-screen.
- **No emoji decorativi.** Le icone sono lineari (Lucide / Material Symbols Outlined).

---

## Mockup 1 — Suite List

### Scopo
Pagina di ingresso al dominio test. Mostra tutte le suite, permette di crearne una nuova, navigare al Suite Editor, vedere a colpo d'occhio l'esito dell'ultima esecuzione e l'eventuale schedulazione attiva.

### Layout
- Header pagina:
  - Titolo: `Test Suites`
  - Sottotitolo grigio: `Define, run and schedule sequences of tests`
  - Bottone primario in alto a destra: `+ New suite`
  - A fianco, bottone secondario `Schedules` che porta alla pagina schedulazioni (icona orologio).
- Filtro/search bar sopra la tabella:
  - Input search per nome
  - Dropdown filtro stato ultima esecuzione (`Any`, `Success`, `Failed`, `Never run`)
  - Toggle `Only scheduled`
- Tabella suites:
  - Colonne: `Name`, `Tests`, `Last run`, `Status`, `Schedule`, `Actions`
  - `Name`: bold + descrizione in piccolo sotto
  - `Tests`: numero (es. `12`), con badge piccolo viola `+3 data-driven` se presenti test data-driven
  - `Last run`: timestamp relativo (`2 hours ago`) + tooltip con assoluto
  - `Status`: badge esecuzione (success/failed/skipped/never)
  - `Schedule`: chip `Every 15min` se attiva, altrimenti `—` grigio
  - `Actions`: kebab menu (`Run now`, `Edit`, `Duplicate`, `Delete`)
- Riga è cliccabile interamente → naviga al Suite Editor.

### Stati
- Empty state: illustrazione di una checklist, testo `No test suites yet. Create one to start verifying your flows.`, CTA `+ New suite`.
- Loading: skeleton di 5 righe.
- Riga in esecuzione: spinner accanto al nome + bordo sinistro blu animato.

### Note interazione
- Cliccando `Run now` da kebab: snackbar in basso `Suite "X" is running… [View]` con link alla execution view.
- Hover sulla riga: bg leggermente più scuro, mostra il chevron destro.

---

## Mockup 2 — Suite Editor (schermo principale)

### Scopo
Schermo dove si compone la suite: setup, lista test, teardown. Run controls in alto. Niente più pagina separata "Advanced suite settings".

### Layout
- Header pagina:
  - Breadcrumb: `Test Suites / <Suite name>`
  - Titolo editabile inline (click per editare)
  - Descrizione editabile inline sotto
  - Toolbar destra:
    - Bottone secondario `Execution history` (apre drawer)
    - Bottone secondario `Schedule` (icona orologio, apre dialog schedulazione)
    - Bottone primario `▶ Run suite`
    - Kebab: `Duplicate`, `Export`, `Delete suite`

- Corpo, dall'alto al basso:

  **Sezione `Setup` (expander, collassato di default se vuoto):**
  - Header: `⚙ Setup` + sottotitolo grigio `Runs once before all tests` + chip `0 steps` o `3 steps`
  - Contenuto espanso: lista step con drag handle, ogni step mostra titolo (`sendMessageQueue`, `setVariable`, etc.) + sintesi 1 riga di config; bottone `+ Add step` in fondo.
  - Hover step: x rossa per delete, freccia drag.

  **Sezione `Tests` (sempre espansa, è il core):**
  - Header: `Tests` + counter `(7)` + a destra bottone `+ Add test`
  - Lista verticale di card test, drag-and-drop riordinabile:
    - Ogni card test:
      - Riga 1: icona template (lucchetto per send_verify, target per mock_assert, terminale per custom) + nome test (bold) + chip template kind
      - Riga 2: descrizione 1 riga grigia troncata
      - Riga 3 (metadata): chip data-driven se ON (`🔁 50 rows from customers`), badge esito ultima esecuzione (success/failed/idle), durata
      - Action a destra: bottone `▶ Run` piccolo + kebab (`Edit`, `Duplicate`, `Convert to custom`, `Delete`)
    - Click sulla card → naviga al Test Editor di quel test
  - Empty state: card tratteggiata centrata `No tests yet. Add your first test.` con CTA `+ Add test`.

  **Sezione `Teardown` (expander, collassato di default se vuoto):**
  - Stesso pattern di `Setup`.
  - Nota informativa piccola: `Teardown runs even if tests fail`.

### Drawer esecuzione (laterale destro, on demand)
- Apre da `Execution history` o auto da `Run suite`.
- Header drawer: `Execution #324 — Running 3/7 tests`
- Progress bar in cima.
- Lista timeline: setup → test1 → test2 → … → teardown, ognuno con stato live e durata.
- Click su elemento timeline: espande log step interni di quel test.
- In fondo: bottone `Open full execution view` (porta a schermo dedicato §6).

### Note interazione
- Drag-and-drop: ogni elemento ha handle a sinistra, hint visuale durante drag (riga con bordo blu).
- `+ Add test` apre Mockup 3 (dialog template chooser).
- `+ Add step` (in setup/teardown) apre Mockup 5 (step editor) direttamente, senza template chooser perché qui non si scelgono template, è custom puro.

---

## Mockup 3 — New Test Dialog (Template chooser)

### Scopo
Dialog modale che si apre da `+ Add test`. L'utente sceglie un template tra 3 card. È il momento più importante: deve essere chiarissimo cosa fa ogni template.

### Layout
- Dialog modale, larghezza ~720px, max-height 80vh.
- Titolo: `New test`
- Sottotitolo grigio: `Choose a template to start. You can convert to a custom test later.`
- Tre card affiancate (responsive: 3 col → 1 col su mobile), ognuna stessa altezza:

  **Card 1 — Send & Verify**
  - Icona grande in alto: freccia che esce + check
  - Titolo: `Send & Verify`
  - Una frase: `Send a message to a queue and verify the side effects.`
  - Bullet list step preview:
    - `1. Send message to a queue`
    - `2. Wait`
    - `3. Assert on database or queue`
  - Footer card: chip neutro `Most common`

  **Card 2 — Mock & Assert**
  - Icona: target con onda
  - Titolo: `Mock & Assert`
  - Frase: `Verify the side effects after an external system calls your mock.`
  - Bullet:
    - `1. Wait for the trigger`
    - `2. Read the side effect (queue or database)`
    - `3. Assert the result`
  - Footer: chip neutro `Mock-driven flows`

  **Card 3 — Custom**
  - Icona: terminale / sliders
  - Titolo: `Custom`
  - Frase: `Build the test step-by-step. Full control over commands and variables.`
  - Bullet:
    - `Empty step list`
    - `Choose any commands`
    - `Manage variables and scopes`
  - Footer: chip ambra `Advanced`

- Card hoverable (bordo blu su hover).
- Card selezionata ha bordo blu pieno + bg lievemente blu.

- Footer dialog:
  - Sinistra: link testo `Learn about templates →` (apre docs)
  - Destra: bottone secondario `Cancel`, bottone primario `Continue` (disabilitato finché non si seleziona una card)

### Note interazione
- Click su card = seleziona + abilita Continue.
- Doppio click su card = seleziona + Continue automatico.
- `Continue` chiude il dialog e apre Mockup 4 (Test Editor) con il template scelto.

---

## Mockup 4 — Test Editor (modalità Template)

### Scopo
Schermo dove si configura un test usando un template. È il flusso normale (90% dei casi). Form chiaro in alto, timeline read-only sotto.

### Layout
- Header pagina:
  - Breadcrumb: `Test Suites / <Suite> / <Test name>`
  - Titolo editabile inline + chip template kind (`Send & Verify`)
  - Sottotitolo: descrizione editabile
  - Toolbar destra:
    - Toggle `Advanced` (disabilitato per template, attivabile solo da `Convert to custom` — vedi sotto)
    - Bottone secondario `▶ Run test`
    - Kebab: `Duplicate`, `Convert to custom`, `Delete`

- Corpo a 2 colonne (60/40):

  **Colonna sinistra (60%) — Form configurazione**

  Esempio per `Send & Verify`:
  - Sezione `Send`:
    - Field `Queue` — dropdown tipologia broker → poi dropdown queue
    - Field `Payload` — switch radio `Inline JSON` / `From JSON Array datasource` / `From dataset`
      - Se Inline: editor JSON con syntax highlight, validazione live, hint inline `Use ${row.column} for data-driven`
      - Se Datasource: dropdown selezione
    - Field `Wait after send` — input numerico ms con preset chip `100ms`, `500ms`, `1s`, `5s`
  - Sezione `Verify`:
    - Lista verticale di assert blocks, drag-and-drop riordinabili:
      - Per ogni assert:
        - Riga compatta: dropdown target (`Queue`/`Database`/`None`), poi campo dipendente (queue selector o query editor), operator dropdown (`equals`, `contains`, `matches schema`, `exists`), expected value editor
        - Hover: bottone x per remove
      - Bottone `+ Add assertion` in fondo (tratteggiato)
    - Empty state se nessun assert: blocco grigio chiaro `No assertions. Test will only check that send succeeds.`

  - Sezione `Iteration` (sempre presente, indipendente dal template):
    - Toggle `Run for each row of dataset`
    - Se ON: dropdown dataset + preview piccola `50 rows from customers`
    - Hint inline: `Refer to row values as ${row.<column>} in payload, queries or expected values.`
    - Warning se rows > 1000: `⚠ This will run 1500 times. Consider limiting the dataset.`

  **Colonna destra (40%) — Timeline read-only + utility**

  - Card `Generated steps` (sticky):
    - Titolo + sottotitolo: `These are the actual commands that will run. Read-only in template mode.`
    - Lista verticale step generati (basata su template_config corrente, refresh live):
      - Step 1: icona send + titolo `sendMessageQueue` + sintesi config (queue name, payload preview)
      - Step 2: icona attesa + titolo `wait 500ms`
      - Step 3+: icone assert + titolo `assert exists on queue X`
    - Ogni step ha sfondo grigio chiaro, no actions (read-only).
    - In fondo, link `Convert to custom to edit steps directly →`.

  - Card `Last execution` (se presente):
    - Status, durata, timestamp, link `View details`.

### Stati speciali
- Test data-driven con preview riga: pulsante piccolo `Preview with row 0` apre dialog con la prima riga del dataset e mostra la timeline con valori risolti (utile per debug).

### Note interazione
- Save automatico al blur dei field, con indicatore piccolo `Saved ✓` in alto a destra.
- `Convert to custom` apre confirm dialog: `This will copy the current generated steps as editable. You can't go back. Continue?`. Conferma → entra in Mockup 5 (Test Editor custom).

---

## Mockup 5 — Test Editor (modalità Custom / Advanced)

### Scopo
Schermo per utenti avanzati. Step editabili, scope variabili visibili. Reaching qui solo via `Convert to custom` o creando un test `Custom` da zero.

### Layout
- Header come Mockup 4, ma chip template = `Custom`. Toggle `Advanced` attivo e ON di default per i Custom.

- Corpo a 2 colonne (70/30):

  **Colonna sinistra (70%) — Step list editabile**
  - Toolbar:
    - Bottone primario `+ Add step` (apre Mockup 6 — Step Editor)
    - Bottone secondario `+ Add source` (apre dialog dedicato per dataset/jsonArray batch)
    - Toggle `Run for each row` (stesso comportamento di Mockup 4)
  - Lista step:
    - Ogni step è una card:
      - Drag handle a sinistra
      - Icona kind step (send, set variable, assert, query, etc.)
      - Titolo step + sottotitolo con sintesi config
      - Chip `produces: <constantName>` se lo step ha `resultConstant`
      - Action: edit (matita) → riapre Step Editor; remove (x)
    - Tra step, sottile separatore con freccia che indica flusso.
  - Sezione collassata `Sources` (se presenti): lista dataset/jsonArray batch, sola lettura inline + edit dialog.

  **Colonna destra (30%) — Pannello Variables & Scope**
  - Tabs orizzontali in cima: `Variables`, `Constants`, `Run envelope`
  - Tab `Variables`:
    - Lista variabili dichiarate via `setVariable` negli step, con scope (`local`/`global`) e tipo (`value`/`json`/`function`).
    - Read-only qui: per editare si va sullo step `setVariable`.
  - Tab `Constants`:
    - Lista delle `command_constant_definitions` accessibili dalla suite, con definitionId e descrizione.
  - Tab `Run envelope`:
    - Mostra la struttura dell'envelope a runtime (`trigger.type`, `trigger.metadata`, `global`, `local`, `result.constants`) come tree read-only con annotazioni.

### Note interazione
- Reorder step via drag.
- Tasto Esc o click fuori chiude dialog step editor senza salvare.
- Le sources non sono mischiate ai step (rimangono in sezione separata) per non rompere la semantica dichiarativa/eseguibile.

---

## Mockup 6 — Step Editor Dialog

### Scopo
Dialog modale unico per creare/editare uno step (command). Si apre da `+ Add step` o dall'icona matita su uno step esistente. Forma adattiva in base allo step kind selezionato.

### Layout
- Dialog modale, larghezza ~640px.
- Header:
  - Titolo: `New step` o `Edit step: <kind>`
  - Bottone close (x) in alto a destra.

- Step 1 (solo in creazione): scelta del kind.
  - Grid di tile selezionabili, raggruppati per categoria:
    - **Producers** (producono valori): `setVariable`, `query database`, `receiveMessage`, `loadDataset`
    - **Consumers** (effettuano azioni): `sendMessageQueue`, `saveTable`, `exportDataset`, `runSuite`
    - **Assertions**: `assertEquals`, `assertContains`, `assertMatchesSchema`, `assertExists`
    - **Control**: `wait`, `deleteVariable`
  - Ogni tile: icona, nome, micro-descrizione 1 riga.
  - Click → passa a step 2.

- Step 2: form configurazione kind-specific.
  - Esempio per `sendMessageQueue`:
    - `Queue` (selector cascading broker→queue)
    - `Payload` (radio: inline JSON / source ref / runtime value)
    - Se `runtime value`: dropdown variabili disponibili nello scope
    - Optional: `Result constant name` (per riusare l'output altrove)
  - Esempio per `assertEquals`:
    - `Actual` (radio: runtime value / source ref)
    - `Expected` (radio: literal / runtime value / constant ref / built-in `$now`/`$today`)
  - Esempio per `setVariable`:
    - `Name` (input string)
    - `Type` (radio: value / json / function)
    - Se `function`: editor con autocompletion basic (sintassi documentata)
  - Esempio per `runSuite`:
    - `Suite` (dropdown delle suite esistenti)
    - Note avviso: `Running a suite from inside another suite can create complex execution trees.`

- Footer dialog:
  - Sinistra: link `Step reference docs →`
  - Destra: bottone secondario `Cancel`, bottone primario `Add step` (o `Save changes`)
  - Validazione live: bottone disabilitato finché form non è valido, errori inline sotto i field.

### Note interazione
- In edit, step 1 è skippato (kind già scelto, non modificabile, solo "Change kind" come azione secondaria che resetta il form con conferma).
- Se l'utente apre da editor `Custom` di un test in modalità avanzata, vede tutti i kind. In `setup`/`teardown`, alcuni kind non avrebbero senso (es. `runSuite` in setup di una suite stessa) — filtrare o warning.

---

## Mockup 7 — Mock Server Endpoint Editor (con behavior selector)

### Scopo
Schermo o drawer per configurare un endpoint API mock. Il pezzo nuovo è il selettore "When called, do…".

### Layout
- Schermo `Mock Server Editor` esistente: lista API a sinistra, dettaglio a destra. Qui specifichiamo il pannello dettaglio.

- Pannello dettaglio (colonna principale):
  - Header endpoint:
    - Riga 1: `Method` (chip colorato: GET verde, POST blu, ecc.) + path (monospace)
    - Riga 2: `Description` editabile
  - Sezione `Request matching`:
    - Method dropdown
    - Path input (con hint `Templated paths like /orders/{id} match literally`)
    - Optional: header/query matching
  - Sezione `Response`:
    - Status code input (default 200)
    - Headers (key/value table)
    - Body editor JSON con preview
  - **Sezione `Behavior` (NUOVA, prominente):**
    - Titolo sezione: `When this endpoint is called`
    - 3 radio card grandi affiancate:

      **Card A — Reply only**
      - Icona: freccia di ritorno
      - Titolo: `Reply only`
      - Descrizione: `Return the response above. No side effects.`
      - Selezionata di default.

      **Card B — Reply and run suite**
      - Icona: freccia di ritorno + play
      - Titolo: `Reply and run suite`
      - Descrizione: `Return the response, then trigger a test suite in background.`
      - Quando selezionata, mostra inline:
        - Field `Suite to run` — dropdown suite con search
        - Hint: `Suite will receive trigger info in runEnvelope.trigger`
        - Link `View linked suite →`

      **Card C — Advanced**
      - Icona: sliders
      - Titolo: `Advanced`
      - Descrizione: `Configure pre-response and post-response commands manually.`
      - Chip ambra `Power user`
      - Quando selezionata, mostra sotto la card:
        - Sezione expander `Pre-response commands` (sync, no side effects) — lista step come Mockup 5 ridotto
        - Sezione expander `Post-response commands` (async) — stessa cosa
        - Tutto editabile via Step Editor (Mockup 6)

  - Footer:
    - Bottone secondario `Test endpoint` (apre dialog con request builder per provare il mock)
    - Bottone primario `Save`

### Stati
- Conversion hint: se l'endpoint era in `Advanced` con pipeline semplice (es. solo 1 `runSuite` in post), badge informativo in alto: `This pipeline can be simplified. [Switch to Reply and run suite]`.
- Conversion safety: passare da `Advanced` a `Reply only`/`Reply and run suite` mostra dialog conferma con cosa verrà perso.

### Note interazione
- Il behavior selector è la decisione principale dell'utente, deve dominare visivamente la sezione.
- Le 3 card sono mutuamente esclusive (radio), bordo blu pieno sulla selezionata, bordo grigio sulle altre.

---

## Mockup 8 — Mock Server Queue Binding Editor

### Scopo
Pannello per configurare un binding queue mock. Stesso pattern di Mockup 7 ma con behavior diversi.

### Layout
- Quasi identico a Mockup 7 ma:
  - Niente sezione `Response` (le queue non rispondono).
  - Sezione `Source queue` con selector queue da ascoltare.
  - **Sezione `Behavior`:**
    - Card A — `Ack only`: `Receive and acknowledge the message. No side effects.`
    - Card B — `Ack and run suite`: `Acknowledge, then trigger a test suite with the message in trigger metadata.`
    - Card C — `Advanced`: pipeline command come oggi.
  - Nota in fondo: `ACK is always performed, even if commands fail.`

---

## Mockup 9 — Execution View / Debug

### Scopo
Schermo dedicato per vedere l'esito di un'esecuzione suite. Timeline gerarchica, log live, variabili runtime, supporto a esecuzioni data-driven (parent/child).

### Layout
- Header pagina:
  - Breadcrumb: `Test Suites / <Suite> / Execution #324`
  - Titolo: `Execution #324`
  - Status badge grande (Running / Success / Failed / Skipped)
  - Metadata riga: durata, started at, trigger (`Manual` / `Schedule` / `Mock API: POST /orders`), executor
  - Toolbar destra: `Re-run`, `Export logs`, `Open suite`

- Corpo a 2 colonne (60/40):

  **Colonna sinistra (60%) — Timeline gerarchica**
  - Tree view verticale:
    ```
    ▼ ⚙ Setup                              [✓ 120ms]
       └ sendMessageQueue                  [✓ 80ms]
       └ setVariable token                 [✓ 5ms]
    ▼ ▶ Test: send customer event          [✓ 5.2s]   🔁 50/50 rows
       ▶ Iteration #0 (id=c001)            [✓ 102ms]
       ▶ Iteration #1 (id=c002)            [✓ 98ms]
       ...
    ▼ ▶ Test: verify ack received          [✗ 1.8s]
       └ wait 500ms                        [✓]
       └ receiveMessage from ack-queue     [✓]
       └ assertEquals                      [✗ Expected ... Got ...]
    ▼ ⚙ Teardown                           [✓ 50ms]
       └ deleteVariable token              [✓]
    ```
  - Ogni nodo:
    - Icona stato (check/x/spinner/idle)
    - Titolo
    - Durata in stile mono a destra
    - Chevron expand/collapse
    - Click → seleziona e mostra dettagli a destra
  - Test data-driven: nodo padre con `🔁 N/M rows` chip viola, child sono iterazioni numerate; un'iterazione fallita appare in rosso senza far fallire automaticamente le altre (configurabile in futuro, per ora documentare comportamento attuale).

  **Colonna destra (40%) — Dettaglio nodo selezionato**
  - Card `Step details`:
    - Kind, status, durata
    - Config snapshot (read-only, JSON)
  - Card `Inputs` (variabili e source usati):
    - Lista chiave/valore
  - Card `Output`:
    - Output dello step (per producer); per assert: `actual` vs `expected` con diff visivo.
  - Card `Logs`:
    - Lista log timestampati di quel step.
  - Card `Run envelope` (collassata):
    - Snapshot del runEnvelope al momento dello step.

- Stream live (se in running):
  - Connessione SSE, badge `Live` lampeggiante in header.
  - Auto-scroll della timeline al nodo corrente.
  - Pausa auto-scroll se l'utente scrolla manualmente, mostra pill `Resume live`.

### Note interazione
- Tasto `f` filtra solo i nodi falliti.
- Tasto `c` collassa tutti i nodi.
- Click su iterazione data-driven mostra a destra anche `row_snapshot` (la riga dataset usata).

---

## Mockup 10 — Convert to Custom — Confirm Dialog

### Scopo
Dialog di conferma critico. La conversione è irreversibile.

### Layout
- Dialog modale piccolo (~420px).
- Icona warning (triangolo ambra) grande.
- Titolo: `Convert to custom test?`
- Body:
  > This will replace the template form with the editable step list.
  >
  > **You won't be able to switch back to template mode.**
  >
  > Your current configuration will be copied as the starting point.
- Lista informativa:
  - `✓ Your steps will be preserved`
  - `✓ Data-driven setting will be preserved`
  - `✗ Template form will be removed`
- Footer:
  - Bottone secondario `Cancel`
  - Bottone primario destructive (rosso ambra) `Convert to custom`

---

## Mockup 11 — Run Confirmation / Quick Run Drawer

### Scopo
Quando si preme `Run suite` o `Run test`, un drawer compare a destra con start immediato e progress live. Niente full page reload.

### Layout
- Drawer laterale destro, larghezza ~480px, overlay trasparente sul resto.
- Header: `Running: <Suite/Test name>` + status + bottone close.
- Progress bar in cima (se applicabile, per suite).
- Lista compatta esecuzione live (versione ridotta di Mockup 9 timeline).
- Footer: `Open full execution view →` (link a Mockup 9).
- Su completion: il drawer resta aperto con summary, l'utente può chiudere o aprire vista completa.

---

## Mockup 12 — Empty / First Time Suite Creation Wizard (opzionale, post-MVP)

### Scopo
Per chi crea la prima suite mai: micro-wizard a 3 step che produce una suite con 1 test già configurato.

### Layout
- Modal full-screen o dialog grande.
- Step 1: `Name your suite` — input nome + descrizione.
- Step 2: `Pick a starting template` — stesso pattern di Mockup 3.
- Step 3: `Configure your first test` — form ridotto del template (queue + payload + 1 assert) con valori suggeriti.
- Footer wizard: `Back` / `Next` / `Create suite`.

Skip totale via link `Skip and start empty →`.

---

## Note finali per il tool di design

- **Coerenza:** tutti i mockup condividono header, sidebar, palette, tipografia. Il tool deve generarli come parte di un design system coerente, non schermi sciolti.
- **Densità:** UI desktop interna, l'utente sa cosa fa. Niente over-explanation. Le hint inline sono brevi.
- **Accessibilità:** focus visibile, contrasto AA, label esplicite sui field, support tastiera (Esc chiude dialog, Enter conferma quando ovvio).
- **Responsive:** desktop-first. Da 1024px in giù collassa la sidebar a icone, le 2 colonne diventano 1 colonna scrollabile.
- **Animazioni:** sobrie. Solo transizioni 150-200ms su hover/expand/drawer. Niente bouncing, niente parallax.

## Schermi NON inclusi (intenzionalmente)
- Login / autenticazione (esiste già).
- Configurazione brokers, datasource, database connections (fuori scope di questa rifattorizzazione).
- Schedules editor (esiste già, basta linkarlo).
- Logs page (esiste già).

## Ordine di consegna suggerito al designer
1. Mockup 2 (Suite Editor) e Mockup 3 (Template Chooser) — il cuore del nuovo flusso
2. Mockup 4 (Test Editor template mode) — l'esperienza più frequente
3. Mockup 7 (Mock Endpoint Editor) — semplificazione mock
4. Mockup 9 (Execution View) — debug e fiducia nel sistema
5. Mockup 1 (Suite List) — ingresso al dominio
6. Mockup 5, 6, 8, 10, 11 — supporto avanzato
7. Mockup 12 — onboarding (post-MVP)
