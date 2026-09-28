# DebateAgents

A multi-agent debate simulation studying how AI agents with distinct personalities argue, escalate, and (sometimes) radicalize when placed in sustained disagreement with each other.

Six agents — three arguing **PRO**, three arguing **CON** — debate a user-supplied topic over multiple rounds. Each agent has a fixed stance, a distinct reasoning style, and parametric personality traits (extremity, concession probability, rhetorical intensity) that shape how it argues. A neutral moderator evaluates each round. A web research layer lets agents ground their arguments in real sources they find themselves, biased toward their own worldview.

The simulation runs in two modes:
- **Individual Mode** — all six agents speak for themselves, six statements per round.
- **Team Mode** — each side of three agents brainstorms privately (propose → critique → synthesize) and presents one team statement per round, two statements per round in total.

A separate **model comparison** harness (`model_eval/`) runs the same debates with Claude Haiku, Sonnet and Opus debaters and compares their cost and behaviour. See [Model comparison](#model-comparison-model_eval).

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
- **Frontend:** React (Vite) + Tailwind. A landing page to pick a mode, a chat-style live debate feed (PRO on the left, CON on the right), agent extremity cards, a collapsible moderator panel, an analysis dashboard, and a history page for past runs. In Team Mode, each team's private brainstorm streams live into a collapsible "brainstorming…" typing bubble that shows each member's proposal (with the sources it used) and critique. The feed only follows new content when you're already at the bottom; if you've scrolled up, a "↓ N new" button appears instead. The History page lists past runs newest first and can be filtered by mode.
- **Memory:** ChromaDB (local, persistent) with `sentence-transformers` embeddings.
  - **Agent private memory** — scoped per simulation session (fresh each debate). In Team Mode, all three members store the team's public statement, so their next proposals stay consistent with what the team actually said.
  - **Team channel** (Team Mode) — scoped per team per session; holds that team's proposals and critiques
  - **Agent source memory (RAG)** — scoped per topic (reused across sessions on the same topic, avoids redundant web searches)
- **Web research:** SerpApi + custom HTML extraction, chunked with a recursive chunker and filtered for quality before ingestion.
- **LLM:** Anthropic API, called with isolated context per agent (no shared conversation state between agents at the API level — only the orchestrator-controlled shared transcript). Which model runs each **role** (agent turn, draft, critique, synthesis, moderator, scorers, report) comes from a **model profile**; the default, `all_haiku`, is Claude Haiku everywhere. Every call's token usage and cost is logged per run.

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
│   ├── config.py        # model profiles per role, pricing, topic_key hashing, loads .env
│   ├── run_context.py    # per-run state: model profile, cost log, seeded randomness, API key
│   ├── memory.py         # ChromaDB memory (agent private + document RAG)
│   ├── chunker.py        # recursive chunking + chunk quality filtering
│   ├── ingest.py          # web search → chunk → embed → store (per agent, per topic)
│   ├── retrieve.py         # source retrieval with distance filtering
│   └── tools.py             # legacy LangChain helpers (not used by the live simulation)
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
├── model_eval/            # model comparison harness (Haiku vs Sonnet vs Opus)
│   ├── experiments.py      # experiment definitions (topic, modes, profiles, rounds, seeds, spend cap)
│   ├── run_experiment.py   # runner: plan + cost estimate → typed confirmation → runs
│   ├── estimate.py          # cost estimates (baseline, then measured from earlier runs)
│   ├── summarize.py          # comparison table + summary.csv + runs.csv
│   └── results/               # per-experiment output (gitignored)
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

## Model comparison (`model_eval/`)

### The question

**When the debating agents run on a more capable model, does the debate behave differently, and what does it cost?** Specifically: do Sonnet or Opus debaters argue more or less extremely than Haiku, do the two sides pull further apart or closer together over the rounds, and how much more does each run cost?

It compares **debate behaviour and cost**. It does not yet score argument *quality* (see [What it can't tell you](#what-it-cant-tell-you)).

### What changes between runs, and what stays fixed

A fair comparison changes one thing at a time. Here, only the **debaters' model** changes:

| | Changes between runs | Fixed across all runs |
|---|---|---|
| **Debaters** (`agent_turn`; Team Mode's `draft`, `critique`, `synthesis`) | ✅ Haiku 4.5 / Sonnet 5 / Opus 5.5, set by the profile | |
| **Judges** (moderator, extremity scorer, position scorer, report) | | Always Haiku 4.5. If the graders changed too, a difference in scores could come from the grader rather than the debater. The moderator also matters for another reason: its summary goes into the debate history, so it shapes what the debaters see next. |
| **Topic and web sources** | | "AI regulation", with the same cached sources for every run |
| **Prompts, personas, word limits** | | Identical. The visible-answer `max_tokens` is the same for every model |
| **Randomness** (turn order, presenter order, the order proposals appear in prompts) | | Controlled by a **seed**. Seed 3 gives every model the same setup |
| **Model wording** | Varies from run to run, even with the same seed | This is why every model runs several seeds |

Model-specific settings, needed because Sonnet 5 and Opus 5.5 "think" privately before answering by default:
- **Sonnet 5:** thinking turned off.
- **Opus 5.5:** thinking can't be turned off, so it runs at the lowest effort, with **+1,000 extra `max_tokens`** reserved for thinking. Without that, the pilot showed Opus using most of a 300-token critique budget on thinking and returning 18–83 words. With the allowance, it has the same room for its visible answer as the other models.

### The experiments

| | `pilot` | `main` |
|---|---|---|
| Purpose | Check everything works; measure real per-model cost | The actual comparison |
| Modes | Individual + Team | Individual + Team |
| Models | Haiku, Sonnet, Opus | Haiku, Sonnet, Opus |
| Rounds per debate | 1 | 3 |
| Seeds (repeats) | 1 | 4 (seeds 1-4) |
| Debates | 6 | 24 (2 modes × 3 models × 4 seeds) |
| Cost | ≈ $0.80 spent (including re-running Opus after the fix) | ≈ **$7.04** estimated (from pilot measurements), stop cap $7.20 |
| Status | ✅ done | not run yet |

Measured pilot cost per 1-round debate:

| | Haiku | Sonnet | Opus |
|---|---|---|---|
| Individual Mode | $0.025 | $0.051 | $0.095 |
| Team Mode | $0.037 | $0.096 | $0.214 |

### What each debate is measured on

Every debate saves a transcript with a full `cost_log` (one entry per AI call). `summarize.py` turns those into these metrics, averaged per mode and model:

| Metric | What it means | Range / how to read it | Comes from |
|---|---|---|---|
| **cost** | Total spend for the debate, report included | USD; lower is cheaper | Real token usage × price per model |
| **$/round** | cost ÷ rounds | USD | same |
| **calls** | Number of AI calls | Should be 43 (Individual) / 55 (Team) for 3 rounds: 14 or 18 per round + 1 report | `cost_log` |
| **trunc d/j** | Calls cut off by the word limit: debaters / judges | **Must be 0/0.** Anything else means some answers were cut short, and that run's scores are unreliable | `stop_reason: "max_tokens"` |
| **extremity** | How extreme or hostile the statements are | 1 (very moderate) to 10 (very extreme), averaged over every statement and round | Haiku extremity scorer, one call per statement |
| **ext drift** | Did the debate get more extreme over time? | Last round's average minus the first round's. **Positive = escalated**, negative = calmed down | same |
| **polarization** | How far apart the sides ended up | Final round's average PRO position minus average CON position. Positions run from −10 (fully against) to +10 (fully for), so the gap runs 0–20. **Higher = further apart**; negative would mean the sides crossed over | Haiku position scorer, one batched call per round |
| **pol drift** | Did the sides move apart or together? | Final gap minus first-round gap. **Positive = polarized further**, negative = converged | same |

The raw material is also saved for reading directly: every statement, the moderator's summary each round, the final report, and in Team Mode each round's proposals and critiques.

### How to run it

```bash
python -m model_eval.run_experiment main --dry-run   # the plan and cost estimate; spends nothing
python -m model_eval.run_experiment main             # type "main" to confirm
python -m model_eval.summarize main                  # re-print the results table any time
```

- **Duration:** expect roughly 1–2 hours for `main`. Keep the terminal open and the computer awake.
- **Stopping:** Ctrl+C, a rate limit or the spend cap stops the batch. Run the same command again to continue; finished debates are skipped and interrupted ones are retried.
- **Order:** debates run seed by seed, so an early stop still leaves every model with the same number of runs.
- **Key:** it uses `MODEL_EVAL_API_KEY` only, on its own workspace (with an $8 spend limit and its own rate limits).

**Output** goes to `model_eval/results/main/`:

| File | Contents |
|---|---|
| `transcript_<run>.json` | Everything about one debate |
| `report_<run>.md` | The final report (written by Haiku) |
| `logs/<run>.log` | Everything printed during that run |
| `summary.csv` | The averages table |
| `runs.csv` | One row per debate, with its seed |
| `spend_log.jsonl` | Actual vs estimated cost for every run |
| `experiment.json` | The settings and prices used |

### How to evaluate the outputs

Work through these in order. Each step decides whether the next one is worth trusting.

**1. Check the runs are valid.**
- Every row shows **4 runs** and no `✗` (interrupted runs).
- `trunc d/j` is **0/0** everywhere.
- `calls` is **43** (Individual) or **55** (Team) for every run. Fewer means something stopped early.
- Search the logs for scorer failures: `grep -l "Could not parse" model_eval/results/main/logs/*`. A failed position score becomes 0.
- A failed **extremity** score silently becomes **5** and leaves no trace. Treat any run where extremity is exactly 5.0 everywhere with suspicion.

If any check fails, fix the cause and re-run the affected debates before reading further.

**2. Compare cost.** Cost is the one measurement with no noise worth worrying about. It answers "what does the upgrade cost?": for example, Opus debates cost about 4–6× as much as Haiku ones in the pilot.

**3. Compare behaviour, using the seeds as pairs.** Every model ran the same 4 seeds, so compare **seed by seed** in `runs.csv`: Haiku seed 1 vs Opus seed 1, seed 2 vs seed 2, and so on. A difference between models is **probably real** only if both of these hold:
- **Same direction for every seed.** For example, Opus is more polarized than Haiku in all 4 pairs, not 3 of 4.
- **Bigger than the normal variation within a model.** Look at the spread of one model's 4 values. If Haiku's polarization ranges from 8 to 14, a 2-point gap between models means nothing.

With only 4 runs per group, anything weaker than that is **inconclusive**. Report it that way; don't call it a finding.

**4. Read the debates themselves.** The numbers don't show everything:
- Open the same seed across models (e.g. `transcript_main_team_all_haiku_s1.json` next to `..._all_opus_s1.json`) and compare them side by side.
- **Persona fidelity:** does Aggro still sound like a populist hardliner, and Hermes like an evidence-first moderate? A model that flattens the personas changes what the whole project measures.
- **Staying in character:** look for refusals, meta-commentary ("as an AI…"), or balanced answers from agents meant to be one-sided.
- **Evidence use:** each statement's `sources` list shows which retrieved sources the reply actually reflects (verified by text similarity).
- **Team Mode:** read the `brainstorm_log`. Does the synthesis actually combine the proposals, or just copy one?
- The moderator summaries and final reports give Haiku's written reading of each debate.

**5. State conclusions within their limits.** A good conclusion names the mode, the metric, the direction and the evidence. For example: *"In Team Mode, Opus debaters polarized further than Haiku in all 4 paired seeds (mean gap 15.2 vs 11.0), at 5.8× the cost."* Avoid "Opus is better at debating": nothing here measures quality.

### What it can't tell you

- **Quality isn't scored.** Extremity and position describe *how* a model debates, not how *well*. Higher extremity isn't better or worse; it's a different behaviour.
- **Haiku judges every model.** The scores are Haiku's reading of each debate, and a small model may read a larger model's more nuanced arguments differently.
- **One topic.** Results for "AI regulation" may not carry over to other topics.
- **Small sample:** 4 runs per group, 3 rounds each. Enough to spot large, consistent differences, not subtle ones.
- **The models aren't configured identically.** Opus still thinks a little; Sonnet doesn't think at all. This is the closest match the API allows.
- **Scorer noise and silent defaults** (a failed extremity score becomes 5; see step 1).
- **Prices are unverified** until checked against Anthropic's pricing page. Costs are computed from `PRICING` in `shared/config.py`, which may not match your actual bill.

### Guardrails

- The cost estimate is always shown first, and running requires typing the experiment name.
- It refuses to run unattended (no terminal, cron or piped input).
- **Spend cap per experiment:** it refuses to start if the estimate is over the cap, and stops before any run that would cross it. If runs cost more than estimated, later estimates are scaled up.
- It stops the whole batch on the first failed run.
- It uses only the eval workspace's API key. That workspace's spend limit in the Anthropic Console is the final backstop.

## To-do

**Week 8 — Flagship extensions ✅ Complete**

Team Mode is complete end-to-end: live propose → critique → synthesize brainstorms, rotating presenter, team-aware moderator and report, team-shaped transcripts tagged with their mode, and a History page that filters by mode and shows each team run's saved brainstorms. See [Recently completed](#recently-completed) for the full list.

Deferred to a later week (not started): dynamic agent count and mid-debate topic injection.

<hr>

**Model comparison**

- ✅ Runtime support: a model per role (profiles), per-call cost logging, seeding, and new transcript fields
- ✅ `model_eval/` harness with guardrails, cost estimates and summary tables; pilot run done
- **Next:** run `main` (24 debates, ≈ $7.04), then evaluate it following [How to evaluate the outputs](#how-to-evaluate-the-outputs)
- Optional: add a quality metric (argument strength, evidence use), judged by one fixed model across all runs

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
- Mode-specific final report: Team Mode uses its own prompt (team position drift, presenter effect, team radicalization, fault lines, verdict), and the report file records the mode
- Mode-specific transcript saving: every saved run has a `mode` field. Team runs also save `presenter_log`, `brainstorm_log` (proposals, critiques, per-proposal sources) and team statements. Older runs without `mode` are inferred from their logs
- History page: an All / Individual / Team toggle, a mode badge on each run, and a team detail view with the saved brainstorm shown above each team statement and no influence map. Comparisons label each run's mode and warn when modes are mixed
- Fixed: History never showed per-statement sources (the `/detail` endpoint's response model dropped `statements`), and Individual Mode saved only one statement per round. Older individual runs with incomplete statements fall back to the raw transcript
- History ordered newest first. It had been sorted by filename, and filenames became random session ids, so the order was effectively random. New runs now save a `saved_at` time; older runs fall back to the file's modified time
- History page polish: a single "History" entry point (the navbar); "← Back to Live" goes one step back to the debate as you left it (pre-, mid- or post-run); larger, centered "History" heading; the mode tag shows only under "All", with a coloured mode heading under "Individual"/"Team"; each run shows topic, round count, and a small italic DD/MM/YYYY date; long topics end in "…"
- Fixed duplicate events after reconnecting mid-run: the snapshot and the reopened stream both held events queued while the page was away. Events now carry a sequence number, and the frontend skips ones it has already applied
- Debate feed no longer yanks you to the bottom on every update: it follows new content only when you're at the bottom, and otherwise shows a WhatsApp-style "↓ N new" button
- Model profiles: every AI call belongs to a role, and a profile picks each role's model (default `all_haiku`, identical to before). The judges stay on Haiku in every profile
- Per-call cost logging (`cost_log`: role, model, tokens, cost, `stop_reason`), with `model_config`, `total_cost_usd`, `seed` and `experiment_id` saved in every transcript
- Seeded runs: one seed controls turn order, presenter order and the order proposals appear in prompts
- The scorers moved from LangChain to direct Anthropic SDK calls with identical requests
- Fixed: the moderator's summary was being cut off at 300 tokens even on Haiku (now 500); `.env` is now loaded explicitly instead of through an incidental import chain
- `model_eval/` harness: experiments, a runner with guardrails, cost estimates that learn from measured runs, and summary tables (`summary.csv`, `runs.csv`)
- Opus thinking allowance (+1,000 `max_tokens`): the pilot showed Opus's thinking using up the critique budget, leaving 18–83-word critiques


## Status

Week 8 is complete, and both modes are functional end-to-end. Individual Mode (web RAG → 6-agent debate → moderator → analysis report) remains validated across multiple topics. Team Mode runs a genuine team debate: private propose → critique → synthesize brainstorms, a rotating presenter, a team-aware moderator and report, and team-shaped saved transcripts. The History page lists runs of either mode newest first, with a mode filter and a team-aware detail view.

The model comparison is built and piloted: model profiles with fixed Haiku judges, per-call cost logging, seeded runs, and the `model_eval/` harness. The pilot confirmed every model runs cleanly with no truncated answers, and measured real costs. Next is running `main` (24 debates, ≈ $7.04) and evaluating it, followed by the hosted vector DB migration, automation, and deploy.
