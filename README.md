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

### Week 8 — Flagship extensions
- [ ] **Team brainstorm + presenter selection** *(the big one)* — teams privately brainstorm before speaking, evaluate their own arguments, elect a presenter each round based on argumentative strength; presenter can rotate. Kept as a **separate debate mode** alongside individual mode, not a replacement — studies group consensus vs individual radicalization as distinct research questions.
- [ ] Dynamic agent count — configurable at runtime instead of hardcoded 3v3
- [ ] Mid-debate topic injection — moderator introduces a new fact or event mid-simulation
- [ ] Interactive user participation mode — user becomes an actual debater with free-text input, agents respond to the user's specific arguments, continues until user types "quit" or similar

### Model comparison
- [ ] Compare Haiku vs Sonnet vs Opus on debate quality — run only once the system is feature-complete and stable (after Week 8's flagship extensions), so results reflect the final architecture. Run on shortened simulations (3-4 rounds) to control cost.
- [ ] Analyze outputs and determine which model fits which task best (e.g. agent responses vs moderator summaries vs final report generation may not all need the same model tier)

### Hosted vector DB migration (pre-deploy requirement)
- [ ] Migrate ChromaDB from local `PersistentClient` to a hosted solution (Chroma Cloud, Pinecone, or similar) before deploying — Render/Railway's ephemeral disk wipes local storage on every redeploy or restart, so local persistence won't survive in production
- [ ] Update `shared/memory.py`'s client initialization accordingly; verify agent memory and source collections both migrate correctly
- [ ] Test that topic-scoped source collections still correctly skip re-ingestion after migration (verify the "already ingested" check still works against the hosted DB)

### Week 9 — Automation (with mandatory safety guardrails)
- [ ] Claude Code refactor pass on the codebase — done here, after the flagship architecture is finalized, so refactoring isn't wasted on code that's about to change
- [ ] Batch runner script — multiple simulations, different seeds, comparative output. **Must always require explicit confirmation before running** (prints estimated cost upfront, waits for typed "yes"). Never runs unbounded or unattended.
- [ ] GitHub Actions automation — **manual `workflow_dispatch` trigger ONLY, requiring a typed confirmation string.** NOT a blind `schedule:` cron job. If genuine unattended scheduling is ever added later, it must include a hard daily run-count cap checked before any API call fires, so a bug can't silently trigger unlimited runs overnight.
- [ ] **Anthropic Console spending limit must be set BEFORE any automation work begins** — the real backstop against runaway cost regardless of code-level bugs. Non-negotiable prerequisite, not a nice-to-have.

### Future research — not scheduled, dedicated deep-dive later
- [ ] **Design a principled algorithm for measuring inter-agent influence** in multi-agent debate. Investigated three approaches during Week 7 (raw embedding similarity for multi-target attribution, softmax-normalized relative attribution, LLM-judged influence estimation) — all either reproduce the same unresolved absolute-threshold problem or add no information beyond existing position-drift data. Requires original methodological work, not a quick fix. Current `InfluenceMap` ships with the simpler, defensible "engagement-correlated position drift" model in the meantime (single-target-per-turn, accumulated across rounds, round-scoped) — relabeled in UI and write-up as "engagement-correlated influence," not "influence," to avoid overclaiming causation. Key finding: reply-to-reply and reply-to-source cosine similarity consistently produces smooth, uninformative distributions with no natural threshold across every attempt this project has made (RAG retrieval, source citation verification, and influence attribution all hit this same wall) — worth treating as a standing methodological limitation of sentence-embedding similarity for this class of problem.
- [ ] Once a better influence algorithm is designed, alter the automation pipeline (batch runner, GitHub Actions) to incorporate it into future runs

### Pre-deploy hardening → Deploy
- [ ] Rate limiting (per user/session)
- [ ] Hard server-side cap on max_rounds regardless of frontend input
- [ ] Per-user history isolation (anonymous localStorage-based ID, no accounts)
- [ ] Deploy — Vercel (frontend) + Render/Railway (backend), or equivalent alternatives

### Final research write-up
- [ ] Methodology, findings, and all the honest caveats built up throughout the project, including:
  - Every problem faced and how it was addressed (RAG retrieval debugging, source citation verification, the influence-algorithm investigation and its deliberate deferral)
  - What was built vs what was deliberately left as future work, and why
  - Influence metric caveat: engagement-correlated drift, not proven causation
  - Source citation caveat: semantic similarity proxy, not confirmed derivation
  - Retrieval quality is topic-dependent — casual/low-coverage topics may yield weaker source grounding than well-documented policy topics
  - Standing limitation: sentence-embedding cosine similarity produced smooth, non-bimodal distributions across every application tried in this project — genuinely informative thresholds could not be derived from the data itself in any of these cases

### Recently completed
- [x] Round-scoped influence map — can view influence per individual round or cumulative across the whole debate
- [x] PDF export pagination fixed — content no longer duplicates across pages; whitespace-aware page-break detection added
- [x] Influence map standalone PNG export — legible node labels drawn directly on canvas, white background fix for readability, filename reflects active round filter
- [x] Comparative analysis — extremity AND position metrics now both available via toggle in ComparisonView
- [x] **RAG quality debugging and fix** — diagnosed and resolved zero-retrieval bug: strengthened content filtering, calibrated distance threshold from real measured data, fixed round-1 empty-query fallback, cleared and re-ingested stale collections
- [x] **Source citation verification via cosine similarity** — implemented and validated; produces varied, non-trivial verified/unverified splits across agents and turns
- [x] **Generalized agent personas** — removed hardcoded "regulation" framing, reworded 3 of 6 reasoning styles to work for arbitrary two-sided topics
- [x] Report section hidden from Analysis tab (both live view and History) while still included in PDF export
- [x] **Multi-target influence attribution — investigated and deliberately deferred** (see Future Research section) — explored three methods, found all either redundant with existing position-drift data or blocked by an unresolvable absolute-threshold problem inherent to sentence-embedding similarity on this task

## Status

Core pipeline (web RAG → 6-agent debate → moderator → analysis report) is functional end-to-end and validated across multiple topics spanning policy debates (AI regulation) and casual two-sided topics (cars vs bikes, pineapple on pizza, tea vs coffee). The web UI includes a live debate feed, agent extremity cards, collapsible moderator panel, an Analysis tab with extremity drift, position drift, and a round-scoped interactive influence map, a history browser with multi-run comparison, and a final report viewer cleanly separated from the Analysis tab display while still bundled into PDF exports. RAG retrieval quality has been debugged and calibrated with a real, data-driven distance threshold, and source citations are verified via cosine similarity rather than shown purely on retrieval availability. Agent personas are topic-agnostic. Influence attribution currently uses a simple, honestly-scoped "engagement-correlated position drift" model — a more principled algorithm is tracked as dedicated future research rather than a quick fix, after three investigated approaches were found insufficient.

Remaining work is sequenced deliberately: the flagship team-debate extension (Week 8) comes first since it's the last major architectural change, followed by model comparison and a hosted vector DB migration (both meaningful only once the architecture is stable), then automation and refactoring (Week 9, safe to do only after the code stops changing shape), then pre-deploy hardening and deploy, with the final write-up documenting the full journey including dead ends. Automation work carries mandatory safety guardrails — no unattended scheduled runs, explicit cost confirmation required before any batch execution, and an account-level spending cap as the ultimate backstop — to prevent unintended API cost from unattended runs.