# Proposed System Architecture

## Components
1. RPM traffic model
2. QKD key-generation model with configurable channel conditions
3. Key pool for usable key material
4. Availability monitor
5. Adaptive switching/recovery controller
6. PQC fallback abstraction (select a specific standardized algorithm before implementation)
7. Metrics collector

## Key-pool model
`B(t + Δt) = min(B_max, max(0, B(t) + (r_key(t) - r_req(t)) × Δt))`

`B(t)` is usable pool depth, `B_max` is pool capacity, `r_key(t)` is usable key-generation rate, and `r_req(t)` is key-consumption rate. Define units consistently in implementation.

## Key availability ratio
`ψ_QKD = r_key / r_req`

- `ψ_QKD > 1`: key material may accumulate.
- `ψ_QKD = 1`: generation and consumption are balanced.
- `ψ_QKD < 1`: the pool may deplete if the condition persists.

Do not trigger switching from the ratio alone; consider pool depth, persistence, and the security policy. QBER is a disturbance indicator in the model, not definitive proof of malicious activity.
