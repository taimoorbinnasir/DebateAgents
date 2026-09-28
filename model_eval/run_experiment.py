"""
Run a model-comparison experiment (see experiments.py).

    python -m model_eval.run_experiment pilot --dry-run   # plan + cost estimate only, spends nothing
    python -m model_eval.run_experiment pilot             # asks you to type "pilot" before spending

Guardrails:
- Prints every planned run with its cost estimate before anything is spent.
- Needs you to type the experiment name to start, and refuses to run without a terminal
  (no cron / CI / piped input — no unattended spending).
- Stops before a run would push total spend past the experiment's max_spend_usd. If runs cost
  more than estimated, later estimates are scaled up by the worst overrun seen so far. A
  single run can still exceed its estimate; the workspace spend limit is the hard backstop.
- Stops the whole batch on the first failed or interrupted run (e.g. rate limits).
- Uses MODEL_EVAL_API_KEY only (its own workspace, billing and rate limits) — never the
  web app's ANTHROPIC_API_KEY.
- Resumable: completed runs are skipped, so re-running continues. Interrupted runs count as
  not done and are retried. Every run's cost (interrupted ones too) is appended to
  results/<experiment>/spend_log.jsonl, so overwriting a transcript never loses spend.
- Runs one simulation at a time (the workspace rate limits assume this).
"""
import os, sys, json, argparse, contextlib, traceback
from datetime import datetime

# Chroma opens ./memory_db at import time, relative to the working directory — run from the
# project root, where the cached web sources live, BEFORE importing any simulation module
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from shared.config import MODEL_PROFILES, PRICING, JUDGE_ROLES, JUDGE_MODEL  # also loads .env
from model_eval.experiments import EXPERIMENTS, expand_runs
from model_eval.estimate import estimate_run, _measured_rates, RESULTS_DIR
from model_eval.summarize import print_summary


def is_complete(transcript_path: str) -> bool:
    if not os.path.exists(transcript_path):
        return False
    try:
        with open(transcript_path) as f:
            return not str(json.load(f).get("stop_reason", "")).startswith("Simulation interrupted")
    except (json.JSONDecodeError, OSError):
        return False


def check_sources_cached(topic: str) -> list[str]:
    """Agents with no cached web sources for this topic (they'd trigger SerpApi searches)."""
    from shared.agents import AGENT_PARAMS
    from shared.config import topic_key
    from shared.memory import chroma
    existing = {c.name for c in chroma.list_collections()}
    missing = []
    for p in AGENT_PARAMS.values():
        name = f"agent_{p['name']}_sources_{topic_key(topic)}"
        if name not in existing or not chroma.get_collection(name).get(where={"topic": topic}, limit=1)["ids"]:
            missing.append(p["name"])
    return missing


