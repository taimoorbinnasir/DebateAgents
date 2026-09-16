# DebateAgents

A multi-agent debate simulation studying how AI agents with distinct personalities argue, escalate, and (sometimes) radicalize when placed in sustained disagreement with each other.

Six agents — three arguing **PRO**, three arguing **CON** — debate a user-supplied topic over multiple rounds. Each agent has a fixed stance, a distinct reasoning style, and parametric personality traits (extremity, concession probability, rhetorical intensity) that shape how it argues. A neutral moderator evaluates each round. A web research layer lets agents ground their arguments in real sources they find themselves, biased toward their own worldview.

## Research question

Does an extremist agent pull the rest of the group toward its position over time, or does it become isolated? More broadly: how do personality, evidence access, and group dynamics shape the trajectory of a multi-agent disagreement?

## How it works

```
User inputs topic
      ↓
Each agent searches the web with a personality-biased query
      ↓
Sources are chunked, embedded, and stored per-agent (RAG)
      ↓
Agents debate in interleaved PRO/CON turns across N rounds
      ↓
Each agent recalls its own past statements + retrieves relevant sources
      ↓
A moderator evaluates each round (strongest/weakest argument, fallacies, drift)
      ↓
Simulation ends on round limit or conversation convergence
      ↓
A structured analysis report is generated and saved
```

### Agents

| Name | Stance | Reasoning style | Extremity |
|---|---|---|---|
| Aggro | PRO | Populist / aggressive | High |
| Elenchos | PRO | Socratic | Moderate |
| Peitho | PRO | Economist | Moderate |
| Ekstros | CON | Ideologue | High |
| Eleftheria | CON | Libertarian | Moderate |
| Hermes | CON | Evidence-first | Low–moderate |

