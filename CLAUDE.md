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
  — Team Mode instead: per team, per round: 3 drafts → 3 critiques → 1 synthesis by a rotating presenter
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

## Key files

```
DebateAgents/
├── shared/
│   ├── agents.py        — AGENT_PARAMS (6 personas), TEAM_COMPOSITION, build_system_prompt(), REASONING_STYLES,
│   │                      moderator_summary(shared_history, round_num, statements_per_round=6, team_mode=False)
│   ├── config.py         — topic_key() hashing, LANGUAGE_INSTRUCTION constant
│   ├── memory.py          — ChromaDB client, embedder, store/recall functions (agent + team channel scopes);
│   │                        store_team_draft(..., kind="draft"|"critique") — kind is part of the id
│   ├── chunker.py          — chunk_recursive(), is_valid_chunk() (content quality filter)
│   ├── ingest.py            — web search → chunk → embed → store, topic-scoped
│   ├── retrieve.py           — retrieve_agent_sources() with distance filtering
│   └── tools.py                — shared LLM instance (legacy LangChain remnant, still used by scoring calls)
├── Week5/
│   ├── DebateAgents.py    — CORE SIMULATION FILE: run_individual_round_loop, run_team_round_loop,
│   │                         run_simulation_streamed (mode dispatcher), agent_respond,
│   │                         team mode: agent_draft_argument, agent_critique, synthesize_team_statement,
│   │                         team_brainstorm (streams brainstorm_* events), to_citations,
│   │                         score_team_positions_batch, should_stop_team
│   ├── helpers.py           — get_last_opponent_statement / get_last_ally_statement (individual format "Name: ..."),
│   │                         get_last_team_statement (team format "PRO TEAM (Name): ..."), clean_history, should_stop
│   └── eval.py               — score_extremity, score_positions_batch, compute_influence_edges, conclude_simulation,
│                               display_name() (agent_id → persona name, "pro"/"con" → "PRO team")
├── backend/
│   ├── main.py             — FastAPI routes (/simulation/start, /status, /snapshot, /stream, /events,
│   │                         /opinion [deprecated/reverted], /simulations, /simulations/compare,
│   │                         /simulations/{id}/detail, /simulations/{id}/report)
│   ├── manager.py            — SimulationManager: in-memory state (includes "mode"), background thread,
│   │                          push_event(), record_opinion() [deprecated]
│   ├── models.py               — Pydantic schemas (SimulationRequest has `mode`)
│   └── sse.py                    — SSE generator; forwards every event type as-is
└── frontend/src/
    ├── main.jsx                — Router setup
    ├── pages/
    │   ├── LandingPage.jsx      — mode selection
    │   ├── IndividualMode.jsx  — 6-agent live view
    │   ├── TeamMode.jsx         — 2-team live view (identical structure to IndividualMode; no InfluenceMap)
    │   └── HistoryPage.jsx      — mode toggle (All/Individual/Team), mode heading/badges, team detail view,
    │                              newest-first list, "Back to Live" = navigate(-1)
    ├── components/
    │   ├── DebateFeed.jsx        — chat layout (PRO left, CON right, both modes); groups brainstorm_* events;
    │   │                             follow-if-at-bottom scrolling + "↓ N new" button
    │   ├── BrainstormBlock.jsx  — Team Mode typing bubble + collapsible proposals/critiques with per-proposal sources
    │   ├── ExtremityChart / PositionChart — draw one line per key present in the log (6 agents or 2 teams)
    │   ├── Navbar (the only link to History; carries the live session), TopicForm, AgentCard, ModeratorPanel, InfluenceMap, ReportModal, ReportContent,
    │   │   ComparisonView, SourceBadge, FormattedText, RoundHeader
    │   └── (OpinionPrompt.jsx — built then DELIBERATELY REVERTED, do not resurrect without discussion)
    ├── hooks/useSimulation.jsx  — accepts { mode }, passes it to startSimulation; state rebuilt from events on reconnect
    ├── api/simulation.js       — startSimulation(topic, maxRounds, mode)
    └── utils/exportPDF.js       — whitespace-aware pagination, working correctly
```

## Current state — what works, what doesn't

### ✅ Fully working: Individual Mode
Complete pipeline validated on multiple topics. All UI features work: live feed (now chat-style), extremity/position charts, round-scoped influence map (with standalone PNG export), history browser with multi-run comparison, PDF export, session reconnect via snapshot endpoint.

