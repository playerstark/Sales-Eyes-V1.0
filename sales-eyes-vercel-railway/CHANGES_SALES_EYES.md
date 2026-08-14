# Sales Eyes — What changed & how to run it

## Redesign: chat-style flow (latest)

The app was redesigned from a multi-page wizard into a single conversational
chat interface, matching this flow directly:

1. Type a prospect description (e.g. `"Sundar Pichai, CEO, Google"`) in one
   box.
2. The AI researches them — real web search, news, and a synthesized
   research report shown as a chat bubble (this replaces the old scattered
   findings grid).
3. It asks you to upload a document about your product, right in the chat
   (drag-drop or file picker).
4. It asks which script type: SPIN, Sandler, or Challenger — tap to choose.
5. It generates and shows the final script, personalized with the
   prospect's name, opening with a hook grounded in the research report,
   and grounded in your uploaded product material. Copy/download buttons
   included.

### What changed to support this

- **New `research_summary` field + `/sessions/{id}/summarize` endpoint.**
  Previously the script-generation prompt was built from a raw list of
  scattered findings. Now there's a synthesis step: DeepSeek condenses all
  findings into one coherent report first (Overview / Recent News /
  Company Context / Notable Hook Opportunities), and *that* report is what
  gets shown to the user and fed into script generation — matching the
  "documents sent through the API" framing from the product spec.
- **`generate_sales_script` now explicitly labels two documents in the
  prompt** — "DOCUMENT 1 — PROSPECT RESEARCH REPORT" and "DOCUMENT 2 —
  PRODUCT / COMPANY MATERIAL" — each with its stated nature and allowed
  use, plus the requested script type. This was verified directly by
  mocking the DeepSeek HTTP call and inspecting the actual outgoing prompt
  (see "Verified by running it" below).
- **Frontend rewritten as one chat page** (`/research/[sessionId]`)
  replacing the old research-progress / style-picker / results wizard.
  The old step pages and now-unused components (`MaterialUpload.tsx`,
  `MaterialsList.tsx`, `PainPointsDisplay.tsx`) were removed.
- **Name-parsing heuristic extended** to handle plain comma-separated
  input (`"Name, Title, Company"`) — the exact format used in the product
  spec's own example. It previously only handled dash-separated
  (`"Name — Title — Company"`) and "at"-separated (`"Name, Title at
  Company"`) forms.
- The separate "Prospect Intelligence" candidate-verification module
  (`/research/[sessionId]/intelligence/...`) is a more elaborate,
  separate feature from an earlier iteration; it still exists in the repo
  but isn't part of the new chat flow and isn't linked from it.

### Known minor limitation

