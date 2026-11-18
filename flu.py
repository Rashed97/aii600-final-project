"""Shared helpers for analysis.ipynb: checksum check and data loading.

Functions two people would otherwise edit inside the notebook live here.
"""
from hashlib import sha256
from pathlib import Path
import re

import pandas as pd

ROOT = Path(__file__).parent
DATA = ROOT / "data"
NHSN_FILE = "nhsn_hrd_virginia.csv"
NSSP_FILE = "nssp_ed_virginia.csv"

# Federal hospital reporting to NHSN was mandated through 30 April 2024,
# voluntary from 1 May to 31 October 2024, and mandated again from 1 November 2024
# (source: the dataset's own description on data.cdc.gov).
VOLUNTARY_START = pd.Timestamp("2024-05-01")
VOLUNTARY_END = pd.Timestamp("2024-10-31")


def expected_hashes(readme=DATA / "README.md"):
    """Read `file name` -> SHA-256 from data/README.md, the one place they are recorded."""
    pairs = re.findall(r"`([\w.\-]+\.csv)`[^\n]*?`([0-9a-f]{64})`", readme.read_text())
    return dict(pairs)


def verify_data():
    """Raise if a data file is missing or its SHA-256 differs from data/README.md."""
    expected = expected_hashes()
    if not expected:
        raise RuntimeError("No SHA-256 lines found in data/README.md")
    for name, want in expected.items():
        path = DATA / name
        if not path.exists():
            raise FileNotFoundError(
                f"{path} is missing. Run: gh release download data --dir data --repo Rashed97/aii600-final-project"
            )
        got = sha256(path.read_bytes()).hexdigest()
        if got != want:
            raise ValueError(f"{name}: SHA-256 {got} does not match data/README.md ({want})")
    return expected


def season_of(week_end):
    """Label a week by flu season, July to June: 2 Nov 2024 -> '2024-25'."""
    start = week_end.year if week_end.month >= 7 else week_end.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def reporting_regime(week_end):
    if week_end < VOLUNTARY_START:
        return "mandated (to Apr 2024)"
    if week_end <= VOLUNTARY_END:
        return "voluntary (May-Oct 2024)"
    return "mandated (from Nov 2024)"


def load_nhsn():
    """One row per week ending Saturday: Virginia confirmed flu admissions and who reported."""
    raw = pd.read_csv(DATA / NHSN_FILE, parse_dates=["weekendingdate"])
    out = raw.rename(
        columns={
            "weekendingdate": "week_end",
            "totalconfflunewadm": "flu_adm",                    # confirmed influenza new admissions, patients
            "totalconfflunewadmhosprep": "hosp_reporting",      # hospitals that reported the flu admission field
            "totalconfflunewadmperchosprep": "pct_hosp_reporting",
            "totalconfc19newadm": "covid_adm",
            "totalconfrsvnewadm": "rsv_adm",
            "numinptbeds": "inpatient_beds",                    # staffed inpatient beds at the reporting hospitals
        }
    )[["week_end", "flu_adm", "hosp_reporting", "pct_hosp_reporting", "covid_adm", "rsv_adm", "inpatient_beds"]]
    out = out.sort_values("week_end").reset_index(drop=True)
    out["season"] = out.week_end.map(season_of)
    out["regime"] = out.week_end.map(reporting_regime)
    return out


def load_nssp(county="All"):
    """Weekly share of emergency-department visits diagnosed as influenza, percent.

    county="All" is the statewide row. Any county in a health service area carries
    that area's value, so county="Fairfax" gives the Fairfax-Arlington area.
    """
    raw = pd.read_csv(DATA / NSSP_FILE, parse_dates=["week_end"])
    out = raw.loc[raw.county == county, ["week_end", "percent_visits_influenza", "hsa"]]
    out = out.rename(columns={"percent_visits_influenza": "ed_flu_pct"})
    return out.sort_values("week_end").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Split, features, model, and the cost of a booking
# ---------------------------------------------------------------------------
from statistics import NormalDist

import numpy as np

FIT_START = pd.Timestamp("2022-10-01")       # first week of the ED series; the two pandemic seasons end before it
HELD_OUT_START = pd.Timestamp("2025-07-01")  # forecasts for weeks ending on or after this date are held out
TREATMENTS = ("as-is", "drop", "rescale")


def weekly_frame(treatment):
    """One row per forecast: what is known when week t ends, and the admissions of week t+1.

    treatment says what to do with the voluntary-reporting weeks (May to October 2024):
      "as-is"   use the reported counts
      "drop"    leave out every forecast whose known week or target week is in the window
      "rescale" multiply those weeks' counts by (typical share of hospitals reporting) /
                (share reporting that week); the typical share is the median over the
                training weeks outside the window, so no held-out week is used
    """
    if treatment not in TREATMENTS:
        raise ValueError(f"treatment must be one of {TREATMENTS}")
    d = load_nhsn().merge(load_nssp("All")[["week_end", "ed_flu_pct"]], on="week_end")
    d = d[d.week_end >= FIT_START].sort_values("week_end").reset_index(drop=True)
    in_window = d.regime.str.startswith("voluntary")
    d["adm"] = d.flu_adm
    if treatment == "rescale":
        train_outside = ~in_window & (d.week_end < HELD_OUT_START)
        typical = d.loc[train_outside, "pct_hosp_reporting"].median()
        d.loc[in_window, "adm"] = d.loc[in_window, "flu_adm"] * typical / d.loc[in_window, "pct_hosp_reporting"]
    out = pd.DataFrame(
        {
            "week_known": d.week_end,
            "week_target": d.week_end.shift(-1),
            "adm_now": d.adm,                       # admissions in the week just ended
            "ed_now": d.ed_flu_pct,                 # ED flu share in the week just ended, percent
            "adm_next": d.adm.shift(-1),            # the quantity to forecast, Q
            "hosp_next": d.hosp_reporting.shift(-1),
            "window": in_window | in_window.shift(-1, fill_value=False),
        }
    ).dropna(subset=["adm_next"])
    if treatment == "drop":
        out = out[~out.window]
    out["set"] = np.where(out.week_target < HELD_OUT_START, "train", "held-out")
    return out.reset_index(drop=True)


FEATURES = ["const", "log_adm_now", "log_ed_now", "sin_year", "cos_year"]


def design(frame):
    """Columns of the regression: 1, log admissions now, log ED share now, and one yearly wave."""
    angle = 2 * np.pi * frame.week_target.dt.dayofyear / 365.25
    return np.column_stack(
        [np.ones(len(frame)), np.log(frame.adm_now), np.log(frame.ed_now), np.sin(angle), np.cos(angle)]
    )


def fit_ols(X, y):
    """Least squares. Returns the coefficients and the residual standard error."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    sigma = float(np.sqrt(resid @ resid / (len(y) - X.shape[1])))
    return beta, sigma


def lognormal_quantile(mu, sigma, q):
    """Quantile q of a forecast whose log is Normal(mu, sigma^2)."""
    return np.exp(mu + NormalDist().inv_cdf(q) * sigma)


def booking_quantile(c_shift, c_short):
    """The quantile of Q that minimises c_shift*K + c_short*max(Q - K, 0): 1 - c_shift/c_short."""
    return max(0.0, 1 - c_shift / c_short)


def booking_cost(K, Q, c_shift, c_short):
    """Cost of booking capacity K when Q admissions arrive, week by week."""
    K, Q = np.asarray(K, float), np.asarray(Q, float)
    return c_shift * K + c_short * np.maximum(Q - K, 0)
