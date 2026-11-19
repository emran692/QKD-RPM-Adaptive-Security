from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

input_file = Path(
    "results/anomaly_detection_v5_hybrid_confirmation/v5_if_timeseries.csv"
)
output_dir = Path("results/figures")
output_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(input_file)

for col in ["time_seconds", "mode_transition", "rekey_event", "rekey_success"]:
    df[col] = pd.to_numeric(df[col])

evaluation = df[
    (df["time_seconds"] >= 220) &
    (df["time_seconds"] <= 507)
].copy().sort_values("time_seconds")

# Validate evaluation data
if len(evaluation) != 288:
    raise ValueError(f"Expected 288 observations, found {len(evaluation)}")

mode_counts = evaluation["operating_mode"].value_counts().to_dict()

if mode_counts.get("QKD", 0) != 220:
    raise ValueError(f"Unexpected QKD count: {mode_counts}")

if mode_counts.get("PQC_FALLBACK", 0) != 68:
    raise ValueError(f"Unexpected PQC count: {mode_counts}")

transitions = evaluation[evaluation["mode_transition"] == 1]
rekeys = evaluation[evaluation["rekey_event"] == 1]

transition_times = transitions["time_seconds"].tolist()
rekey_times = rekeys["time_seconds"].tolist()

if transition_times != [226, 294]:
    raise ValueError(f"Unexpected transition times: {transition_times}")

if rekey_times != [226, 286, 294, 354, 414, 474]:
    raise ValueError(f"Unexpected rekey times: {rekey_times}")

if not (rekeys["rekey_success"] == 1).all():
    raise ValueError("One or more rekey events were unsuccessful")

# Map operating modes to categorical levels
mode_map = {
    "QKD": 1,
    "PQC_FALLBACK": 0
}
evaluation["mode_level"] = evaluation["operating_mode"].map(mode_map)

if evaluation["mode_level"].isna().any():
    raise ValueError("Unexpected operating mode found")

# Separate scheduled rekeys from transition-triggered rekeys
scheduled = rekeys[rekeys["rekey_reason"] == "SCHEDULED"]

# Plot
fig, ax = plt.subplots(figsize=(12, 6))

# Operating mode timeline
ax.step(
    evaluation["time_seconds"],
    evaluation["mode_level"],
    where="post",
    linewidth=2.5,
    label="Operating mode"
)

# Mark transition events
for _, event in transitions.iterrows():
    time = event["time_seconds"]
    ax.axvline(time, linestyle="--", linewidth=1.3, alpha=0.8)

    if event["operating_mode"] == "PQC_FALLBACK":
        label = "QKD → PQC fallback"
        y = 0.35
    else:
        label = "PQC fallback → QKD"
        y = 0.65

    ax.annotate(
        f"{label}\n{int(time)} s",
        xy=(time, mode_map[event["operating_mode"]]),
        xytext=(time + 5, y),
        fontsize=9,
        arrowprops={"arrowstyle": "->", "linewidth": 0.8}
    )

# Mark scheduled rekey events
for _, event in scheduled.iterrows():
    time = event["time_seconds"]
    level = mode_map[event["operating_mode"]]

    ax.scatter(
        time,
        level,
        marker="o",
        s=65,
        zorder=5,
        label="Scheduled rekey" if time == scheduled.iloc[0]["time_seconds"] else None
    )

# Axis formatting
ax.set_title(
    "Adaptive QKD–PQC Operating-Mode Transition Timeline",
    fontsize=14,
    fontweight="bold",
    pad=14
)
ax.set_xlabel("Time (seconds)", fontsize=11)
ax.set_ylabel("Operating Mode", fontsize=11)

ax.set_yticks([0, 1])
ax.set_yticklabels(["PQC_FALLBACK", "QKD"])

ax.set_xlim(220, 507)
ax.set_ylim(-0.25, 1.25)
ax.set_xticks(range(220, 508, 20))
ax.grid(True, axis="x", alpha=0.3)

ax.legend(loc="lower right")

fig.text(
    0.5,
    0.015,
    "Evaluation: 220–507 seconds | "
    "QKD: 220 observations | PQC fallback: 68 observations | "
    "6 successful rekey events",
    ha="center",
    fontsize=9
)

plt.tight_layout(rect=[0, 0.05, 1, 1])

output_file = output_dir / "Figure_4_4_QKD_PQC_Transition_Timeline.png"
fig.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close(fig)

print("\n========== FIGURE 4.4 GENERATED ==========")
print(f"Evaluation observations : {len(evaluation)}")
print(f"QKD observations       : {mode_counts['QKD']}")
print(f"PQC fallback samples   : {mode_counts['PQC_FALLBACK']}")
print(f"Mode transitions       : {transition_times}")
print(f"All rekey events       : {rekey_times}")
print(f"Successful rekeys      : {int(rekeys['rekey_success'].sum())}")
print(f"\nSaved: {output_file}")
print("Verification: PASSED")
