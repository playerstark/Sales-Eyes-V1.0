# Sales Eyes

Sales Eyes is an AI-powered prospect research assistant for sales teams. Give it whatever you know about a prospect — a company name, a contact's role, a stray LinkedIn URL — and it builds a research plan, gathers findings from the web, resolves conflicting/duplicate information into a confidence-scored profile, and turns the results into a tailored sales script (SPIN, Challenger, Sandler, or a custom methodology) using DeepSeek AI.

## Features

- **Freeform intake** — type anything you know about a prospect and Sales Eyes turns it into a structured research plan.
- **Automated research pipeline** — web search, page fetching, and deterministic/entity extraction providers collect findings about the company and contact.
- **Prospect Intelligence** — candidate identity resolution, conflict detection, and confidence scoring surface the most reliable facts when sources disagree.
- **Material uploads** — attach product PDFs/Word docs so generated scripts can reference your own materials.
- **Script generation** — pick a sales methodology and generate a customized script from the selected findings.
- **Auth & sessions** — JWT-based accounts so research sessions are private per user.

## Tech Stack

| Layer      | Technology |
|------------|------------|
| Frontend   | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Backend    | FastAPI, SQLAlchemy (async), Pydantic v2 |
| Database   | PostgreSQL 15 |
| AI         | DeepSeek (via configurable OpenAI-compatible endpoint) |
| Research   | DuckDuckGo search, BeautifulSoup/lxml scraping, Wappalyzer, NewsAPI (optional) |
| Documents  | pypdf, python-docx |
| Infra      | Docker Compose |

## Project Structure

```
sales-eyes/
├── backend/
│   └── app/
│       ├── main.py               # FastAPI app, middleware, error handlers
│       ├── core/                 # config, database, security, deps
│       ├── models/                # SQLAlchemy models
│       ├── schemas/               # Pydantic schemas
│       ├── routes/                # auth, research, materials, intelligence
│       └── services/
│           ├── deepseek_service.py
│           ├── research_service.py
│           ├── plan_executor.py
│           ├── painpoint_service.py
│           ├── linkedin_service.py
│           ├── newsapi_service.py
│           └── intelligence/      # orchestrator, identity resolver,
│                                   # conflict detector, confidence scorer,
│                                   # and search/extraction providers
├── frontend/
│   ├── app/                       # Next.js App Router pages
│   │   ├── page.tsx                # prospect intake
│   │   ├── login/, register/       # auth
│   │   ├── dashboard/              # session list
│   │   └── research/[sessionId]/   # plan, findings, and intelligence views
│   └── components/                 # SettingsModal, Intelligence/* UI
├── database/                      # numbered SQL migrations (000_init.sql, ...)
├── docker-compose.yml
└── .env.example
```

## Prerequisites

- Docker and Docker Compose
- A DeepSeek-compatible API key (default config points at `aicredits.in`; you can swap in `api.deepseek.com` directly — see `.env.example`)

## Getting Started

1. **Copy the environment file and fill in secrets**
   ```bash
   cp .env.example .env
   ```
   At minimum set:
   - `JWT_SECRET_KEY` — a long random string
   - `DEEPSEEK_API_KEY` — your API key
   - `POSTGRES_PASSWORD` — change from the default for anything beyond local dev

2. **Start the stack**
   ```bash
   docker-compose up --build
   ```
   This starts Postgres, the FastAPI backend, and the Next.js frontend, and applies the SQL files in `database/` on first boot.

3. **Open the app**
   - Frontend: http://localhost:3000
   - Backend health check: http://localhost:8000/api/health

4. **Create an account** at `/register`, then log in.

## Using Sales Eyes

1. **Enter what you know** about a prospect on the homepage and start research.
2. **Review the generated plan and findings** on the session page; select the findings you want to use.
3. **Check Prospect Intelligence** (candidate cards, conflict panel, confidence scores, evidence timeline) if you need to resolve ambiguous or conflicting data.
4. **Pick a sales methodology** (SPIN, Challenger, Sandler, or custom) and generate a script.
5. **Copy or download** the resulting script.

You can also set your DeepSeek API key at runtime via the settings (gear icon) once logged in, instead of only through `.env`.

## API Overview

All backend routes are mounted under `/api`:

| Prefix | Purpose |
|---|---|
| `/api/auth` | Registration, login, JWT auth |
| `/api/research` | Research sessions, plans, findings, script generation |
| `/api/materials` | Upload/manage product materials (PDF/DOCX) |
| `/api/intelligence` | Prospect intelligence: candidates, conflicts, confidence, evidence |

Interactive API docs are available at `http://localhost:8000/docs` while the backend is running.

## Database

Migrations live in `database/` and run automatically against a fresh Postgres volume:

- `000_init.sql` — base schema (users, sessions, etc.)
- `003_add_materials_support.sql`
- `004_intelligence_schema.sql`
- `005_add_prospect_details.sql`
- `006_add_research_summary.sql`

## Further Documentation

The repo includes deeper design docs for specific subsystems:

- `INTELLIGENCE_ARCHITECTURE.md`, `INTELLIGENCE_DATA_MODEL.md`, `INTELLIGENCE_API_REFERENCE.md`, `INTELLIGENCE_PROVIDERS.md` — the Prospect Intelligence subsystem
- `MATERIAL_UPLOAD_FEATURE.md`, `QUICK_START_MATERIALS.md` — product material uploads
- `QUICKSTART.md` — an earlier end-to-end walkthrough of the research → script flow
- `ARCHITECTURE_NEW.md`, `COMPLETE_IMPLEMENTATION_GUIDE.md` — broader architecture notes
- `PHASE1_COMPLETION.md` … `PHASE5_COMPLETION.md`, `ALL_PHASES_SUMMARY.md`, `CHANGES.md` — build history and changelog

## Troubleshooting

- **"Failed to generate plan"** — confirm `DEEPSEEK_API_KEY` is set and valid, and that the backend can reach the configured `DEEPSEEK_ENDPOINT`.
- **Findings not appearing** — check that the plan generated successfully first; findings populate once the research pipeline runs against the plan.
- **Styling looks off** — rebuild with `docker-compose up --build` so Tailwind picks up changes, and hard-refresh the browser.
- **Settings modal missing** — it only appears once you're logged in and on an authenticated page (not `/`, `/login`, or `/register`).

## Security Notes

This project ships with development defaults (e.g. a placeholder `POSTGRES_PASSWORD` and `JWT_SECRET_KEY` in `.env.example`). Replace all of these before deploying anywhere beyond your own machine, and keep `.env` out of version control.
