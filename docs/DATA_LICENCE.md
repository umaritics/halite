# FAA SDR Data Licence

## Source

**FAA Service Difficulty Reports (SDR)**
- Index: <https://www.faa.gov/av-info/download_SDR>
- Direct CSV: `https://external.apic4e.faa.gov/sdrs/retrieve/SDR-{YEAR}.csv`
- Years available: 1995–2026

## Licence

The FAA Service Difficulty Reports are works of the United States federal government.
Under **17 U.S.C. § 105**, copyright protection is not available for works of the
United States Government, making them **public domain**.

No permission is required to use, copy, reproduce, or distribute these records.

## Usage in This Project

The raw CSV files (`backend/data/raw/`) and processed outputs (`backend/data/processed/`)
are excluded from version control via `.gitignore`.

They are downloaded at runtime by `backend/scripts/fetch_sdr_data.py`.

Supersession pair labels in `ground_truth_pairs.csv` were **written by the FAA**
inside the `Discrepancy` field using the pattern:
`SUPPLEMENTAL REPORT FOR (OperatorControlNumber)`.

No label engineering was performed by this project.
The evaluation in `docs/evaluation_results.md` measures whether the conflict engine
recovers these FAA-authored links without being shown them.

## Citation

> Federal Aviation Administration. (2025). Service Difficulty Reporting System
> (SDR) Public Data, Year 2025.
> https://www.faa.gov/av-info/download_SDR
