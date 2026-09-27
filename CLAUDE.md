# CLAUDE.md — DebateAgents Project Context

## What this project is

A multi-agent debate simulation studying how AI agents with distinct personalities argue, escalate, and (sometimes) radicalize when placed in sustained disagreement. Six agents (3 PRO, 3 CON) debate a user-supplied topic over multiple rounds, grounded in web-researched sources via RAG, evaluated by a moderator, and analyzed via extremity/position drift and influence tracking.

**Owner's background:** CS student/fresh graduate, learning agentic AI development through this project as a structured Phase 1→2→3 roadmap (LLM API basics → RAG/memory/agents → this multi-agent capstone). Comfortable with React. Prefers concise answers, wants to understand *why* fixes work, values honest methodological framing over overclaiming results.

**This is primarily a research-based project. The owner considers turning this into a practical, real-world project if a potential use case is found.**

## Architecture

```
User inputs topic
      ↓
Each agent searches the web with a personality-biased query (SerpApi)
      ↓
Sources chunked, filtered, embedded, stored per-agent in ChromaDB (topic-scoped)
      ↓
Agents debate in interleaved PRO/CON turns across N rounds (Claude Haiku, isolated API contexts per agent)
      ↓
Each agent recalls its own past statements (session-scoped memory) + retrieves relevant sources
      ↓
Moderator evaluates each round; extremity + position scored per round (batched, 1 LLM call/round each)
      ↓
Simulation ends on round limit or conversation convergence (embedding similarity check)
      ↓
Structured analysis report generated and saved (session_id-keyed filename)
```

**Stack:**
- Backend: FastAPI + Python, background thread per simulation, SSE for live streaming to frontend
- Frontend: React (Vite) + Tailwind, react-force-graph-2d for influence map, recharts for charts, jsPDF + html2canvas for export
- Memory: ChromaDB (local `PersistentClient`, **NOT yet migrated to hosted** — will break on deploy due to ephemeral disk)
- Embeddings: `sentence-transformers` (`all-MiniLM-L6-v2`)
- LLM: Claude Haiku via Anthropic API, isolated `Anthropic()` client calls per agent turn (not LangChain — LangChain was abandoned early due to version instability)

## Key files (paths as referenced throughout development — verify against actual repo)

```
DebateAgents/
├── shared/
│   ├── agents.py        — AGENT_PARAMS (6 personas), TEAM_COMPOSITION, build_system_prompt(), REASONING_STYLES
│   ├── config.py         — topic_key() hashing, LANGUAGE_INSTRUCTION constant
│   ├── memory.py          — ChromaDB client, embedder, store/recall functions (agent + team channel scopes)
│   ├── chunker.py          — chunk_recursive(), is_valid_chunk() (content quality filter)
│   ├── ingest.py            — web search → chunk → embed → store, topic-scoped
│   ├── retrieve.py           — retrieve_agent_sources() with distance filtering
│   └── tools.py                — shared LLM instance (legacy LangChain remnant, mostly unused now)
├── Week5/
│   ├── eval.py            - EVALUATION FILES: score_extremity, print_extremity_chart, score_positions_batch, compute_influence_edges, conclude_simulation
│   ├── DebateAgents.py          — CORE SIMULATION FILE: run_individual_round_loop, run_team_round_loop, 
│                             run_simulation_streamed (mode dispatcher), agent_respond, team_brainstorm,
│                             select_presenter, score_extremity, score_positions_batch, 
│                             compute_influence_edges, moderator_summary, should_stop, should_stop_team,
│                             conclude_simulation
│   └── helpers.py            - HELPER FUNCTIONS: get_last_opponent_statement, get_last_ally_statement, should_stop, clean_history, extract_agent_id_from_message
├── backend/
│   ├── main.py             — FastAPI routes (/simulation/start, /status, /snapshot, /stream, 
│   │                         /opinion [deprecated/reverted], /simulations, /simulations/compare, 
│   │                         /simulations/{id}/detail, /simulations/{id}/report)
│   ├── manager.py            — SimulationManager: in-memory state, background thread, push_event(), 
│   │                          record_opinion() [deprecated]
│   └── models.py               — Pydantic schemas (SimulationRequest now needs `mode` field added)
└── frontend/src/
    ├── main.jsx                — Router setup (needs updating: Landing, IndividualMode, TeamMode, HistoryPage)
    ├── pages/
    │   ├── Landing.jsx          — NEW, mode-selection landing page (written, not yet tested)
    │   ├── IndividualMode.jsx  — renamed from App.jsx, fully working
    │   ├── TeamMode.jsx         — NEW, mirrors IndividualMode structure, NOT YET WORKING (see below)
    │   └── HistoryPage.jsx      — needs mode toggle/filter added (not yet done)
    ├── components/
    │   ├── Navbar.jsx            — NEW, written
    │   ├── TopicForm, AgentCard, DebateFeed, ModeratorPanel, ExtremityChart, PositionChart,
    │   │   InfluenceMap, ReportModal, ReportContent, ComparisonView, SourceBadge — all working
    │   └── (OpinionPrompt.jsx — built then DELIBERATELY REVERTED, do not resurrect without discussion)
    ├── hooks/useSimulation.js   — now accepts { mode = "individual" }, needs verification this actually 
    │                              threads through correctly end-to-end with TeamMode.jsx
    ├── api/simulation.js       — startSimulation() needs `mode` param added if not already
    └── utils/exportPDF.js       — whitespace-aware pagination, working correctly
```

