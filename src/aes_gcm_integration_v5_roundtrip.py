
"""
AES-256-GCM Integration for Adaptive QKD/PQC RPM System

IMPORTANT:
- QKD key material is represented by random simulation placeholders.
- PQC key material is represented by random simulation placeholders.
- No physical QKD or actual ML-KEM exchange is performed.
- Session keys are retained in memory only and never written to disk.
"""

import base64
import csv
import json
import secrets
import time

from bisect import bisect_right
from pathlib import Path
from collections import defaultdict

import pandas as pd

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


# --------------------------------------------------
# 1. FILE PATHS
# --------------------------------------------------

TRAFFIC_FILE = Path(
    "data/physionet_ptt/processed/real_rpm_traffic.csv"
)

# Must match adaptive_controller_v5.py's default output prefix:
# results/adaptive_508s_v5_timeseries.csv
CONTROLLER_FILE = Path(
    "results/adaptive_508s_v5_timeseries.csv"
)

OUTPUT_DIR = Path("results/aes_gcm")

ENCRYPTED_FILE = OUTPUT_DIR / "aes_encrypted_traffic.csv"
SUMMARY_FILE = OUTPUT_DIR / "aes_gcm_summary.json"


# --------------------------------------------------
# 2. CRYPTOGRAPHIC CONFIGURATION
# --------------------------------------------------

AES_KEY_BYTES = 32          # AES-256
NONCE_BYTES = 12            # 96-bit GCM nonce
TAG_BYTES = 16              # 128-bit authentication tag

NUMBER_OF_SESSIONS = 5


# --------------------------------------------------
# 3. SENSOR-TO-SESSION MAPPING
# --------------------------------------------------

SENSOR_SESSION_MAP = {
    "ECG": "SESSION_1",
    "PPG_pleth_1": "SESSION_2",
    "Heart_Rate": "SESSION_3",
    "Temperature": "SESSION_4",
    "SpO2": "SESSION_5",
    "Systolic_BP": "SESSION_5",
    "Diastolic_BP": "SESSION_5"
}


# --------------------------------------------------
# 4. LOAD INPUT DATA
# --------------------------------------------------

def load_data():

    if not TRAFFIC_FILE.exists():
        raise FileNotFoundError(
            f"RPM traffic file not found: {TRAFFIC_FILE}"
        )

    if not CONTROLLER_FILE.exists():
        raise FileNotFoundError(
            f"Controller file not found: {CONTROLLER_FILE}"
        )

    traffic = pd.read_csv(TRAFFIC_FILE)

    controller = pd.read_csv(CONTROLLER_FILE)

    required_traffic_columns = {
        "packet_id",
        "elapsed_seconds",
        "sensor",
        "sample_count",
        "payload_bytes",
        "encoding",
        "source",
        "payload_base64"
    }

    required_controller_columns = {
        "time_seconds",
        "operating_mode",
        "rekey_event",
        "key_source",
        "session_key_epoch"
    }

    missing_traffic = (
        required_traffic_columns - set(traffic.columns)
    )

    missing_controller = (
        required_controller_columns - set(controller.columns)
    )

    if missing_traffic:
        raise ValueError(
            f"Missing traffic columns: {missing_traffic}"
        )

    if missing_controller:
        raise ValueError(
            f"Missing controller columns: {missing_controller}"
        )

    # Confirm that this is a V5-compatible controller output.
    if controller.empty:
        raise ValueError("V5 controller timeseries is empty.")

    valid_modes = {"QKD", "PQC_FALLBACK"}
    unexpected_modes = set(controller["operating_mode"].dropna()) - valid_modes
    if unexpected_modes:
        raise ValueError(
            f"Unexpected operating modes in controller output: "
            f"{sorted(unexpected_modes)}"
        )

    return traffic, controller


# --------------------------------------------------
# 5. BUILD KEY SCHEDULE
# --------------------------------------------------

