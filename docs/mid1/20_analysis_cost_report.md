# Conflict-analysis cost and quality report — 2026-10-17

Scope: measurement only. No production candidate weight, threshold, routing,
classifier, or persistence behavior was changed. No full analysis was run and
no shared-staging write was made.

## Executive result

The current full-corpus job is expensive because 1,835 of 2,079 records enter
the model path, the engine classifies one top-ranked pair per such record, and
each classification makes five self-consistency requests. A cold run therefore
projects to **9,175 requests**. The configured free-tier model allows 1,000
requests/day, so requests alone require at least **10 quota days**. Token days
cannot be projected honestly from the current cache because it stores neither
usage nor individual votes, and the attempted fresh-call measurement was not
authorized by the execution service after its own usage limit was reached.

## Reproducibility and candidate-rule reconciliation

Measured command (in-memory graph, real local corpus, no model calls):

```text
python scripts/measure_analysis_cost.py \
  --corpus <local>/backend/data/processed/sdr_poc_corpus.csv \
  --ground-truth <local>/backend/data/processed/ground_truth_pairs.csv
```

The current rule in `find_candidate_pairs` searches earlier records on the
same aircraft and awards positive integer weight for exact part name, exact
JASC, exact location, or being within 30 days. Any positive score is a
candidate, sorted by score/date/ID and capped at 25. `process_record` sends
only candidate 1 to the classifier, not all candidates.

The current result is:

```json
{
  "records": 2079,
  "records_with_candidates": 1835,
  "raw_positive_score_pairs": 32457,
  "pairs_after_25_cap": 19119,
  "pairs_sent_per_model_record": 1,
  "self_consistency_requests_per_sent_pair": 5
}
```

`docs/evaluation_results.md` says 1,617 records had no candidate, yet its
current generator `scripts/evaluate_conflict_detection.py` does not calculate
that number. Git history shows the harness began in commit `56eccb1`, gained
resume/balancing behavior, temporarily allowed stub inference in `8520662`,
and was replaced in `ffc0659` by a report generator over saved CSVs. The
present script writes 121 detected, 117 auto-resolved, 4 review, 1,958
remaining, and 1,617 no-candidate as literal prose. It calculates only metrics
from `gt_results.csv` and `neg_results.csv`.

Consequently, these documented full-corpus numbers are **not reproducible
today** from the script or current code: 1,617 no-candidate, 121 detected, 117
auto-resolved, 4 review, and 1,958 remaining. The saved 141-positive/209-negative
CSV calculation does reproduce archived threshold metrics, including recall
0.660 and F1 0.762, but that is a pair-evaluation artifact from
`openai/gpt-oss-120b`, not a current full-corpus run.

## Candidate histogram

Counts are uncapped positive-score candidates; the separate total above shows
the effect of the 25 cap.

| Candidates for a record | Records |
| ---: | ---: |
| 0 | 244 |
| 1 | 261 |
| 2 | 209 |
| 3–5 | 372 |
| 6+ | 993 |

There are 32,457 raw pairs and 19,119 after the per-record cap, but only 1,835
top-1 pairs go to the LLM. Five passes make that 9,175 cold-cache requests.

## Classification cost and provider limits

The local cache has 63 final majority results. It has no prompt-token,
completion-token, total-token, per-pass vote, or model-response fields. Thus it
cannot provide token averages or vote agreement. A bounded script,
`scripts/measure_groq_usage.py`, was prepared with a hard maximum of 10 calls.
Its execution request was rejected before Python started because the Codex
execution service had reached its own usage limit. **Fresh calls completed: 0;
token projection: NOT RUN / UNVERIFIED.** This was not a Groq response and no
Groq quota was consumed by that attempt.

Only `qwen/qwen3.8-27b` is configured locally; there is no fallback key/model
configured. On 2026-10-17, Groq's official free-plan table lists 30 RPM, 1,000
RPD, 8,000 TPM, and 200,000 TPD for that model:
https://console.groq.com/docs/rate-limits. Groq notes that account limits can
have exceptions and the console is the exact organization-level source.

