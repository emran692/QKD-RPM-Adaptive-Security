
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path.cwd()

INPUT_DIR = (
    ROOT / "results" / "experiment_3_multi_seed_robustness_20261116"
)

OUTPUT_DIR = (
    ROOT / "results" / "experiment_3_statistical_analysis_20261116"
)

DETAIL_FILE = INPUT_DIR / "multi_seed_detailed_results.csv"
PAIRED_FILE = INPUT_DIR / "paired_hybrid_vs_v5_deltas.csv"

EXPECTED_CONTROLLERS = {
    "V5_BASELINE",
    "HYBRID_IF_PERSISTENCE_3",
}

EXPECTED_SEEDS = set(range(1001, 1011))

EXPECTED_SCENARIOS = {
    "baseline",
    "short",
    "long",
    "multiple",
    "gradual",
}

CONTROLLER_ORDER = [
    "HYBRID_IF_PERSISTENCE_3",
    "V5_BASELINE",
]

# --------------------------------------------------
# 1. INPUT AND OUTPUT SAFETY CHECKS
# --------------------------------------------------

if not DETAIL_FILE.exists():
    raise FileNotFoundError(f"Missing file: {DETAIL_FILE}")

if not PAIRED_FILE.exists():
    raise FileNotFoundError(f"Missing file: {PAIRED_FILE}")

if OUTPUT_DIR.exists():
    raise FileExistsError(
        "Output directory already exists. "
        f"Refusing to overwrite: {OUTPUT_DIR}"
    )

detail = pd.read_csv(DETAIL_FILE)
paired_source = pd.read_csv(PAIRED_FILE)

# --------------------------------------------------
# 2. DETAILED DATA VALIDATION
# --------------------------------------------------

required_detail_columns = {
    "replication_seed",
    "scenario",
    "controller",
    "pqc_duration_seconds",
    "qkd_duration_seconds",
    "fallback_count",
    "false_fallback_count",
    "missed_degradation_intervals",
    "mean_detected_fallback_delay_seconds",
    "accounting_valid",
}

missing_columns = required_detail_columns - set(detail.columns)

if missing_columns:
    raise ValueError(
        f"Missing detailed CSV columns: {sorted(missing_columns)}"
    )

if len(detail) != 100:
    raise ValueError(
        f"Expected 100 detailed rows, found {len(detail)}"
    )

if set(detail["controller"].unique()) != EXPECTED_CONTROLLERS:
    raise ValueError("Unexpected controller names.")

if set(detail["replication_seed"].unique()) != EXPECTED_SEEDS:
    raise ValueError("Unexpected replication seeds.")

if set(detail["scenario"].unique()) != EXPECTED_SCENARIOS:
    raise ValueError("Unexpected scenario names.")

if detail.duplicated(
    ["replication_seed", "scenario", "controller"]
).any():
    raise ValueError("Duplicate seed-scenario-controller combinations.")

pair_sizes = detail.groupby(
    ["replication_seed", "scenario"]
).size()

if len(pair_sizes) != 50 or pair_sizes.ne(2).any():
    raise ValueError(
        "Each of the 50 seed-scenario combinations "
        "must contain exactly two controllers."
    )

if not (
    detail["accounting_valid"]
    .astype(str)
    .str.strip()
    .str.lower()
    .eq("true")
    .all()
):
    raise ValueError("At least one accounting validation failed.")

# --------------------------------------------------
# 3. NUMERIC DATA PREPARATION
# --------------------------------------------------

numeric_metrics = [
    "pqc_duration_seconds",
    "qkd_duration_seconds",
    "fallback_count",
    "false_fallback_count",
    "missed_degradation_intervals",
    "mean_detected_fallback_delay_seconds",
]

for metric in numeric_metrics:
    detail[metric] = pd.to_numeric(
        detail[metric],
        errors="coerce"
    )

# --------------------------------------------------
# 4. PAIRED CSV VALIDATION
# --------------------------------------------------

required_paired_columns = {
    "replication_seed",
    "scenario",
    "delta_pqc_seconds_hybrid_minus_v5",
    "delta_fallback_count_hybrid_minus_v5",
}

missing_paired_columns = (
    required_paired_columns - set(paired_source.columns)
)

if missing_paired_columns:
    raise ValueError(
        f"Missing paired CSV columns: {sorted(missing_paired_columns)}"
    )

if len(paired_source) != 50:
    raise ValueError(
        f"Expected 50 paired rows, found {len(paired_source)}"
    )

if paired_source.duplicated(
    ["replication_seed", "scenario"]
).any():
    raise ValueError("Duplicate rows in paired-delta CSV.")

