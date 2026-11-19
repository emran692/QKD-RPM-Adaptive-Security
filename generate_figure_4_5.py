from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

input_file = Path(
    "results/anomaly_detection_v5_hybrid_confirmation/v5_if_timeseries.csv"
)
output_file = Path(
    "results/figures/Figure_4_5_Key_Pool_Balance_and_Replenishment.png"
)

# Load evaluation window
df = pd.read_csv(input_file)
df = df[
    (df["time_seconds"] >= 220) &
    (df["time_seconds"] <= 507)
].copy()

# Convert numeric fields
numeric_columns = [
    "time_seconds",
    "key_pool_bits",
    "accepted_key_bits",
    "qkd_consumed_bits",
    "rekey_event",
    "rekey_success",
]

for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="raise")

# Only successful QKD rekeys affect the QKD pool
qkd_rekeys = df[
    (df["operating_mode"] == "QKD") &
    (df["rekey_event"] == 1) &
    (df["rekey_success"] == 1)
]

# Identify pool replenishment completion observations
replenishments = df[
    (df["accepted_key_bits"] > 0) &
    (df["key_pool_bits"] == 30000)
]

# Validate source data
assert len(df) == 288
assert len(qkd_rekeys) == 4
assert len(replenishments) == 4
assert df["key_pool_bits"].min() == 28720
assert df["key_pool_bits"].max() == 30000

# Generate plot
fig, ax = plt.subplots(figsize=(13, 6.5))

ax.plot(
    df["time_seconds"],
    df["key_pool_bits"],
    linewidth=1.8,
    label="Key-pool balance"
)

ax.axhline(
    y=30000,
    linestyle="--",
    linewidth=1.4,
    label="Key-pool capacity (30,000 bits)"
)

ax.scatter(
    qkd_rekeys["time_seconds"],
    qkd_rekeys["key_pool_bits"],
    marker="D",
    s=75,
    zorder=4,
    label="Successful QKD rekey"
)

ax.scatter(
    replenishments["time_seconds"],
    replenishments["key_pool_bits"],
    marker="o",
    s=65,
    zorder=4,
    label="Pool replenishment completed"
)

ax.set_title(
    "Key-Pool Balance and Replenishment During QKD Rekey Events",
    fontsize=14,
    fontweight="bold"
)

ax.set_xlabel("Time (seconds)", fontsize=11)
ax.set_ylabel("Key-pool balance (bits)", fontsize=11)

ax.set_xlim(220, 507)
ax.set_ylim(28400, 30200)
ax.grid(True, linestyle=":", alpha=0.6)
ax.legend(loc="lower right", fontsize=9)

fig.tight_layout()

# Save figure
output_file.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close(fig)

# Verify output
assert output_file.exists()
assert output_file.stat().st_size > 0

print("\n========== FIGURE 4.5 GENERATED ==========")
print(f"Evaluation observations        : {len(df)}")
print(f"Minimum key-pool balance       : {df['key_pool_bits'].min()} bits")
print(f"Maximum key-pool balance       : {df['key_pool_bits'].max()} bits")
print(f"Successful QKD rekeys          : {len(qkd_rekeys)}")
print(f"QKD rekey times                : {qkd_rekeys['time_seconds'].astype(int).tolist()}")
print(f"Replenishment completion times : {replenishments['time_seconds'].astype(int).tolist()}")
print(f"\nSaved: {output_file}")
print("Verification: PASSED")