def generate_key_schedule(controller):

    rekey_rows = controller[
        controller["rekey_event"].astype(int) == 1
    ].copy()

    rekey_rows = rekey_rows.sort_values("time_seconds")

    if rekey_rows.empty:
        raise ValueError("No successful rekey events found.")

    key_schedule = {}

    key_registry = {}

    for _, row in rekey_rows.iterrows():

        epoch = int(row["session_key_epoch"])
        source = str(row["key_source"])
        mode = str(row["operating_mode"])
        rekey_time = float(row["time_seconds"])

        if source not in (
            "SIMULATED_QKD_POOL",
            "SIMULATED_PQC"
        ):
            raise ValueError(
                f"Unexpected key source: {source}"
            )

        if epoch <= 0:
            raise ValueError("Invalid session key epoch.")

        if mode == "QKD" and source != "SIMULATED_QKD_POOL":
            raise ValueError(
                f"V5 mode/source mismatch at {rekey_time}s: "
                f"mode={mode}, source={source}"
            )
        if mode == "PQC_FALLBACK" and source != "SIMULATED_PQC":
            raise ValueError(
                f"V5 mode/source mismatch at {rekey_time}s: "
                f"mode={mode}, source={source}"
            )

        session_keys = {}

        for session_id in [
            f"SESSION_{i}"
            for i in range(1, NUMBER_OF_SESSIONS + 1)
        ]:

            # Simulation placeholder only.
            # This is NOT actual QKD or ML-KEM output.
            key = secrets.token_bytes(AES_KEY_BYTES)

            session_keys[session_id] = key

            key_registry[(epoch, session_id)] = key

        key_schedule[rekey_time] = {
            "epoch": epoch,
            "mode": mode,
            "key_source": source
        }

    schedule_times = sorted(key_schedule.keys())

    return key_schedule, schedule_times, key_registry


# --------------------------------------------------
# 6. CREATE AUTHENTICATED METADATA
# --------------------------------------------------