Each agent is a fictional character in a structured academic debate simulation — this framing matters (see [Design notes](#design-notes)).

## Architecture

- **Backend:** FastAPI + Python. Simulation runs in a background thread; events stream to the frontend via Server-Sent Events (SSE).
- **Frontend:** React (Vite) + Tailwind. Live debate feed, agent extremity cards, collapsible moderator panel, analysis dashboard, and a history page for past runs.
- **Memory:** ChromaDB (local, persistent) with `sentence-transformers` embeddings.
  - **Agent private memory** — scoped per simulation session (fresh each debate)
  - **Agent source memory (RAG)** — scoped per topic (reused across sessions on the same topic, avoids redundant web searches)
- **Web research:** SerpApi + custom HTML extraction, chunked with a recursive chunker and filtered for quality before ingestion.
- **LLM:** Claude Haiku via the Anthropic API, called with isolated context per agent (no shared conversation state between agents at the API level — only the orchestrator-controlled shared transcript).

## Setup

```bash
git clone <repo-url>
cd DebateAgents
pip install -r requirements.txt

cd frontend
npm install
```

Add a `.env` file in the project root:
```
ANTHROPIC_API_KEY=sk-ant-...
SERP_API_KEY=...
```

## Running

```bash
# Terminal 1 — backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

Open `http://localhost:5173`, enter a topic, choose a round count, and start the debate.

## Project structure

```
DebateAgents/
├── shared/
│   ├── agents.py       # agent personalities, parametric traits, system prompt builder
│   ├── config.py        # model config, topic_key hashing
│   ├── memory.py         # ChromaDB memory (agent private + document RAG)
│   ├── chunker.py        # recursive chunking + chunk quality filtering
│   ├── ingest.py          # web search → chunk → embed → store (per agent, per topic)
│   ├── retrieve.py         # source retrieval with distance filtering
│   └── tools.py             # LangChain LLM instance, shared tools
├── Week5/
│   └── Phase2.py         # core simulation loop, agent turns, moderator, stopping conditions
├── backend/
│   ├── main.py            # FastAPI routes
│   ├── manager.py          # simulation state, background thread, SSE event queue
│   └── models.py            # Pydantic schemas
├── frontend/
│   └── src/
│       ├── App.jsx           # live view (feed + agent cards + analysis toggle)
│       ├── pages/HistoryPage.jsx  # past simulation browser
│       ├── components/         # AgentCard, DebateFeed, ModeratorPanel, ReportModal, etc.
│       └── hooks/useSimulation.js  # SSE connection + live state
└── Resources/
    ├── <AgentName>/         # raw web sources each agent found
    └── simulations/          # saved transcripts (.json) + analysis reports (.md)
```

## Design notes

**Why "fictional character" framing matters.** Early versions of this project had agents refuse to argue in character — Claude's safety training reads direct behavioral instructions ("be aggressive," "never concede") as requests to misbehave. Reframing each agent as a fictional participant in an academic debate simulation, with behavior described through parametric traits rather than imperative commands, resolved this without any attempt to bypass safety guardrails. This is documented as the core architectural lesson of the project.

**Why agents use isolated API contexts.** Each agent's turn is a fresh API call with its own system prompt and constructed context — not a shared conversation thread. This prevents one agent's response (or an early refusal, during debugging) from contaminating every subsequent agent's context.

**Why sources are topic-scoped but memory is session-scoped.** Re-running the same topic reuses previously found sources (saves SerpApi calls and embedding time), but each debate run gets a completely fresh memory of what was actually said — so agents don't "remember" arguments from a previous, unrelated run of the same topic.

## To-do

**Week 8 — Flagship extensions**

**Status:** Team Mode backend scaffolding integrated (Parts 1-4 of the original breakdown), but NOT actually running as team mode yet — currently a mislabeled copy of Individual Mode. Real team-mode behavior (brainstorm → presenter selection → single team statement) still needs to be verified/fixed end-to-end. Treat the sub-tasks below as the real remaining work before Team Mode is genuinely done.

- Fix Team Mode's backend loop to actually behave like team mode, not individual mode. Currently run_team_round_loop is producing one statement per agent (6 total) exactly like run_individual_round_loop, rather than one statement per TEAM (2 total) via brainstorm+selection. Verify team_brainstorm() and select_presenter() are actually being called and their output is what gets appended to shared_history — not each agent responding individually and unprompted the way Individual Mode does.
- Fix live frontend updates for Team Mode. Agents/teams are arguing correctly on the backend but the frontend (`TeamMode.jsx`, DebateFeed) isn't rendering the SSE events in real time. Check: is the SSE stream actually connected for team-mode sessions (openStream called correctly in `useSimulation({ mode: "team" })`), are agent_statement events actually being pushed with agent_id: "pro"/"con" as expected, and is DebateFeed receiving/rendering them.
- Rework evaluation metrics for 2-team comparison instead of 6-agent comparison. Extremity chart, position chart, and influence map currently still operate on a 6-way individual-agent basis even for team-mode runs. Decide which metrics remain meaningful with only 2 comparison units:
  - **Extremity chart:** keep, but should show exactly 2 lines ("PRO Team", "CON Team"), not 6
  - **Position chart:** keep, same 2-line treatment
  - **Influence map:** likely not meaningful with only 2 nodes — a 2-node graph reduces to a single bidirectional edge, which isn't worth visualizing as a "map." Consider removing InfluenceMap entirely from Team Mode's Analysis view, or replacing it with a simpler "who influenced whom, and by how much, per round" text/table summary instead
- Fix final report generation for Team Mode. `conclude_simulation` is currently generating the report using Individual Mode's framing (referencing 6 named agents, extremity per individual, etc.) even for team-mode runs. Needs a team-aware report prompt — analyzing 2 teams' position drift and presenter patterns, not 6 agents' individual behavior. **Consider: should the report also comment on presenter selection (which agent got picked to speak each round, and whether that rotated or stayed fixed)?**
- Fix transcript saving for Team Mode. Saved transcript JSON is currently being written in Individual Mode's shape/format regardless of which mode actually ran. Needs to correctly reflect team-mode's actual data: 2-key extremity/position logs, presenter_log, team-level statements — not silently reuse the individual-mode schema.
- Add a mode field to every saved transcript/report, so past runs are correctly tagged as "individual" or "team" at save time (_currently no such field exists, so past runs can't be distinguished after the fact_).
- Update History page to toggle/filter between Individual and Team runs. `HistoryPage.jsx` currently shows all past simulations mixed together with no way to distinguish mode. Add either a toggle (Individual / Team / All) or a badge per list item, using the new mode field from the transcript JSON. Also update `HistoryPage.jsx`'s detail view to correctly render team-mode's data shape (2-line charts, no influence map or a team-appropriate replacement, team-aware report) — same fixes as above, but for viewing past runs, not just live ones.
- See the evaluation criterion for Presenter Selection. Currently, the backend is running the same way as Individual Mode, but only one of the agents with the best dist score is kept (_so it's essentially best-from-3 vs best-from-3 rather than an actual mutli-agent brainstorm_).

<hr>

**Model comparison**

- Compare Haiku vs Sonnet vs Opus on debate quality — run only once the system is feature-complete and stable (after Week 8's flagship extensions are genuinely finished, per the sub-tasks above). Run on shortened simulations (3-4 rounds) to control cost.
- Analyze outputs and determine which model fits which task best

<hr>

**Hosted vector DB migration (pre-deploy requirement)**
- Migrate ChromaDB from local PersistentClient to a hosted solution (Chroma Cloud, Pinecone, or similar) before deploying
- Update shared/memory.py's client initialization accordingly; verify agent memory, source collections, AND team channel collections (new in Week 8) all migrate correctly
- Test that topic-scoped source collections still correctly skip re-ingestion after migration

<hr>

**Week 9 — Automation (with mandatory safety guardrails)**
- Claude Code refactor pass on the codebase
- Batch runner script — must always require explicit confirmation before running, prints estimated cost upfront
- GitHub Actions automation — manual workflow_dispatch trigger ONLY, requires typed confirmation string, NOT a blind cron schedule
- Anthropic Console spending limit must be set BEFORE any automation work begins
- Future research — not scheduled, dedicated deep-dive later
- Design a principled algorithm for measuring inter-agent influence in multi-agent debate. Investigated three approaches during Week 7 (raw embedding similarity, softmax-normalized attribution, LLM-judged influence) — all either reproduce the same unresolved threshold problem or add no information beyond position-drift data. Current InfluenceMap ships with the simpler "engagement-correlated position drift" model for Individual Mode. Note: Team Mode's 2-node structure may make this entire line of investigation moot for that mode specifically — worth revisiting once Team Mode's own metrics are decided.
- Once a better influence algorithm is designed, alter the automation pipeline to incorporate it

<hr>

**Pre-deploy hardening → Deploy**
- Rate limiting (per user/session)
- Hard server-side cap on max_rounds
- Per-user history isolation (anonymous localStorage-based ID, no accounts)
- Deploy — Vercel + Render/Railway

<hr>

**Final research write-up**
- Methodology, findings, and all honest caveats, including:
  - Every problem faced and how it was addressed
  - Individual Mode vs Team Mode as two distinct research questions (personality-driven radicalization vs group consensus/presenter dynamics)
  - Influence metric caveat (engagement-correlated drift, not proven causation) and its likely inapplicability to Team Mode's 2-node structure
  - Source citation caveat (semantic similarity proxy)
  - Retrieval quality is topic-dependent
  - Standing limitation: sentence-embedding cosine similarity produced smooth, non-bimodal distributions across every application tried

## Recently completed
- Round-scoped influence map (Individual Mode)
- PDF export pagination and final-line clipping fixed
- Influence map standalone PNG export
- Comparative analysis — extremity AND position metrics, toggleable
- RAG quality debugging and fix (content filtering, distance threshold calibration, empty-query fallback)
- Source citation verification via cosine similarity
- Generalized agent personas — topic-agnostic, no hardcoded "regulation" framing
- Report section hidden from Analysis tab while still included in PDF export
- Multi-target influence attribution — investigated and deliberately deferred
- Team Mode backend scaffolding — data model, memory scope, brainstorm step, presenter selection logic, and dispatch wrapper all written (Parts 1-4) — integration verified incomplete, see Week 8 sub-tasks above
- Separate routed pages for Individual Mode and Team Mode with shared navbar


## Status

Core individual-mode pipeline (web RAG → 6-agent debate → moderator → analysis report) remains fully functional and validated across multiple topics. Team Mode's backend logic (private brainstorm, presenter selection, team-level memory) and frontend scaffolding (separate routed page, navbar, mode-aware useSimulation hook) have been built, but end-to-end integration is not yet correct: the backend loop is currently behaving like Individual Mode rather than genuine team-based brainstorm-and-present behavior, live frontend updates aren't streaming for team-mode sessions, and the analysis metrics (extremity, position, influence map), final report, and saved transcript are all still using Individual Mode's shape regardless of which mode actually ran. History also doesn't yet distinguish between the two modes. These integration gaps are now broken out as explicit Week 8 sub-tasks and are the next work to complete before moving on to model comparison, automation, or deploy.