if set(paired_source["replication_seed"].unique()) != EXPECTED_SEEDS:
    raise ValueError("Paired CSV contains unexpected seeds.")

if set(paired_source["scenario"].unique()) != EXPECTED_SCENARIOS:
    raise ValueError("Paired CSV contains unexpected scenarios.")

# Independently recalculate the two paired deltas
# from the detailed results.

detail_pivot = detail.pivot(
    index=["replication_seed", "scenario"],
    columns="controller",
    values=[
        "pqc_duration_seconds",
        "fallback_count",
    ]
)

calculated = pd.DataFrame(index=detail_pivot.index)

calculated["delta_pqc_seconds_hybrid_minus_v5"] = (
    detail_pivot["pqc_duration_seconds"]["HYBRID_IF_PERSISTENCE_3"]
    - detail_pivot["pqc_duration_seconds"]["V5_BASELINE"]
)

calculated["delta_fallback_count_hybrid_minus_v5"] = (
    detail_pivot["fallback_count"]["HYBRID_IF_PERSISTENCE_3"]
    - detail_pivot["fallback_count"]["V5_BASELINE"]
)

paired_check = paired_source.set_index(
    ["replication_seed", "scenario"]
).sort_index()

calculated = calculated.sort_index()

for column in [
    "delta_pqc_seconds_hybrid_minus_v5",
    "delta_fallback_count_hybrid_minus_v5",
]:
    source_values = pd.to_numeric(
        paired_check[column],
        errors="coerce"
    )

    calculated_values = calculated[column]

    if not np.allclose(
        source_values.to_numpy(dtype=float),
        calculated_values.to_numpy(dtype=float),
        equal_nan=True
    ):
        raise ValueError(
            f"Paired CSV validation failed for: {column}"
        )

# --------------------------------------------------
# 5. OVERALL SEED-LEVEL AGGREGATION
# --------------------------------------------------

# Duration and delay metrics:
# Mean across the five scenarios for each seed/controller.
#
# Event-count metrics:
# Sum across the five scenarios for each seed/controller.

mean_metrics = [
    "pqc_duration_seconds",
    "qkd_duration_seconds",
    "mean_detected_fallback_delay_seconds",
]

sum_metrics = [
    "fallback_count",
    "false_fallback_count",
    "missed_degradation_intervals",
]

overall = detail.groupby(
    ["replication_seed", "controller"],
    as_index=False
).agg({
    **{metric: "mean" for metric in mean_metrics},
    **{metric: "sum" for metric in sum_metrics},
})

if len(overall) != 20:
    raise ValueError(
        f"Expected 20 seed-controller aggregate rows, found {len(overall)}"
    )

# --------------------------------------------------
# 6. PAIRED STATISTICAL TESTS
# --------------------------------------------------

def paired_statistics(frame, grouping, label):

    results = []

    # Overall analysis:
    # All ten seed-level pairs are tested together.
    if grouping is None:
        grouped_frames = [("overall", frame)]

    # Scenario-wise analysis:
    # Ten paired seeds are tested separately per scenario.
    else:
        grouped_frames = list(
            frame.groupby(grouping, dropna=False)
        )

    for group_value, group in grouped_frames:

        if not isinstance(group_value, tuple):
            group_value = (group_value,)

        for metric in numeric_metrics:

            pivot = group.pivot(
                index="replication_seed",
                columns="controller",
                values=metric
            )

            if not EXPECTED_CONTROLLERS.issubset(
                set(pivot.columns)
            ):
                continue

            paired = pivot[
                CONTROLLER_ORDER
            ].dropna()

            n = len(paired)

            if n == 0:
                continue

            hybrid_values = paired[
                "HYBRID_IF_PERSISTENCE_3"
            ]

            v5_values = paired[
                "V5_BASELINE"
            ]

            differences = (
                hybrid_values - v5_values
            ).to_numpy(dtype=float)

            mean_diff = float(np.mean(differences))
            median_diff = float(np.median(differences))

            sd_diff = (
                float(np.std(differences, ddof=1))
                if n > 1
                else np.nan
            )

            # Paired t-test and 95% confidence interval
            if n > 1:

                se = sd_diff / np.sqrt(n)

                critical = stats.t.ppf(
                    0.975,
                    df=n - 1
                )

                ci_low = mean_diff - critical * se
                ci_high = mean_diff + critical * se

                t_stat, t_p = stats.ttest_rel(
                    hybrid_values,
                    v5_values
                )

                t_stat = float(t_stat)
                t_p = float(t_p)

            else:
                ci_low = np.nan
                ci_high = np.nan
                t_stat = np.nan
                t_p = np.nan

            # Wilcoxon signed-rank test
            if np.all(differences == 0):

                w_stat = 0.0
                w_p = 1.0

            else:

                try:

                    w = stats.wilcoxon(
                        hybrid_values,
                        v5_values,
                        alternative="two-sided",
                        zero_method="wilcox",
                        method="auto"
                    )

                    w_stat = float(w.statistic)
                    w_p = float(w.pvalue)

                except ValueError:

                    w_stat = np.nan
                    w_p = np.nan

            results.append({

                "analysis": label,

                "group": " | ".join(
                    map(str, group_value)
                ),

                "metric": metric,

                "n_paired": n,

                "mean_hybrid_minus_v5": mean_diff,

                "median_hybrid_minus_v5": median_diff,

                "sd_paired_difference": sd_diff,

                "ci95_lower": ci_low,

                "ci95_upper": ci_high,

                "paired_t_statistic": t_stat,

                "paired_t_p_value": t_p,

                "wilcoxon_statistic": w_stat,

                "wilcoxon_p_value": w_p,

            })

    return results