## Current state — what works, what doesn't

### ✅ Fully working: Individual Mode
Complete pipeline validated on multiple topics (AI regulation, cars vs bikes, pineapple on pizza, tea vs coffee). All UI features work: live feed, extremity/position charts, round-scoped influence map (with standalone PNG export, node names always visible), history browser with multi-run comparison, PDF export (report hidden from Analysis tab view but included in export via off-screen-then-revealed DOM trick), session reconnect via snapshot endpoint.

### ⚠️ Scaffolded but broken: Team Mode (Week 8 flagship feature)
**Backend and frontend code exists for team mode, but does NOT actually work as team mode.** Confirmed symptoms as of last session:
1. Backend loop (`run_team_round_loop`) is producing behavior identical to Individual Mode — each of the 6 agents speaks individually, rather than: 3 agents privately brainstorm → 1 LLM call selects best draft → that becomes the team's single public statement (2 statements/round total, not 6)
2. Frontend doesn't stream live updates for team-mode sessions (SSE connection or event handling likely broken for this mode specifically)
3. Extremity chart, position chart, and influence map are still using individual 6-agent data shape even when team mode ran
4. Final report (`conclude_simulation`) generates using individual-mode framing regardless of actual mode
5. Saved transcript JSON uses individual-mode's shape regardless of actual mode
6. No `mode` field exists on saved transcripts, so past runs can't be distinguished
7. History page has no way to filter/toggle between Individual and Team runs

**Diagnosis not yet completed** — the actual `run_team_round_loop` code was never pasted for review before this handoff; the specific bug (dispatcher not routing correctly? loop internally falling through to `agent_respond`? some other issue?) needs fresh investigation.

## Critical architectural decisions and WHY (do not relitigate without cause)

1. **Isolated API contexts per agent** — each agent turn is a fresh `Anthropic()` client call, not a shared conversation thread. Prevents one agent's response/refusal from contaminating others' context.
2. **Fictional-character framing in system prompts** — agents are framed as "portraying a fictional character in an academic debate simulation," NOT given direct behavioral commands like "be aggressive." This was necessary to stop Claude's safety training from refusing to roleplay extreme personas. Do not revert to direct behavioral instructions.
3. **Session-scoped agent memory, topic-scoped source memory** — agent private memory resets each simulation run (session_id-keyed); web-searched sources persist and are reused across runs of the same topic (topic_key-hashed) to save SerpApi calls.
4. **Batched scoring calls** — extremity and position are each scored with ONE LLM call per round (all 6 agents at once via JSON response), not 6 separate calls. Cuts API cost ~6x.
5. **Influence metric is deliberately simple and honestly-scoped** — single-target-per-turn engagement, correlated with subsequent position drift, accumulated across rounds, now round-scoped (viewable per-round or cumulative). NOT multi-target attribution — that was investigated (3 methods: raw embedding similarity, softmax-normalized attribution, LLM-judged influence) and deliberately abandoned because all three either reproduce an unresolvable absolute-threshold problem (sentence-embedding cosine similarity produces smooth, non-bimodal distributions with no natural cutoff — confirmed empirically, not assumed) or add no information beyond existing position-drift data. This is documented as a genuine research finding, not a dropped feature. Do not attempt to re-solve this without dedicating focused time to genuinely new methodology.
6. **RAG distance threshold is `dist < 1.15`**, calibrated empirically from real measured data across two test topics (not guessed). Content-quality filtering (`is_valid_chunk`) rejects failed fetches, blocked/403 pages, Cloudflare walls, and non-English UI boilerplate — this was necessary because bad content (not threshold miscalibration) was the root cause of a "zero retrieval" bug earlier in development.
7. **Source citations verified via cosine similarity** (reply embedding vs. source chunk embedding, threshold ~0.35) rather than shown purely on retrieval availability — prevents citing sources that were retrieved but not actually reflected in the agent's reply.
8. **PDF export uses html2canvas + custom whitespace-aware pagination** (not naive fixed-height slicing, which caused content duplication and mid-line cuts before being fixed). Report section is hidden from normal Analysis-tab view via an off-screen-then-temporarily-revealed DOM technique (required because `display:none` is invisible to html2canvas, but `position:absolute; left:-9999px` sometimes also fails to capture — the working fix reveals the element at `position:static` immediately before capture, then hides it again after).

