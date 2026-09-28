"""
Experiment definitions for the model comparison.

Each experiment expands into runs: every mode × every profile × every seed.
The same seeds are used for every profile, so each model gets the same turn order,
presenter order and prompt shuffles (LLM output itself still varies between runs —
that's what the repeats are for).

Profiles (shared/config.py): the debating roles use the profile's model; the judges
(moderator, scorers, report) are always Haiku.
"""

EXPERIMENTS = {
    # Small first run: one of everything, 1 round. Measures real per-model cost
    # (especially Opus's effort-low thinking) and checks for truncation before
    # committing to the main run. Estimated ≈ $0.40.
    "pilot": {
        "topic":       "AI regulation",   # sources already cached → no SerpApi searches
        "modes":       ["individual", "team"],
        "profiles":    ["all_haiku", "all_sonnet", "all_opus"],
        "rounds":      1,
        "seeds":       [1],
        "max_spend_usd": 1.00,            # the runner stops before exceeding this
    },

    # Main comparison: 4 repeats (seeds) per model per mode, 3 rounds each.
    # Estimated ≈ $7.04 from the pilot's measured costs.
    "main": {
        "topic":       "AI regulation",
        "modes":       ["individual", "team"],
        "profiles":    ["all_haiku", "all_sonnet", "all_opus"],
        "rounds":      3,
        "seeds":       [1, 2, 3, 4],
        "max_spend_usd": 7.20,            # $8 workspace limit − ~$0.80 already spent on the pilot
    },
}


def expand_runs(experiment_id: str) -> list[dict]:
    """One dict per simulation to run, in a stable order."""
    spec = EXPERIMENTS[experiment_id]
    runs = []
    for seed in spec["seeds"]:                 # seed-major: a partial batch still covers
        for mode in spec["modes"]:             # every model, instead of finishing Haiku first
            for profile in spec["profiles"]:
                runs.append({
                    "run_id":  f"{experiment_id}_{mode}_{profile}_s{seed}",
                    "topic":   spec["topic"],
                    "mode":    mode,
                    "profile": profile,
                    "rounds":  spec["rounds"],
                    "seed":    seed,
                })
    return runs
