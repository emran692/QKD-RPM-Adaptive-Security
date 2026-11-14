
"""
QKD Key Pool Management
Connects RPM sensor sessions with QKD-generated key material.

Model:
- 5 independent RPM sensor sessions
- AES-256 session keys
- Rekey interval: 60 seconds
- Initial key reserve: 5 x 256 bits
"""

import csv
import argparse
from pathlib import Path

SESSION_KEY_BITS = 256
REKEY_INTERVAL_SECONDS = 60
INITIAL_POOL_BITS = 5 * SESSION_KEY_BITS
MAX_POOL_BITS = 30_000


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def simulate_key_pool(rpm_file, qkd_file):

    rpm_data = load_csv(rpm_file)
    qkd_data = load_csv(qkd_file)

    # Count independent sensor sessions from RPM traffic.
    sensors = sorted(set(row["sensor"] for row in rpm_data))
    number_of_sessions = len(sensors)

    key_demand_per_event = number_of_sessions * SESSION_KEY_BITS

    # Initial reserve contains the first set of session keys.
    pool = INITIAL_POOL_BITS

    results = []
    total_consumed = 0
    total_discarded = 0
    successful_rekeys = 0
    failed_rekeys = 0
    minimum_pool = pool

    for row in qkd_data:

        second = int(row["time_seconds"])
        generated = int(row["generated_key_bits"])

        # Allocate session keys at startup and every rekey interval.
        rekey_event = (second % REKEY_INTERVAL_SECONDS == 0)

        consumed = 0
        shortage = 0
        discarded = 0

        if rekey_event:

            if pool >= key_demand_per_event:

                pool -= key_demand_per_event
                consumed = key_demand_per_event
                total_consumed += consumed
                successful_rekeys += 1

            else:

                shortage = key_demand_per_event - pool
                failed_rekeys += 1

        # Add newly generated QKD key material.
        available_space = MAX_POOL_BITS - pool
        accepted = min(generated, available_space)

        discarded = generated - accepted
        pool += accepted

        total_discarded += discarded
        minimum_pool = min(minimum_pool, pool)

        results.append({
            "time_seconds": second,
            "channel_status": row["channel_status"],
            "qber": row["qber"],
            "generated_key_bits": generated,
            "rekey_event": rekey_event,
            "key_consumed_bits": consumed,
            "key_shortage_bits": shortage,
            "discarded_key_bits": discarded,
            "key_pool_bits": pool
        })

    summary = {
        "number_of_sensor_sessions": number_of_sessions,
        "session_key_size_bits": SESSION_KEY_BITS,
        "rekey_interval_seconds": REKEY_INTERVAL_SECONDS,
        "key_demand_per_rekey_bits": key_demand_per_event,
        "successful_rekeys": successful_rekeys,
        "failed_rekeys": failed_rekeys,
        "total_key_consumed_bits": total_consumed,
        "total_key_discarded_bits": total_discarded,
        "minimum_pool_bits": minimum_pool,
        "final_pool_bits": pool
    }

    return results, summary


def save_results(results, summary):

    output = Path("results")
    output.mkdir(exist_ok=True)

    with open(
        output / "key_pool_timeseries.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=results[0].keys()
        )

        writer.writeheader()
        writer.writerows(results)

    with open(
        output / "key_pool_summary.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=summary.keys()
        )

        writer.writeheader()
        writer.writerow(summary)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--rpm",
        default="data/synthetic_rpm/rpm_traffic.csv"
    )

    parser.add_argument(
        "--qkd",
        default="results/qkd_generation.csv"
    )

    args = parser.parse_args()

    results, summary = simulate_key_pool(
        args.rpm,
        args.qkd
    )

    print("\n========== KEY POOL SUMMARY ==========")

    for key, value in summary.items():
        print(f"{key}: {value}")

    print("======================================\n")

    save_results(results, summary)

    print("Key pool time series saved.")
    print("Key pool summary saved.")


if __name__ == "__main__":
    main()
