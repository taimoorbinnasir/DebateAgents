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
- LLM: Anthropic API, isolated `Anthropic()` client per call (made inside `RunContext.create`). Model per role comes from a **model profile** (default `all_haiku`). LangChain was abandoned early due to version instability; the scorers were its last live users and now call the SDK directly

## Key files

```
DebateAgents/
├── shared/
│   ├── agents.py        — AGENT_PARAMS (6 personas), TEAM_COMPOSITION, build_system_prompt(), REASONING_STYLES,
│   │                      moderator_summary(shared_history, round_num, statements_per_round=6, team_mode=False)
│   ├── config.py         — topic_key() hashing, LANGUAGE_INSTRUCTION, ROLES, MODEL_PROFILES, get_model(),
│   │                        MODEL_REQUEST_OPTIONS (per-model thinking/effort), PRICING, compute_cost()
│   ├── run_context.py     — RunContext (profile, cost_log, seeded rng, api_key) + ctx.create(role, ...);
│   │                        response_text() (first text block)
│   ├── memory.py          — ChromaDB client, embedder, store/recall functions (agent + team channel scopes);
│   │                        store_team_draft(..., kind="draft"|"critique") — kind is part of the id
│   ├── chunker.py          — chunk_recursive(), is_valid_chunk() (content quality filter)
│   ├── ingest.py            — web search → chunk → embed → store, topic-scoped
│   ├── retrieve.py           — retrieve_agent_sources() with distance filtering
│   └── tools.py                — legacy LangChain `llm`; no longer used by the live simulation. Still the
│                                  file that calls load_dotenv() (reached via ingest → web_rag → tools)
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

### Model profiles, cost logging, seeding (runtime for model comparison)
- **Roles** (`shared/config.py` `ROLES`): `draft`, `critique`, `synthesis` (team), `agent_turn` (individual), `moderator`, `extremity_scorer`, `position_scorer`, `report`. Research makes no LLM calls (the search query is a template).
- **Profiles:** `MODEL_PROFILES` maps every role to a model: `all_haiku` (default), `all_sonnet` (`claude-sonnet-5` debaters), `all_opus` (`claude-opus-5-5` debaters). Use `get_model(role, profile)`; it raises on an unknown role or profile.
- **Judges are fixed (owner decision):** `JUDGE_ROLES` = moderator, extremity_scorer, position_scorer, report always use `JUDGE_MODEL` (`claude-haiku-4-5`) in every profile, so a comparison changes only who debates, not who grades. Profile names describe the debating roles only; the transcript's `model_config.roles` records the exact mapping.
- **Thinking policy (`MODEL_REQUEST_OPTIONS`):** Sonnet 5 and Opus 5.5 think by default, and thinking counts against `max_tokens` (unchanged per call site), so thinking is minimized. Sonnet 5 → `thinking: disabled`; Opus 5.5 can't disable it → `output_config.effort: "low"`. Haiku sends nothing extra. Owner decision; revisit only deliberately.
- **`RunContext`** (one per run, created in `run_simulation_streamed`, passed as a required keyword-only `ctx` to every LLM-calling function; never global, since sims run in threads). `ctx.create(role, round_num=, agent_id=, **request)` builds a fresh `Anthropic()` client, adds the profile's model + options, and appends to `ctx.cost_log`: `{role, model, round, agent_id, input_tokens, output_tokens, cost_usd, stop_reason}`. `agent_id` is the agent; team extremity scoring logs the team; batched calls log null.
- **`stop_reason` in cost_log** is how truncation is detected (`"max_tokens"`). Watch it closely for Sonnet/Opus. `score_extremity` silently returns 5 on unparseable output, so truncated scorer replies would otherwise bias results invisibly.
- **Parsing:** all call sites use `response_text(response)` (first text block, `""` if none). Identical to `content[0].text` for Haiku; required for thinking models, whose `content[0]` is a thinking block.
- **Scorers:** direct SDK calls with `max_tokens=SCORER_MAX_TOKENS` (1024, the langchain-anthropic 0.1.23 default they previously ran with; no temperature), so the requests are unchanged.
- **Seed:** `run_simulation_streamed(..., seed=N)` → `RunContext.rng = random.Random(N)`, else the global `random` (unseeded behavior unchanged). It controls: Individual turn-order shuffles, the Team presenter offset, and the proposal/critique order shuffle inside team prompts (`format_team_contributions`). It does NOT make LLM outputs deterministic.
- **API key:** `RunContext.api_key` (None → `ANTHROPIC_API_KEY`). Intended for model_eval to use its own workspace key per run. Deliberately not exposed over HTTP.
- **Saved transcripts** now also have `model_config` (`{profile, roles}`), `cost_log` (report call included), `total_cost_usd`, `experiment_id` (null unless set) and `seed`. `conclude_simulation(..., output_dir=None)` defaults to `Resources/simulations/`; experiment runs should pass their own folder so they don't appear in History.
- **API:** `SimulationRequest` has `model_profile` (default `all_haiku`, unknown → 400 in `main.py` before the thread starts) and `seed`; verified end-to-end to reach `run_simulation_streamed`. `experiment_id`, `output_dir` and `api_key` are Python-only parameters of `run_simulation_streamed`.
- **Pydantic gotcha:** `model_config` is reserved in Pydantic v2. `SimulationTranscript` stores it as `run_model_config` with `alias="model_config"` (the API still returns `model_config`). Construct it via `**{"model_config": ...}`.
- **Measured on Haiku (1 round, "AI regulation", real runs):** Individual 15 calls, ≈$0.023 (agent_turn 58%, report 16%, moderator 12%). Team 19 calls, ≈$0.037 (critique 37%, draft 28%, synthesis 18%). Per round: 14 calls Individual, 18 Team; plus 1 report per run.

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
- **Moderator `max_tokens` raised 300 → 500 (owner decision):** at 300 it was truncated mid-sentence even on Haiku (263-300 tokens used in 4 runs). Moderator summaries in runs saved before this change may be cut short.
- `.env` is loaded explicitly in `shared/config.py` (absolute path to the project `.env`, doesn't override existing env vars). Every entry point imports config. `shared/tools.py` still calls `load_dotenv()` too, which is harmless.
- (Owner: don't delete yet.) The legacy CLI `run_simulation()` in `Week5/DebateAgents.py` (used by `__main__`) is broken: it loops over `turn_order` before defining it, calls `agent_respond` without `session_id`/`ctx`, and uses the global `random`. Not on any live path (the server uses `run_simulation_streamed`).
- `index.css` sets `text-align: center` on `#root` (Vite template leftover). Set alignment explicitly (`text-left`) on new elements rather than changing the global rule.
- `shared/__pycache__/*.pyc` is tracked in git; consider adding `__pycache__/` to .gitignore.
- Moderator summaries generated before the plain-language fix were produced without LANGUAGE_INSTRUCTION (a literal placeholder was being sent), so they aren't directly comparable with later runs.