### ✅ Fully working: Team Mode (Week 8 complete)
Per team, per round, in order (PRO then CON):
1. `agent_draft_argument` ×3: isolated proposals responding to the opposing team's last statement
2. `agent_critique` ×3: each member sees all 3 proposals (shuffled) → keep / drop / missing
3. `synthesize_team_statement` ×1: the presenter writes the single public statement in their persona voice
4. `score_extremity` on the final statement only

- **Presenter:** `TEAM_COMPOSITION[team][(round - 1 + offset) % 3]`, with `offset` random once per session per team. No merit selection.
- **Sources:** per-proposal sources are verified against that proposal. The pool of those is shown to the presenter, and the final statement is verified against the pool.
- **Memory:** all 3 members store the team's public statement; proposals and critiques go to the team channel.
- **History format:** `"PRO TEAM (Presenter): text"`. The presenter's name is deliberately kept in the history (owner's choice). Agents are instead told `TEAM_ADDRESS_INSTRUCTION` ("refer to the other side as 'the opposing team'").
- **Events:** `brainstorm_start`, `brainstorm_draft` (with `sources`), `brainstorm_critique`, then `agent_statement` with `agent_id: "pro"|"con"`, `presenter`, and `sources`.
- **Frontend:** a typing bubble while the team brainstorms (CON on the right), collapsing to a toggle when done; 2-line charts; InfluenceMap replaced by a note; the report button appears on completion.
- **Cost:** ~18 LLM calls per round (Individual Mode ~12).

