# Data

The files the notebook reads are not committed. They are assets on the GitHub release tagged `data`, which is public. Download them into this folder from the project root:

```bash
gh release download data --dir data --repo Rashed97/aii600-final-project
```

`analysis.ipynb` checks each file against the SHA-256 below before it reads anything, through `flu.verify_data()`.

## Source and terms

Both files are extracts of public CDC datasets on data.cdc.gov, licensed **Public Domain U.S. Government**, so the terms allow republishing and the files are on the release.

1. **NHSN Weekly Hospital Respiratory Data (HRD) Metrics by Jurisdiction (Preliminary)**, dataset `mpgq-jmmr`, CDC Division of Healthcare Quality Promotion, National Healthcare Safety Network. Hospitals submit weekly counts to NHSN; the CDC aggregates them to the state. The dataset is revised every Wednesday. Reporting was federally mandated through 30 April 2024, voluntary from 1 May to 31 October 2024, and mandated again from 1 November 2024.
2. **NSSP Emergency Department Visit Trajectories by State and Sub State Regions: COVID-19, Flu, RSV, Combined**, dataset `rdmq-nq56`, CDC National Syndromic Surveillance Program. The share of all emergency-department visits with a discharge diagnosis of each pathogen, from facilities that send data to NSSP. Revised weekly.

## Files

Snapshot taken 11 November 2026 with `python fetch_data.py`, which holds the exact queries. The last week in both files ends 31 October 2026.

| File | SHA-256 | Rows | Columns |
|---|---|---:|---:|
| `nhsn_hrd_virginia.csv` | `3f5e0d82e18588d450e6697f1c47e66ce9fbace0ad2396dcdf5bbc09b8c2b9ab` | 326 | 322 |
| `nssp_ed_virginia.csv` | `f51e089aacf75ae559915cd7c4f4c7644c21fd036f5a26c7be50071b528d99a8` | 28,890 | 20 |

Both are the source rows for Virginia with every column kept. Nothing was filtered, renamed, or filled.

## Unit of observation, sample size, time span

- `nhsn_hrd_virginia.csv`: one row per **state-week** for Virginia, weeks ending Saturday, 8 August 2020 to 31 October 2026 (326 weeks). The flu admission count is empty for the first 10 weeks and present for the 316 weeks from 17 October 2020.
- `nssp_ed_virginia.csv`: one row per **area-week**, 135 areas (the statewide row `county = All`, plus Virginia counties and independent cities) by 214 weeks, 1 October 2022 to 31 October 2026. A county row carries the value of its health service area, not a county-level measurement.

## Replacing the snapshot

Both sources revise past weeks, so a new download will not match the hashes above. To take a new snapshot on purpose: run `python fetch_data.py`, update the table above with the hashes it prints, upload with

```bash
gh release upload data data/nhsn_hrd_virginia.csv data/nssp_ed_virginia.csv --repo Rashed97/aii600-final-project --clobber
```

and add a `decisions.md` entry in the same pull request.
