"""
V5 + Isolation Forest integration experiment.

This script preserves the original adaptive_controller_v5.py and
anomaly_detection_v3.py. It:
1. Loads the same synthetic QKD input used by V5.
2. Trains Isolation Forest on the normal baseline (t = 0..219).
3. Produces anomaly scores/predictions for the full simulation.
4. Runs the original V5 controller as the baseline.
5. Runs a separate V5+IF controller. IF fallback requires 3 consecutive
   anomaly predictions; all original V5 QBER, pool and recovery rules remain.
6. Evaluates anomaly predictions against the injected degradation interval.
7. Compares controller outcomes and validates key-pool accounting.

This is a simulation experiment, not a real cyberattack detector.
QKD bits are synthetic and PQC rekey success remains abstractly assumed.
"""

from pathlib import Path
import csv
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    confusion_matrix,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
)

import adaptive_controller_v5 as v5


# ----------------------------- CONFIGURATION -----------------------------

INPUT_FILE = Path("results/qkd_generation_508s_v3.csv")
OUTPUT_DIR = Path("results/anomaly_detection_v5_hybrid_confirmation")

FEATURES = ["qber", "qkd_key_rate_bps"]
TRAIN_START = 0
TRAIN_END_EXCLUSIVE = 220
DEGRADED_START = 220
DEGRADED_END_EXCLUSIVE = 280

IF_ESTIMATORS = 300
IF_CONTAMINATION = 0.05
IF_RANDOM_STATE = 42

# Persistence is deliberately used to avoid switching on a single isolated
# anomaly flag. This is a design parameter to be evaluated, not a learned value.
ANOMALY_PERSISTENCE_REQUIRED = 3


# ----------------------------- ANOMALY MODEL -----------------------------

