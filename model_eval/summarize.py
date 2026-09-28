"""
Summarize an experiment's results into one comparison table per mode.

    python -m model_eval.summarize pilot

Writes model_eval/results/<experiment>/summary.csv as well.

Metrics (averaged over runs; each run's numbers come from its saved transcript):
- cost, cost/round, calls   — real API spend from cost_log
- truncated                 — calls cut off by max_tokens (debaters vs judges); should be 0
- extremity                 — mean extremity score, 1-10, all speakers and rounds
- extremity drift           — last round's mean minus first round's (needs 2+ rounds)
- polarization              — final round: mean PRO position minus mean CON position (-10..10
                              scale, so the gap is 0-20; higher = sides further apart)
- polarization drift        — change in that gap from the first round to the last (2+ rounds)

Caveats: the judges (scorers, moderator, report) are Haiku in every profile, so these are
Haiku's readings of each model's debate. A seed fixes ordering, not what the models say —
compare averages across seeds, and treat small differences with few runs as noise.
"""
import os, sys, csv, glob, json
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.agents import AGENT_PARAMS
from shared.config import JUDGE_ROLES, MODEL_PROFILES

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def _stance(key: str) -> str:
    """Log keys: agent_ids in individual mode, 'pro'/'con' in team mode."""
    return AGENT_PARAMS[key]["stance"] if key in AGENT_PARAMS else key


def _round_means(log: dict, stance: str | None = None) -> list[float]:
    """Mean score per round across speakers (optionally only one side)."""
    series = [v for k, v in log.items() if stance is None or _stance(k) == stance]
    rounds = max((len(v) for v in series), default=0)
    means = []
    for i in range(rounds):
        vals = [v[i] for v in series if i < len(v) and v[i] is not None]
        means.append(sum(vals) / len(vals) if vals else None)
    return means


def run_metrics(t: dict) -> dict:
    ext = _round_means(t["extremity_log"])
    pro, con = _round_means(t["position_log"], "pro"), _round_means(t["position_log"], "con")
    gaps = [p - c for p, c in zip(pro, con) if p is not None and c is not None]
    rounds = len(ext)
    all_ext = [x for v in t["extremity_log"].values() for x in v if x is not None]
    trunc = [e for e in t["cost_log"] if e["stop_reason"] == "max_tokens"]
    return {
        "cost":            t["total_cost_usd"],
        "cost_per_round":  t["total_cost_usd"] / rounds if rounds else None,
        "calls":           len(t["cost_log"]),
        "trunc_debaters":  sum(1 for e in trunc if e["role"] not in JUDGE_ROLES),
        "trunc_judges":    sum(1 for e in trunc if e["role"] in JUDGE_ROLES),
        "extremity":       sum(all_ext) / len(all_ext) if all_ext else None,
        "extremity_drift": ext[-1] - ext[0] if rounds >= 2 and None not in (ext[0], ext[-1]) else None,
        "polarization":    gaps[-1] if gaps else None,
        "polarization_drift": gaps[-1] - gaps[0] if len(gaps) >= 2 else None,
    }


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def summarize(experiment_id: str) -> list[dict]:
    groups, interrupted = defaultdict(list), defaultdict(int)
    for path in sorted(glob.glob(os.path.join(RESULTS_DIR, experiment_id, "transcript_*.json"))):
        with open(path) as f:
            t = json.load(f)
        key = (t["mode"], t["model_config"]["profile"])
        if str(t["stop_reason"]).startswith("Simulation interrupted"):
            interrupted[key] += 1
            continue
        groups[key].append(run_metrics(t))

    rows = []
    # profiles in MODEL_PROFILES order (cheapest → most capable), not alphabetical
    order = {p: i for i, p in enumerate(MODEL_PROFILES)}
    for (mode, profile) in sorted(set(groups) | set(interrupted), key=lambda k: (k[0], order.get(k[1], 99), k[1])):
        ms = groups.get((mode, profile), [])
        row = {"mode": mode, "profile": profile, "runs": len(ms), "interrupted": interrupted[(mode, profile)]}
        for field in ("cost", "cost_per_round", "calls", "extremity", "extremity_drift",
                      "polarization", "polarization_drift"):
            row[field] = _mean(m[field] for m in ms)
        row["trunc_debaters"] = sum(m["trunc_debaters"] for m in ms)
        row["trunc_judges"]   = sum(m["trunc_judges"] for m in ms)
        rows.append(row)
    return rows


def _fmt(v, spec):
    return "–" if v is None else format(v, spec)


def print_summary(experiment_id: str):
    rows = summarize(experiment_id)
    if not rows:
        print(f"\nNo results yet for '{experiment_id}'.")
        return

    print(f"\n=== Summary: {experiment_id} (averages per run) ===")
    for mode in ("individual", "team"):
        mode_rows = [r for r in rows if r["mode"] == mode]
        if not mode_rows:
            continue
        print(f"\n{mode.upper()} MODE")
        print(f"  {'profile':<11}{'runs':>5}{'cost':>9}{'$/round':>9}{'calls':>7}{'trunc d/j':>11}"
              f"{'extremity':>11}{'ext drift':>11}{'polariz.':>10}{'pol drift':>11}")
        for r in mode_rows:
            runs = f"{r['runs']}" + (f"+{r['interrupted']}✗" if r["interrupted"] else "")
            print(f"  {r['profile']:<11}{runs:>5}{_fmt(r['cost'], '.3f'):>9}{_fmt(r['cost_per_round'], '.3f'):>9}"
                  f"{_fmt(r['calls'], '.0f'):>7}{str(r['trunc_debaters']) + '/' + str(r['trunc_judges']):>11}"
                  f"{_fmt(r['extremity'], '.2f'):>11}{_fmt(r['extremity_drift'], '+.2f'):>11}"
                  f"{_fmt(r['polarization'], '.1f'):>10}{_fmt(r['polarization_drift'], '+.1f'):>11}")
    total = sum((r["cost"] or 0) * r["runs"] for r in rows)
    print(f"\n  Completed-run spend: ${total:.2f}  (see spend_log.jsonl for every run, incl. interrupted)")
    print("  ✗ = interrupted runs (excluded).  trunc d/j = truncated calls, debaters/judges — should be 0.")
    print("  Drift columns need 2+ rounds. Judges are Haiku in every profile.")

    path = os.path.join(RESULTS_DIR, experiment_id, "summary.csv")
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  CSV: {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m model_eval.summarize <experiment>")
    print_summary(sys.argv[1])