## Deliberately deferred / do not build without discussion
- **Interactive user participation mode** (user as free-text 7th debater) — distinct from the reverted "opinion slider" feature; a real future feature, not yet built.
- **Multi-target influence attribution** — see point 5 above. Genuinely investigated and abandoned; revisiting requires new methodology, not a quick fix.
- **Dynamic agent count, mid-debate topic injection** — originally planned for Week 8, deferred to a later week, not started.

## Immediate next task (where the last session left off)

**Model comparison, part 1 (runtime) is done**: profiles, per-call cost logging, seeding and the new transcript fields (see "Model profiles, cost logging, seeding" above).

**Next: the `model_eval/` folder** (a separate task, not started):
- An experiment runner that calls `run_simulation_streamed(..., model_profile=, seed=, experiment_id=, output_dir=, api_key=)` directly (not over HTTP), writing to its own output folder so runs stay out of History.
- The owner is setting up a **separate Anthropic workspace with its own API key**, stored in `.env` as `MODEL_EVAL_API_KEY`. The model_eval runner reads it and passes it as `run_simulation_streamed(api_key=...)`. Don't overwrite `ANTHROPIC_API_KEY`, and never use it from the web app. Sonnet/Opus have their own per-model rate limits, so pace the runs.
- Mandatory guardrails (from Week 9 principles): an explicit confirmation step, a printed cost estimate before any batch (use the measured per-role costs above × model price ratios), and no unattended scheduling.
- Budget: the owner had ~$14 of credits left when this was written. Estimated cost per 3-round run (Haiku judges; debater cost scaled by price ratio from measured Haiku runs; Opus effort-low thinking not yet measured): Individual ≈ $0.07 Haiku / $0.11 Sonnet / $0.20-0.25 Opus; Team ≈ $0.12 / $0.21 / $0.40-0.50. The runner must print its estimate and ask before running.
- Verify `PRICING` against Anthropic's official pricing page (currently marked unverified).

## Roadmap (Team Mode is done; model comparison is next)

1. Model comparison (Haiku vs Sonnet vs Opus). Runtime part done; model_eval/ folder is NEXT
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
