# Research Gap and Motivation

## Working gap statement
Investigate whether QKD secret-key generation can keep pace with continuous cryptographic key demand in high-frequency RPM, particularly when channel degradation or disturbance reduces key generation.

## System-level hypothesis
If key consumption exceeds usable QKD key generation for long enough, the available key pool may shrink and become insufficient. A controller considering both pool depth and sustained key availability may manage transitions more effectively than a fixed QKD-only policy. This is a hypothesis to test.

## Questions
1. Under what traffic/channel conditions does the pool deplete?
2. How do pool capacity and key-generation rate affect depletion time?
3. What switching threshold balances continuity and security requirements?
4. What latency/throughput overhead does adaptive control introduce?
5. Does ML anomaly detection improve decisions over a rule-based controller?

## Scope notes
- This is a system-level design, not a new QKD protocol.
- Increased QBER may indicate noise or disturbance; it is not definitive proof of an attacker.
- A short period with generation below demand need not trigger immediate fallback if the pool remains sufficient.
- PQC fallback has a different security model from QKD.
