"""
Multi-seed robustness evaluation: V5 baseline vs Hybrid V5 + Isolation Forest.

Design:
- 10 independent replication seed bases (1001..1010)
- 5 fixed synthetic channel scenarios per replication
- 50 generated traces, 100 controller executions
- Same generated trace is supplied to V5 and Hybrid for paired comparison
- Isolation Forest is trained on t=0..219 of that replication's baseline trace
  and reused across all five scenarios in the same replication
- IF model random_state remains fixed at 42 to isolate variation in QKD traces
- Hybrid IF persistence is fixed at 3
- IF QBER confirmation threshold is fixed at 0.0600

This is a synthetic system-level robustness experiment, not physical QKD
or real cyberattack validation. PQC rekey success remains simulated.
"""

from pathlib import Path
import sys
import random
import importlib.util

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


ROOT = Path.cwd()
SRC = ROOT / "src"
OUTPUT_DIR = ROOT / "results" / "multi_seed_robustness_v5_hybrid"

REPLICATION_SEEDS = list(range(1001, 1011))  # 10 independent replications
DURATION = 508

NORMAL_RATE_RANGE = (850, 1300)
DEGRADED_RATE_RANGE = (450, 1150)
NORMAL_QBER_RANGE = (0.015, 0.090)
DEGRADED_QBER_RANGE = (0.055, 0.130)

SCENARIOS = {
    "baseline": {
        "type": "intervals",
        "intervals": [(220, 280)],
        "seed_offset": 0,
    },
    "short": {
        "type": "intervals",
        "intervals": [(220, 230)],
        "seed_offset": 1,
    },
    "long": {
        "type": "intervals",
        "intervals": [(220, 400)],
        "seed_offset": 2,
    },
    "multiple": {
        "type": "intervals",
        "intervals": [(100, 130), (300, 360)],
        "seed_offset": 3,
    },
    "gradual": {
        "type": "gradual",
        "intervals": [(220, 280)],
        "seed_offset": 4,
    },
}

FEATURES = ["qber", "qkd_generation_bps"]
TRAIN_START = 0
TRAIN_END_EXCLUSIVE = 220
IF_ESTIMATORS = 300
IF_CONTAMINATION = 0.05
IF_RANDOM_STATE = 42

HYBRID_PERSISTENCE = 3
IF_QBER_CONFIRMATION_THRESHOLD = 0.0600


