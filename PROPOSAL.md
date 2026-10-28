# Proposal

## Hypothesis

Next week's confirmed-influenza hospital admissions in Virginia can be forecast well enough, from the admissions already reported and the share of emergency-department visits that are influenza-like, that a hospital system booking surge nursing shifts a week ahead loses less money than it does by booking to last week's count.

The quantity: **confirmed influenza admissions to Virginia hospitals in the coming week** (patients per week, statewide, as reported to the CDC's National Healthcare Safety Network), forecast one week ahead throughout the 2025–26 season, which is the held-out period.

## Data

Two public CDC series, both in the public domain and republishable, so the files go on the `data` release with SHA-256 hashes.

1. **NHSN weekly hospital respiratory data**, jurisdiction Virginia (`data.cdc.gov/resource/mpgq-jmmr`). Unit of observation: one state-week. 325 weeks from 8 August 2020 to 24 October 2026, of which 313 have a nonzero flu admission count (flu reporting begins 31 October 2020). Columns used: confirmed new flu admissions, the number of hospitals reporting that week, and the same for COVID-19 and RSV. Collected by hospitals submitting weekly to NHSN; the CDC aggregates to the state.
2. **NSSP emergency-department visit share** for Virginia and its health service areas (`data.cdc.gov/resource/rdmq-nq56`): the percentage of ED visits diagnosed as influenza, weekly from October 2022. Used as a leading indicator, since ED visits precede admissions.

How the measurement differs from what the decision needs. The decision is about one hospital system's admissions; the series is the whole state, so the model forecasts a statewide count and the system scales it by its market share. The count depends on how many hospitals reported: between 84 and 100 of Virginia's roughly 100 acute-care hospitals in most weeks, but as few as 26 during May 2024 to November 2024, when federal reporting was voluntary. A low-reporting week undercounts admissions by a factor that is not random; that is bias, not noise, and we will either rescale by hospitals reporting or exclude that window from fitting and say which. A "confirmed" admission also requires a test, so admissions during a testing shortage are undercounted in a way that correlates with the peak.

## Decision affected by the model

A hospital system's nursing director books surge shifts for the coming week. Each extra shift staffed is a fixed wage cost whether or not the patients arrive; each admission beyond staffed capacity means a boarded patient in the emergency department or a diversion, which costs more than a wage. So the loss is a newsvendor: for staffed capacity $K$ and realised admissions $Q$, cost $= c_{\text{shift}} \cdot K + c_{\text{short}} \cdot \max(Q - K, 0)$, with $c_{\text{short}} > c_{\text{shift}}$. The costlier mistake is understaffing. The rule will therefore book to an upper quantile of the forecast, the critical fractile $c_{\text{short}} / (c_{\text{short}} + c_{\text{shift}})$, not to the point forecast. The alternative being set aside is booking to last week's admissions, which is the baseline the model is scored against, in shifts and dollars rather than in RMSE.