| Model | RPM | RPD | TPM | TPD | Projected request-days | Projected token-days |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `qwen/qwen3.8-27b` | 30 | 1,000 | 8,000 | 200,000 | ceil(9,175/1,000) = **10** | NOT RUN / UNVERIFIED |

The previous partial run stopped on a provider 429 saying TPD 200,000, used
199,716, requested 424. That is evidence of the account-wide limit, not a clean
per-classification token sample, because earlier account activity and cache
hits were mixed into the run.

## Quality of the 103-record partial run

The 63 cached model decisions plus 40 no-candidate fast paths reproduce the
previous chronological partial run without network access:

```json
{
  "records": 103,
  "labels": {
    "contradicts": 1,
    "no_candidates": 40,
    "no_conflict": 15,
    "scope_disjoint": 27,
    "supersedes": 20
  },
  "scores": {
    "0.0": 40,
    "0.15": 3,
    "0.3": 26,
    "0.5": 18,
    "0.65": 5,
    "0.7000000000000001": 8,
    "0.8": 3
  },
  "distinct_score_values": 7,
  "largest_bin_share": "40/103 = 38.8%",
  "analysis_state": {"scored": 102, "needs_review": 1},
  "supersedes_edges": 20
}
```

Vote-agreement distribution is **unavailable**, not zero: the cache stores only
the majority label/rationale. The 20 corrections are a partial, early-date
slice and are not a corpus quality estimate.

### Ten deterministic random SUPERSEDES pairs

Seed: `20261017`. Text is pasted as stored so a reviewer can judge the model.

1. **AALA202501093468 → AALA202501063468**

| Side | Date | Part | JASC | Text |
| --- | --- | --- | --- | --- |
| Newer | 2025-01-05 | MODULE | 3350 | AIRCRAFT WAS NOT GROUNDED: DURING ACCOMPLISHMENT OF W/C 08T20033001 FOUND RIGHT OVERWING ESCAPE ROUND ILLUMINATION LIGHT (L548) INOPERATIVE. REMOVE AND REPLACED LIGHT MODULE. OPERTIONAL CHECK GOOD. PER AMM 25-25-11. |
| Older | 2025-01-05 | LIGHT | 3350 | AIRCRAFT WAS NOT GROUNDED: DURING ACCOMPLISHMENT OF W/C 08T20033001 FOUND RIGHT OVERWING ESCAPE GROUND ILLUMINATION LIGHT (L548) INOPERATIVE. (OPEN). |

2. **AALA202501074549 → AALA202501034549**

| Side | Date | Part | JASC | Text |
| --- | --- | --- | --- | --- |
| Newer | 2025-01-02 | PUMP | 2822 | AIRCRAFT WAS GROUNDED: AN EMERGENCY WAS NOT DECLARED DUE TO: DURING CRUISE BOTH OF NUMBER 2 ENGINE AFT FUEL PUMP LOW PRESSURE LIGHT ILLUMINATED AND STAYED ON; AIRCRAFT AIR INTERRUPTED BACK TO AND LANDED SAFELY AT MIA. **SUPPLEMENTAL REPORT FOR (AALA202501034549): ACCOMPLISHED FUEL QUANTITY CHECKS WITH FUELSTICKS, PER AIRCRAFT 737-800 FUELING MANUAL 12-11-02. CONFIRMED CORRECT QUANTITY. SUMPED NUMBER 2 FUEL TANK, PER AMM 12-11-00. NO WATER CONTANIMINANTS FOUND. TRANSFERED FUEL, PER AMM 28-26-00-201-650-802. FOUND NUMBER 2 FUEL TANK AFT FUEL BOOST PUMP LOSING PRESSURE. REMOVED AND REPLACED NUMBER 2 AFT BOOST PUMP, PER AMM 28-22-41 REF TSI 0106154**(CLOSED). |
| Older | 2025-01-02 | PUMP | 7314 | AIRCRAFT WAS GROUNDED: AN EMERGENCY WAS NOT DECLARED DUE TO: DURING CRUISE BOTH OF NUMBER 2 ENGINE AFT FUEL PUMP LOW PRESSURE LIGHT ILLUMINATED AND STAYED ON; AIRCRAFT AIR INTERRUPTED BACK TO AND LANDED SAFELY AT MIA. **SUPPLEMENTAL REPORT WILL BE SUBMITTED**(OPEN). |

