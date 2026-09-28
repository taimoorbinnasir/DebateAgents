"""
Cost estimates for planned runs, shown before anything is spent.

Two sources, best first:
1. MEASURED — earlier results in model_eval/results/ for the same mode + profile:
   average real cost per round (from cost_log) plus the report call.
2. BASELINE — average tokens per call, per role, measured on real 1-round Haiku runs
   ("AI regulation", Sept 2026), priced with each profile's model. Rough for Sonnet/Opus:
   their replies may be longer, and Opus still thinks a little at effort "low".
"""
import glob, json, os
from collections import defaultdict
from shared.config import MODEL_PROFILES, compute_cost

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

# (avg input tokens, avg output tokens, calls per round) per role, from real Haiku runs
BASELINE_PER_ROUND = {
    "individual": {
        "agent_turn":       (1257, 200, 6),
        "extremity_scorer": (238,  5,   6),
        "position_scorer":  (1331, 78,  1),
        "moderator":        (1353, 300, 1),
    },
    "team": {
        "draft":            (796,  190, 6),
        "critique":         (1163, 217, 6),
        "synthesis":        (2138, 223, 2),
        "extremity_scorer": (260,  5,   2),
        "position_scorer":  (530,  15,  1),
        "moderator":        (673,  289, 1),
    },
}
# Report: one call per run; its input grows with the transcript (≈ one round's text per round)
BASELINE_REPORT = {
    "individual": {"input": 1993, "input_per_extra_round": 1500, "output": 365},
    "team":       {"input": 1295, "input_per_extra_round": 750,  "output": 376},
}

BASELINE_MARGIN = 1.3   # later rounds carry more context; replies vary in length
MEASURED_MARGIN = 1.15  # measured data is much closer, but runs still vary
# Opus 5.5 can't turn thinking off (effort "low" is the floor); its thinking tokens bill as output
OUTPUT_MULTIPLIER = {"claude-opus-5-5": 1.5}


def _report_scale(rounds: int) -> float:
    """Report cost relative to a 1-round run. Only its input grows with the transcript
    (output doesn't): on the baseline numbers, 3 rounds ≈ 1.8x → ~+50% per extra round."""
    return 1 + 0.5 * (rounds - 1)


def _baseline_estimate(mode: str, profile: str, rounds: int) -> float:
    roles = MODEL_PROFILES[profile]
    total = 0.0
    for role, (inp, out, calls) in BASELINE_PER_ROUND[mode].items():
        model = roles[role]
        out = out * OUTPUT_MULTIPLIER.get(model, 1.0)
        total += compute_cost(model, inp, out) * calls * rounds
    rep = BASELINE_REPORT[mode]
    report_model = roles["report"]
    report_in = rep["input"] + rep["input_per_extra_round"] * (rounds - 1)
    total += compute_cost(report_model, report_in, rep["output"] * OUTPUT_MULTIPLIER.get(report_model, 1.0))
    return total * BASELINE_MARGIN


def _measured_rates() -> dict:
    """{(mode, profile): (avg cost per round excluding report, avg report cost, n runs)}"""
    per_round, report, count = defaultdict(list), defaultdict(list), defaultdict(int)
    for path in glob.glob(os.path.join(RESULTS_DIR, "*", "transcript_*.json")):
        try:
            with open(path) as f:
                t = json.load(f)
            if str(t.get("stop_reason", "")).startswith("Simulation interrupted"):
                continue  # partial runs would under-state cost
            key = (t["mode"], t["model_config"]["profile"])
            rounds = max((len(v) for v in t["extremity_log"].values()), default=0)
            if rounds == 0:
                continue
            report_cost = sum(e["cost_usd"] for e in t["cost_log"] if e["role"] == "report")
            per_round[key].append((t["total_cost_usd"] - report_cost) / rounds)
            report[key].append(report_cost / _report_scale(rounds))  # stored as 1-round equivalent
            count[key] += 1
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return {k: (sum(per_round[k]) / len(per_round[k]), sum(report[k]) / len(report[k]), count[k])
            for k in count}


def estimate_run(mode: str, profile: str, rounds: int, measured: dict | None = None) -> tuple[float, str]:
    """(estimated USD for one run, where the estimate came from)"""
    measured = _measured_rates() if measured is None else measured
    if (mode, profile) in measured:
        per_round, report, n = measured[(mode, profile)]
        return (per_round * rounds + report * _report_scale(rounds)) * MEASURED_MARGIN, \
               f"measured ({n} run{'s' if n > 1 else ''})"
    return _baseline_estimate(mode, profile, rounds), "baseline"
