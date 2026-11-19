from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# Paths
input_file = Path(
    "results/anomaly_detection_v5_hybrid_confirmation/v5_if_timeseries.csv"
)
output_dir = Path("results/figures")
output_dir.mkdir(parents=True, exist_ok=True)

# Load data
df = pd.read_csv(input_file)

# Evaluation period only
df["time_seconds"] = pd.to_numeric(df["time_seconds"])
df["qber"] = pd.to_numeric(df["qber"])
df["rolling_qber"] = pd.to_numeric(df["rolling_qber"])

evaluation = df[
    (df["time_seconds"] >= 220) &
    (df["time_seconds"] <= 507)
].copy()

evaluation = evaluation.sort_values("time_seconds")

# Validate data
if len(evaluation) != 288:
    raise ValueError(f"Expected 288 rows, found {len(evaluation)}")

if evaluation[["qber", "rolling_qber"]].isna().any().any():
    raise ValueError("Missing QBER values found in evaluation period")

degraded_count = (evaluation["channel_status"] == "DEGRADED").sum()
normal_count = (evaluation["channel_status"] == "NORMAL").sum()

if degraded_count != 60 or normal_count != 228:
    raise ValueError(
        f"Unexpected channel distribution: "
        f"DEGRADED={degraded_count}, NORMAL={normal_count}"
    )

# Convert QBER fraction into percentage
evaluation["qber_percent"] = evaluation["qber"] * 100
evaluation["rolling_qber_percent"] = evaluation["rolling_qber"] * 100

# Create figure
fig, ax = plt.subplots(figsize=(12, 6))

# Identify contiguous degraded intervals from actual labels
times = evaluation["time_seconds"].tolist()
statuses = evaluation["channel_status"].tolist()

start = None
previous_time = None

for time, status in zip(times, statuses):
    if status == "DEGRADED":
        if start is None:
            start = time
        previous_time = time
    else:
        if start is not None:
            ax.axvspan(
                start - 0.5,
                previous_time + 0.5,
                alpha=0.15
            )
            start = None

if start is not None:
    ax.axvspan(
        start - 0.5,
        previous_time + 0.5,
        alpha=0.15
    )

# Plot raw and rolling QBER
ax.plot(
    evaluation["time_seconds"],
    evaluation["qber_percent"],
    linewidth=1.0,
    alpha=0.55,
    label="Raw QBER"
)

ax.plot(
    evaluation["time_seconds"],
    evaluation["rolling_qber_percent"],
    linewidth=2.0,
    label="Rolling QBER"
)

# Labels and formatting
ax.set_title(
    "QBER Variation During the Evaluation Period",
    fontsize=14,
    fontweight="bold",
    pad=14
)

ax.set_xlabel("Time (seconds)", fontsize=11)
ax.set_ylabel("Quantum Bit Error Rate (%)", fontsize=11)

ax.set_xlim(220, 507)
ax.grid(True, alpha=0.3)

# Legend
handles, labels = ax.get_legend_handles_labels()
handles.append(
    Patch(
        facecolor="grey",
        alpha=0.15,
        label="Degraded channel intervals"
    )
)
ax.legend(handles=handles, loc="upper right")

# Footnote
fig.text(
    0.5,
    0.015,
    "Evaluation: 220–507 seconds | "
    "288 observations | 60 degraded, 228 normal",
    ha="center",
    fontsize=9
)

plt.tight_layout(rect=[0, 0.05, 1, 1])

# Save
output_file = output_dir / "Figure_4_2_QBER_vs_Time.png"
fig.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close(fig)

# Report
print("\n========== FIGURE 4.2 GENERATED ==========")
print(f"Evaluation observations : {len(evaluation)}")
print(f"Normal observations     : {normal_count}")
print(f"Degraded observations   : {degraded_count}")
print(f"Mean raw QBER           : {evaluation['qber'].mean():.6f}")
print(f"Mean rolling QBER       : {evaluation['rolling_qber'].mean():.6f}")
print(f"Minimum raw QBER        : {evaluation['qber'].min():.6f}")
print(f"Maximum raw QBER        : {evaluation['qber'].max():.6f}")
print(f"\nSaved: {output_file}")
print("Verification: PASSED")
