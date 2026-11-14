
"""
Adaptive QKD/PQC Controller V5
System-level simulation using rolling QBER monitoring.

QKD key generation is synthetic.
PQC rekey success is abstractly assumed.
No physical quantum communication or actual ML-KEM exchange is performed.

V5 changes:
- 20-second rolling QBER monitoring.
- Fallback threshold: 0.066592.
- One consecutive crossing required for fallback.
- Recovery threshold: 0.06.
- Three consecutive rolling observations required for recovery.

The key-pool, rekey, fallback, recovery and accounting
logic follows the existing V4 controller design.
"""

import csv
import argparse
from pathlib import Path

# --------------------------------------------------
# CONTROLLER CONFIGURATION
# --------------------------------------------------

FALLBACK_POOL_THRESHOLD = 3000
RECOVERY_POOL_THRESHOLD = 10000

ROLLING_WINDOW_SECONDS = 20
QBER_FALLBACK_THRESHOLD = 0.066592
QBER_RECOVERY_THRESHOLD = 0.06

FALLBACK_CONSECUTIVE_REQUIRED = 1
RECOVERY_CONSECUTIVE_REQUIRED = 3

SESSION_KEY_BITS = 256
REKEY_INTERVAL_SECONDS = 60
NUMBER_OF_SESSIONS = 5

INITIAL_POOL_BITS = 12000
MAX_POOL_BITS = 30000

QKD_DEMAND_PER_REKEY = NUMBER_OF_SESSIONS * SESSION_KEY_BITS


# --------------------------------------------------
# INPUT
# --------------------------------------------------

def load_qkd_data(path):
    with open(path, newline="", encoding="utf-8") as file:
        data = list(csv.DictReader(file))

    if not data:
        raise ValueError("QKD input file is empty.")

    required = {
        "time_seconds",
        "qber",
        "generated_key_bits",
        "channel_status",
    }

    missing = required - set(data[0].keys())

    if missing:
        raise ValueError(
            f"Missing required input columns: {sorted(missing)}"
        )

    return data


# --------------------------------------------------
# ROLLING QBER
# --------------------------------------------------

def calculate_rolling_qber(qber_history, window):
    if len(qber_history) < window:
        return None

    recent_values = qber_history[-window:]

    return sum(recent_values) / window


# --------------------------------------------------
# CONTROLLER
# --------------------------------------------------

