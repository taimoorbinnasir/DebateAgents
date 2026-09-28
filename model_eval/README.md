# model_eval — Haiku vs Sonnet vs Opus

Runs the same debates with different models and compares cost and debate behaviour.

## How a comparison works

- A **profile** picks the model for the debating roles (`agent_turn`, or `draft` / `critique` / `synthesis` in Team Mode). Profiles are `all_haiku`, `all_sonnet` and `all_opus`, defined in `shared/config.py`.
- The **judges** (moderator, extremity scorer, position scorer, report) are **always Haiku**, so only the debaters change between profiles. This isn't just about grading: the moderator's summary goes into the debate history, so fixing it also keeps what the debaters see the same.
- Every profile runs with the **same seeds**, so turn order, presenter order and prompt shuffles match across models. Model outputs still vary, so each experiment repeats over several seeds and you compare the averages.
- Runs use **`MODEL_EVAL_API_KEY`** (its own workspace, billing and rate limits), never the web app's key.

## Usage (from the project root)

```bash
python -m model_eval.run_experiment pilot --dry-run   # plan + cost estimate, spends nothing
python -m model_eval.run_experiment pilot             # type "pilot" to confirm and run
python -m model_eval.summarize pilot                  # re-print the comparison table
```

Suggested order: run **`pilot`** first (1 round, 1 run per model per mode, ≈ $0.40). It measures real Sonnet/Opus costs and shows whether anything gets truncated. Then **`main`** (3 rounds × 5 seeds, ≈ $6). Its dry-run estimate uses the pilot's measured costs automatically.

Experiments are defined in `experiments.py`: topic, modes, profiles, rounds, seeds and a spend cap.

## Guardrails

- The plan and cost estimate are always printed first. `--dry-run` stops there.
- Running requires typing the experiment name, and refuses without an interactive terminal (no cron, CI or piped input).
- **Spend cap per experiment** (`max_spend_usd`): the runner refuses to start if the estimate exceeds it, and stops before any run that would cross it. The workspace spend limit in the Anthropic Console is the hard backstop.
- **Stops the whole batch on the first failed run** (for example, rate limits), instead of repeating the failure.
- **Resumable:** re-running the same command skips completed runs and retries interrupted ones.
- Runs one simulation at a time, which is what the workspace rate limits were sized for.

## Output: `model_eval/results/<experiment>/` (gitignored)

| File | What |
|---|---|
| `transcript_<run>.json` | Full saved run, including `model_config`, `cost_log` (every call's tokens, cost and `stop_reason`), `total_cost_usd` and `seed` |
| `report_<run>.md` | The final report (written by Haiku) |
| `logs/<run>.log` | Everything the simulation printed during that run |
| `spend_log.jsonl` | One line per run with the actual vs estimated cost. Append-only, so it includes interrupted runs |
| `experiment.json` | The spec, profiles and prices used when the experiment started |
| `summary.csv` | The comparison table |

These runs don't appear on the History page, which only reads `Resources/simulations/`.

## Reading the summary

Metrics are averaged per mode and profile:
- **cost**, **$/round** and **calls**;
- **truncated calls** (should be 0);
- mean **extremity** (1–10), and **extremity drift** (last round minus first);
- **polarization**: final mean PRO position minus mean CON position, and its **drift** across rounds.

The drift columns need 2 or more rounds.

**Caveats:**
- These are Haiku's readings of each model's debate.
- A seed fixes ordering, not content.
- With about 5 runs per cell, small differences are likely noise.
- Prices in `shared/config.py` are unverified until checked against Anthropic's pricing page.
- Debate *quality* (argument strength, evidence use) isn't scored yet. The tables cover cost and the project's existing extremity and position metrics.
