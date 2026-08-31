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

### Immediate
- [ ] Week 7 in progress: Days 1-3 done (position scoring, influence derivation, API wiring, plain language, source citation attachment); Days 4-6 remain

### Week 7 — Analysis tooling (remaining)
- [ ] Day 4: Influence map visualization (directed graph, react-force-graph) + hover-to-cite source badges on debate statements
- [ ] Day 5: Position drift chart (reuse ExtremityChart pattern, -10 to +10 scale) + user opinion input UI
- [ ] Day 6: Comparative analysis across multiple runs of the same topic + PDF export

### Simulation behavior
- [ ] **Team brainstorm + presenter selection** *(flagship — Week 9)* — keep as a **separate debate mode** alongside individual mode, not a replacement; studies group consensus vs individual radicalization as distinct research questions
- [ ] Self-directed mid-debate retrieval
- [ ] Selective agent participation
- [ ] Agent-to-agent direct addressing
- [ ] Dynamic agent count
- [ ] Mid-debate topic injection
- [ ] Content hash-based document ingestion
- [ ] Memory reset utility

### Source citation integrity
- [ ] **Source usage verification via cosine similarity** — compare agent reply embedding against retrieved source chunk embeddings, only attach citations above a similarity threshold (e.g. 0.35); zero extra API cost since it reuses the existing sentence-transformers embedder. More defensible than self-reported usage via system prompt. Note in write-up: similarity is a proxy for topical alignment, not proof the agent derived its argument from that specific source.

### Model comparison
- [ ] Compare Haiku vs Sonnet vs Opus on debate quality — run on **shortened simulations (3-4 rounds)** to control cost before committing to a model switch

### UX / Human-in-the-loop
- [ ] User opinion input — capture the user's own stance after each round (or end of debate)
- [ ] Hover-to-cite sources — badge on each statement showing sources, citation list on hover (data pipeline built Day 3; frontend UI is Day 4)

### Output
- [ ] MiroFish-style structured prediction report
- [ ] Final research write-up — must include explicit methodology caveats on:
  - Influence metric (engagement-correlated drift, not proven causation)
  - Source citation (semantic similarity proxy, not confirmed derivation)

### Infrastructure (post feature-complete, pre-deploy)
- [ ] Claude Code refactor pass
- [ ] Batch runner script
- [ ] GitHub Actions nightly automation
- [ ] Rate limiting (per user/session)
- [ ] Hard server-side cap on max_rounds
- [ ] Anthropic Console spending limit
- [ ] Per-user history isolation (anonymous localStorage-based ID, no accounts — deferred until deploy is imminent)
- [ ] Deploy (Vercel + Railway/Render) — **last step**

### Recently completed
- [x] Full Week 6 build: FastAPI + SSE backend, React live feed, analysis dashboard, history browser
- [x] Final report formatting — left-aligned, table rendering, consistent style with debate feed/moderator panel
- [x] Session-based memory scoping — topic-scoped source collections, session-scoped agent memory
- [x] Fictional-character reframing fix for agent personality refusals
- [x] Round-2 crash bug fixed
- [x] Mid-run disconnect/reconnect via full-state snapshot endpoint
- [x] Report/transcript filename consistency — session_id used everywhere
- [x] Report length control via explicit prompt constraints
- [x] "Back to Live" navigation correctly restores an in-progress debate
- [x] Day 7 integration testing complete, including CORS verification
- [x] Week 7 Day 1: batched position scoring per round (1 call instead of 6), influence edges derived algorithmically from position deltas (zero extra LLM cost)
- [x] Week 7 Day 2: position_log, influence_edges, and user_opinions wired through status/snapshot/transcript endpoints; opinion submission endpoint added
- [x] Week 7 Day 3: plain-language instruction added to agents, moderator, and final report prompts; source citations attached to each agent statement event

## Status

Core pipeline (web RAG → 6-agent debate → moderator → analysis report) is functional end-to-end, with a working live-streaming web UI (React + FastAPI/SSE), extremity drift visualization, position logging, agent influence logging, collapsible moderator panel, formatted final report viewer, and a history browser for past runs. Mid-run disconnects and page refreshes now recover full state correctly. Remaining work is Week 7-9 extensions above, then deployment last.