def run_controller(qkd_data):

    pool = INITIAL_POOL_BITS
    mode = "QKD"

    results = []
    events = []

    total_generated = 0
    total_consumed = 0
    total_discarded = 0

    qkd_successful_rekeys = 0
    qkd_failed_rekeys = 0
    pqc_successful_rekeys = 0

    fallback_activations = 0
    recovery_events = 0

    session_key_epoch = 0
    next_rekey_time = 0

    mode_duration = {
        "QKD": 0,
        "PQC_FALLBACK": 0,
    }

    qber_history = []

    fallback_consecutive = 0
    recovery_consecutive = 0

    for row in qkd_data:

        t = int(float(row["time_seconds"]))
        qber = float(row["qber"])
        generated = int(row["generated_key_bits"])

        if generated < 0:
            raise ValueError(
                f"Negative generated key bits at time {t}."
            )

        qber_history.append(qber)

        rolling_qber = calculate_rolling_qber(
            qber_history,
            ROLLING_WINDOW_SECONDS
        )

        previous_mode = mode
        transition_reason = ""

        # --------------------------------------------------
        # 1. ADAPTIVE MODE SELECTION
        # --------------------------------------------------

        if rolling_qber is not None:

            if mode == "QKD":

                if rolling_qber >= QBER_FALLBACK_THRESHOLD:
                    fallback_consecutive += 1
                else:
                    fallback_consecutive = 0

                if (
                    fallback_consecutive
                    >= FALLBACK_CONSECUTIVE_REQUIRED
                ):
                    mode = "PQC_FALLBACK"
                    fallback_activations += 1
                    transition_reason = "ROLLING_QBER_HIGH"

                    recovery_consecutive = 0

            elif mode == "PQC_FALLBACK":

                if rolling_qber <= QBER_RECOVERY_THRESHOLD:
                    recovery_consecutive += 1
                else:
                    recovery_consecutive = 0

                if (
                    pool >= RECOVERY_POOL_THRESHOLD
                    and recovery_consecutive
                    >= RECOVERY_CONSECUTIVE_REQUIRED
                ):
                    mode = "QKD"
                    recovery_events += 1
                    transition_reason = "ROLLING_QBER_RECOVERED"

                    fallback_consecutive = 0

        # Preserve the existing low-pool fallback condition.
        if mode == "QKD" and pool <= FALLBACK_POOL_THRESHOLD:
            mode = "PQC_FALLBACK"
            fallback_activations += 1
            transition_reason = "LOW_QKD_POOL"

            fallback_consecutive = 0
            recovery_consecutive = 0

        mode_transition = previous_mode != mode

        # --------------------------------------------------
        # 2. QKD KEY GENERATION AND ACCOUNTING
        # --------------------------------------------------

        total_generated += generated

        accepted = 0
        discarded = 0

        # Only accept newly generated QKD bits while operating
        # in QKD mode. Bits generated during fallback are discarded.
        if mode == "QKD":

            available_space = MAX_POOL_BITS - pool

            accepted = min(generated, available_space)
            discarded = generated - accepted

            pool += accepted

        else:
            discarded = generated

        total_discarded += discarded

        # --------------------------------------------------
        # 3. SESSION REKEYING
        # --------------------------------------------------

        qkd_consumed = 0
        qkd_shortage = 0

        qkd_rekey = 0
        pqc_rekey = 0
        rekey_event = 0

        rekey_reason = ""
        key_source = "NONE"

        # A mode transition takes priority over scheduled rekeying.
        if mode_transition:

            rekey_event = 1
            rekey_reason = "MODE_TRANSITION"

        elif t >= next_rekey_time:

            rekey_event = 1

            if t == 0:
                rekey_reason = "INITIAL_ALLOCATION"
            else:
                rekey_reason = "SCHEDULED"

        if rekey_event:

            if mode == "QKD":

                if pool >= QKD_DEMAND_PER_REKEY:

                    pool -= QKD_DEMAND_PER_REKEY
                    qkd_consumed = QKD_DEMAND_PER_REKEY

                    total_consumed += qkd_consumed
                    qkd_successful_rekeys += 1

                    qkd_rekey = 1
                    key_source = "SIMULATED_QKD_POOL"

                    session_key_epoch += 1

                else:

                    qkd_shortage = (
                        QKD_DEMAND_PER_REKEY - pool
                    )

                    qkd_failed_rekeys += 1
                    rekey_reason = "QKD_POOL_SHORTAGE"

            elif mode == "PQC_FALLBACK":

                # Abstract success assumption only.
                # Actual ML-KEM is not implemented.
                pqc_rekey = 1
                pqc_successful_rekeys += 1

                key_source = "SIMULATED_PQC"
                session_key_epoch += 1

            next_rekey_time = t + REKEY_INTERVAL_SECONDS

        # --------------------------------------------------
        # 4. MODE DURATION
        # --------------------------------------------------

        mode_duration[mode] += 1

        # --------------------------------------------------
        # 5. TRANSITION EVENTS
        # --------------------------------------------------

        if mode_transition:

            events.append({
                "time_seconds": t,
                "previous_mode": previous_mode,
                "new_mode": mode,
                "reason": transition_reason,
                "qber": qber,
                "rolling_qber": (
                    rolling_qber
                    if rolling_qber is not None
                    else ""
                ),
                "key_pool_bits": pool,
                "immediate_rekey": rekey_event,
                "key_source": key_source,
            })

        # --------------------------------------------------
        # 6. TIME SERIES
        # --------------------------------------------------

        results.append({
            "time_seconds": t,
            "qber": qber,
            "rolling_qber": (
                rolling_qber
                if rolling_qber is not None
                else ""
            ),
            "channel_status": row["channel_status"],
            "qkd_generation_bps": generated,
            "operating_mode": mode,

            "mode_transition": int(mode_transition),

            "rekey_event": rekey_event,
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

    # --------------------------------------------------
    # 7. ACCOUNTING VALIDATION
    # --------------------------------------------------

    expected_bits = (
        INITIAL_POOL_BITS + total_generated
    )

    actual_bits = (
        total_consumed + total_discarded + pool
    )

    accounting_valid = expected_bits == actual_bits

    # --------------------------------------------------
    # 8. SUMMARY
    # --------------------------------------------------

    summary = {
        "controller_version": "V5",
        "duration_seconds": len(qkd_data),

        "rolling_window_seconds": ROLLING_WINDOW_SECONDS,
        "qber_fallback_threshold": QBER_FALLBACK_THRESHOLD,
        "qber_recovery_threshold": QBER_RECOVERY_THRESHOLD,

        "fallback_consecutive_required": (
            FALLBACK_CONSECUTIVE_REQUIRED
        ),
        "recovery_consecutive_required": (
            RECOVERY_CONSECUTIVE_REQUIRED
        ),

        "initial_pool_bits": INITIAL_POOL_BITS,
        "total_generated_bits": total_generated,
        "total_consumed_bits": total_consumed,
        "total_discarded_bits": total_discarded,
        "final_pool_bits": pool,

        "qkd_successful_rekeys": qkd_successful_rekeys,
        "pqc_simulated_successful_rekeys": pqc_successful_rekeys,
        "total_successful_rekeys": (
            qkd_successful_rekeys + pqc_successful_rekeys
        ),
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


# --------------------------------------------------
# OUTPUT
# --------------------------------------------------

def save_results(results, events, summary, output_prefix):

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    timeseries_path = Path(str(prefix) + "_timeseries.csv")
    events_path = Path(str(prefix) + "_events.csv")
    summary_path = Path(str(prefix) + "_summary.csv")

    with open(
        timeseries_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=results[0].keys()
        )
        writer.writeheader()
        writer.writerows(results)

    event_fields = [
        "time_seconds",
        "previous_mode",
        "new_mode",
        "reason",
        "qber",
        "rolling_qber",
        "key_pool_bits",
        "immediate_rekey",
        "key_source",
    ]

    with open(
        events_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=event_fields
        )
        writer.writeheader()
        writer.writerows(events)

    with open(
        summary_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=summary.keys()
        )
        writer.writeheader()
        writer.writerow(summary)

    return timeseries_path, events_path, summary_path


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Adaptive QKD/PQC Controller V5"
    )

    parser.add_argument(
        "--qkd",
        default="results/qkd_generation_508s_v3.csv"
    )

    parser.add_argument(
        "--output-prefix",
        default="results/adaptive_508s_v5"
    )

    args = parser.parse_args()

    qkd_data = load_qkd_data(args.qkd)

    results, events, summary = run_controller(qkd_data)

    print("\n========== ADAPTIVE CONTROLLER V5 SUMMARY ==========")

    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\n========== MODE TRANSITIONS ==========")

    if events:
        for event in events:
            print(event)
    else:
        print("No mode transitions.")

    print("\n========== REKEY EVENTS ==========")

    for row in results:
        if row["rekey_event"]:
            print(
                f"Time: {row['time_seconds']}s | "
                f"Mode: {row['operating_mode']} | "
                f"Reason: {row['rekey_reason']} | "
                f"Source: {row['key_source']} | "
                f"Epoch: {row['session_key_epoch']}"
            )

    print("\n========== ACCOUNTING CHECK ==========")

    if summary["accounting_valid"]:
        print("PASS: Key-pool accounting is balanced.")
    else:
        print("FAIL: Key-pool accounting mismatch.")

    paths = save_results(
        results,
        events,
        summary,
        args.output_prefix
    )

    print("\n========== OUTPUT FILES ==========")

    for path in paths:
        print(path)

    print("\nV5 controller execution completed.")


if __name__ == "__main__":
    main()