3. **AALA202501181933 → AALA202501151933**

| Side | Date | Part | JASC | Text |
| --- | --- | --- | --- | --- |
| Newer | 2025-01-13 | CIDS | 2300 | AIRCRAFT WAS NOT GROUNDED: FLIGHT DIVERTED TO MEM, CHANGED FROM MCI ITS INTENDED DESTINATIOIN INTERCOM SYSTEM (ALL HAND SETS) INOPERATIVE, EMERGENCY CALL ALARMON AND EMERGENCY CALL LIGHT ILLUMINATING CONTINUOUSLY; UNABLE TNO RESET. EMERGENCY LIGHTS ILLUMINATED IN THE CABIN DURING THESE FAULTS. **SUPPLEMENTAL REPORT FOR AALA202501151933 WILL BE SUBMITTED.** (CLOSED) MAINTENANCE RE-ACTIVATED CIDS #1 DIRECTOR IAW AMM 23-73-00. PERFORMED BITE TEST OF CIDS IAW AMM 23-73-00. NO FAULTS NOTED. REMOVED &AMP; REPLACED #1 CIDS DIRECTOR IAW AMM 23-73-34. |
| Older | 2025-01-13 | LIGHT | 2340 | AIRCRAFT WAS NOT GROUNDED: FLIGHT DIVERTED TO MEM, CHANGED FROM MCI ITS INTENDED DESTINATIOIN INTERCOM SYSTEM (ALL HAND SETS) INOPERATIVE, EMERGENCY CALL ALARM ON AND EMERGENCY CALL LIGHT ILLUMINATING CONTINUOUSLY; UNABLE TNO RESET. EMERGENCY LIGHTS ILLUMINATED IN THE CABIN DURING THESE FAULTS. (OPEN) |

4. **AALA202501159236 → AALA202501137877**

| Side | Date | Part | JASC | Text |
| --- | --- | --- | --- | --- |
| Newer | 2025-01-12 | COMPENSATOR | 2840 | AIRCRAFT WAS GROUNDED: CENTER FUEL TANK WILL NOT BURN BELOW 0.11 LBS, TRIED CYCLING LEFT AND RIGHT FUEL PUMPS ON AND OFF, QUANTITY INCREASED TO 0.21 AND WOULD NOT BURN DOWN. DURING TROUBLESHOOTING, TRANSFERRED 5,000 LBS FUEL TO CENTER TANK. ATEMPTED TO TRANSFER 5,000 LBS OF FUEL FROM CENTER TANK TO LEFT AND RIGHT WINGS, AND CENTER TANK STOPS TRANSFERRING 920LBS OR .92 PN LOWER EICAS DISPLAY. CONFIRMED FUEL QUANTITY FOR CENTER TANK INACCURATE, PER AMM 28-41-00. **SUPPLEMENTAL REPORT FOR (AALA202501137877): REMOVED AND REPLACED TANK COMPENSATOR, TANK NUMBER 4 (AALA202501137877) AND 5 (AALA202501159236). PER AMM 28-41-21-401. BITE CHECKS GOOD**(CLOSED). |
| Older | 2025-01-12 | TRANSFER SYS | 2820 | AIRCRAFT WAS GROUNDED: CENTER FUEL TANK WILL NOT BURN BELOW 0.11 LBS, TRIED CYCLING LEFT AND RIGHT FUEL PUMPS ON AND OFF, QUANTITY INCREASED TO 0.21 AND WOULD NOT BURN DOWN. DURING TROUBLESHOOTING, TRANSFERRED 5,000 LBS FUEL TO CENTER TANK. ATEMPTED TO TRANSFER 5,000 LBS OF FUEL FROM CENTER TANK TO LEFT AND RIGHT WINGS, AND CENTER TANK STOPS TRANSFERRING 920LBS OR .92 PN LOWER EICAS DISPLAY. CONFIRMED FUEL QTY FOR CENTER TANK INACCURATE, PER AMM 28-41-00. **SUPPLEMENTAL REPORT WILL BE SUBMITTED**(OPEN). |

