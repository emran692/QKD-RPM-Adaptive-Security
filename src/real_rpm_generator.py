
import pandas as pd
import numpy as np
import base64
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================

INPUT_FILE = "data/physionet_ptt/processed/s1_sit_processed.csv"
HR_FILE = "data/physionet_ptt/processed/s1_sit_ecg_heart_rate.csv"
INFO_FILE = "data/physionet_ptt/csv/subjects_info.csv"

OUTPUT_DIR = Path("data/physionet_ptt/processed")
OUTPUT_FILE = OUTPUT_DIR / "real_rpm_traffic.csv"

RECORD_NAME = "s1_sit"
SAMPLING_RATE = 500
PACKET_INTERVAL = 1.0

# ==========================================
# HELPER FUNCTION
# ==========================================

def encode_float32(values):
    """Encode numeric values as little-endian Float32 bytes."""
    array = np.asarray(values, dtype="<f4")
    raw_bytes = array.tobytes()

    encoded = base64.b64encode(raw_bytes).decode("ascii")

    return encoded, len(raw_bytes)


def create_packet(packets, timestamp, sensor, values,
                  source, encoding="Float32-LE"):

    encoded, payload_size = encode_float32(values)

    packets.append({
        "elapsed_seconds": round(float(timestamp), 3),
        "sensor": sensor,
        "sample_count": len(values),
        "payload_bytes": payload_size,
        "encoding": encoding,
        "source": source,
        "payload_base64": encoded
    })


# ==========================================
# LOAD DATA
# ==========================================

print("Loading real PhysioNet RPM data...")

df = pd.read_csv(INPUT_FILE)
hr_df = pd.read_csv(HR_FILE)
info_df = pd.read_csv(INFO_FILE)

subject = info_df[
    info_df["record"].astype(str).str.strip() == RECORD_NAME
]

if subject.empty:
    raise ValueError(f"Record {RECORD_NAME} not found in subjects_info.csv")

subject = subject.iloc[0]

# ==========================================
# GENERATE ECG AND PPG PACKETS
# ==========================================

packets = []

total_samples = len(df)
total_duration = float(df["elapsed_seconds"].iloc[-1])

number_of_windows = int(np.ceil(total_duration / PACKET_INTERVAL))

print("\nGenerating ECG and PPG packets...")

for window in range(number_of_windows):

    start = window * PACKET_INTERVAL
    end = start + PACKET_INTERVAL

    segment = df[
        (df["elapsed_seconds"] >= start) &
        (df["elapsed_seconds"] < end)
    ]

    if segment.empty:
        continue

    # ECG: actual recorded samples
    ecg_values = segment["ecg"].to_numpy(dtype=np.float32)

    create_packet(
        packets,
        start,
        "ECG",
        ecg_values,
        "PhysioNet ecg"
    )

    # PPG: only channel pleth_1
    ppg_values = segment["pleth_1"].to_numpy(dtype=np.float32)

    create_packet(
        packets,
        start,
        "PPG_pleth_1",
        ppg_values,
        "PhysioNet pleth_1"
    )


# ==========================================
# GENERATE HEART RATE PACKETS
# ==========================================

print("Generating ECG-derived heart-rate packets...")

hr_df["time_window"] = (
    hr_df["elapsed_seconds"] // PACKET_INTERVAL
).astype(int)

hr_summary = hr_df.groupby("time_window")["heart_rate_bpm"].median()

for window, heart_rate in hr_summary.items():

    create_packet(
        packets,
        float(window),
        "Heart_Rate",
        [heart_rate],
        "ECG-derived median HR"
    )


# ==========================================
# GENERATE TEMPERATURE PACKETS
# ==========================================

print("Generating temperature packets...")

df["time_window"] = (
    df["elapsed_seconds"] // PACKET_INTERVAL
).astype(int)

temperature_summary = df.groupby("time_window")["temp_1"].median()

for window, temperature in temperature_summary.items():

    create_packet(
        packets,
        float(window),
        "Temperature",
        [temperature],
        "PhysioNet temp_1"
    )


# ==========================================
# GENERATE SPO2 START/END EVENTS
# ==========================================

print("Generating SpO2 measurement events...")

spo2_events = [
    (0.0, subject["spo2_start"], "start"),
    (total_duration, subject["spo2_end"], "end")
]

for timestamp, value, label in spo2_events:

    create_packet(
        packets,
        timestamp,
        "SpO2",
        [value],
        f"PhysioNet recorded {label} measurement"
    )


# ==========================================
# GENERATE BLOOD PRESSURE EVENTS
# ==========================================

print("Generating blood-pressure measurement events...")

bp_events = [
    (0.0, subject["bp_sys_start"], "Systolic_BP", "start"),
    (0.0, subject["bp_dia_start"], "Diastolic_BP", "start"),
    (total_duration, subject["bp_sys_end"], "Systolic_BP", "end"),
    (total_duration, subject["bp_dia_end"], "Diastolic_BP", "end")
]

for timestamp, value, sensor, label in bp_events:

    create_packet(
        packets,
        timestamp,
        sensor,
        [value],
        f"PhysioNet recorded {label} measurement"
    )


# ==========================================
# SAVE RPM TRAFFIC
# ==========================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

result = pd.DataFrame(packets)

result = result.sort_values(
    by=["elapsed_seconds", "sensor"]
).reset_index(drop=True)

result.insert(
    0,
    "packet_id",
    np.arange(1, len(result) + 1)
)

result.to_csv(OUTPUT_FILE, index=False)


# ==========================================
# SUMMARY
# ==========================================

print("\n========== REAL RPM TRAFFIC SUMMARY ==========")

print("Dataset record:", RECORD_NAME)
print("Total original samples:", total_samples)
print("Sampling frequency:", SAMPLING_RATE, "Hz")
print("Recording duration:", round(total_duration, 2), "seconds")

print("\nPackets by sensor:")

print(
    result.groupby("sensor").size().to_string()
)

total_bytes = int(result["payload_bytes"].sum())
total_bits = total_bytes * 8

print("\nTotal packets:", len(result))
print("Total payload:", total_bytes, "bytes")
print("Total payload:", total_bits, "bits")

print(
    "Average payload data rate:",
    round(total_bits / total_duration, 2),
    "bps"
)

print("\nPacket encoding: Float32 little-endian")
print("PPG channels used: pleth_1 only")

print("\nOutput saved:", OUTPUT_FILE)

print("\nReal RPM traffic generation completed.")
