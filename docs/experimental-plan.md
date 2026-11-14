# Experimental Plan (Draft)

## Comparison
- Baseline A: QKD-only policy; explicitly define behavior when usable key material is insufficient.
- Optional Baseline B: fixed fallback policy.
- Proposed: adaptive key-pool-aware QKD/PQC switching and recovery.

## Variables
RPM packet rate/payload; QKD usable key-generation rate; pool capacity and initial depth; channel degradation severity/duration; simulated QBER; controller thresholds; fallback overhead.

## Metrics
End-to-end latency, throughput, packet delivery ratio (PDR), QBER, pool depth, depletion time, fallback activation delay, recovery time, and time spent in each mode.

## Experimental discipline
Define parameter units/ranges before running experiments; use repeatable random seeds; run multiple trials; report variability; separate simulated observations from analytical expectations; do not claim improvement before baseline comparisons.
