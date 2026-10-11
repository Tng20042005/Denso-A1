# Dataset survey — G1 public-real freeze

Updated: 2026-10-07

## Decision

**Primary: CWRU 12 kHz Drive-End subset. Backup/external validation: Paderborn Bearing DataCenter.**

CWRU was selected for the first executable public-real run because its official
site exposes a small, directly downloadable Matlab corpus with documented
normal/fault files, 12 kHz signals, DE/FE/BA channels and RPM/load metadata.
Paderborn is the stronger external check for metadata and licensing. It has now
been executed as the external public-real validation after CWRU cross-load
remained close to saturation at k=1 and k=2.

The CWRU raw files are downloaded under `data/raw/cwru/` and are git-ignored.
The benchmark stores SHA-256 checksums and a frozen group manifest in
`reports/cwru/`.

## Candidate comparison

| Dataset | Structure / labels | Sampling / measurement | Grouping | License / decision |
| --- | --- | --- | --- | --- |
| **CWRU** | Official normal baseline plus inner/ball/outer seeded faults, load and RPM tables; Matlab files | 12 kHz for this subset; DE/FE/BA and RPM keys | One Matlab recording/file is one immutable group | Official page documents access and attribution but does not state a SPDX license; retain source attribution and do not redistribute raw files. **Primary** |
| **Paderborn** | 26 damaged + 6 healthy states; 4 operating conditions; 20 × 4-second measurements per setting; damage fact sheets | Official publication reports 64 kHz for main signals; vibration and motor current plus speed/torque/load/temp | Bearing code + operating-condition code + measurement index | CC BY-NC 4.0; citation required; commercial use requires contact. **Backup/external validation** |
| **IMS/NASA** | Public IMS ZIP and bearing degradation experiments | Official catalog page does not expose sampling rate or raw group schema | Run/group semantics require inspection of ZIP and source documentation | Catalog lists public access and USA.gov government-works license, but schema/terms are not sufficient to freeze this run. **Deferred** |

## CWRU freeze

- Source: `https://engineering.case.edu/bearingdatacenter/download-data-file`
- Fault index: `https://engineering.case.edu/bearingdatacenter/12k-drive-end-bearing-fault-data`
- Normal index: `https://engineering.case.edu/bearingdatacenter/normal-baseline-data`
- Download base: `https://engineering.case.edu/sites/default/files/{id}.mat`
- Files: `97–100` normal; `105–108` inner-race 0.007-inch; `118–121`
  ball 0.007-inch; `130–133` outer-race 0.007-inch at 6 o'clock.
- Channel: `DE`; sampling rate: 12,000 Hz.
- `fault_origin`: `seeded_physical`, not `field_observed`.
- Windowing: 4096 samples, non-overlapping.
- Group: raw Matlab file ID; all windows from one file remain together.
- Test: measured `public_real` samples only; no generated samples.
- Files and checksums: `reports/cwru/summary.json`.

## CWRU data card

- Name: `CWRU_Bearing_Data_Center`
- Source type: `public_real`
- Version: `official-12k-download`
- Signals: acceleration, single DE channel in the frozen run
- Native rate: 12,000 Hz
- Labels: binary normal/fault; diagnostic condition retained separately
- Fault origin: seeded physical EDM faults
- Group unit: source Matlab recording
- Intended use: public-real utility validation for this prototype
- Not intended: DENSO-specific or field-natural-fault performance claim
- Raw data policy: never commit or redistribute raw files from this repo

## Paderborn external-validation freeze

- Source: `https://mb.uni-paderborn.de/en/kat/research/bearing-datacenter/data-sets-and-download`
- License: CC BY-NC 4.0; citation required; no commercial redistribution.
- Frozen condition: `N15_M07_F10`.
- Signal: `vibration_1`, 64,000 Hz; non-overlapping 4096-sample windows.
- Measurement budget: repetitions `[1, 2, 3, 4, 5]` for each selected bearing.
- Bearing groups: 4 healthy bearings plus 6 real accelerated-damage bearings;
  all windows from one bearing remain in one split partition.
- Test: measured fault-bearing groups plus a measured healthy group; no
  generated samples are allowed in test.
- Artifact: `reports/paderborn/summary.json`, `split_manifest.json`,
  `raw_metrics.json`, and `run_audit.md`.
