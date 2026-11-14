# PhysioNet Dataset Setup

## Dataset

Pulse Transit Time PPG Dataset (v1.1.0)

- Official page: https://physionet.org/content/pulse-transit-time-ppg/1.1.0/
- DOI: https://doi.org/10.13026/jpan-6n92

Check the official PhysioNet page for license and citation requirements.

## Required Files

Download these files from the official dataset:

1. s1_sit.csv
2. subjects_info.csv

Place them inside:

- csv/s1_sit.csv
- csv/subjects_info.csv

## Preprocessing

Run from the repository root:

python .\src\process_physionet.py

python .\src\real_rpm_generator.py

## Generated Files

- processed/s1_sit_processed.csv
- processed/s1_sit_ecg_heart_rate.csv
- processed/real_rpm_traffic.csv

The final file is used by the AES-GCM integration experiment.

## Data Handling

Dataset CSV files are excluded from this Git repository.

Download the data directly from PhysioNet and follow its attribution and licensing requirements.