# DebateAgents

A multi-agent debate simulation studying how AI agents with distinct personalities argue, escalate, and (sometimes) radicalize when placed in sustained disagreement with each other.

Six agents — three arguing **PRO**, three arguing **CON** — debate a user-supplied topic over multiple rounds. Each agent has a fixed stance, a distinct reasoning style, and parametric personality traits (extremity, concession probability, rhetorical intensity) that shape how it argues. A neutral moderator evaluates each round. A web research layer lets agents ground their arguments in real sources they find themselves, biased toward their own worldview.

The simulation runs in two modes:
- **Individual Mode** — all six agents speak for themselves, six statements per round.
- **Team Mode** — each side of three agents brainstorms privately (propose → critique → synthesize) and presents one team statement per round, two statements per round in total.

## Research question

Does an extremist agent pull the rest of the group toward its position over time, or does it become isolated? More broadly: how do personality, evidence access, and group dynamics shape the trajectory of a multi-agent disagreement? Team Mode adds a second question: when agents with different temperaments have to agree on one shared statement, does the team moderate or amplify its members?

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

### Team Mode round

Each team's turn runs in order (PRO first, then CON), and each step is a separate, isolated API call:

```
1. Draft      (×3)  each member privately proposes an argument, responding to the opposing team's last statement
2. Critique   (×3)  each member reads all three proposals (shuffled) → what to keep, what to drop, what's missing
3. Synthesize (×1)  this round's presenter writes the team's single public statement, in their own persona voice
4. Score      (×1)  extremity is scored on the final statement only
```

