"""Download the two CDC feeds this project uses, for Virginia only, into data/.

The frozen copy the analysis runs on is the `data` release on GitHub, with the
SHA-256 of each file in data/README.md. Both feeds are revised every Wednesday,
so a fresh download will not match those hashes. Run this script only to take a
new snapshot on purpose, and record the new hashes and the date in
data/README.md and decisions.md in the same commit.

    python fetch_data.py
"""
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

DATA = Path(__file__).parent / "data"

# Socrata CSV export. $order makes the row order, and so the hash, repeatable
# for a given state of the source.
FEEDS = {
    # NHSN Weekly Hospital Respiratory Data by jurisdiction (preliminary).
    "nhsn_hrd_virginia.csv": (
        "https://data.cdc.gov/resource/mpgq-jmmr.csv",
        {"$where": "jurisdiction='VA'", "$order": "weekendingdate", "$limit": 5000},
    ),
    # NSSP emergency-department visit shares, state and sub-state.
    "nssp_ed_virginia.csv": (
        "https://data.cdc.gov/resource/rdmq-nq56.csv",
        {"$where": "geography='Virginia'", "$order": "week_end,fips,county", "$limit": 200000},
    ),
}


def main():
    DATA.mkdir(exist_ok=True)
    for name, (url, params) in FEEDS.items():
        raw = urlopen(f"{url}?{urlencode(params)}", timeout=120).read()
        (DATA / name).write_bytes(raw)
        print(f"{sha256(raw).hexdigest()}  {name}  ({raw.count(b'\n') - 1:,} rows)")


if __name__ == "__main__":
    main()
