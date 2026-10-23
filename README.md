# Quantum Key Distribution for Remote Patient Monitoring Systems

**Status:** In Progress  
**Supervisor:** Dr. U. Hariharan  
**Team IDs:** 23BAI70692, 23BAI70700

## Overview
This project investigates the mismatch between Quantum Key Distribution (QKD) secret-key generation and continuous cryptographic key demand in high-frequency Remote Patient Monitoring (RPM).

The proposed system models a QKD key pool at an edge gateway and studies an adaptive controller that selects between QKD-derived key material and a post-quantum cryptography (PQC) fallback when key availability becomes insufficient.

**ML status:** Isolation Forest is a candidate anomaly-detection model; it is not yet implemented or evaluated.

## Research gap
We will investigate whether QKD key generation can keep pace with continuous RPM key demand, especially when channel degradation or disturbance reduces or interrupts key generation. This is a hypothesis to validate, not a claim that all prior work lacks a solution.

## Planned objectives
1. Model RPM telemetry and key demand.
2. Simulate QKD key generation under changing channel conditions.
3. Track key-pool depth and depletion time.
4. Design adaptive QKD/PQC switching and recovery.
5. Evaluate latency, throughput, PDR, QBER, pool depletion, switching, and recovery.
6. Test whether ML-based anomaly detection adds value over a rule-based controller.

## Proposed architecture
RPM traffic → Edge gateway → QKD key pool → Availability monitor → Adaptive controller → QKD mode / PQC fallback → Healthcare server

Switching to PQC changes the security model: QKD and PQC rely on different security assumptions. This trade-off will be documented.

## Repository status
This is a documentation-first starter scaffold. It does not yet contain a validated implementation or experimental results. The project is a system-level adaptive design, not a new QKD protocol.

## Structure
- `docs/` — research gap, architecture, experimental plan
- `src/` — future implementation
- `tests/` — future unit tests
- `results/` — future experiment outputs

## Research integrity
Do not report expected values as measured results. Label simulated results clearly, record assumptions and software versions, verify references against original papers, and never upload credentials, private data, or confidential material.
