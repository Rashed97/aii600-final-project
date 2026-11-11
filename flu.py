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
        }
    )[["week_end", "flu_adm", "hosp_reporting", "pct_hosp_reporting", "covid_adm", "rsv_adm"]]
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