- **Presenter:** round-robin within the team, with a random starting member chosen once per session. There is no "best presenter" judgment (see [Design notes](#design-notes)).
- **Sources:** each proposal keeps only the sources verified against its own text. The presenter sees the pooled sources the proposals actually used, and the final statement is verified against that pool.
- **Moderator:** sees only the current round's two team statements and evaluates PRO team vs CON team.

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
- **Frontend:** React (Vite) + Tailwind. A landing page to pick a mode, a chat-style live debate feed (PRO on the left, CON on the right), agent extremity cards, a collapsible moderator panel, an analysis dashboard, and a history page for past runs. In Team Mode, each team's private brainstorm streams live into a collapsible "brainstorming…" typing bubble that shows each member's proposal (with the sources it used) and critique.
- **Memory:** ChromaDB (local, persistent) with `sentence-transformers` embeddings.
  - **Agent private memory** — scoped per simulation session (fresh each debate). In Team Mode, all three members store the team's public statement, so their next proposals stay consistent with what the team actually said.
  - **Team channel** (Team Mode) — scoped per team per session; holds that team's proposals and critiques
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

Open `http://localhost:5173`, pick Individual or Team Mode, enter a topic, choose a round count, and start the debate.

To run without the frontend, start the backend and use the API directly:

```bash
curl -s -X POST localhost:8000/simulation/start \
  -H "Content-Type: application/json" \
  -d '{"topic": "tea vs coffee", "max_rounds": 2, "mode": "team"}'

# then stream the events live, using the returned session_id
curl -N localhost:8000/simulation/<session_id>/stream
```

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
│   ├── DebateAgents.py   # simulation loops (individual + team), agent turns, team brainstorm, mode dispatcher
│   ├── helpers.py         # history lookups (last opponent / ally / team statement), stopping conditions
│   └── eval.py             # extremity + position scoring, influence edges, final report
├── backend/
│   ├── main.py            # FastAPI routes
│   ├── manager.py          # simulation state, background thread, SSE event queue
│   └── models.py            # Pydantic schemas
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── LandingPage.jsx     # mode selection
│       │   ├── IndividualMode.jsx  # 6-agent live view (feed + agent cards + analysis toggle)
│       │   ├── TeamMode.jsx         # 2-team live view
│       │   └── HistoryPage.jsx      # past simulation browser
│       ├── components/         # AgentCard, DebateFeed, BrainstormBlock, ModeratorPanel, ReportModal, etc.
│       └── hooks/useSimulation.jsx  # SSE connection + live state (mode-aware)
└── Resources/
    ├── <AgentName>/         # raw web sources each agent found
    └── simulations/          # saved transcripts (.json) + analysis reports (.md)
```

## Design notes

**Why "fictional character" framing matters.** Early versions of this project had agents refuse to argue in character — Claude's safety training reads direct behavioral instructions ("be aggressive," "never concede") as requests to misbehave. Reframing each agent as a fictional participant in an academic debate simulation, with behavior described through parametric traits rather than imperative commands, resolved this without any attempt to bypass safety guardrails. This is documented as the core architectural lesson of the project.

**Why agents use isolated API contexts.** Each agent's turn is a fresh API call with its own system prompt and constructed context — not a shared conversation thread. This prevents one agent's response (or an early refusal, during debugging) from contaminating every subsequent agent's context.

**Why sources are topic-scoped but memory is session-scoped.** Re-running the same topic reuses previously found sources (saves SerpApi calls and embedding time), but each debate run gets a completely fresh memory of what was actually said — so agents don't "remember" arguments from a previous, unrelated run of the same topic.

**Why Team Mode synthesizes instead of picking the best draft.** The first version had each member draft independently and an LLM judge pick one draft to publish word for word. In practice that was best-of-3 sampling, not a team: members never saw each other's work, and the judge had a built-in bias (option order was fixed, with the hardliner always first, and a parse failure silently chose option 1). The current flow makes members read and critique each other's proposals, and the final statement is written from all of them.

**Why the presenter rotates instead of being chosen on merit.** The presenter doesn't choose an argument; they write the synthesis from all three proposals and critiques, so quality comes from the synthesis step. Choosing a "best" presenter would bring the judge bias back and mix up *whose voice* with *whose argument*. A fixed rotation order would also confound results: the hardliner would always open, and extremity drift across rounds would partly just be the rotation. So the rotation starts at a random member each session, and `presenter_log` records who presented each round.

**Why the moderator's input window depends on the mode.** The moderator evaluates only the current round's statements: six in Individual Mode, two in Team Mode. A fixed six-line window in Team Mode pulled in the previous round and the moderator's own earlier summary.

## To-do

**Week 8 — Flagship extensions**

**Status:** Team Mode now runs end-to-end as genuine team mode: live propose → critique → synthesize brainstorm, rotating presenter, two statements per round, team-aware moderator, 2-line extremity and position charts, and a final report that generates without errors. The remaining sub-tasks are about what gets saved and how past runs are viewed.

- Make the final report team-aware. `conclude_simulation` no longer crashes on team data, but its prompt is still worded for six individual agents ("did any agent shift position?"). It needs a team framing: the two teams' position drift, and presenter patterns across rounds. **Consider: should the report also comment on how the presenter's persona shaped each team statement?**
- Fix transcript saving for Team Mode. The saved JSON still uses Individual Mode's shape. It should include `presenter_log` and the per-round brainstorm (`brainstorm_log`: proposals, critiques, and the sources each used). Both are already collected in `run_team_round_loop` but not yet written.
- Add a `mode` field to every saved transcript/report, so past runs are tagged "individual" or "team" at save time. The mode is now carried through the backend and stored in the in-memory session state, but it isn't saved to disk yet.
- Update the History page to toggle/filter between Individual and Team runs (a toggle or a badge per item, using the new `mode` field), and make its detail view render team-mode data: 2-line charts, no influence map, team-aware report, and optionally the saved brainstorms.
- Remaining Team Mode frontend errors noted during testing (to be triaged next session).

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
  - Team Mode: the presenter's persona shapes each team statement's tone, so team extremity partly reflects who presented that round (recorded in `presenter_log`)
  - Moderator summaries from runs before the plain-language fix were generated without the language instruction (a literal `{LANGUAGE_INSTRUCTION}` placeholder was being sent), so they aren't directly comparable with later runs

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
- Separate routed pages for Individual Mode and Team Mode with shared navbar
- Team Mode now actually runs: the `mode` sent by the frontend was being dropped in `main.py`/`manager.py`, so every run fell back to Individual Mode. The same fix restored Individual Mode's live streaming, which a positional-argument bug in the mode dispatcher had broken.
- Team Mode brainstorm redesigned: propose → critique → synthesize, replacing the best-of-3 LLM-judge selection
- Presenter rotation with a random start per session (replaces judge-based presenter selection)
- Opponent lookup fixed for team-format statements (drafters were always told "no opponent statement yet")
- Agents told to refer to the other side as "the opposing team", not by individual names
- Team-aware moderator: correct per-mode input window, team framing, and the language instruction now actually applied (was sent as a literal placeholder, in both modes)
- Per-proposal source attribution, with pooled sources verified against the final team statement
- Live "brainstorming…" typing bubble with expandable proposals, critiques, and per-proposal sources
- Chat-style debate feed in both modes (PRO left, CON right)
- Team Mode extremity and position charts (2 lines); influence map replaced with an explanatory note in Team Mode
- "Simulation error: pro" crash at the end of Team Mode runs fixed, which also restores the final report button


## Status

Individual Mode (web RAG → 6-agent debate → moderator → analysis report) remains fully functional and validated across multiple topics. Team Mode now works end-to-end as a genuine team debate: each side brainstorms privately (propose → critique → synthesize), a rotating presenter delivers one statement per team per round, the moderator evaluates team vs team, and the live feed, charts, and final report all work for team runs. What's left for Team Mode is persistence and history: saving team-shaped transcripts (with presenter and brainstorm data), tagging saved runs with their mode, team-aware report wording, and a History page that can filter and display team runs. These are the next work before moving on to model comparison, automation, or deploy.