- **Report:** `conclude_simulation(..., mode, presenter_log, brainstorm_log)` picks `_team_report_prompt` or `_individual_report_prompt` (the latter's wording is unchanged).
- **Saved transcript:** always has `mode` and `statements`; team runs also have `presenter_log` and `brainstorm_log` (drafts `{agent_id, agent_name, text, sources}`, critiques `{agent_id, agent_name, text}`, the same shape `BrainstormBlock` renders). Old files without `mode` go through `infer_mode()` (eval.py): logs keyed only by pro/con mean team.
- **History:** an All / Individual / Team toggle, mode badges, and the team detail view (saved brainstorms above team statements, no influence map). `hasCompleteStatements()` falls back to raw transcript lines for old individual runs that saved one statement per round.

### Shared UX behaviour (both modes)
- **History ordering:** newest first, by `saved_at` (written by `conclude_simulation`), falling back to file mtime for older runs. Filenames are session ids, NOT dates, so never sort by filename.
- **History entry point:** only the navbar's "History" link. It passes `?from=<session>&mode=<mode>`, read from `window.location` at click time, because `useSimulation` writes `?session=` with `history.replaceState`, which React Router doesn't see.
- **"← Back to Live":** `navigate(-1)` (returns to the debate page as it was; `useSimulation` reconnects from `?session=`). Falls back to the `from`/`mode` params when `location.key === "default"` (History opened directly).
- **Reconnect de-duplication:** `manager.push_event` stamps each event with `seq`; `useSimulation` drops any `seq <= lastSeqRef`. Without this, events queued while the page was away arrive twice (once in the snapshot, once from the reopened stream).
- **Feed scrolling (`DebateFeed`):** follows new content only if the reader is within 60px of the bottom (instant scroll, not smooth, so it doesn't misread its own scroll as "scrolled up"); otherwise shows a "↓ N new" / "New activity" button.
- **Layout:** chat-style feed (PRO left, CON right) in both modes.

## Critical architectural decisions and WHY (do not relitigate without cause)

1. **Isolated API contexts per agent** — each agent turn is a fresh `Anthropic()` client call, not a shared conversation thread. Prevents one agent's response/refusal from contaminating others' context.
2. **Fictional-character framing in system prompts** — agents are framed as "portraying a fictional character in an academic debate simulation," NOT given direct behavioral commands like "be aggressive." This was necessary to stop Claude's safety training from refusing to roleplay extreme personas. Do not revert to direct behavioral instructions.
3. **Session-scoped agent memory, topic-scoped source memory** — agent private memory resets each simulation run (session_id-keyed); web-searched sources persist and are reused across runs of the same topic (topic_key-hashed) to save SerpApi calls.
4. **Batched scoring calls** — extremity and position are each scored with ONE LLM call per round (all 6 agents at once via JSON response), not 6 separate calls. Cuts API cost ~6x.
5. **Influence metric is deliberately simple and honestly-scoped** — single-target-per-turn engagement, correlated with subsequent position drift, accumulated across rounds, now round-scoped (viewable per-round or cumulative). NOT multi-target attribution — that was investigated (3 methods: raw embedding similarity, softmax-normalized attribution, LLM-judged influence) and deliberately abandoned because all three either reproduce an unresolvable absolute-threshold problem (sentence-embedding cosine similarity produces smooth, non-bimodal distributions with no natural cutoff — confirmed empirically, not assumed) or add no information beyond existing position-drift data. This is documented as a genuine research finding, not a dropped feature. Do not attempt to re-solve this without dedicating focused time to genuinely new methodology.
6. **RAG distance threshold is `dist < 1.15`**, calibrated empirically from real measured data across two test topics (not guessed). Content-quality filtering (`is_valid_chunk`) rejects failed fetches, blocked/403 pages, Cloudflare walls, and non-English UI boilerplate — this was necessary because bad content (not threshold miscalibration) was the root cause of a "zero retrieval" bug earlier in development.
7. **Source citations verified via cosine similarity** (reply embedding vs. source chunk embedding, threshold ~0.35) rather than shown purely on retrieval availability — prevents citing sources that were retrieved but not actually reflected in the agent's reply.
8. **PDF export uses html2canvas + custom whitespace-aware pagination** (not naive fixed-height slicing, which caused content duplication and mid-line cuts before being fixed). Report section is hidden from normal Analysis-tab view via an off-screen-then-temporarily-revealed DOM technique (required because `display:none` is invisible to html2canvas, but `position:absolute; left:-9999px` sometimes also fails to capture — the working fix reveals the element at `position:static` immediately before capture, then hides it again after).

9. **Team Mode = propose → critique → synthesize, not select-the-best.** The original best-of-3 + LLM-judge design was abandoned: members never collaborated, and the judge had fixed option order (hardliner first) and a silent fallback to option 1.
10. **The presenter rotates with a random start; it is never chosen on merit.** Merit selection brings back judge bias and mixes up voice with argument. A fixed start would confound extremity drift with the rotation order. `presenter_log` records who presented, for later control.
11. **The moderator's window equals statements per round** (`statements_per_round`: 6 individual, 2 team). A fixed window of 6 in Team Mode leaked the previous round and the moderator's own summary into its input.
12. **Log keys differ by mode:** agent_ids in Individual Mode, `"pro"`/`"con"` in Team Mode. Any code that indexes `AGENT_PARAMS[key]` on a log must go through `display_name()` (eval.py) or equivalent. This bug caused the "Simulation error: pro" crash.

## Known non-blocking issues
- (Resolved) PDF export final-line clipping — was fixed.
- ESLint flags unused `_` variables in IndividualMode.jsx / TeamMode.jsx, and a missing-dependency warning on useSimulation's mount effect (all pre-existing, harmless).
- `index.css` sets `text-align: center` on `#root` (Vite template leftover). Set alignment explicitly (`text-left`) on new elements rather than changing the global rule.
- `shared/__pycache__/*.pyc` is tracked in git; consider adding `__pycache__/` to .gitignore.
- Moderator summaries generated before the plain-language fix were produced without LANGUAGE_INSTRUCTION (a literal placeholder was being sent), so they aren't directly comparable with later runs.

## Deliberately deferred / do not build without discussion
- **Interactive user participation mode** (user as free-text 7th debater) — distinct from the reverted "opinion slider" feature; a real future feature, not yet built.
- **Multi-target influence attribution** — see point 5 above. Genuinely investigated and abandoned; revisiting requires new methodology, not a quick fix.
- **Dynamic agent count, mid-debate topic injection** — originally planned for Week 8, deferred to a later week, not started.

## Immediate next task (where the last session left off)

**Week 8 is complete** (owner-confirmed). Next is **model comparison** (item 1 below):
- Haiku vs Sonnet vs Opus on debate quality, on short runs (3-4 rounds) to control cost.
- Team Mode costs ~18 LLM calls per round vs ~12 for Individual Mode; confirm with the owner which mode(s) to compare, and the budget, before running anything.
- The model is hardcoded as `"claude-haiku-4-5"` in 7 places: `Week5/DebateAgents.py` (draft, critique, synthesis, agent_respond), `Week5/eval.py` (report), `shared/agents.py` (moderator) and `shared/tools.py` (the LangChain `llm` used for extremity and position scoring). Making the model configurable is the first step. Decide whether the scorers and the moderator should stay fixed on one model so that scores remain comparable across the models being tested.

## Roadmap (Team Mode is done; model comparison is next)

1. Model comparison (Haiku vs Sonnet vs Opus) — NEXT, now that Team Mode is stable
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