5. **AALA202501132199 → AALA202501088435**

| Side | Date | Part | JASC | Text |
| --- | --- | --- | --- | --- |
| Newer | 2025-01-07 | PUMP | 2822 | AIRCRAFT WAS NOT GROUNDED: LEFT CENTER TANK FUEL BOOST PUMP REMAINS ILLUMINATED AFTER SELECTED ON. THIS IS A REPEAT ITEM, ORGINAL FIX DID NOT CORRECT ISSUE. **SUPPLEMENTAL REPORT FOR (AALA202501088435): REPLACED LEFT HAND CENTER PUMP ((AALA202501132199)) AND RAM (UFI)-UNIVERSAL FAULT INTERRUPTER ((AALA202501088435)), PER AMM 28-22-99. SATISFACTORY OPERATION TEST PERFORMED. LEFT HAND CENTER PUMP OPERTIONAL CHECK GOOD. |
| Older | 2025-01-07 | WARNING MESSAGE | 2822 | AIRCRAFT WAS NOT GROUNDED: LEFT CENTER TANK FUEL BOOST PUMP REMAINS ILLUMINATED AFTER SELECTED ON. THIS IS A REPEAT ITEM, ORGINAL FIX DID NOT CORRECT ISSUE. **SUPPLEMENTAL REPORT WILL BE SUBMITTED**(OPEN). |

6. **AALA202501240287 → AALA202501160287**

| Side | Date | Part | JASC | Text |
| --- | --- | --- | --- | --- |
| Newer | 2025-01-15 | TRANSMITTER | 7320 | AIRCRAFT WAS NOT GROUNDED: NUMBER 2 ENGINE FUEL FLOW INDICATOR STOPPED WORKING SHORTLY AFTER TAKEOFF. **SUPPLEMENTAL REPORT FOR (AALA202501160287): PERFORMED TROUBLESHOOTING. PER FIM 73-31-00-810-801-F00 FOUND NO FAULTS. CLEANED AND SECURED FUEL TRANSMITTERS CANNON PLUG. OPERTIONAL CHECK GOOD**(CLOSED). |
| Older | 2025-01-15 | INDICATOR | 3120 | AIRCRAFT WAS NOT GROUNDED: NUMBER 2 ENGINE FUEL FLOW INDICATOR STOPPED WORKING SHORTLY AFTER TAKEOFF. **SUPPLEMENTAL REPORT WILL BE SUBMITTED**(OPEN). |

7. **AALA202501247485 → AALA202501130507**

| Side | Date | Part | JASC | Text |
| --- | --- | --- | --- | --- |
| Newer | 2025-01-12 | PUMP | 2913 | AIRCRAFT WAS GROUNDED: AN EMERGENCY WAS DECLARED DUE TO: FOLLOWING THE PREVIOUS WRITE UP REGARDING THE LOSS OF HYDRAULIC SYSTEM-B (AALA202501136707), AN ENGINE NUMBER 2 OIL FILTER BYPASS MESSAGE ILLUMINATED. AFTER RUNNING THIS ASSOCIATED QRH PROCEDURE FOLLOWING DISCONNECTING THE AUTO THROTTLE ONCE ENGINE 2 WAS CONFIRMED AND IDLED, THE ASSOCIATED OIL FILTER BYPASS LIGHT REMAINED ILLUMINATED. THE ENGINE NUMBER 2 WAS THEN SHUT DOWN PER QRH INSTRUCTION; AIRCRAFT DIVERTED TO AND LANDED SAFELY AT SLC. PERFORMED 3 OIL FLUSHES (AALA202501130507), PER AMM 12-13-11-100-801. CHANGED OIL CARTRIDGE FILTER (AALA202501136707), PER AMM 79-21-07-400-801-G00. REMOVE AND REPLACED EDP- ENGINE DRIVEN PUMP (AALA202501247485), PER AMM 29-11-11-400-801. |
| Older | 2025-01-12 | HYDRAULIC SYSTEM | 2910 | AIRCRAFT WAS GROUNDED: AN EMERGENCY WAS DECLARED DUE TO: FOLLOWING THE PREVIOUS WRITE UP REGARDING THE LOSS OF HYDRAULIC SYSTEM-B (AALA202501136707), AN ENGINE NUMBER 2 OIL FILTER BYPASS MESSAGE ILLUMINATED. AFTER RUNNING THIS ASSOCIATED QRH PROCEDURE FOLLOWING DISCONNECTING THE AUTO THROTTLE ONCE ENGINE 2 WAS CONFIRMED AND IDLED, THE ASSOCIATED OIL FILTER BYPASS LIGHT REMAINED ILLUMINATED. THE ENGINE NUMBER 2 WAS THEN SHUT DOWN PER QRH INSTRUCTION; AIRCRAFT DIVERTED TO AND LANDED SAFELY AT SLC. **SUPPLEMENTAL REPORT WILL BE SUBMITTED**(OPEN). |