## Known non-blocking issues
- (Resolved) PDF export final-line clipping — was fixed.

## Deliberately deferred / do not build without discussion
- **Interactive user participation mode** (user as free-text 7th debater) — distinct from the reverted "opinion slider" feature; a real future feature, not yet built.
- **Multi-target influence attribution** — see point 5 above. Genuinely investigated and abandoned; revisiting requires new methodology, not a quick fix.
- **Dynamic agent count, mid-debate topic injection** — planned Week 8 items, not started.

## Immediate next task (where the last session left off)

**Fix Team Mode so it actually functions as team mode**, per the 7 sub-tasks below (all filed under "Week 8" in the project to-do list):

1. Fix `run_team_round_loop` in `Week5/Phase2.py` to genuinely call `team_brainstorm()` → `select_presenter()` → single team statement, not per-agent individual responses. **First step: get the user to paste the actual current contents of `run_team_round_loop` and the `run_simulation_streamed` dispatcher to diagnose why it's behaving like Individual Mode.**
2. Fix live SSE streaming for team-mode sessions in the frontend (`TeamMode.jsx`, `useSimulation.js`).
3. Rework analysis metrics for 2-team comparison instead of 6-agent — extremity/position charts should show 2 lines; InfluenceMap likely needs to be removed or replaced for team mode (2-node graph reduces to one trivial edge).
4. Fix `conclude_simulation`'s report generation to use team-aware framing (2 teams' position drift, presenter selection patterns) instead of individual-agent framing.
5. Fix transcript saving to use team-mode's actual data shape (2-key logs, presenter_log) instead of silently reusing individual-mode's schema.
6. Add a `mode` field to every saved transcript/report at save time.
7. Update `HistoryPage.jsx` to toggle/filter between Individual and Team runs, and correctly render team-mode's data shape in the detail view.

## After Team Mode is genuinely fixed, the roadmap continues:

1. Model comparison (Haiku vs Sonnet vs Opus) — deliberately deferred until Team Mode is stable
2. Hosted ChromaDB migration (required before deploy — local `PersistentClient` won't survive Render/Railway's ephemeral disk)
3. Week 9 — Automation: Claude Code refactor pass, batch runner script, GitHub Actions — **all with mandatory safety guardrails**: no blind cron scheduling, explicit confirmation required before any batch run, Anthropic Console spending limit set BEFORE automation work begins (owner has explicitly stated concern about unattended overnight API spend)
4. Future research: principled inter-agent influence algorithm (see point 5 above)
5. Pre-deploy hardening: rate limiting, max_rounds server cap, per-user history isolation (anonymous ID, no accounts)
6. Deploy: Vercel (frontend) + Render/Railway (backend)
7. Final research write-up — must include all the honest methodological caveats accumulated throughout (influence metric scope, source citation as proxy not proof, RAG retrieval quality being topic-dependent, the standing finding that sentence-embedding cosine similarity produces uninformative smooth distributions across every application tried in this project)

## Communication preferences (from conversation history)
- Wants concise answers by default, but appreciates thorough walkthroughs for genuinely new implementation steps
- Wants to understand root causes of bugs, not just patches — has repeatedly pushed back on guessed fixes in favor of diagnosing with real data/print statements first
- Values honest scoping over impressive-sounding overclaims (this shaped the entire influence-metric investigation and its conclusion)
- Prefers being told directly when an idea has real limitations, rather than being told everything is a good idea
- Uses `ask_user_input_v0`-style clarifying questions well — respond concretely when asked before proceeding
