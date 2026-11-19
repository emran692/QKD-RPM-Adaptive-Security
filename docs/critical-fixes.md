# Critical Fixes â€” Local Review Patch

This document records the limited critical-fix patch applied to the local project snapshot. It does not claim physical QKD, a real ML-KEM exchange, or clinical validation.

## 1. QKD pool replenishment during PQC fallback

Both `src/adaptive_controller_v5.py` and the integrated controller in `src/anomaly_detection_v5_hybrid_confirmation.py` now permit background pool replenishment while the operating mode remains `PQC_FALLBACK`, but only when **both** conditions hold:

- `channel_status` is `NORMAL` (case-insensitive); and
- the current QBER is at or below `QBER_RECOVERY_THRESHOLD`.

These bits are added to the pool but are not consumed for QKD rekeying until the controller satisfies its existing recovery persistence and pool-depth checks and switches back to QKD. Bits generated during a degraded/unhealthy channel remain discarded. The accounting summary reports `background_qkd_bits_accepted_during_fallback` separately.

This is a simulation policy for background key-pool replenishment. A deployed QKD system would need protocol-level authenticated parameter estimation, error correction, privacy amplification, finite-key security analysis, and a trusted implementation before accepting key material.

## 2. Explicit successful-rekey state

The baseline and hybrid controllers now emit `rekey_success` for every rekey row:

- `1`: a simulated QKD-pool or simulated PQC rekey succeeded and the epoch advanced;
- `0`: an attempt occurred but no key was established (for example, QKD pool shortage).

The AES key-schedule builder filters by this explicit flag. For older controller CSVs without the field, it uses a compatibility filter requiring a recognized simulated key source and a positive epoch. Failed `key_source=NONE` attempts are skipped instead of being treated as key epochs.

AES-GCM still uses random simulation placeholder keys. This patch does not add real QKD or ML-KEM key establishment.

## 3. Isolation Forest holdout evaluation

`evaluate_anomaly_model()` now excludes the baseline training interval `[TRAIN_START, TRAIN_END_EXCLUSIVE)` from reported classification metrics. Metrics are calculated only on observations outside that training interval. The output records the number of excluded training samples and the evaluation time bounds.

The synthetic ground-truth degradation interval remains `[DEGRADED_START, DEGRADED_END_EXCLUSIVE)`. These labels describe the controlled simulator scenario, not independently labelled cyberattacks or clinical events.

## 4. Regression tests

Run from the repository root:

```bash
python -m unittest discover -s tests -v
```

The tests cover:

- recovery from low pool when the simulated channel is healthy;
- rejection of background bits during degraded channel conditions;
- failed QKD rekey explicitly marked unsuccessful;
- equivalent replenishment/recovery behavior in the V5+IF controller;
- skipping failed rekey attempts in both new and legacy controller CSV formats;
- exclusion of training observations from Isolation Forest metrics; and
- rejection of an empty holdout set.

## Scope and reproducibility notes

Only the three critical source modules, a new regression-test module, and this documentation/report were added or changed by this patch. The original uploaded project snapshot was retained as the starting point. Existing local modifications present in that uploaded snapshot were not reverted. No remote repository operation was performed.
