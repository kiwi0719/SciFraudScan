"""Download the real datasets the false-positive measurement runs on.

    python benchmarks/false_positives/fetch_datasets.py

300 datasets sampled from Rdatasets (https://vincentarelbundock.github.io/Rdatasets/),
a mirror of the example data shipped with R packages. They are ordinary
published teaching and research data with no connection to research
misconduct, which is the point: anything the checks say about them is a
statement about ordinary data.
"""

from __future__ import annotations

import concurrent.futures as futures
import pathlib
import urllib.request

import pandas as pd

INDEX = "https://vincentarelbundock.github.io/Rdatasets/datasets.csv"
OUT = pathlib.Path(__file__).resolve().parent / "rdata"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    index = pd.read_csv(INDEX)
    chosen = index[
        index["Rows"].between(20, 5000)
        & index["Cols"].between(3, 60)
        & (index["n_numeric"] >= 2)
    ].sample(300, random_state=11)

    def fetch(row) -> str | None:
        path = OUT / f"{row.Package}__{row.Item}.csv"
        if path.exists() and path.stat().st_size:
            return path.name
        try:
            with urllib.request.urlopen(row.CSV, timeout=30) as response:
                path.write_bytes(response.read())
        except Exception:
            return None
        return path.name

    with futures.ThreadPoolExecutor(16) as pool:
        got = [name for name in pool.map(fetch, chosen.itertuples()) if name]
    print(f"downloaded {len(got)} of {len(chosen)} datasets into {OUT}")


if __name__ == "__main__":
    main()