def create_aad(packet, session_id, epoch, key_source):

    metadata = {
        "packet_id": int(packet["packet_id"]),
        "elapsed_seconds": float(packet["elapsed_seconds"]),
        "sensor": str(packet["sensor"]),
        "session_id": session_id,
        "key_epoch": int(epoch),
        "key_source": key_source,
        "sample_count": int(packet["sample_count"]),
        "encoding": str(packet["encoding"]),
        "source": str(packet["source"])
    }

    aad = json.dumps(
        metadata,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")

    return aad


# --------------------------------------------------
# 7. ENCRYPT RPM TRAFFIC
# --------------------------------------------------

def encrypt_traffic(
    traffic,
    key_schedule,
    schedule_times,
    key_registry
):

    encrypted_records = []

    used_nonces = defaultdict(set)

    encryption_start = time.perf_counter()

    plaintext_total = 0
    ciphertext_total = 0

    for _, packet in traffic.sort_values(
        ["elapsed_seconds", "packet_id"]
    ).iterrows():

        packet_id = int(packet["packet_id"])

        elapsed = float(packet["elapsed_seconds"])

        sensor = str(packet["sensor"])

        if sensor not in SENSOR_SESSION_MAP:
            raise ValueError(
                f"Unknown sensor: {sensor}"
            )

        session_id = SENSOR_SESSION_MAP[sensor]

        # Find the latest rekey event at or before packet time.
        schedule_index = bisect_right(
            schedule_times,
            elapsed
        ) - 1

        if schedule_index < 0:
            raise ValueError(
                f"No session key available for packet {packet_id}"
            )

        rekey_time = schedule_times[schedule_index]

        event = key_schedule[rekey_time]

        epoch = event["epoch"]
        key_source = event["key_source"]
        operating_mode = event["mode"]

        key = key_registry[(epoch, session_id)]

        # Decode actual RPM packet payload.
        plaintext = base64.b64decode(
            str(packet["payload_base64"]),
            validate=True
        )

        expected_length = int(packet["payload_bytes"])

        if len(plaintext) != expected_length:
            raise ValueError(
                f"Payload size mismatch for packet {packet_id}: "
                f"expected {expected_length}, got {len(plaintext)}"
            )

        # Construct authenticated metadata.
        aad = create_aad(
            packet,
            session_id,
            epoch,
            key_source
        )

        # Generate a fresh nonce and enforce uniqueness per key.
        nonce = secrets.token_bytes(NONCE_BYTES)

        while nonce in used_nonces[(epoch, session_id)]:
            nonce = secrets.token_bytes(NONCE_BYTES)

        used_nonces[(epoch, session_id)].add(nonce)

        aesgcm = AESGCM(key)

        encrypted_output = aesgcm.encrypt(
            nonce,
            plaintext,
            aad
        )

        # cryptography AESGCM returns ciphertext || tag.
        ciphertext = encrypted_output[:-TAG_BYTES]
        tag = encrypted_output[-TAG_BYTES:]

        if len(ciphertext) != len(plaintext):
            raise RuntimeError(
                "Unexpected AES-GCM ciphertext length."
            )

        plaintext_total += len(plaintext)
        ciphertext_total += len(ciphertext)

        encrypted_records.append({
            "packet_id": packet_id,
            "elapsed_seconds": elapsed,
            "sensor": sensor,
            "session_id": session_id,
            "operating_mode": operating_mode,
            "key_source": key_source,
            "key_epoch": epoch,

            "sample_count": int(packet["sample_count"]),
            "encoding": str(packet["encoding"]),

            "plaintext_bytes": len(plaintext),
            "ciphertext_bytes": len(ciphertext),

            "nonce_b64": base64.b64encode(
                nonce
            ).decode("ascii"),

            "ciphertext_b64": base64.b64encode(
                ciphertext
            ).decode("ascii"),

            "tag_b64": base64.b64encode(
                tag
            ).decode("ascii"),

            "aad_b64": base64.b64encode(
                aad
            ).decode("ascii")
        })

    encryption_time = (
        time.perf_counter() - encryption_start
    )

    return (
        encrypted_records,
        encryption_time,
        plaintext_total,
        ciphertext_total,
        used_nonces
    )


# --------------------------------------------------
# 8. DECRYPT AND VERIFY ALL PACKETS
# --------------------------------------------------

def decrypt_and_verify(
    encrypted_records,
    key_registry,
    original_traffic
):

    decryption_start = time.perf_counter()

    verified_packets = 0
    failed_packets = 0
    round_trip_verified_packets = 0
    round_trip_failures = 0

    # Retain the original payload bytes for an exact byte-for-byte
    # comparison after authenticated decryption.
    original_payloads = {}
    for _, packet in original_traffic.iterrows():
        packet_id = int(packet["packet_id"])
        original_payloads[packet_id] = base64.b64decode(
            str(packet["payload_base64"]),
            validate=True
        )

    for record in encrypted_records:

        epoch = int(record["key_epoch"])
        session_id = record["session_id"]

        key = key_registry[(epoch, session_id)]

        nonce = base64.b64decode(
            record["nonce_b64"],
            validate=True
        )

        ciphertext = base64.b64decode(
            record["ciphertext_b64"],
            validate=True
        )

        tag = base64.b64decode(
            record["tag_b64"],
            validate=True
        )

        aad = base64.b64decode(
            record["aad_b64"],
            validate=True
        )

        if len(nonce) != NONCE_BYTES:
            raise ValueError("Invalid GCM nonce length.")

        if len(tag) != TAG_BYTES:
            raise ValueError("Invalid GCM authentication tag length.")

        aesgcm = AESGCM(key)

        try:

            decrypted = aesgcm.decrypt(
                nonce,
                ciphertext + tag,
                aad
            )

            if len(decrypted) != int(record["plaintext_bytes"]):
                failed_packets += 1
                round_trip_failures += 1
                continue

            verified_packets += 1

            packet_id = int(record["packet_id"])
            original_plaintext = original_payloads.get(packet_id)

            if original_plaintext is None:
                round_trip_failures += 1
            elif decrypted == original_plaintext:
                round_trip_verified_packets += 1
            else:
                round_trip_failures += 1

        except InvalidTag:

            failed_packets += 1

    decryption_time = (
        time.perf_counter() - decryption_start
    )

    return (
        verified_packets,
        failed_packets,
        round_trip_verified_packets,
        round_trip_failures,
        decryption_time
    )


# --------------------------------------------------
# 9. CIPHERTEXT TAMPERING TEST
# --------------------------------------------------

def run_tamper_test(
    encrypted_records,
    key_registry
):

    if not encrypted_records:
        raise ValueError("No encrypted packets available.")

    record = encrypted_records[0]

    epoch = int(record["key_epoch"])
    session_id = record["session_id"]

    key = key_registry[(epoch, session_id)]

    nonce = base64.b64decode(
        record["nonce_b64"]
    )

    ciphertext = bytearray(
        base64.b64decode(record["ciphertext_b64"])
    )

    tag = base64.b64decode(
        record["tag_b64"]
    )

    aad = base64.b64decode(
        record["aad_b64"]
    )

    if not ciphertext:
        raise ValueError(
            "Cannot tamper with an empty ciphertext."
        )

    # Modify one bit in the ciphertext.
    ciphertext[0] ^= 0x01

    aesgcm = AESGCM(key)

    try:

        aesgcm.decrypt(
            nonce,
            bytes(ciphertext) + tag,
            aad
        )

        return False

    except InvalidTag:

        return True


# --------------------------------------------------
# 9A. ADDITIONAL AES-GCM INTEGRITY TESTS
# --------------------------------------------------

def run_additional_integrity_tests(encrypted_records, key_registry):
    """Test AAD, tag, nonce modification, and wrong-key rejection
    against the first encrypted packet. Each test expects InvalidTag.
    """
    if not encrypted_records:
        raise ValueError("No encrypted packets available.")

    record = encrypted_records[0]
    epoch = int(record["key_epoch"])
    session_id = record["session_id"]
    key = key_registry[(epoch, session_id)]

    nonce = base64.b64decode(record["nonce_b64"], validate=True)
    ciphertext = base64.b64decode(record["ciphertext_b64"], validate=True)
    tag = base64.b64decode(record["tag_b64"], validate=True)
    aad = base64.b64decode(record["aad_b64"], validate=True)

    if len(nonce) != NONCE_BYTES:
        raise ValueError("Invalid GCM nonce length in test record.")
    if len(tag) != TAG_BYTES:
        raise ValueError("Invalid GCM authentication tag length in test record.")
    if not aad:
        raise ValueError("AAD is empty; cannot test AAD tampering.")

    def authentication_rejects(test_key, test_nonce, test_ciphertext, test_tag, test_aad):
        try:
            AESGCM(test_key).decrypt(
                test_nonce, test_ciphertext + test_tag, test_aad
            )
            return False
        except InvalidTag:
            return True

    # Test 1: Modify one bit in authenticated metadata (AAD).
    modified_aad = bytearray(aad)
    modified_aad[0] ^= 0x01
    aad_tampering_detected = authentication_rejects(
        key, nonce, ciphertext, tag, bytes(modified_aad)
    )

    # Test 2: Modify one bit in the authentication tag.
    modified_tag = bytearray(tag)
    modified_tag[0] ^= 0x01
    tag_tampering_detected = authentication_rejects(
        key, nonce, ciphertext, bytes(modified_tag), aad
    )

    # Test 3: Modify one bit in the nonce.
    modified_nonce = bytearray(nonce)
    modified_nonce[0] ^= 0x01
    nonce_modification_rejected = authentication_rejects(
        key, bytes(modified_nonce), ciphertext, tag, aad
    )

    # Test 4: Attempt decryption using a different 256-bit key.
    wrong_key = secrets.token_bytes(AES_KEY_BYTES)
    while wrong_key == key:
        wrong_key = secrets.token_bytes(AES_KEY_BYTES)
    wrong_key_rejected = authentication_rejects(
        wrong_key, nonce, ciphertext, tag, aad
    )

    return {
        "aad_tampering_detected": aad_tampering_detected,
        "tag_tampering_detected": tag_tampering_detected,
        "nonce_modification_rejected": nonce_modification_rejected,
        "wrong_key_rejected": wrong_key_rejected
    }


# --------------------------------------------------
# 10. SAVE ENCRYPTED TRAFFIC
# --------------------------------------------------

def save_encrypted_traffic(records):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not records:
        raise ValueError("No encrypted records to save.")

    with open(
        ENCRYPTED_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=records[0].keys()
        )

        writer.writeheader()
        writer.writerows(records)


# --------------------------------------------------
# 11. MAIN EXECUTION
# --------------------------------------------------

def main():

    print("\n========== AES-256-GCM RPM INTEGRATION ==========\n")

    traffic, controller = load_data()

    print("Input RPM packets:", len(traffic))

    (
        key_schedule,
        schedule_times,
        key_registry
    ) = generate_key_schedule(controller)

    print("Key epochs:", len(key_schedule))
    print("Sessions per epoch:", NUMBER_OF_SESSIONS)
    print("AES key size:", AES_KEY_BYTES * 8, "bits")

    print("\n========== KEY EPOCHS ==========")

    for event_time in schedule_times:

        event = key_schedule[event_time]

        print(
            f"Time: {event_time}s | "
            f"Epoch: {event['epoch']} | "
            f"Mode: {event['mode']} | "
            f"Source: {event['key_source']}"
        )

    (
        encrypted_records,
        encryption_time,
        plaintext_total,
        ciphertext_total,
        used_nonces
    ) = encrypt_traffic(
        traffic,
        key_schedule,
        schedule_times,
        key_registry
    )

    (
        verified_packets,
        failed_packets,
        round_trip_verified_packets,
        round_trip_failures,
        decryption_time
    ) = decrypt_and_verify(
        encrypted_records,
        key_registry,
        traffic
    )

    tamper_detected = run_tamper_test(
        encrypted_records,
        key_registry
    )

    additional_integrity_tests = run_additional_integrity_tests(
        encrypted_records,
        key_registry
    )

    all_integrity_tests_passed = (
        tamper_detected
        and all(additional_integrity_tests.values())
    )

    print("\\n========== ADDITIONAL INTEGRITY TESTS ==========")
    for test_name, result in additional_integrity_tests.items():
        print(f"{test_name}: {result}")
    print("ciphertext_tampering_detected:", tamper_detected)
    print("all_integrity_tests_passed:", all_integrity_tests_passed)

    save_encrypted_traffic(encrypted_records)

    total_nonce_bytes = (
        len(encrypted_records) * NONCE_BYTES
    )

    total_tag_bytes = (
        len(encrypted_records) * TAG_BYTES
    )

    total_crypto_bytes = (
        ciphertext_total
        + total_nonce_bytes
        + total_tag_bytes
    )

    unique_nonce_count = sum(
        len(nonces)
        for nonces in used_nonces.values()
    )

    summary = {

        "total_packets": len(traffic),

        "encrypted_packets": len(encrypted_records),

        "verified_packets": verified_packets,

        "failed_decryptions": failed_packets,

        "all_packets_verified": (
            verified_packets == len(encrypted_records)
            and failed_packets == 0
        ),

        "round_trip_verified_packets": round_trip_verified_packets,

        "round_trip_failures": round_trip_failures,

        "all_round_trip_verified": (
            round_trip_verified_packets == len(encrypted_records)
            and round_trip_failures == 0
        ),

        "aes_algorithm": "AES-256-GCM",

        "aes_key_size_bits": AES_KEY_BYTES * 8,

        "nonce_size_bytes": NONCE_BYTES,

        "authentication_tag_size_bytes": TAG_BYTES,

        "number_of_sessions": NUMBER_OF_SESSIONS,

        "number_of_key_epochs": len(key_schedule),

        "unique_nonces": unique_nonce_count,

        "plaintext_total_bytes": plaintext_total,

        "ciphertext_total_bytes": ciphertext_total,

        "nonce_total_bytes": total_nonce_bytes,

        "authentication_tag_total_bytes": total_tag_bytes,

        "total_encrypted_payload_bytes": total_crypto_bytes,

        "gcm_overhead_bytes": (
            total_nonce_bytes + total_tag_bytes
        ),

        "encryption_time_seconds": encryption_time,

        "decryption_time_seconds": decryption_time,

        "encryption_throughput_bytes_per_second": (
            plaintext_total / encryption_time
            if encryption_time > 0 else None
        ),

        "decryption_throughput_bytes_per_second": (
            plaintext_total / decryption_time
            if decryption_time > 0 else None
        ),

        "tamper_detection_success": tamper_detected,

        "additional_integrity_tests": additional_integrity_tests,

        "all_integrity_tests_passed": all_integrity_tests_passed,

        "key_generation": (
            "Random simulation placeholders; "
            "not actual QKD or ML-KEM output"
        ),

        "encrypted_output_file": str(ENCRYPTED_FILE)
    }

    with open(
        SUMMARY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            summary,
            file,
            indent=4
        )

    print("\n========== ENCRYPTION RESULTS ==========")

    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\nEncrypted traffic saved:", ENCRYPTED_FILE)
    print("Summary saved:", SUMMARY_FILE)

    if (
        summary["all_packets_verified"]
        and summary["all_round_trip_verified"]
        and all_integrity_tests_passed
    ):

        print(
            "\\nSUCCESS: All packets passed round-trip verification "
            "and all AES-GCM integrity tests passed."
        )

    else:

        print(
            "\nWARNING: One or more validation checks failed."
        )

    print("\n========================================\n")


if __name__ == "__main__":
    main()
