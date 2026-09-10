# G0: Misdiagnosis Density

## Measurement

Ground-truth pairs: **141** (from `ground_truth_pairs.csv`)
Pairs resolved (both records found in corpus): **141**
Pairs missing from corpus: **0**

| Metric | Count | Percentage |
|--------|-------|-----------|
| Different `PartName` | 92 | **65.2%** |
| Different `JASCCode` | 60 | 42.6% |
| Different `PartLocation` | 67 | 47.5% |

## Top-20 Component Transition Pairs (different PartName only)

| Rank | Superseded Part | Superseding Part | Support |
|------|-----------------|-----------------|---------|
|  1 | `WARNING MESSAGE` | `PROXIMITY SENSOR` | 3 |
|  2 | `INDICATOR` | `COMPENSATOR` | 2 |
|  3 | `LIGHT` | `CONNECTOR` | 2 |
|  4 | `PUMP` | `CONNECTOR` | 2 |
|  5 | `UNKNOWN` | `TRANSFER TUBE` | 2 |
|  6 | `UNKNOWN` | `A/C PACK` | 2 |
|  7 | `LAVATORY` | `TOILET` | 2 |
|  8 | `PUMP` | `PRESSURE SWITCH` | 2 |
|  9 | `WARNING MESSAGE` | `INTERRUPTER` | 1 |
| 10 | `WARNING MESSAGE` | `PUMP` | 1 |
| 11 | `HYDRAULIC SYSTEM` | `OIL FILTER` | 1 |
| 12 | `INDICATOR` | `TRANSMITTER` | 1 |
| 13 | `UNKNOWN` | `CONTROL SERVO` | 1 |
| 14 | `LIGHT` | `CIDS` | 1 |
| 15 | `FUEL SYS` | `CHECK VALVE` | 1 |
| 16 | `INDICATION SYS` | `COMPENSATOR` | 1 |
| 17 | `TRANSFER SYS` | `COMPENSATOR` | 1 |
| 18 | `LANDING GEAR` | `BYPASS VALVE` | 1 |
| 19 | `BUTTON` | `FLASHLIGHT ASSY` | 1 |
| 20 | `DRIVE ASSY` | `WIRE` | 1 |

## Distinct Component Pairs by Support Threshold

| Support ≥ | Distinct Pairs |
|-----------|---------------|
| 3  | 1 |
| 5  | 0 |
| 10 | 0 |

## Decision Rule

**Thresholds**: ≥ 30% different-part pairs AND ≥ 10 distinct component pairs at support ≥ 3.

**Observed**: 65.2% different-part pairs, 1 pairs at support ≥ 3.

**Decision**: **Skip G2** — both thresholds were not met. G3 is built without dependency edges. This finding is documented here.

*The thresholds were stated in the G0 specification before this measurement was run and have not been adjusted.*

## Confidence Threshold Provisional Status

The `MAINT_CONFIDENCE_THRESHOLD` has been set to a provisional value of `0.72` in `.env.example` and `config.py`. This threshold dictates whether a conflict is auto-accepted or routed for manual review. It is provisional pending full calibration via the T7 evaluation harness (`evaluate_conflict_detection.py`), as the optimal threshold shifts when the confidence metric is properly constrained to `[0,1]`.
