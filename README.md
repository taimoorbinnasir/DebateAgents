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

### Simulation behavior
- [ ] **Team brainstorm + presenter selection** *(flagship extension — Week 9)* — each team privately brainstorms before speaking, evaluates its own arguments, and elects a presenter each round based on argumentative strength; presenter can rotate
- [ ] Self-directed mid-debate retrieval — agents decide when they need more sources rather than relying solely on initial research
- [ ] Selective agent participation — not every agent speaks every round
- [ ] Agent-to-agent direct addressing — explicitly target a specific opponent by name
- [ ] Dynamic agent count — configurable at runtime instead of hardcoded 3v3
- [ ] Mid-debate topic injection — moderator introduces a new fact or event mid-simulation
- [ ] Content hash-based document ingestion (instead of filename-based dedup)
- [ ] Memory reset utility (programmatic, no manual folder deletion)

### Analysis + metrics
- [ ] Influence map — directed graph of who triggered whose escalation
- [ ] Position drift tracker — spectrum movement per round, not just extremity
- [ ] Comparative analysis across multiple runs of the same topic

### Output
- [ ] MiroFish-style structured prediction report
- [ ] PDF export combining transcript + charts
- [ ] Final research write-up documenting methodology and findings

### Infrastructure (post feature-complete)
- [ ] Claude Code refactor pass on the codebase
- [ ] Batch runner script — multiple simulations, different seeds, comparative output
- [ ] GitHub Actions — automated nightly run on a fixed topic
- [ ] Rate limiting (per IP/session) before any public deployment
- [ ] Hard server-side cap on `max_rounds` regardless of frontend input
- [ ] Anthropic Console spending limit set as a safety net
- [ ] Consider auth gate / invite-only access instead of fully public
- [ ] Deploy (Vercel for frontend, Railway/Render for backend) — **last step**, after everything above is complete

### Recently completed
- [x] Full Week 6 build: FastAPI + SSE backend, React live feed, analysis dashboard, history browser
- [x] Final report formatting — left-aligned, table rendering, consistent style with debate feed/moderator panel
- [x] Session-based memory scoping — topic-scoped source collections (reused across runs), session-scoped agent memory (fresh per debate)
- [x] Fictional-character reframing fix for agent personality refusals — agents now stay in character reliably
- [x] Round-2 crash bug fixed
- [x] Mid-run disconnect/reconnect via full-state snapshot endpoint (not just SSE replay)
- [x] Report/transcript filename consistency — `session_id` used everywhere, no more timestamp/UUID mismatch
- [x] Report length control via explicit prompt constraints (word/sentence budgets) instead of relying on `max_tokens` truncation
- [x] "Back to Live" navigation correctly restores an in-progress debate via URL-carried session ID
- [x] Remaining Day 7 integration checks - CORS verification check done

## Status

Core pipeline (web RAG → 6-agent debate → moderator → analysis report) is functional end-to-end, with a working live-streaming web UI (React + FastAPI/SSE), extremity drift visualization, collapsible moderator panel, formatted final report viewer, and a history browser for past runs. Mid-run disconnects and page refreshes now recover full state correctly. Remaining work is CORS verification, then the Week 7-9 extensions above, then deployment last.