# --------------------------------------------------
# 7. RUN OVERALL AND SCENARIO-WISE ANALYSIS
# --------------------------------------------------

results = []

# Overall: 10 paired seed-level observations.
results.extend(
    paired_statistics(
        overall,
        None,
        "overall_seed_level"
    )
)

# Scenario-wise: 10 paired observations per scenario.
results.extend(
    paired_statistics(
        detail,
        ["scenario"],
        "scenario_wise"
    )
)

results_df = pd.DataFrame(results)

if results_df.empty:
    raise ValueError("No statistical test results were generated.")

# --------------------------------------------------
# 8. HOLM MULTIPLE-COMPARISON CORRECTION
# --------------------------------------------------

def holm_adjust(p_values):

    p_values = np.asarray(
        p_values,
        dtype=float
    )

    adjusted = np.full(
        len(p_values),
        np.nan,
        dtype=float
    )

    valid_indices = np.where(
        np.isfinite(p_values)
    )[0]

    if len(valid_indices) == 0:
        return adjusted

    valid_p = p_values[valid_indices]

    order = np.argsort(valid_p)

    sorted_p = valid_p[order]

    m = len(sorted_p)

    adjusted_sorted = np.maximum.accumulate(
        (m - np.arange(m)) * sorted_p
    )

    adjusted_sorted = np.minimum(
        adjusted_sorted,
        1.0
    )

    adjusted_valid = np.empty(
        m,
        dtype=float
    )

    adjusted_valid[order] = adjusted_sorted

    adjusted[valid_indices] = adjusted_valid

    return adjusted

# Apply Holm correction separately to:
# 1. All paired t-test p-values
# 2. All Wilcoxon p-values

results_df["paired_t_holm_adjusted_p"] = holm_adjust(
    results_df["paired_t_p_value"].to_numpy()
)

results_df["wilcoxon_holm_adjusted_p"] = holm_adjust(
    results_df["wilcoxon_p_value"].to_numpy()
)

# --------------------------------------------------
# 9. SAVE OUTPUTS
# --------------------------------------------------

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=False
)

test_output = (
    OUTPUT_DIR / "experiment3_paired_statistical_tests.csv"
)

aggregate_output = (
    OUTPUT_DIR / "experiment3_seed_level_aggregates.csv"
)

results_df.to_csv(
    test_output,
    index=False
)

overall.to_csv(
    aggregate_output,
    index=False
)

# --------------------------------------------------
# 10. COMPLETION REPORT
# --------------------------------------------------

print("\nSTATISTICAL ANALYSIS COMPLETED")

print(
    "Overall seed-level observations:",
    overall["replication_seed"].nunique()
)

print(
    "Detailed input rows:",
    len(detail)
)

print(
    "Paired-delta rows validated:",
    len(paired_source)
)

print(
    "Statistical test rows:",
    len(results_df)
)

print(
    "Output directory:",
    OUTPUT_DIR
)

print("\nInterpretation:")

print(
    "Positive differences mean Hybrid values are higher than V5."
)

print(
    "Negative differences mean Hybrid values are lower than V5."
)

print(
    "95% confidence intervals use the paired t-distribution."
)

print(
    "Both paired tests are two-sided."
)

print(
    "Holm correction is applied separately to t-test and Wilcoxon p-values."
)

print(
    "Wilcoxon is the more cautious primary comparison for "
    "discrete event-count metrics; t-test results are also reported."
)

print(
    "Overall duration metrics are scenario means; "
    "event-count metrics are scenario sums per seed."
)

print(
    "\nAll source experiment CSV files remain unchanged."
)