def import_from_path(module_name, path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def is_degraded(time_value, intervals):
    return any(start <= time_value < end for start, end in intervals)


def generate_qkd_scenario(scenario_name, configuration, seed):
    """Reuses the project's established synthetic scenario generation logic."""
    rng = random.Random(seed)
    scenario_type = configuration["type"]
    intervals = configuration["intervals"]
    rows = []

    for time_value in range(DURATION):
        degraded = is_degraded(time_value, intervals)

        if scenario_type == "intervals":
            if degraded:
                rate = rng.uniform(*DEGRADED_RATE_RANGE)
                qber = rng.uniform(*DEGRADED_QBER_RANGE)
                channel_status = "degraded"
            else:
                rate = rng.uniform(*NORMAL_RATE_RANGE)
                qber = rng.uniform(*NORMAL_QBER_RANGE)
                channel_status = "normal"

        elif scenario_type == "gradual":
            start, end = intervals[0]

            if time_value < start or time_value >= end:
                progress = 0.0
            else:
                midpoint = (start + end) / 2
                if time_value <= midpoint:
                    progress = (time_value - start) / (midpoint - start)
                else:
                    progress = (end - time_value) / (end - midpoint)

            progress = max(0.0, min(1.0, progress))

            normal_qber = rng.uniform(*NORMAL_QBER_RANGE)
            degraded_qber = rng.uniform(*DEGRADED_QBER_RANGE)
            normal_rate = rng.uniform(*NORMAL_RATE_RANGE)
            degraded_rate = rng.uniform(*DEGRADED_RATE_RANGE)

            qber = normal_qber * (1 - progress) + degraded_qber * progress
            rate = normal_rate * (1 - progress) + degraded_rate * progress
            channel_status = "degraded" if progress >= 0.5 else "normal"

        else:
            raise ValueError(f"Unknown scenario: {scenario_name}")

        rows.append({
            "time_seconds": time_value,
            "generated_key_bits": int(round(rate)),
            "qkd_generation_bps": round(rate, 3),
            "qber": round(qber, 6),
            "channel_status": channel_status,
        })

    return pd.DataFrame(rows)


def fit_if_on_baseline(baseline_df):
    train = baseline_df[
        (baseline_df["time_seconds"] >= TRAIN_START)
        & (baseline_df["time_seconds"] < TRAIN_END_EXCLUSIVE)
    ]
    if len(train) != 220:
        raise ValueError(f"Expected 220 IF training rows, found {len(train)}")

    scaler = StandardScaler()
    x_train = scaler.fit_transform(train[FEATURES].astype(float))

    model = IsolationForest(
        n_estimators=IF_ESTIMATORS,
        contamination=IF_CONTAMINATION,
        max_samples="auto",
        random_state=IF_RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(x_train)
    return scaler, model, len(train)


def score_scenario(df, scaler, model):
    x_all = scaler.transform(df[FEATURES].astype(float))
    predictions = model.predict(x_all)
    scored = df.copy()
    scored["anomaly_score"] = model.decision_function(x_all)
    scored["anomaly_prediction"] = (predictions == -1).astype(int)
    return scored


def normalize_events(events):
    if isinstance(events, pd.DataFrame):
        return events.to_dict(orient="records")
    return [dict(item) for item in events]


def get_fallback_times(events):
    times = []
    for event in normalize_events(events):
        new_mode = str(event.get("new_mode", "")).upper()
        if new_mode in {"PQC", "PQC_FALLBACK"}:
            times.append(int(event["time_seconds"]))
    return sorted(times)


def get_if_fallback_times(events):
    times = []
    for event in normalize_events(events):
        reason = str(event.get("reason", "")).upper()
        if reason == "ISOLATION_FOREST_PERSISTENT_ANOMALY":
            times.append(int(event["time_seconds"]))
    return sorted(times)


def evaluate_run(replication_seed, scenario, controller_name,
                 events, summary, intervals):
    fallback_times = get_fallback_times(events)
    if_fallback_times = get_if_fallback_times(events)

    false_fallback_times = [
        t for t in fallback_times
        if not any(start <= t < end for start, end in intervals)
    ]

    delays = []
    missed_intervals = 0
    for start, end in intervals:
        matched = [t for t in fallback_times if start <= t < end]
        if matched:
            delays.append(min(matched) - start)
        else:
            missed_intervals += 1

    expected = int(summary["accounting_expected_bits"])
    actual = int(summary["accounting_actual_bits"])
    accounting_valid = bool(summary["accounting_valid"]) and expected == actual

    return {
        "replication_seed": replication_seed,
        "scenario": scenario,
        "controller": controller_name,
        "fallback_count": len(fallback_times),
        "recovery_count": int(summary["recovery_count"]),
        "fallback_times_seconds": ";".join(map(str, fallback_times)),
        "if_triggered_fallback_count": len(if_fallback_times),
        "if_triggered_fallback_times_seconds": ";".join(map(str, if_fallback_times)),
        "false_fallback_count": len(false_fallback_times),
        "false_fallback_times_seconds": ";".join(map(str, false_fallback_times)),
        "missed_degradation_intervals": missed_intervals,
        "fallback_delay_values_seconds": ";".join(map(str, delays)),
        "mean_detected_fallback_delay_seconds": (
            float(np.mean(delays)) if delays else np.nan
        ),
        "qkd_duration_seconds": int(summary["qkd_duration_seconds"]),
        "pqc_duration_seconds": int(summary["pqc_duration_seconds"]),
        "qkd_successful_rekeys": int(summary["qkd_successful_rekeys"]),
        "pqc_simulated_successful_rekeys": int(
            summary["pqc_simulated_successful_rekeys"]
        ),
        "total_successful_rekeys": int(summary["total_successful_rekeys"]),
        "failed_qkd_rekeys": int(summary["failed_qkd_rekeys"]),
        "final_pool_bits": int(summary["final_pool_bits"]),
        "accounting_expected_bits": expected,
        "accounting_actual_bits": actual,
        "accounting_valid": accounting_valid,
    }


def aggregate_results(detail_df):
    rows = []
    for (controller, scenario), group in detail_df.groupby(
        ["controller", "scenario"], sort=True
    ):
        rows.append({
            "controller": controller,
            "scenario": scenario,
            "replications": int(len(group)),
            "total_false_fallbacks": int(group["false_fallback_count"].sum()),
            "total_missed_intervals": int(
                group["missed_degradation_intervals"].sum()
            ),
            "total_if_triggered_fallbacks": int(
                group["if_triggered_fallback_count"].sum()
            ),
            "mean_pqc_duration_seconds": float(
                group["pqc_duration_seconds"].mean()
            ),
            "std_pqc_duration_seconds": float(
                group["pqc_duration_seconds"].std(ddof=1)
            ),
            "mean_qkd_duration_seconds": float(
                group["qkd_duration_seconds"].mean()
            ),
            "mean_fallback_delay_seconds": float(
                group["mean_detected_fallback_delay_seconds"].mean()
            ),
            "mean_fallback_count": float(group["fallback_count"].mean()),
            "all_accounting_valid": bool(group["accounting_valid"].all()),
        })
    return pd.DataFrame(rows)


def main():
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))

    v5 = import_from_path("adaptive_controller_v5", SRC / "adaptive_controller_v5.py")
    hybrid = import_from_path(
        "anomaly_detection_v5_hybrid_confirmation",
        SRC / "anomaly_detection_v5_hybrid_confirmation.py",
    )

    all_rows = []
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    original_persistence = hybrid.ANOMALY_PERSISTENCE_REQUIRED
    try:
        hybrid.ANOMALY_PERSISTENCE_REQUIRED = HYBRID_PERSISTENCE

        for replication_seed in REPLICATION_SEEDS:
            print(f"Running replication seed {replication_seed}...")

            scenario_frames = {}
            scenario_seeds = {}

            for scenario, config in SCENARIOS.items():
                # Each replication gets a distinct deterministic seed per scenario.
                scenario_seed = replication_seed * 10 + config["seed_offset"]
                scenario_seeds[scenario] = scenario_seed
                scenario_frames[scenario] = generate_qkd_scenario(
                    scenario, config, scenario_seed
                )

            # Fit one IF model per replication on that replication's normal baseline.
            scaler, model, training_count = fit_if_on_baseline(
                scenario_frames["baseline"]
            )

            rep_dir = OUTPUT_DIR / f"replication_{replication_seed}"
            rep_dir.mkdir(parents=True, exist_ok=True)

            for scenario, config in SCENARIOS.items():
                df = scenario_frames[scenario]
                scored = score_scenario(df, scaler, model)
                qkd_rows = df.to_dict(orient="records")
                intervals = config["intervals"]

                # Preserve each generated trace and its IF scores for reproducibility.
                trace = scored.copy()
                trace.insert(0, "replication_seed", replication_seed)
                trace.insert(1, "scenario_seed", scenario_seeds[scenario])
                trace.to_csv(
                    rep_dir / f"{scenario}_qkd_and_if_trace.csv", index=False
                )

                # V5 baseline on exactly the same trace.
                _, v5_events, v5_summary = v5.run_controller(qkd_rows)
                all_rows.append(evaluate_run(
                    replication_seed, scenario, "V5_BASELINE",
                    v5_events, v5_summary, intervals
                ))

                # Hybrid on the same trace and same IF predictions.
                _, hybrid_events, hybrid_summary = (
                    hybrid.run_controller_with_anomaly(
                        qkd_rows,
                        scored,
                        if_qber_confirmation_threshold=(
                            IF_QBER_CONFIRMATION_THRESHOLD
                        ),
                    )
                )
                all_rows.append(evaluate_run(
                    replication_seed, scenario, "HYBRID_IF_PERSISTENCE_3",
                    hybrid_events, hybrid_summary, intervals
                ))

                # Persist event-level audit trail for both controllers.
                pd.DataFrame(normalize_events(v5_events)).to_csv(
                    rep_dir / f"{scenario}_v5_events.csv", index=False
                )
                pd.DataFrame(normalize_events(hybrid_events)).to_csv(
                    rep_dir / f"{scenario}_hybrid_events.csv", index=False
                )

    finally:
        hybrid.ANOMALY_PERSISTENCE_REQUIRED = original_persistence

    detail_df = pd.DataFrame(all_rows)
    detail_df.to_csv(OUTPUT_DIR / "multi_seed_detailed_results.csv", index=False)

    aggregate_df = aggregate_results(detail_df)
    aggregate_df.to_csv(OUTPUT_DIR / "multi_seed_by_scenario_summary.csv", index=False)

    overall_rows = []
    for controller_name, group in detail_df.groupby("controller"):
        overall_rows.append({
            "controller": controller_name,
            "replications": int(len(group)),
            "total_false_fallbacks": int(group["false_fallback_count"].sum()),
            "total_missed_intervals": int(
                group["missed_degradation_intervals"].sum()
            ),
            "total_if_triggered_fallbacks": int(
                group["if_triggered_fallback_count"].sum()
            ),
            "mean_pqc_duration_seconds": float(
                group["pqc_duration_seconds"].mean()
            ),
            "std_pqc_duration_seconds": float(
                group["pqc_duration_seconds"].std(ddof=1)
            ),
            "mean_qkd_duration_seconds": float(
                group["qkd_duration_seconds"].mean()
            ),
            "all_accounting_valid": bool(group["accounting_valid"].all()),
        })

    overall_df = pd.DataFrame(overall_rows)
    overall_df.to_csv(OUTPUT_DIR / "multi_seed_overall_summary.csv", index=False)

    # Paired deltas: Hybrid minus V5 for each same seed and scenario.
    pivot = detail_df.pivot_table(
        index=["replication_seed", "scenario"],
        columns="controller",
        values=["pqc_duration_seconds", "fallback_count",
                "false_fallback_count", "missed_degradation_intervals"],
        aggfunc="first",
    )
    delta_rows = []
    for (seed, scenario), row in pivot.iterrows():
        delta_rows.append({
            "replication_seed": seed,
            "scenario": scenario,
            "delta_pqc_seconds_hybrid_minus_v5": (
                row[("pqc_duration_seconds", "HYBRID_IF_PERSISTENCE_3")]
                - row[("pqc_duration_seconds", "V5_BASELINE")]
            ),
            "delta_fallback_count_hybrid_minus_v5": (
                row[("fallback_count", "HYBRID_IF_PERSISTENCE_3")]
                - row[("fallback_count", "V5_BASELINE")]
            ),
            "hybrid_false_fallbacks": row[
                ("false_fallback_count", "HYBRID_IF_PERSISTENCE_3")
            ],
            "hybrid_missed_intervals": row[
                ("missed_degradation_intervals", "HYBRID_IF_PERSISTENCE_3")
            ],
        })
    pd.DataFrame(delta_rows).to_csv(
        OUTPUT_DIR / "paired_hybrid_vs_v5_deltas.csv", index=False
    )

    if not detail_df["accounting_valid"].all():
        failed = detail_df.loc[
            ~detail_df["accounting_valid"],
            ["replication_seed", "scenario", "controller",
             "accounting_expected_bits", "accounting_actual_bits"]
        ]
        raise RuntimeError(
            "Key-pool accounting failed:\n" + failed.to_string(index=False)
        )

    print("\n========== MULTI-SEED ROBUSTNESS ==========")
    print(f"Replication seeds: {REPLICATION_SEEDS}")
    print(f"Scenarios per replication: {len(SCENARIOS)}")
    print(f"Generated traces: {len(REPLICATION_SEEDS) * len(SCENARIOS)}")
    print(f"Controller runs: {len(detail_df)}")
    print(f"IF training samples per replication: {training_count}")
    print(f"Hybrid IF persistence: {HYBRID_PERSISTENCE}")
    print(f"IF QBER confirmation threshold: {IF_QBER_CONFIRMATION_THRESHOLD:.4f}")
    print("\nOverall comparison:")
    print(overall_df.to_string(index=False))
    print("\nBy-scenario comparison:")
    print(aggregate_df.to_string(index=False))
    print("\nAll key-pool accounting checks passed.")
    print(f"Outputs: {OUTPUT_DIR}")
    print("Synthetic channel data only; PQC rekey success remains simulated.")
    print("===========================================\n")


if __name__ == "__main__":
    main()