def fit_and_score_isolation_forest(qkd_df):
    required = ["time_seconds"] + FEATURES
    missing = [c for c in required if c not in qkd_df.columns]
    if missing:
        raise ValueError(f"QKD input missing columns: {missing}")

    if qkd_df[required].isnull().any().any():
        raise ValueError("Missing values in QKD model input.")
    if not np.isfinite(qkd_df[FEATURES].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite values in QKD model input.")
    if qkd_df["time_seconds"].duplicated().any():
        raise ValueError("Duplicate time_seconds values.")
    if not qkd_df["time_seconds"].is_monotonic_increasing:
        raise ValueError("QKD input must be sorted by time_seconds.")

    baseline = qkd_df[
        (qkd_df["time_seconds"] >= TRAIN_START)
        & (qkd_df["time_seconds"] < TRAIN_END_EXCLUSIVE)
    ]
    if baseline.empty:
        raise ValueError("Normal training baseline is empty.")

    scaler = StandardScaler()
    x_train = scaler.fit_transform(baseline[FEATURES].astype(float))
    x_all = scaler.transform(qkd_df[FEATURES].astype(float))

    model = IsolationForest(
        n_estimators=IF_ESTIMATORS,
        contamination=IF_CONTAMINATION,
        max_samples="auto",
        random_state=IF_RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(x_train)

    predictions = model.predict(x_all)
    output = qkd_df.copy()
    output["anomaly_score"] = model.decision_function(x_all)
    output["anomaly_prediction"] = (predictions == -1).astype(int)
    output["anomaly_status"] = np.where(
        output["anomaly_prediction"] == 1, "ANOMALY", "NORMAL"
    )
    return output, len(baseline)


def evaluate_anomaly_model(scored):
    # Evaluate only observations outside the normal-baseline training window.
    # The degradation interval remains the synthetic ground-truth scenario
    # defined above; this is not a labelled real-world attack dataset.
    training_mask = (
        (scored["time_seconds"] >= TRAIN_START)
        & (scored["time_seconds"] < TRAIN_END_EXCLUSIVE)
    )
    evaluation = scored.loc[~training_mask].copy()
    if evaluation.empty:
        raise ValueError("No held-out observations available for evaluation.")

    actual = (
        (evaluation["time_seconds"] >= DEGRADED_START)
        & (evaluation["time_seconds"] < DEGRADED_END_EXCLUSIVE)
    ).astype(int)
    predicted = evaluation["anomaly_prediction"].astype(int)
    cm = confusion_matrix(actual, predicted, labels=[0, 1])

    metrics = {
        "total_samples": int(len(evaluation)),
        "excluded_training_samples": int(training_mask.sum()),
        "evaluation_start_time": float(evaluation["time_seconds"].min()),
        "evaluation_end_time": float(evaluation["time_seconds"].max()),
        "detected_anomalies": int(predicted.sum()),
        "true_negatives": int(cm[0, 0]),
        "false_positives": int(cm[0, 1]),
        "false_negatives": int(cm[1, 0]),
        "true_positives": int(cm[1, 1]),
        "accuracy": float(accuracy_score(actual, predicted)),
        "precision": float(precision_score(actual, predicted, zero_division=0)),
        "recall": float(recall_score(actual, predicted, zero_division=0)),
        "f1_score": float(f1_score(actual, predicted, zero_division=0)),
    }
    report = classification_report(
        actual, predicted,
        labels=[0, 1],
        target_names=["Normal simulation period", "Injected degradation"],
        zero_division=0,
    )
    return metrics, report


# ----------------------------- INTEGRATED CONTROLLER -----------------------------

def run_controller_with_anomaly(qkd_rows, scored_df, if_qber_confirmation_threshold=None):
    """
    V5 controller logic with a hybrid IF fallback condition:
    three consecutive IF anomaly predictions AND rolling QBER at or above
    the user-specified IF confirmation threshold. This prevents IF-only
    fallback when the rolling QBER remains below that threshold.

    Original V5 QBER thresholds, rolling window, key-pool thresholds,
    rekey schedule, recovery persistence and accounting are retained.
    """
    if if_qber_confirmation_threshold is None:
        if_qber_confirmation_threshold = v5.QBER_RECOVERY_THRESHOLD
    if not 0.0 <= float(if_qber_confirmation_threshold) <= 1.0:
        raise ValueError("IF QBER confirmation threshold must be between 0 and 1.")
    if_qber_confirmation_threshold = float(if_qber_confirmation_threshold)

    anomaly_by_time = {
        int(row.time_seconds): int(row.anomaly_prediction)
        for row in scored_df[["time_seconds", "anomaly_prediction"]].itertuples(index=False)
    }
    score_by_time = {
        int(row.time_seconds): float(row.anomaly_score)
        for row in scored_df[["time_seconds", "anomaly_score"]].itertuples(index=False)
    }

    pool = v5.INITIAL_POOL_BITS
    mode = "QKD"
    results, events = [], []

    total_generated = total_consumed = total_discarded = 0
    background_qkd_bits_accepted = 0
    qkd_successful_rekeys = qkd_failed_rekeys = pqc_successful_rekeys = 0
    fallback_activations = recovery_events = 0
    session_key_epoch = 0
    next_rekey_time = 0

    mode_duration = {"QKD": 0, "PQC_FALLBACK": 0}
    qber_history = []
    fallback_consecutive = recovery_consecutive = anomaly_consecutive = 0

    for row in qkd_rows:
        t = int(float(row["time_seconds"]))
        qber = float(row["qber"])
        generated = int(row["generated_key_bits"])
        if generated < 0:
            raise ValueError(f"Negative generated key bits at time {t}.")

        anomaly_prediction = anomaly_by_time.get(t, 0)
        anomaly_score = score_by_time.get(t, float("nan"))
        if t not in anomaly_by_time:
            raise ValueError(f"No anomaly prediction for time {t}.")

        qber_history.append(qber)
        rolling_qber = v5.calculate_rolling_qber(
            qber_history, v5.ROLLING_WINDOW_SECONDS
        )

        previous_mode = mode
        transition_reason = ""

        if anomaly_prediction == 1:
            anomaly_consecutive += 1
        else:
            anomaly_consecutive = 0

        # Original V5 QBER trigger plus persistent IF anomaly trigger.
        if rolling_qber is not None:
            if mode == "QKD":
                if rolling_qber >= v5.QBER_FALLBACK_THRESHOLD:
                    fallback_consecutive += 1
                else:
                    fallback_consecutive = 0

                qber_trigger = (
                    fallback_consecutive >= v5.FALLBACK_CONSECUTIVE_REQUIRED
                )
                # Hybrid confirmation: IF persistence alone is insufficient.
                # Require rolling QBER to reach the user-specified threshold.
                anomaly_qber_confirmed = (
                    rolling_qber >= if_qber_confirmation_threshold
                )
                anomaly_trigger = (
                    anomaly_consecutive >= ANOMALY_PERSISTENCE_REQUIRED
                    and anomaly_qber_confirmed
                )
                anomaly_streak_at_decision = anomaly_consecutive

                if qber_trigger or anomaly_trigger:
                    mode = "PQC_FALLBACK"
                    fallback_activations += 1
                    if qber_trigger:
                        transition_reason = "ROLLING_QBER_HIGH"
                    else:
                        transition_reason = "ISOLATION_FOREST_PERSISTENT_ANOMALY"
                    recovery_consecutive = 0
                    anomaly_consecutive = 0

            elif mode == "PQC_FALLBACK":
                if rolling_qber <= v5.QBER_RECOVERY_THRESHOLD:
                    recovery_consecutive += 1
                else:
                    recovery_consecutive = 0

                if (
                    pool >= v5.RECOVERY_POOL_THRESHOLD
                    and recovery_consecutive >= v5.RECOVERY_CONSECUTIVE_REQUIRED
                ):
                    mode = "QKD"
                    recovery_events += 1
                    transition_reason = "ROLLING_QBER_RECOVERED"
                    fallback_consecutive = 0
                    anomaly_consecutive = 0

        # Original V5 low-pool fallback condition.
        if mode == "QKD" and pool <= v5.FALLBACK_POOL_THRESHOLD:
            mode = "PQC_FALLBACK"
            fallback_activations += 1
            transition_reason = "LOW_QKD_POOL"
            fallback_consecutive = recovery_consecutive = 0
            anomaly_consecutive = 0

        mode_transition = previous_mode != mode

        total_generated += generated
        accepted = discarded = 0

        # Background QKD replenishment is permitted during PQC fallback only
        # while the simulator reports a normal channel and QBER is within the
        # recovery threshold. The bits are not consumed until mode recovery.
        channel_is_healthy = (
            str(row["channel_status"]).strip().upper() == "NORMAL"
            and qber <= v5.QBER_RECOVERY_THRESHOLD
        )
        may_replenish = mode == "QKD" or (
            mode == "PQC_FALLBACK" and channel_is_healthy
        )
        if may_replenish:
            available_space = v5.MAX_POOL_BITS - pool
            accepted = min(generated, available_space)
            discarded = generated - accepted
            pool += accepted
            if mode == "PQC_FALLBACK":
                background_qkd_bits_accepted += accepted
        else:
            discarded = generated
        total_discarded += discarded

        qkd_consumed = qkd_shortage = 0
        qkd_rekey = pqc_rekey = rekey_event = 0
        rekey_reason = ""
        key_source = "NONE"
        rekey_success = 0

        if mode_transition:
            rekey_event = 1
            rekey_reason = "MODE_TRANSITION"
        elif t >= next_rekey_time:
            rekey_event = 1
            rekey_reason = "INITIAL_ALLOCATION" if t == 0 else "SCHEDULED"

        if rekey_event:
            if mode == "QKD":
                if pool >= v5.QKD_DEMAND_PER_REKEY:
                    pool -= v5.QKD_DEMAND_PER_REKEY
                    qkd_consumed = v5.QKD_DEMAND_PER_REKEY
                    total_consumed += qkd_consumed
                    qkd_successful_rekeys += 1
                    qkd_rekey = 1
                    key_source = "SIMULATED_QKD_POOL"
                    rekey_success = 1
                    session_key_epoch += 1
                else:
                    qkd_shortage = v5.QKD_DEMAND_PER_REKEY - pool
                    qkd_failed_rekeys += 1
                    rekey_reason = "QKD_POOL_SHORTAGE"
            else:
                # Same abstract PQC success assumption as original V5.
                pqc_rekey = 1
                pqc_successful_rekeys += 1
                key_source = "SIMULATED_PQC"
                rekey_success = 1
                session_key_epoch += 1
            next_rekey_time = t + v5.REKEY_INTERVAL_SECONDS

        mode_duration[mode] += 1

        if mode_transition:
            events.append({
                "time_seconds": t,
                "previous_mode": previous_mode,
                "new_mode": mode,
                "reason": transition_reason,
                "qber": qber,
                "rolling_qber": rolling_qber if rolling_qber is not None else "",
                "anomaly_prediction": anomaly_prediction,
                "anomaly_score": anomaly_score,
                "anomaly_consecutive_count": (
                    anomaly_streak_at_decision
                    if transition_reason == "ISOLATION_FOREST_PERSISTENT_ANOMALY"
                    else anomaly_consecutive
                ),
                "key_pool_bits": pool,
                "immediate_rekey": rekey_event,
                "key_source": key_source,
            })

        results.append({
            "time_seconds": t,
            "qber": qber,
            "rolling_qber": rolling_qber if rolling_qber is not None else "",
            "channel_status": row["channel_status"],
            "qkd_generation_bps": generated,
            "anomaly_score": anomaly_score,
            "anomaly_prediction": anomaly_prediction,
            "anomaly_consecutive_count": anomaly_consecutive,
            "operating_mode": mode,
            "mode_transition": int(mode_transition),
            "rekey_event": rekey_event,
            "rekey_success": rekey_success,
            "rekey_reason": rekey_reason,
            "key_source": key_source,
            "session_key_epoch": session_key_epoch,
            "qkd_rekey_event": qkd_rekey,
            "pqc_rekey_event": pqc_rekey,
            "qkd_consumed_bits": qkd_consumed,
            "qkd_shortage_bits": qkd_shortage,
            "generated_key_bits": generated,
            "accepted_key_bits": accepted,
            "discarded_key_bits": discarded,
            "key_pool_bits": pool,
            "fallback_consecutive_count": fallback_consecutive,
            "recovery_consecutive_count": recovery_consecutive,
        })

    expected_bits = v5.INITIAL_POOL_BITS + total_generated
    actual_bits = total_consumed + total_discarded + pool
    accounting_valid = expected_bits == actual_bits

    summary = {
        "controller_version": "V5_PLUS_IF_HYBRID_CONFIRMATION",
        "duration_seconds": len(qkd_rows),
        "anomaly_persistence_required": ANOMALY_PERSISTENCE_REQUIRED,
        "if_qber_confirmation_threshold": if_qber_confirmation_threshold,
        "rolling_window_seconds": v5.ROLLING_WINDOW_SECONDS,
        "qber_fallback_threshold": v5.QBER_FALLBACK_THRESHOLD,
        "qber_recovery_threshold": v5.QBER_RECOVERY_THRESHOLD,
        "initial_pool_bits": v5.INITIAL_POOL_BITS,
        "total_generated_bits": total_generated,
        "total_consumed_bits": total_consumed,
        "total_discarded_bits": total_discarded,
        "background_qkd_bits_accepted_during_fallback": background_qkd_bits_accepted,
        "final_pool_bits": pool,
        "qkd_successful_rekeys": qkd_successful_rekeys,
        "pqc_simulated_successful_rekeys": pqc_successful_rekeys,
        "total_successful_rekeys": qkd_successful_rekeys + pqc_successful_rekeys,
        "failed_qkd_rekeys": qkd_failed_rekeys,
        "fallback_count": fallback_activations,
        "recovery_count": recovery_events,
        "qkd_duration_seconds": mode_duration["QKD"],
        "pqc_duration_seconds": mode_duration["PQC_FALLBACK"],
        "final_epoch": session_key_epoch,
        "final_mode": mode,
        "accounting_expected_bits": expected_bits,
        "accounting_actual_bits": actual_bits,
        "accounting_valid": accounting_valid,
    }
    return results, events, summary


# ----------------------------- OUTPUT HELPERS -----------------------------

def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Missing {INPUT_FILE}. Run the QKD simulator first or set INPUT_FILE."
        )

    qkd_rows = v5.load_qkd_data(INPUT_FILE)
    qkd_df = pd.read_csv(INPUT_FILE)

    scored, training_samples = fit_and_score_isolation_forest(qkd_df)
    anomaly_metrics, report = evaluate_anomaly_model(scored)

    # Original V5 baseline is run unchanged.
    baseline_results, baseline_events, baseline_summary = v5.run_controller(qkd_rows)

    # New integrated controller is run on identical input.
    integrated_results, integrated_events, integrated_summary = (
        run_controller_with_anomaly(qkd_rows, scored)
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scored.to_csv(OUTPUT_DIR / "isolation_forest_v5_predictions.csv", index=False)
    pd.DataFrame([anomaly_metrics]).to_csv(
        OUTPUT_DIR / "isolation_forest_v5_metrics.csv", index=False
    )

    write_csv(OUTPUT_DIR / "v5_baseline_timeseries.csv", baseline_results)
    write_csv(OUTPUT_DIR / "v5_baseline_events.csv", baseline_events)
    pd.DataFrame([baseline_summary]).to_csv(
        OUTPUT_DIR / "v5_baseline_summary.csv", index=False
    )

    write_csv(OUTPUT_DIR / "v5_if_timeseries.csv", integrated_results)
    write_csv(OUTPUT_DIR / "v5_if_events.csv", integrated_events)
    pd.DataFrame([integrated_summary]).to_csv(
        OUTPUT_DIR / "v5_if_summary.csv", index=False
    )

    comparison = {
        "metric": [
            "QKD duration (seconds)",
            "PQC duration (seconds)",
            "Fallback count",
            "Recovery count",
            "QKD successful rekeys",
            "Simulated PQC successful rekeys",
            "Total successful rekeys",
            "Final key pool (bits)",
            "Key accounting valid",
        ],
        "V5_baseline": [
            baseline_summary["qkd_duration_seconds"],
            baseline_summary["pqc_duration_seconds"],
            baseline_summary["fallback_count"],
            baseline_summary["recovery_count"],
            baseline_summary["qkd_successful_rekeys"],
            baseline_summary["pqc_simulated_successful_rekeys"],
            baseline_summary["total_successful_rekeys"],
            baseline_summary["final_pool_bits"],
            baseline_summary["accounting_valid"],
        ],
        "V5_plus_IF": [
            integrated_summary["qkd_duration_seconds"],
            integrated_summary["pqc_duration_seconds"],
            integrated_summary["fallback_count"],
            integrated_summary["recovery_count"],
            integrated_summary["qkd_successful_rekeys"],
            integrated_summary["pqc_simulated_successful_rekeys"],
            integrated_summary["total_successful_rekeys"],
            integrated_summary["final_pool_bits"],
            integrated_summary["accounting_valid"],
        ],
    }
    pd.DataFrame(comparison).to_csv(
        OUTPUT_DIR / "v5_vs_v5_if_comparison.csv", index=False
    )

    with (OUTPUT_DIR / "anomaly_classification_report.txt").open(
        "w", encoding="utf-8"
    ) as f:
        f.write(report)

    print("\n========== V5 + ISOLATION FOREST EXPERIMENT ==========")
    print(f"Input observations: {len(qkd_df)}")
    print(f"Normal-baseline training samples: {training_samples}")
    print("\nAnomaly detection metrics:")
    for key, value in anomaly_metrics.items():
        print(f"{key}: {value}")

    print("\nV5 baseline summary:")
    for key, value in baseline_summary.items():
        print(f"{key}: {value}")

    print("\nV5 + IF summary:")
    for key, value in integrated_summary.items():
        print(f"{key}: {value}")

    print("\nComparison:")
    print(pd.DataFrame(comparison).to_string(index=False))

    if not baseline_summary["accounting_valid"]:
        raise RuntimeError("Original V5 baseline key accounting failed.")
    if not integrated_summary["accounting_valid"]:
        raise RuntimeError("V5+IF key accounting failed.")

    print(f"\nAll outputs saved in: {OUTPUT_DIR}")
    print("Both key-accounting checks passed.")
    print("IF fallback requires 3 consecutive anomalies AND rolling QBER confirmation.")
    print(
        "IF QBER confirmation threshold: "
        f"{integrated_summary['if_qber_confirmation_threshold']}"
    )
    print("PQC rekey success remains simulated; this is not real ML-KEM.")
    print("======================================================\n")


if __name__ == "__main__":
    main()