The name-parsing heuristic can occasionally misfire on input that has no
actual name in it (e.g. a title-only description like "VP of Sales at
TechCorp, focuses on enterprise SaaS" can get "VP" mis-parsed as a name).
This is a pre-existing heuristic edge case, not a regression — DeepSeek is
the intended fallback for messy input, but only triggers when the
heuristic finds *nothing*, not when it finds something wrong. Worth
tightening later if it comes up in practice, but low severity since the
common "Name, Title, Company" case now works correctly.

## Verified by actually running it (this session)

- Re-ran the exact spec example end-to-end: `"Sundar Pichai, CEO, Google"`
  → confirmed `prospect_name`, `prospect_title`, `prospect_company` all
  parse correctly via the DB.
- Confirmed `/summarize` is correctly wired (reaches the DeepSeek call
  boundary, fails only on the sandbox's blocked host — same pattern as
  every other DeepSeek call here).
- Mocked the DeepSeek HTTP call to inspect the real prompts sent by both
  `summarize_research` and `generate_sales_script`, and confirmed:
  the summary prompt embeds the parsed name/title/company and raw
  findings correctly; the script prompt correctly prioritizes
  `research_summary` over raw findings when both are present, correctly
  labels both documents with their nature/use, and correctly includes the
  requested methodology (tested with Challenger).
- Full TypeScript check across the whole frontend: zero errors (after
  fixing a real discriminated-union bug — `Omit<Message, "id">` doesn't
  distribute over TS unions, so it silently collapsed the `Message` type
  and would have caused type-check failures in CI/build).
- Full `next build` production build: succeeds cleanly.

## Earlier fixes (previous session)

1. **Real web search for a prospect.** `plan_executor.py` used to just echo
   your typed input back as a "finding." It now runs real DuckDuckGo
   searches (free, no API key) for the person/company, fetches the top
   result's page content where publicly allowed, and creates findings with
   real source links.
2. **Product document upload now actually reads PDFs and Word docs.**
   Previously only `.txt` files were read into `content_text` — PDFs and
   `.docx` uploads were stored but silently ignored by the AI. Added
   `pypdf` and `python-docx` extraction.
3. **Fixed a bug where finding selection never saved.** Checking a finding
   on the research page updated local UI state only; the backend was never
   told, so script generation always ran on an empty finding set. Now the
   selection is persisted to the database and script generation actually
   uses it (falls back to all findings if none are explicitly selected).
4. **Structured prospect name.** Added `prospect_name` / `prospect_company`
   / `prospect_title` fields, parsed automatically from your freeform input
   (regex first, DeepSeek fallback) when the plan is generated. Used to
   personalize the script and target search/news queries.
5. **Framework-distinct script generation.** SPIN, Sandler, and Challenger
   now produce genuinely different script structures (previously all three
   used the same generic hook/pain/solution/CTA template). The opening hook
   is now required to come from a real research finding (news or public web
   result) — the model is instructed to flag it if none is available rather
   than invent one. The uploaded product material is passed in as grounding
   for the value proposition.
6. **Rebranded to Sales Eyes** across the frontend title/header, API title,
   Docker container labels, and package.json. Database user/name/env vars
   were deliberately left as-is (`sales_stalker` / `salesstalker`) since
   they must match your existing `.env` and Postgres volume — renaming
   those would orphan your existing data.

## Required setup steps

**0. Apply the newest migration too** (adds `research_summary`):
```bash
docker exec -i sales_eyes_db psql -U salesstalker -d sales_stalker < database/006_add_research_summary.sql
```

**1. Rebuild the backend image** (new Python deps: `duckduckgo-search`,
`pypdf`, `python-docx`):
```bash
docker compose build backend
```

**2. Apply the new migration** (adds `prospect_name`/`prospect_company`/
`prospect_title` columns):
```bash
docker exec -i sales_eyes_db psql -U salesstalker -d sales_stalker < database/005_add_prospect_details.sql
```
(Container name changed to `sales_eyes_db`; DB name/user are unchanged.)

**3. Restart everything:**
```bash
docker compose up -d
```

## Known limitation

DuckDuckGo search occasionally rate-limits automated queries (you may see
a "web search unavailable" note in a finding if this happens) — this is a
DuckDuckGo-side throttle, not a bug. If it becomes a regular issue, moving
to a self-hosted SearXNG instance or a paid Brave/Bing API key (the code
is already provider-abstracted for this) would remove the rate limit.

## Verified by actually running it

I stood the app up in a sandbox (local Postgres, backend running directly
against your real `.env` keys) and exercised it end-to-end rather than just
reading the code. That surfaced two real bugs the code-review pass missed,
both now fixed:

- **Company field over-captured.** The prospect-name heuristic parser was
  grabbing the rest of the sentence into "company" (e.g. input like `Name —
  Title — Company, based in City. Interested in X.` produced `company =
  "Company, based in City. Interested in X."`). Fixed to stop at the first
  sentence break.
- **Material upload was silently broken.** The `/api/materials/upload`
  route declared `session_id`/`material_type`/`name` as plain (query)
  parameters, but the frontend sends them as multipart form fields —
  FastAPI was rejecting every real upload from the UI with a 422. Fixed by
  declaring them as `Form(...)` fields so they match what the browser
  actually sends.

What I confirmed working, with real requests against your DB and (where
possible) your real API keys:
- Register → login → JWT auth
- Session creation → freeform prospect text → heuristic name/title/company
  parsing (verified correct output for `"Satya Nadella — CEO — Microsoft,
  based in Redmond..."`)
- PDF upload → real text extraction into `content_text` (verified via
  direct DB query, not just a 200 response)
- DOCX upload → same
- Finding selection → persists `is_selected` correctly and is reflected in
  the findings list the style-selection page reads
- `generate-script` route → correctly assembles selected findings +
  uploaded product material + prospect name into the DeepSeek call
- DeepSeek prompt construction (mocked the HTTP call to inspect the actual
  outgoing prompt) → confirmed news/web findings are separated into the
  "hookable" bucket from pain-point findings, product material is included
  verbatim, and SPIN/Sandler/Challenger each produce genuinely different
  instructions rather than one template

**What I could not test in this sandbox:** actual calls to `aicredits.in`
(DeepSeek), `duckduckgo.com` (web search), and `newsapi.org` — this
sandbox's network egress only allows a small allowlist of package-registry
domains, so those three hosts return a hard 403 here regardless of API key
validity. This is a sandbox restriction, not an app bug (confirmed by
checking the deny reason directly). Your Docker environment has normal
internet access, so those calls should go through — but this means the
live DeepSeek research-plan/script generation and the live web-search step
have not been observed succeeding end-to-end; only the code paths up to
and including the outbound HTTP call were verified. Worth doing one real
run-through after `docker compose up` to confirm.

## End-to-end flow to test
1. Log in → paste a prospect description on the home page (e.g. "Satya
   Nadella — CEO — Microsoft") → Start research.
2. Watch the plan execute — findings should include real web/news results
   with source links, not just an echo of what you typed.
3. Upload a PDF or DOCX product one-pager under "Material Upload."
4. Select a few findings → Continue.
5. Pick SPIN, Sandler, or Challenger → Generate Script.
6. Confirm the script addresses the prospect by name, opens with a hook
   tied to a specific research finding, and references your product
   material rather than generic claims.
