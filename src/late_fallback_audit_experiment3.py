
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path.cwd()

INPUT_DIR = (
    ROOT / "results" / "experiment_3_multi_seed_robustness_20261116"
)

OUTPUT_DIR = (
    ROOT / "results" / "experiment_3_late_fallback_audit_20261116"
)

DETAIL_FILE = INPUT_DIR / "multi_seed_detailed_results.csv"

DURATION_SECONDS = 508

SCENARIO_INTERVALS = {
    "baseline": [(220, 280)],
    "short": [(220, 230)],
    "long": [(220, 400)],
    "multiple": [(100, 130), (300, 360)],
    "gradual": [(220, 280)],
}

CONTROLLERS = {
    "HYBRID_IF_PERSISTENCE_3": "hybrid",
    "V5_BASELINE": "v5",
}

# --------------------------------------------------
# 1. SAFETY AND INPUT VALIDATION
# --------------------------------------------------

if not DETAIL_FILE.exists():
    raise FileNotFoundError(f"Missing file: {DETAIL_FILE}")

if OUTPUT_DIR.exists():
    raise FileExistsError(
        f"Output directory already exists. "
        f"Refusing to overwrite: {OUTPUT_DIR}"
    )

detail = pd.read_csv(DETAIL_FILE)

required_columns = {
    "replication_seed",
    "scenario",
    "controller",
    "fallback_count",
    "false_fallback_count",
    "missed_degradation_intervals",
}

missing_columns = required_columns - set(detail.columns)

if missing_columns:
    raise ValueError(
        f"Missing detailed CSV columns: {sorted(missing_columns)}"
    )

if len(detail) != 100:
    raise ValueError(
        f"Expected 100 detailed rows; found {len(detail)}"
    )

if set(detail["scenario"].unique()) != set(SCENARIO_INTERVALS):
    raise ValueError("Unexpected scenario names in detailed results.")

if set(detail["controller"].unique()) != set(CONTROLLERS):
    raise ValueError("Unexpected controller names.")

if detail.duplicated(
    ["replication_seed", "scenario", "controller"]
).any():
    raise ValueError("Duplicate run records found.")

# --------------------------------------------------
# 2. CLASSIFICATION FUNCTION
# --------------------------------------------------

def classify_fallbacks(fallback_times, intervals):

    intervals = sorted(intervals)

    # Each interval receives its own classification.
    interval_results = []

    late_event_times = []
    genuine_false_times = []

    late_by_interval = []

    for index, (start, end) in enumerate(intervals):

        # Timely fallback: event occurs inside [start, end).
        timely = sorted(
            t for t in fallback_times
            if start <= t < end
        )

        # Late-response window ends when the next interval starts.
        if index + 1 < len(intervals):
            late_window_end = intervals[index + 1][0]
        else:
            late_window_end = DURATION_SECONDS

        # A late fallback must occur after this interval ends,
        # before the next degradation interval starts.
        missed = len(timely) == 0

        late = sorted(
            t for t in fallback_times
            if missed and end <= t < late_window_end
        )

        late_detected = missed and len(late) > 0

        interval_results.append({
            "interval_start_seconds": start,
            "interval_end_seconds": end,
            "timely_detection": not missed,
            "timely_fallback_times": ";".join(map(str, timely)),
            "late_detection": late_detected,
            "late_fallback_times": ";".join(map(str, late)),
            "missed_interval": missed,
            "undetected_interval": missed and not late_detected,
        })

        late_event_times.extend(late)

        late_by_interval.append(late)

    # Genuine false fallbacks are events outside all degradation
    # intervals that are not assigned to a late-response window.
    for t in fallback_times:

        inside_interval = any(
            start <= t < end
            for start, end in intervals
        )

        assigned_late = any(
            t in late_times
            for late_times in late_by_interval
        )

        if not inside_interval and not assigned_late:
            genuine_false_times.append(t)

    return {
        "interval_results": interval_results,
        "late_fallback_times": sorted(late_event_times),
        "genuine_false_fallback_times": sorted(genuine_false_times),
    }

# --------------------------------------------------
# 3. PROCESS ALL 100 RUNS
# --------------------------------------------------

run_rows = []
event_rows = []
interval_rows = []

