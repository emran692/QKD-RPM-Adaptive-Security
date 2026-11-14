# Adaptive QKD–PQC Security Framework for Remote Patient Monitoring

**Research Title:** An Adaptive QKD–PQC Security Framework for Remote Patient Monitoring Using Hybrid Anomaly Detection and Key-Pool Management

**Supervisor:** Dr. U. Hariharan
**Team IDs:** 23BAI70692, 23BAI70700
**Project Status:** Implementation and experimental validation in progress

## 1. Project Overview

This research investigates the challenge of balancing Quantum Key Distribution (QKD) secret-key generation with continuous cryptographic key demand in Remote Patient Monitoring (RPM) environments.

The project develops a system-level adaptive security framework that models RPM traffic, QKD key generation, key-pool management, and adaptive switching between QKD mode and a Post-Quantum Cryptography (PQC) fallback mode.

A hybrid anomaly-detection approach using Isolation Forest and QBER-based confirmation is also implemented to investigate whether machine-learning-assisted detection can improve adaptive security decisions under simulated channel degradation.

## 2. Research Objectives

1. Model synthetic and real-data-derived RPM traffic.
2. Simulate QKD key generation under normal and degraded channel conditions.
3. Investigate key-pool consumption, replenishment, and depletion.
4. Implement adaptive switching between QKD and PQC fallback modes.
5. Evaluate hybrid anomaly detection using Isolation Forest and QBER confirmation.
6. Integrate AES-256-GCM encryption and decryption with simulated RPM traffic and controller-generated key schedules.
7. Examine system performance, security trade-offs, and limitations.

## 3. Proposed Architecture

RPM Sensors → Edge Gateway → QKD Key Generation → Key-Pool Management → Adaptive Security Controller → QKD Mode / PQC Fallback → Healthcare Server

The framework also includes a hybrid anomaly-detection component that analyses simulated QKD channel behaviour and supports adaptive controller decisions.

QKD and PQC rely on different security assumptions. The fallback mechanism therefore represents a change in the security model rather than an equivalent replacement for QKD.

## 4. Implemented Components

| Component | Implementation |
|---|---|
| RPM traffic simulation | `rpm_simulator.py` |
| QKD key-generation simulation | `qkd_simulator.py` |
| Key-pool management | `key_pool.py` |
| Adaptive security controller | `adaptive_controller_v5.py` |
| Hybrid anomaly detection | `anomaly_detection_v5_hybrid_confirmation.py` |
| AES-GCM integration | `aes_gcm_integration_v5_roundtrip.py` |
| PhysioNet preprocessing | `process_physionet.py` |
| Real RPM traffic generation | `real_rpm_generator.py` |

These scripts are included in the repository. Their inclusion and successful syntax compilation do not, by themselves, establish that every experiment is independently reproducible.

## 5. Repository Structure

```text
QKD-RPM-GitHub/
│
├── data/
│   └── physionet_ptt/
│       ├── README.md
│       ├── csv/
│       └── processed/
│
├── docs/
│   ├── architecture.md
│   ├── experimental-plan.md
│   └── research-gap.md
│
├── results/
│
├── src/
│   ├── adaptive_controller_v5.py
│   ├── aes_gcm_integration_v5_roundtrip.py
│   ├── anomaly_detection_v5_hybrid_confirmation.py
│   ├── key_pool.py
│   ├── process_physionet.py
│   ├── qkd_simulator.py
│   ├── real_rpm_generator.py
│   └── rpm_simulator.py
│
├── tests/
├── .gitignore
└── requirements.txt
```

## 6. Software Requirements

- Python
- NumPy
- Pandas
- Matplotlib
- Scikit-learn
- Cryptography

Install the dependencies from the repository root:

```bash
pip install -r requirements.txt
```

The pinned dependency versions are listed in `requirements.txt`.

## 7. PhysioNet Dataset Setup

The real RPM traffic-generation workflow uses the Pulse Transit Time PPG Dataset.

**Dataset:** Pulse Transit Time PPG Dataset v1.1.0

- Official page: https://physionet.org/content/pulse-transit-time-ppg/1.1.0/
- DOI: https://doi.org/10.13026/jpan-6n92

Download the required source files:

- `s1_sit.csv`
- `subjects_info.csv`

Place them in:

```text
data/physionet_ptt/csv/
```

Run preprocessing from the repository root:

```bash
python src/process_physionet.py
python src/real_rpm_generator.py
```

Generated files are stored in:

```text
data/physionet_ptt/processed/
```

These include:

- `s1_sit_processed.csv`
- `s1_sit_ecg_heart_rate.csv`
- `real_rpm_traffic.csv`

The generated RPM traffic file is an input to the AES-GCM integration experiment.

Dataset files are excluded from Git. Obtain the dataset directly from PhysioNet and follow its current licensing, attribution, and citation requirements.

## 8. Experiment Execution

Run all commands from the repository root.

### 8.1 Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 8.2 Generate Synthetic RPM Traffic

```powershell
python .\src\rpm_simulator.py
```

Output:

`data/synthetic_rpm/rpm_traffic.csv`

### 8.3 Generate QKD Simulation Data

Generate the default V2 dataset for the standalone key-pool experiment:

```powershell
python .\src\qkd_simulator.py
```

Generate the V3 dataset for the adaptive controller and hybrid anomaly detection:

```powershell
python .\src\qkd_simulator.py --output results/qkd_generation_508s_v3.csv
```
**Version clarification:** Both output files are generated using the same QKD Simulator V2 implementation, simulation parameters, and random seed. The V3 filename is retained for compatibility with the adaptive controller and hybrid anomaly detection scripts. It does not represent a separate simulator version or a different QKD simulation algorithm.
Outputs:

- `results/qkd_generation_508s_v2.csv`
- `results/qkd_generation_508s_v3.csv`

### 8.4 Run Standalone Key-Pool Experiment

```powershell
python .\src\key_pool.py --rpm data/synthetic_rpm/rpm_traffic.csv --qkd results/qkd_generation_508s_v2.csv
```

Outputs:

- `results/key_pool_timeseries.csv`
- `results/key_pool_summary.csv`

### 8.5 Run Adaptive Controller

```powershell
python .\src\adaptive_controller_v5.py
```

The controller reads `results/qkd_generation_508s_v3.csv`.

Its default output prefix is `results/adaptive_508s_v5`.

### 8.6 Run Hybrid Anomaly Detection

```powershell
python .\src\anomaly_detection_v5_hybrid_confirmation.py
```

The experiment compares the original V5 controller against the V5 controller with Isolation Forest-based anomaly confirmation.

Outputs are saved in:

`results/anomaly_detection_v5_hybrid_confirmation/`

### 8.7 Prepare PhysioNet-Based RPM Traffic

Download the required PhysioNet CSV files as described in `data/physionet_ptt/README.md`.

Run:

```powershell
python .\src\process_physionet.py
python .\src\real_rpm_generator.py
```

The generated RPM traffic file is:

`data/physionet_ptt/processed/real_rpm_traffic.csv`

### 8.8 Run AES-256-GCM Integration

After generating the PhysioNet-based RPM traffic and adaptive controller output, run:

```powershell
python .\src\aes_gcm_integration_v5_roundtrip.py
```

Inputs:

- `data/physionet_ptt/processed/real_rpm_traffic.csv`
- `results/adaptive_508s_v5_timeseries.csv`

Outputs are saved in:

`results/aes_gcm/`

### 8.9 Reproducibility Notes

- Run commands from the repository root.
- Generate the required upstream CSV files before running dependent experiments.
- The standalone key-pool experiment and adaptive controller are separate experiments.
- The AES-GCM integration uses the baseline adaptive controller output, not the hybrid controller output.
- Experiment outputs are generated locally and excluded from Git.
- Runtime validation and independent reproduction of all experiments are still required before claiming complete reproducibility.

## 9. Security Model and Research Limitations

The following distinctions are important when interpreting the implementation:

- **QKD:** Key generation is simulated at the system level. No physical quantum communication hardware or experimental BB84 implementation is used.
- **PQC:** The fallback mechanism is an abstraction. Actual ML-KEM key encapsulation and exchange are not implemented.
- **Anomaly detection:** Isolation Forest is evaluated against simulated channel degradation. This is not proof of detection of real cyberattacks.
- **AES-GCM:** AES-256-GCM encryption and decryption are implemented for the integration experiment. Random placeholder keys are used; they are not actual QKD-derived or ML-KEM-derived keys.
- **RPM data:** PhysioNet-derived traffic is used for simulation. It should not be interpreted as clinical validation of the proposed framework.
- **Performance:** Experimental metrics must be reported only after execution and verification. Simulated values must be clearly identified as simulated results.

## 10. Research Integrity

This project is a system-level adaptive security framework, not a new QKD protocol.

All experimental assumptions, software versions, configurations, and limitations should be documented. Simulated results must not be presented as physical measurements or clinical outcomes.

References and dataset attribution should be verified against their original sources before publication.
