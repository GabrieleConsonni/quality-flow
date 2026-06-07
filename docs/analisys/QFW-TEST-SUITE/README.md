# QualityFlow — Test Suites · Mockup bundle

Bundle pensato per **vibe coding** — passa questa cartella (o le sue parti) come contesto a Cursor / Claude Code / Claude API / v0 quando implementi il dominio Test suites in Angular + DevExtreme.

## Contenuto

| File | Cosa è | Come usarlo |
|---|---|---|
| `01-suites-list.png` ... `09-convert-to-custom.png` | 9 screenshot dei mockup (PNG) | Allegali all'AI come reference visivo. Uno per schermata. |
| `QualityFlow — Test Suites · Implementation plan.md` | Piano implementativo completo (modello dati · API · feature module Angular · rollout 6 fasi · risks) | Caricalo come spec text. La maggior parte degli AI tool lo digerisce nativamente. |
| `QualityFlow — Test Suites mockup.html` | Design canvas interattivo con tutti i mockup affiancati (zoom/pan/focus) | Apri in browser per review visiva, oppure per fare screenshot a piena risoluzione |

## Le 9 schermate

1. **Suites list** — Entry point: tabella suite, filtri, kebab actions, snackbar Run now
2. **Suite editor** — Setup/Tests/Teardown verticali, drag handle, schedule chip, run drawer
3. **New test dialog** — Template chooser (Send & Verify / Mock & Assert / Custom)
4. **Test editor — template mode (Send & Verify)** — Form a sinistra + timeline read-only sticky a destra con preview row 0 risolta
5. **Test editor — custom mode** — Step list editabile + pannello Variables/Constants/Run envelope
6. **Step editor dialog** — Kind chooser raggruppato (Producers/Consumers/Assertions/Control) con search
7. **Execution view** — Timeline gerarchica + detail panel con diff JSON
8. **Quick Run drawer** — Live execution drawer (480px) con progress bar
9. **Convert to Custom** — Confirm dialog destructive irreversibile

## Pattern d'uso consigliato per vibe coding

### Cursor / Claude Code (in repo Angular)

1. Crea cartella `docs/design/` in repo
2. Copia dentro il `.md` del piano + tutti i PNG
3. In Cursor, apri il piano e usa `@docs/design/...png` per referenziare gli screenshot quando chiedi codice
4. Comincia dal componente del piano §4.1 "Feature module" — chiedi all'AI di scaffoldare la struttura
5. Per ogni schermata: allega il PNG corrispondente + linka la sezione rilevante del piano (es. §5.1 per `generated-steps-timeline`)

### Claude API / Anthropic Console

1. Sistema prompt: incolla il piano `.md` intero
2. Per ogni richiesta: allega i 1-2 PNG rilevanti come content blocks tipo `image`
3. Chiedi un componente alla volta, riferendoti agli ID del piano (`5.1`, `5.2`, ...)

### v0 / Lovable / altri AI design-to-code

1. Allega 1 PNG alla volta
2. Specifica: "Angular standalone components + DevExtreme widgets per `dx-data-grid`, `dx-popup`, ecc."
3. Nota che l'output sarà tipicamente HTML/React/Tailwind: tradurrai a Angular manualmente

## Per ottenere PNG a risoluzione superiore

Apri `QualityFlow — Test Suites mockup.html` in Chrome/Firefox:
- click su un artboard per entrare in focus mode (overlay fullscreen)
- usa l'estensione **GoFullPage** o **Awesome Screenshot** per catturare il viewport
- oppure DevTools → ⋮ menu → "Capture full size screenshot" su uno specifico artboard

## Rapporto con i documenti originali

Questo bundle è derivato da:
- `SPEC.md` (specifiche funzionali Quality Flow originale)
- `QFW-SUITE-MOCK-REDESIGN.md` (piano redesign UX+BE concordato in chat)
- `QFW-CLAUDE-DESIGN-MOCKUP-BRIEFS.md` (brief mockup originali)

Le decisioni concrete prese in questa iterazione sono consolidate nel piano `.md` (cap. 0 "Snapshot delle decisioni consolidate").