for _, row in detail.iterrows():

    seed = int(row["replication_seed"])
    scenario = str(row["scenario"])
    controller = str(row["controller"])

    suffix = CONTROLLERS[controller]

    event_file = (
        INPUT_DIR
        / f"replication_{seed}"
        / f"{scenario}_{suffix}_events.csv"
    )

    if not event_file.exists():
        raise FileNotFoundError(
            f"Missing event file: {event_file}"
        )

    events = pd.read_csv(event_file)

    required_event_columns = {
        "time_seconds",
        "previous_mode",
        "new_mode",
        "reason",
    }

    missing_event_columns = (
        required_event_columns - set(events.columns)
    )

    if missing_event_columns:
        raise ValueError(
            f"{event_file.name} missing columns: "
            f"{sorted(missing_event_columns)}"
        )

    fallback_events = events[
        events["new_mode"]
        .astype(str)
        .str.upper()
        .eq("PQC_FALLBACK")
    ].copy()

    fallback_times = sorted(
        fallback_events["time_seconds"]
        .astype(int)
        .tolist()
    )

    intervals = SCENARIO_INTERVALS[scenario]

    classified = classify_fallbacks(
        fallback_times,
        intervals
    )

    interval_results = classified["interval_results"]

    original_false_times = [
        t for t in fallback_times
        if not any(
            start <= t < end
            for start, end in intervals
        )
    ]

    original_missed_count = sum(
        item["missed_interval"]
        for item in interval_results
    )

    genuine_false_times = (
        classified["genuine_false_fallback_times"]
    )

    late_times = classified["late_fallback_times"]

    late_detected_count = sum(
        item["late_detection"]
        for item in interval_results
    )

    undetected_count = sum(
        item["undetected_interval"]
        for item in interval_results
    )

    # Validate new logic against original runner classifications.
    if len(fallback_times) != int(row["fallback_count"]):
        raise ValueError(
            f"Fallback count mismatch: seed={seed}, "
            f"scenario={scenario}, controller={controller}"
        )

    if len(original_false_times) != int(row["false_fallback_count"]):
        raise ValueError(
            f"Original false-fallback count mismatch: "
            f"seed={seed}, scenario={scenario}, "
            f"controller={controller}"
        )

    if original_missed_count != int(
        row["missed_degradation_intervals"]
    ):
        raise ValueError(
            f"Missed-interval count mismatch: "
            f"seed={seed}, scenario={scenario}, "
            f"controller={controller}"
        )

    # One row per controller run.
    run_rows.append({

        "replication_seed": seed,
        "scenario": scenario,
        "controller": controller,

        "fallback_count": len(fallback_times),

        "original_false_fallback_count": len(
            original_false_times
        ),

        "late_fallback_count": len(late_times),

        "genuine_false_fallback_count": len(
            genuine_false_times
        ),

        "missed_degradation_intervals": original_missed_count,

        "late_detected_intervals": late_detected_count,

        "undetected_intervals": undetected_count,

        "fallback_times_seconds": ";".join(
            map(str, fallback_times)
        ),

        "late_fallback_times_seconds": ";".join(
            map(str, late_times)
        ),

        "genuine_false_fallback_times_seconds": ";".join(
            map(str, genuine_false_times)
        ),

    })

    # One row per fallback event.
    for _, event in fallback_events.iterrows():

        event_time = int(event["time_seconds"])

        event_category = (
            "TIMELY"
            if any(
                start <= event_time < end
                for start, end in intervals
            )
            else (
                "LATE"
                if event_time in late_times
                else "GENUINE_FALSE"
            )
        )

        event_rows.append({

            "replication_seed": seed,
            "scenario": scenario,
            "controller": controller,

            "time_seconds": event_time,

            "event_category": event_category,

            "reason": event["reason"],

            "qber": event.get("qber", np.nan),

            "rolling_qber": event.get(
                "rolling_qber",
                np.nan
            ),

        })

    # One row per degradation interval.
    for item in interval_results:

        interval_rows.append({

            "replication_seed": seed,
            "scenario": scenario,
            "controller": controller,

            **item,

        })

# --------------------------------------------------
# 4. CREATE DATAFRAMES
# --------------------------------------------------

run_df = pd.DataFrame(run_rows)

event_df = pd.DataFrame(event_rows)

interval_df = pd.DataFrame(interval_rows)

if len(run_df) != 100:
    raise ValueError("Expected 100 audited controller runs.")

if len(interval_df) != 120:
    raise ValueError(
        f"Expected 120 interval records, found {len(interval_df)}"
    )

# --------------------------------------------------
# 5. SUMMARY BY CONTROLLER AND SCENARIO
# --------------------------------------------------

scenario_summary = run_df.groupby(
    ["controller", "scenario"],
    as_index=False
).agg({

    "fallback_count": "sum",

    "original_false_fallback_count": "sum",

    "late_fallback_count": "sum",

    "genuine_false_fallback_count": "sum",

    "missed_degradation_intervals": "sum",

    "late_detected_intervals": "sum",

    "undetected_intervals": "sum",

})

# Overall controller summary.
overall_summary = run_df.groupby(
    "controller",
    as_index=False
).agg({

    "fallback_count": "sum",

    "original_false_fallback_count": "sum",

    "late_fallback_count": "sum",

    "genuine_false_fallback_count": "sum",

    "missed_degradation_intervals": "sum",

    "late_detected_intervals": "sum",

    "undetected_intervals": "sum",

})

# --------------------------------------------------
# 6. SAVE TO A NEW OUTPUT DIRECTORY
# --------------------------------------------------

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=False
)

run_df.to_csv(
    OUTPUT_DIR / "experiment3_late_fallback_run_level.csv",
    index=False
)

event_df.to_csv(
    OUTPUT_DIR / "experiment3_late_fallback_event_level.csv",
    index=False
)

interval_df.to_csv(
    OUTPUT_DIR / "experiment3_late_fallback_interval_level.csv",
    index=False
)

scenario_summary.to_csv(
    OUTPUT_DIR / "experiment3_late_fallback_scenario_summary.csv",
    index=False
)

overall_summary.to_csv(
    OUTPUT_DIR / "experiment3_late_fallback_overall_summary.csv",
    index=False
)

# --------------------------------------------------
# 7. FINAL VALIDATION REPORT
# --------------------------------------------------

print("\nLATE FALLBACK AUDIT COMPLETED")

print("Controller runs audited:", len(run_df))
print("Fallback events audited:", len(event_df))
print("Degradation intervals audited:", len(interval_df))

print("\n--- OVERALL SUMMARY ---")
print(overall_summary.to_string(index=False))

print("\n--- SCENARIO SUMMARY ---")
print(scenario_summary.to_string(index=False))

print("\n--- SEED 1003 SHORT SCENARIO ---")

print(
    run_df[
        (run_df["replication_seed"] == 1003)
        & (run_df["scenario"] == "short")
    ].to_string(index=False)
)

print("\n--- OUTPUT DIRECTORY ---")
print(OUTPUT_DIR)

print("\nOriginal controller scripts and experiment CSV files were not modified.")
