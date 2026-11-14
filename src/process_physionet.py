
import pandas as pd
import numpy as np
from pathlib import Path

INPUT_FILE = "data/physionet_ptt/csv/s1_sit.csv"
OUTPUT_FILE = "data/physionet_ptt/processed/s1_sit_processed.csv"

SAMPLING_RATE = 500  # Hz, verified from median sample interval

print("Loading original PhysioNet recording...")

df = pd.read_csv(INPUT_FILE)
df["time"] = pd.to_datetime(df["time"])

# Preserve the original timestamp
df = df.rename(columns={"time": "source_time"})

# Create sample-based elapsed time.
# This does not modify or claim to repair the original wall-clock time.
df.insert(
    0,
    "elapsed_seconds",
    np.arange(len(df), dtype=np.float64) / SAMPLING_RATE
)

# Identify original timestamp discontinuities
original_diffs = df["source_time"].diff().dt.total_seconds()
df["timestamp_discontinuity"] = original_diffs.lt(0)

# Extract ECG peak locations
peak_indices = np.flatnonzero(df["peaks"].to_numpy() == 1)

print("\n========== PROCESSING RESULTS ==========")
print("Total samples:", len(df))
print("Sampling rate:", SAMPLING_RATE, "Hz")
print("Sample-based duration:", round(df["elapsed_seconds"].iloc[-1], 3), "seconds")
print("ECG annotated peaks:", len(peak_indices))
print("Timestamp discontinuities:", int(df["timestamp_discontinuity"].sum()))

# Calculate heart rate from consecutive annotated ECG peaks
if len(peak_indices) >= 2:
    rr_intervals = np.diff(peak_indices) / SAMPLING_RATE
    heart_rates = 60 / rr_intervals

    print("\n========== ECG HEART RATE ==========")
    print("Mean HR:", round(float(np.mean(heart_rates)), 2), "bpm")
    print("Median HR:", round(float(np.median(heart_rates)), 2), "bpm")
    print("Minimum HR:", round(float(np.min(heart_rates)), 2), "bpm")
    print("Maximum HR:", round(float(np.max(heart_rates)), 2), "bpm")

    rr_df = pd.DataFrame({
        "peak_sample_index": peak_indices[1:],
        "elapsed_seconds": peak_indices[1:] / SAMPLING_RATE,
        "rr_interval_seconds": rr_intervals,
        "heart_rate_bpm": heart_rates
    })

    rr_output = "data/physionet_ptt/processed/s1_sit_ecg_heart_rate.csv"
    Path(rr_output).parent.mkdir(parents=True, exist_ok=True)
    rr_df.to_csv(rr_output, index=False)
    print("ECG heart-rate data saved:", rr_output)

# Save processed recording while retaining source timestamps
Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

print("\nProcessed dataset saved:", OUTPUT_FILE)
print("Original source CSV remains unchanged.")
