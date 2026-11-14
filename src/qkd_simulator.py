
"""
QKD Key Generation Simulator - Version 2

System-level simulation only.
Not a physical BB84 implementation.

Version 2 introduces controlled, reproducible
variation in QBER and QKD key-generation rate.

All parameter ranges are illustrative simulation
assumptions, not physical QKD measurements.
"""

import csv
import argparse
import random

from pathlib import Path


# --------------------------------------------------
# 1. SIMULATION PARAMETERS
# --------------------------------------------------

NORMAL_KEY_RATE_MIN = 1100
NORMAL_KEY_RATE_MAX = 1300

DEGRADED_KEY_RATE_MIN = 200
DEGRADED_KEY_RATE_MAX = 300

NORMAL_QBER_MIN = 0.012
NORMAL_QBER_MAX = 0.035

DEGRADED_QBER_MIN = 0.115
DEGRADED_QBER_MAX = 0.145


# --------------------------------------------------
# 2. QKD SIMULATION
# --------------------------------------------------

def simulate_qkd(
    duration,
    degraded_start,
    degraded_end,
    seed=42
):

    if duration <= 0:
        raise ValueError("Duration must be positive.")

    if not (
        0 <= degraded_start < degraded_end <= duration
    ):
        raise ValueError("Invalid degradation interval.")

    rng = random.Random(seed)

    results = []

    for second in range(duration):

        if degraded_start <= second < degraded_end:

            channel = "DEGRADED"

            key_rate = rng.randint(
                DEGRADED_KEY_RATE_MIN,
                DEGRADED_KEY_RATE_MAX
            )

            qber = rng.uniform(
                DEGRADED_QBER_MIN,
                DEGRADED_QBER_MAX
            )

        else:

            channel = "NORMAL"

            key_rate = rng.randint(
                NORMAL_KEY_RATE_MIN,
                NORMAL_KEY_RATE_MAX
            )

            qber = rng.uniform(
                NORMAL_QBER_MIN,
                NORMAL_QBER_MAX
            )

        results.append({

            "time_seconds": second,

            "channel_status": channel,

            "qkd_key_rate_bps": key_rate,

            "qber": round(qber, 6),

            "generated_key_bits": key_rate

        })

    return results


# --------------------------------------------------
# 3. SUMMARY
# --------------------------------------------------

def calculate_summary(results):

    total_generated = sum(
        row["generated_key_bits"]
        for row in results
    )

    normal_rows = [
        row for row in results
        if row["channel_status"] == "NORMAL"
    ]

    degraded_rows = [
        row for row in results
        if row["channel_status"] == "DEGRADED"
    ]

    normal_steps = len(normal_rows)
    degraded_steps = len(degraded_rows)

    average_rate = total_generated / len(results)

    def average(rows, column):

        return sum(
            row[column] for row in rows
        ) / len(rows)

    print("\n========== QKD SIMULATION V2 SUMMARY ==========")

    print(f"Total simulation time : {len(results)} seconds")

    print(f"Normal channel        : {normal_steps} seconds")

    print(f"Degraded channel      : {degraded_steps} seconds")

    print(f"Total generated keys  : {total_generated} bits")

    print(f"Average key rate      : {average_rate:.2f} bps")

    print("\nNORMAL CHANNEL")

    print(
        f"Average QBER          : "
        f"{average(normal_rows, 'qber'):.6f}"
    )

    print(
        f"Average key rate      : "
        f"{average(normal_rows, 'qkd_key_rate_bps'):.2f} bps"
    )

    print("\nDEGRADED CHANNEL")

    print(
        f"Average QBER          : "
        f"{average(degraded_rows, 'qber'):.6f}"
    )

    print(
        f"Average key rate      : "
        f"{average(degraded_rows, 'qkd_key_rate_bps'):.2f} bps"
    )

    print("\nSIMULATION RANGES")

    print(
        f"Normal QBER           : "
        f"{NORMAL_QBER_MIN} - {NORMAL_QBER_MAX}"
    )

    print(
        f"Degraded QBER         : "
        f"{DEGRADED_QBER_MIN} - {DEGRADED_QBER_MAX}"
    )

    print("Random seed           : 42")

    print("===============================================\n")


# --------------------------------------------------
# 4. SAVE RESULTS
# --------------------------------------------------

def save_results(results, output_file):

    output = Path(output_file)

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output.open(
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

    print(f"QKD results saved to: {output}")


# --------------------------------------------------
# 5. MAIN
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="System-level QKD simulation V2"
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=508
    )

    parser.add_argument(
        "--degraded-start",
        type=int,
        default=220
    )

    parser.add_argument(
        "--degraded-end",
        type=int,
        default=280
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42
    )

    parser.add_argument(
        "--output",
        default="results/qkd_generation_508s_v2.csv"
    )

    args = parser.parse_args()

    results = simulate_qkd(
        duration=args.duration,
        degraded_start=args.degraded_start,
        degraded_end=args.degraded_end,
        seed=args.seed
    )

    calculate_summary(results)

    save_results(
        results,
        args.output
    )


if __name__ == "__main__":
    main()
