# GitHub Copilot Instructions (Workspace Standard)

## Single source of truth
Always follow the workspace AI rules from the shared repo:

- ../prompt-alkyra/AGENTS.md

## Overrides
- Respect explicit agent override: @agent:*
- Respect explicit work item override: @work:*

## CodeScene MCP
Always apply CodeScene MCP rules defined in:

- ../prompt-alkyra/RULES/CODESCENE_MCP.md

## Security
Always follow:

- ../prompt-alkyra/RULES/SECURITY.md

## Repo-specific notes
- `quality-flow` mirrors the conventions of `transformation` (FastAPI + Polars + Alembic + SQS + testcontainers).
- The Streamlit UI under `app/ui/` is legacy and is being retired through an incremental **refactor** (not a fidelity migration) whose new FE is `quality-flow-ng-app`. Treat the Streamlit code only as a requirements source. Do not add new features in `app/ui/`; route UI work to `quality-flow-ng-app`.
- Refactor order (section by section): Test suites → Home → Configurations (Brokers & Queues, Database, MockServers) → Datasources (Json, Dataset) → Logs.
- See `AGENT.md` at the repo root for the full repo-specific contract.
- For quality-flow refactor tasks, see `../prompt-alkyra/PROMPTS/03_REFACTOR_QUALITY_FLOW.md`.
