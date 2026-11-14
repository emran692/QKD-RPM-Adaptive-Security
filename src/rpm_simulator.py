
"""
RPM Traffic Generator
Project: QKD for Remote Patient Monitoring Systems

Five simulated sensors:
1. ECG
2. Heart Rate
3. SpO2
4. Body Temperature
5. Blood Pressure

All data is synthetic. No real patient data is used.
"""

import csv
import argparse
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Sensor:
    name: str
    interval_seconds: int
    packet_size_bytes: int


SENSORS = [
    Sensor("ECG", 1, 500),
    Sensor("Heart_Rate", 1, 2),
    Sensor("SpO2", 1, 1),
    Sensor("Temperature", 10, 2),
    Sensor("Blood_Pressure", 60, 4),
]


def generate_rpm_traffic(duration_seconds=180):

    packets = []

    for second in range(duration_seconds):

        for sensor in SENSORS:

            if second % sensor.interval_seconds == 0:

                packets.append({
                    "time_seconds": second,
                    "sensor": sensor.name,
                    "packet_size_bytes": sensor.packet_size_bytes,
                    "packet_size_bits": sensor.packet_size_bytes * 8
                })

    return packets


def calculate_statistics(packets, duration_seconds):

    total_packets = len(packets)

    total_bytes = sum(
        packet["packet_size_bytes"] for packet in packets
    )

    total_bits = total_bytes * 8

    data_rate_bps = total_bits / duration_seconds

    print("\n========== RPM TRAFFIC SUMMARY ==========")

    print(f"Simulation duration : {duration_seconds} seconds")
    print(f"Total packets       : {total_packets}")
    print(f"Total data          : {total_bytes} bytes")
    print(f"Total data          : {total_bits} bits")
    print(f"Average data rate   : {data_rate_bps:.2f} bps")

    print("\nSensor-wise packet count:")

    for sensor in SENSORS:

        count = sum(
            1 for packet in packets
            if packet["sensor"] == sensor.name
        )

        print(f"{sensor.name:18}: {count}")

    print("=========================================\n")


def save_to_csv(packets, output_file):

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:

        fieldnames = [
            "time_seconds",
            "sensor",
            "packet_size_bytes",
            "packet_size_bits"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(packets)

    print(f"RPM traffic saved to: {output_path}")


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--duration",
        type=int,
        default=180
    )

    parser.add_argument(
        "--output",
        default="data/synthetic_rpm/rpm_traffic.csv"
    )

    args = parser.parse_args()

    if args.duration <= 0:
        raise ValueError("Duration must be positive.")

    packets = generate_rpm_traffic(args.duration)

    calculate_statistics(packets, args.duration)

    save_to_csv(packets, args.output)


if __name__ == "__main__":
    main()