8. **AALA202501094835 → AALA202501084835**

| Side | Date | Part | JASC | Text |
| --- | --- | --- | --- | --- |
| Newer | 2025-01-07 | UNKNOWN | 2120 | AIRCRAFT WAS GROUNDED: WHILE DESCENDING THE APU WAS STARTED AND A STRONG BURNING ODOR WAS DETECTED. IT SMELT VERY SIMILARTO BURNING PAPER. UPON NOTICING THE SMELL THE BLEED CONFIGURATION WAS IMMEDIATELY REVERTED TO ITS PREVIOUS SETTINGS AND THE APU WAS SHUT DOWN. THIS ALMOST IMMEDIATELY CLEARED THE SMELL. THE CABIN CREW ALSO NOTICED THE SMELL AND IT'S CLEARING. NO ABNORMAL INDICATIONS BESIDES THE ODOR OCCURRED DURING THIS EVENT. INSPECTED APU, COMPARTMENT AND ANY RELATED COMPONENTS FOR DISCREPANCIES AND CONTAMINATION. FOUND NO ABNORMALITIES OR CONTAMINATI ON. RAN APU AND PACKS FOR 30 MINUTES AT DIFFERENT SETTINGS, PER JC 08L00021001. NO ODOR EVIDENT THROUGHOUT CABIN COMPARTMENT OR FLIGHT DECK. |
| Older | 2025-01-07 | APU | 4950 | AIRCRAFT WAS GROUNDED: WHILE DESCENDING THE APU WAS STARTED AND A STRONG BURNING ODOR WAS DETECTED. IT SMELT VERY SIMILARTO BURNING PAPER. UPON NOTICING THE SMELL THE BLEED CONFIGURATION WAS IMMEDIATELY REVERTED TO ITS PREVIOUS SETTINGS AND THE APU WAS SHUT DOWN. THIS ALMOST IMMEDIATELY CLEARED THE SMELL. THE CABIN CREW ALSO NOTICED THE SMELL AND IT'S CLEARING. NO ABNORMAL INDICATIONS BESIDES THE ODOR OCCURRED DURING THIS EVENT. **SUPPLEMENTAL REPORT WILL BE SUBMITTED**(OPEN). |

9. **AALA202501186333 → AALA202501180173**

