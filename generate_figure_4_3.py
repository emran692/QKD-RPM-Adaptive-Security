from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

input_file = Path(
    "results/anomaly_detection_v5_hybrid_confirmation/v5_if_timeseries.csv"
)
output_dir = Path("results/figures")
output_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(input_file)

df["time_seconds"] = pd.to_numeric(df["time_seconds"])
df["qkd_generation_bps"] = pd.to_numeric(df["qkd_generation_bps"])

# Evaluation period
evaluation = df[
    (df["time_seconds"] >= 220) &
    (df["time_seconds"] <= 507)
].copy().sort_values("time_seconds")

# Validate observations and channel labels
if len(evaluation) != 288:
    raise ValueError(f"Expected 288 observations, found {len(evaluation)}")

normal = evaluation[evaluation["channel_status"] == "NORMAL"]
degraded = evaluation[evaluation["channel_status"] == "DEGRADED"]

if len(normal) != 228 or len(degraded) != 60:
    raise ValueError("Channel-label distribution does not match verified data")

# Calculate statistics directly from the CSV
normal_mean = normal["qkd_generation_bps"].mean()
degraded_mean = degraded["qkd_generation_bps"].mean()
overall_mean = evaluation["qkd_generation_bps"].mean()

# Verify against inspected values
if round(normal_mean, 2) != 1201.92:
    raise ValueError(f"Unexpected normal mean: {normal_mean}")

if round(degraded_mean, 2) != 257.67:
    raise ValueError(f"Unexpected degraded mean: {degraded_mean}")

# Plot
fig, ax = plt.subplots(figsize=(12, 6))

# Shade actual degraded intervals
times = evaluation["time_seconds"].tolist()
statuses = evaluation["channel_status"].tolist()

start = None
previous_time = None

for time, status in zip(times, statuses):
    if status == "DEGRADED":
        if start is None:
            start = time
        previous_time = time
    elif start is not None:
        ax.axvspan(start - 0.5, previous_time + 0.5, alpha=0.15)
        start = None

if start is not None:
    ax.axvspan(start - 0.5, previous_time + 0.5, alpha=0.15)

# Generation-rate time series
ax.plot(
    evaluation["time_seconds"],
    evaluation["qkd_generation_bps"],
    linewidth=1.5,
    label="QKD key generation rate"
)

ax.set_title(
    "QKD Key Generation Rate During the Evaluation Period",
    fontsize=14,
    fontweight="bold",
    pad=14
)
ax.set_xlabel("Time (seconds)", fontsize=11)
ax.set_ylabel("QKD Key Generation Rate (bits per second)", fontsize=11)
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

fig.text(
    0.5,
    0.015,
    f"Normal mean: {normal_mean:.2f} bps | "
    f"Degraded mean: {degraded_mean:.2f} bps | "
    f"Overall mean: {overall_mean:.2f} bps",
    ha="center",
    fontsize=9
)

plt.tight_layout(rect=[0, 0.05, 1, 1])

output_file = output_dir / "Figure_4_3_QKD_Generation_Rate_vs_Time.png"
fig.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close(fig)

print("\n========== FIGURE 4.3 GENERATED ==========")
print(f"Evaluation observations : {len(evaluation)}")
print(f"Normal samples           : {len(normal)}")
print(f"Degraded samples         : {len(degraded)}")
print(f"Normal mean              : {normal_mean:.2f} bps")
print(f"Degraded mean            : {degraded_mean:.2f} bps")
print(f"Overall mean             : {overall_mean:.2f} bps")
print(f"\nSaved: {output_file}")
print("Verification: PASSED")
