from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

source = Path(
    "results/experiment_3_statistical_analysis_20261116/"
    "experiment3_paired_statistical_tests.csv"
)
output_dir = Path("results/figures")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "Figure_4_6_Paired_Statistical_Comparisons.png"

df = pd.read_csv(source)
df = df[df["analysis"] == "overall_seed_level"].copy()

expected = {
    "pqc_duration_seconds",
    "qkd_duration_seconds",
    "fallback_count",
    "false_fallback_count",
    "missed_degradation_intervals",
    "mean_detected_fallback_delay_seconds",
}
if set(df["metric"]) != expected:
    raise ValueError("Unexpected metric set. Check the statistical CSV.")

if not (df["n_paired"] == 10).all():
    raise ValueError("Expected 10 paired seeds for every metric.")

data = df.set_index("metric")

time_metrics = [
    ("pqc_duration_seconds", "PQC duration"),
    ("qkd_duration_seconds", "QKD duration"),
    ("mean_detected_fallback_delay_seconds", "Fallback detection delay"),
]

count_metrics = [
    ("fallback_count", "Fallback count"),
    ("false_fallback_count", "False fallback count"),
    ("missed_degradation_intervals", "Missed degradation intervals"),
]

fig, axes = plt.subplots(
    1, 2, figsize=(14, 6.8),
    gridspec_kw={"width_ratios": [1.25, 1]}
)

def draw_panel(ax, metrics, title, x_label, x_limit):
    positions = np.arange(len(metrics))[::-1]

    for position, (metric, label) in zip(positions, metrics):
        row = data.loc[metric]
        mean = float(row["mean_hybrid_minus_v5"])
        lower = float(row["ci95_lower"])
        upper = float(row["ci95_upper"])

        left_error = max(0.0, mean - lower)
        right_error = max(0.0, upper - mean)

        ax.errorbar(
            mean, position,
            xerr=np.array([[left_error], [right_error]]),
            fmt="o", markersize=7, capsize=5,
            elinewidth=1.8
        )

        ax.text(
            x_limit[1] * 0.98, position,
            f"{mean:+.3f}  [{lower:+.3f}, {upper:+.3f}]",
            ha="right", va="center", fontsize=8
        )

    ax.axvline(0, linestyle="--", linewidth=1.2)
    ax.set_yticks(positions)
    ax.set_yticklabels([label for _, label in metrics])
    ax.set_xlim(*x_limit)
    ax.set_xlabel(x_label)
    ax.set_title(title, fontweight="bold")
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)

draw_panel(
    axes[0],
    time_metrics,
    "A. Time-based metrics",
    "Mean paired difference (seconds)",
    (-2.5, 2.5)
)

draw_panel(
    axes[1],
    count_metrics,
    "B. Event-count metrics",
    "Mean paired difference (count)",
    (-0.5, 0.5)
)

fig.suptitle(
    "Paired Differences: Hybrid IF-Persistence Controller vs V5 Baseline",
    fontsize=13, fontweight="bold"
)

fig.text(
    0.5, 0.025,
    "Difference = Hybrid − V5; n = 10 paired replication seeds. "
    "Intervals are reported 95% confidence intervals. "
    "Time metrics: Holm-adjusted paired t-test p = 0.00487, "
    "0.00487 and 0.00292 respectively; Holm-adjusted Wilcoxon p = 0.140625 "
    "for each. False fallbacks and missed intervals: both tests p = 1.000. "
    "Fallback count: all paired differences are zero; t-test not estimable, "
    "Wilcoxon p = 1.000.",
    ha="center", va="bottom", fontsize=8, wrap=True
)

fig.text(
    0.5, 0.005,
    "Negative differences indicate lower values for the hybrid controller.",
    ha="center", va="bottom", fontsize=8, style="italic"
)

plt.tight_layout(rect=[0, 0.12, 1, 0.92])
fig.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close(fig)

print("FIGURE 4.6 GENERATED")
print(f"Source: {source}")
print(f"Output: {output_file}")
print(f"Metrics: {len(df)} | Paired seeds per metric: 10")