def main():
    parser = argparse.ArgumentParser(description="Run a DebateAgents model-comparison experiment.")
    parser.add_argument("experiment", choices=sorted(EXPERIMENTS))
    parser.add_argument("--dry-run", action="store_true", help="show the plan and cost estimate, spend nothing")
    args = parser.parse_args()

    experiment_id = args.experiment
    spec = EXPERIMENTS[experiment_id]
    out_dir = os.path.join(RESULTS_DIR, experiment_id)
    runs = expand_runs(experiment_id)
    for r in runs:
        r["done"] = is_complete(os.path.join(out_dir, f"transcript_{r['run_id']}.json"))
    pending = [r for r in runs if not r["done"]]

    # ---------- API key: the eval workspace's key, never the web app's
    api_key = os.environ.get("MODEL_EVAL_API_KEY")
    if not api_key:
        sys.exit("❌ MODEL_EVAL_API_KEY is not set (add it to .env). Refusing to fall back to ANTHROPIC_API_KEY.")
    if api_key == os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  MODEL_EVAL_API_KEY is the same key as ANTHROPIC_API_KEY — spend won't be separated from the web app.")

    # ---------- Plan + estimate
    measured = _measured_rates()
    total_est = 0.0
    print(f"\nExperiment '{experiment_id}': topic '{spec['topic']}', {spec['rounds']} round(s), "
          f"seeds {spec['seeds']}")
    print(f"Judges ({', '.join(JUDGE_ROLES)}) on {JUDGE_MODEL} in every profile.\n")
    print(f"  {'run':<42}{'status':<9}{'estimate':>10}  source")
    for r in runs:
        est, source = estimate_run(r["mode"], r["profile"], r["rounds"], measured)
        r["estimate"] = est
        if not r["done"]:
            total_est += est
        print(f"  {r['run_id']:<42}{'done' if r['done'] else 'pending':<9}"
              f"{'' if r['done'] else f'${est:.3f}':>10}  {'' if r['done'] else source}")
    cap = spec["max_spend_usd"]
    print(f"\n  {len(pending)} of {len(runs)} runs pending · estimated ${total_est:.2f} · "
          f"stop cap ${cap:.2f} (experiments.py)")
    print("  Prices in shared/config.py PRICING are unverified — check Anthropic's pricing page.")

    missing = check_sources_cached(spec["topic"])
    if missing:
        print(f"\n⚠️  No cached sources for {', '.join(missing)} on this topic: the first run will "
              f"make {len(missing)} SerpApi searches (no Anthropic cost).")

    if not pending:
        print("\nNothing to run — all runs are done.")
        print_summary(experiment_id)
        return
    if total_est > cap:
        sys.exit(f"\n❌ Estimate ${total_est:.2f} exceeds the cap ${cap:.2f}. "
                 f"Reduce seeds/rounds or raise max_spend_usd in experiments.py.")
    if args.dry_run:
        print("\n(dry run — nothing spent)")
        return

    # ---------- Explicit confirmation, interactive only
    if not sys.stdin.isatty():
        sys.exit("\n❌ Refusing to run without an interactive terminal (no unattended spending).")
    answer = input(f"\nType '{experiment_id}' to run {len(pending)} simulations "
                   f"(est. ${total_est:.2f}), anything else to cancel: ").strip()
    if answer != experiment_id:
        sys.exit("Cancelled — nothing spent.")

    # ---------- Record what was run (spec + pricing + profiles at this moment)
    os.makedirs(os.path.join(out_dir, "logs"), exist_ok=True)
    with open(os.path.join(out_dir, "experiment.json"), "w") as f:
        json.dump({"experiment_id": experiment_id, "started_at": datetime.now().isoformat(timespec="seconds"),
                   "spec": spec, "profiles": {p: MODEL_PROFILES[p] for p in spec["profiles"]},
                   "pricing": PRICING}, f, indent=2)

    from Week5.DebateAgents import run_simulation_streamed

    spent = 0.0
    overrun = 1.0  # worst actual/estimate ratio so far; only ever scales estimates up
    for i, r in enumerate(pending, 1):
        next_est = r["estimate"] * overrun
        if spent + next_est > cap:
            print(f"\n🛑 Stopping: the next run (est. ${next_est:.3f}"
                  f"{f', scaled x{overrun:.1f} for overruns so far' if overrun > 1 else ''}) would pass "
                  f"the cap (${spent:.2f} spent of ${cap:.2f}). Re-run later to continue.")
            break

        print(f"[{i}/{len(pending)}] {r['run_id']} … ", end="", flush=True)
        log_path = os.path.join(out_dir, "logs", f"{r['run_id']}.log")
        try:
            # The simulation prints a lot (every turn, every event) — keep it in a per-run log
            with open(log_path, "w") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                run_simulation_streamed(
                    r["topic"], r["rounds"], r["run_id"], mode=r["mode"],
                    model_profile=r["profile"], seed=r["seed"],
                    experiment_id=experiment_id, output_dir=out_dir, api_key=api_key,
                )
        except KeyboardInterrupt:
            print("\n🛑 Interrupted. Completed runs are saved; re-run the same command to continue.")
            break
        except Exception:
            print(f"\n❌ Run crashed — its cost wasn't recorded (check the workspace in the Console). "
                  f"Traceback in {log_path}")
            with open(log_path, "a") as log:
                traceback.print_exc(file=log)
            break

        with open(os.path.join(out_dir, f"transcript_{r['run_id']}.json")) as f:
            t = json.load(f)
        spent += t["total_cost_usd"]
        if r["estimate"] > 0:
            overrun = max(overrun, t["total_cost_usd"] / r["estimate"])
        with open(os.path.join(out_dir, "spend_log.jsonl"), "a") as f:
            f.write(json.dumps({"run_id": r["run_id"], "at": datetime.now().isoformat(timespec="seconds"),
                                "cost_usd": t["total_cost_usd"], "estimate_usd": round(r["estimate"], 5),
                                "stop_reason": t["stop_reason"]}) + "\n")
        truncated = sum(1 for e in t["cost_log"] if e["stop_reason"] == "max_tokens")
        print(f"${t['total_cost_usd']:.3f} (est. ${r['estimate']:.3f}) · {len(t['cost_log'])} calls"
              f"{f' · ⚠️ {truncated} truncated' if truncated else ''} · total ${spent:.2f}")

        # Failures inside the loop are caught by the simulation and saved as "Simulation
        # interrupted: ..." — stop instead of repeating the failure (and its cost) on every run
        if str(t["stop_reason"]).startswith("Simulation interrupted"):
            print(f"🛑 Stopping batch: {t['stop_reason']}")
            print("   Fix the cause, then re-run the same command — this run will be retried.")
            break

    print_summary(experiment_id)


if __name__ == "__main__":
    main()