| Side | Date | Part | JASC | Text |
| --- | --- | --- | --- | --- |
| Newer | 2025-01-10 | CONTROL SERVO | 2730 | AIRCRAFT WAS GROUNDED: AN EMERGENCY WAS DECLARED AND THE AIRCRAFT RETURNED TO CLT DUE TO THE FLIGHT CREW REPORTING THAT AT FL 280 SPEED 310 STARTED GETTING SEVERE VIBRATION FROM TAIL SECTION OF AIRCRAFT. FLIGHT ATTENDANTS REPORTED FROM ROW 15 TO REAR OF AIRCRAFT VIBRATION GOT WORSE AS YOU WALKED TO REAR OF AIRCRAFT. FLIGHT CREW RAN QRH PROCEDURE FOR ABNORMAL VIBRATION. SLOWED TO 280 KTS AND IT SUBSIDED. THE AIRCRAFT LANDED SAFELY AT CLT AND TAXIED TO THE GATE UNDER ITS OWN POWER. **SUPPLEMENTAL REPORT FOR AALA202501136333: MAINTENANCE REPLACED THE LEFT HAND GREEN HYDRAULIC SYSTEM ELEVATOR SERVO CONTROL PER AMM 27-34-51 DUE TO EXCESSIVE PLAY. MAINTENANCE ALSO REPLACED ALL THE HINGE ARM END FITTINGS ON THE LEFT-HAND ELEVATOR (AALA202501188527, AALA202501182131, AALA202501182636, AALA202501180657, AALA202501183050, AALA202501184290) AND THE RIGHT-HAND ELEVATOR (AALA202501188151, AALA202501180198, AALA202501181587, AALA202501188171, AALA202501185876, AALA202501180173) PER AMM 55-16-42 DUE TO EXCESSIVE PLAY. A SATISFACTORY OPERATIONAL CHECK WAS ACCOMPLISHED. ** (CLOSED) |
| Older | 2025-01-10 | HINGE FITTING | 5520 | AIRCRAFT WAS GROUNDED: AN EMERGENCY WAS DECLARED AND THE AIRCRAFT RETURNED TO CLT DUE TO THE FLIGHT CREW REPORTING THAT AT FL 280 SPEED 310 STARTED GETTING SEVERE VIBRATION FROM TAIL SECTION OF AIRCRAFT. FLIGHT ATTENDANTS REPORTED FROM ROW 15 TO REAR OF AIRCRAFT VIBRATION GOT WORSE AS YOU WALKED TO REAR OF AIRCRAFT. FLIGHT CREW RAN QRH PROCEDURE FOR ABNORMAL VIBRATION. SLOWED TO 280 KTS AND IT SUBSIDED. THE AIRCRAFT LANDED SAFELY AT CLT AND TAXIED TO THE GATE UNDER ITS OWN POWER. **ORIGINAL REPORT WAS AALA202501136333** MAINTENANCE REPLACED THE LEFT HAND GREEN HYDRAULIC SYSTEM ELEVATOR SERVO CONTROL PER AMM 27-34-51 DUE TO EXCESSIVE PLAY. MAINTENANCE ALSO REPLACED ALL THE HINGE ARM END FITTINGS ON THE LEFT-HAND ELEVATOR (AALA202501188527, AALA202501182131, AALA202501182636, AALA202501180657, AALA202501183050, AALA202501184290) AND THE RIGHT-HAND ELEVATOR (AALA202501188151, AALA202501180198, AALA202501181587, AALA202501188171, AALA202501185876, AALA202501180173) PER AMM 55-16-42 DUE TO EXCESSIVE PLAY. A SATISFACTORY OPERATIONAL CHECK WAS ACCOMPLISHED. NOTE THIS REPORT IS FOR THE RIGHT HAND #6 ELEVATOR HINGE ARM END FITTING. |

10. **AALA202501155255 → AALA202501151248**

| Side | Date | Part | JASC | Text |
| --- | --- | --- | --- | --- |
| Newer | 2025-01-09 | COMPENSATOR | 2840 | AIRCRAFT WAS NOT GROUNDED: AT THE GATE BEFORE FLIGHT, THE FUEL QUANTITY INDICATED 8500 IN EACH MAIN TANK (BALANCED CONDITION) AND 3700 IN THE CENTER TANK. AFTER ENGINE START, THE LEFT TANK INDICATED ONLY 7200 AND THE AMBER IMBALANCE ANNUNCIATION ILLUMINATED. ALMOST 1500 OF FUEL ARE UNACCOUNTED FOR. AIRCRAFT RETURNED TO THE GATE. LEFT HAND WING FUEL QUANTITY INDICATION CONFIRMED INOPERATIVE **SUPPLEMENTAL REPORT FOR (AALA202501105255): PERFORMED CAP AND RESISTANCE DRY TESTS, PER B737 AMM 28-41-21-710-801. ALL READINGS WITHIN LIMITS BUT NOT LO/2 TO HI/2 FLUCTUATING READINGS AT TANK UNIT 5 AND 6 COMPENSATOR. REMOVED AND REPLACED TANK 5 COMPENSATOR (AALA202501105255) AND TANK 6 COMPENSATOR (AALA202501151248), PER AMM 28-41-21. OPERTIONAL AND BITE CHECKS GOOD. NO FAULTS**(CLOSED). |
| Older | 2025-01-09 | COMPENSATOR | 2840 | AIRCRAFT WAS NOT GROUNDED: AT THE GATE BEFORE FLIGHT, THE FUEL QUANTITY INDICATED 8500 IN EACH MAIN TANK (BALANCED CONDITION) AND 3700 IN THE CENTER TANK. AFTER ENGINE START, THE LEFT TANK INDICATED ONLY 7200 AND THE AMBER IMBALANCE ANNUNCIATION ILLUMINATED. ALMOST 1500 OF FUEL ARE UNACCOUNTED FOR. AIRCRAFT RETURNED TO THE GATE. LEFT HAND WING FUEL QUANTITY INDICATION CONFIRMED INOPERATIVE PERFORMED CAP AND RESISTANCE DRY TESTS, PER B737 AMM 28-41-21-710-801. ALL READINGS WITHIN LIMITS BUT NOT LO/2 TO HI/2 FLUCTUATING READINGS AT TANK UNIT 5 AND 6 COMPENSATOR. REMOVED AND REPLACED TANK 5 COMPENSATOR (AALA202501105255) AND TANK 6 COMPENSATOR (AALA202501151248), PER AMM 28-41-21. OPERTIONAL AND BITE CHECKS GOOD. NO FAULTS. |

Human-review warning: several samples are plausible follow-ups, but pair 9 is
especially suspect because the newer record cites the original report while
the selected older row is one of many component-detail records. The partial
20-edge output must not be presented as validated ground truth.

## Options measured without changing production

Option A's offline gate is: exact nonblank part, JASC, or location, **or** at
least two meaningful shared text tokens with Jaccard overlap ≥0.20. The
`SUPPLEMENTAL REPORT FOR <ID>` answer-key fragment is stripped before overlap;
same-day is not used as a filter. On all 141 ground-truth pairs, current and
tight rules both retrieve 141/141 and rank the true prior first for 124/141.

F1 cannot be defined from 141 positive pairs alone. The archived 0.762 F1 uses
those positives plus 209 sampled negatives and saved GPT-OSS outputs. A changed
gate/model/pass count requires outputs for the changed selected pairs; the
63-entry Qwen cache lacks enough coverage and raw votes. Values below are
therefore explicitly separated into measured retrieval and unavailable
classification effects.

| Option | Projected calls | Projected tokens | Offline recall / F1 | Main risk |
| --- | ---: | --- | --- | --- |
| A. Cheap-feature tight gate | **8,270** (1,654 × 5) | UNVERIFIED | candidate recall 141/141; top-1 124/141; classification F1 NOT RUN | Only 9.9% call reduction; text overlap may miss differently worded later corrections outside this corpus |
| B. One consistency pass | **1,835** | UNVERIFIED | NOT RUN; cache has no individual votes | Model variance/parse failures become single points of failure |
| C. Cheap first pass + escalation | **1,835 + escalation calls** | UNVERIFIED | NOT RUN; no cheaper-model cache/model configured | Unknown escalation rate and distribution shift; adds routing complexity |
| D. Persistent daily budget/resume | **9,175 total**, ≤1,000/day | same unmeasured total | no behavior change; archived recall 0.660/F1 0.762 unchanged | At least 10 days; corpus/model drift across days; must persist exact model/config provenance |

**Recommendation: D, persistent daily budget/resume.** It is the only option
whose quality effect is known to be zero and it lets the current classifier
finish within free-tier request quotas. A is promising as a later cost change,
but should not ship until its classification F1 is measured on the changed
negative selections. This report deliberately does not implement any option.

## NOT RUN / UNVERIFIED

- Fresh Groq usage calls: rejected before execution; 0/10 completed.
- Prompt/completion token mean and full-corpus token projection.
- Vote agreement for the 103 records (not retained in cache).
- Full-corpus label/correction/review distribution.
- Classification F1 for options A, B, or C.
- Shared-staging migration, analysis, or any other graph write.
