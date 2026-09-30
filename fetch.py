"""Download HKO daily CSVs and merge into data/daily.csv. Stdlib only."""
from __future__ import annotations

import csv
import datetime
import os
import time
import urllib.error
import urllib.request

BASE = "https://data.weather.gov.hk/weatherAPI/cis/csvfile/{stn}/ALL/daily_{stn}_{code}_ALL.csv"
RAW_DIR = os.path.join("data", "raw")
OUT = os.path.join("data", "daily.csv")
START = datetime.date(2000, 3, 1)

# (station, code, output column); column order = csv column order
SOURCES = [
    ("HKO", "MAXT", "hko_max_c"),
    ("HKO", "MINT", "hko_min_c"),
    ("HKO", "TEMP", "hko_mean_c"),
    ("KP", "MAXT", "kp_max_c"),
    ("KP", "MINT", "kp_min_c"),
    ("KP", "TEMP", "kp_mean_c"),
    ("HKO", "RF", "hko_rain_mm"),
    ("HKO", "RH", "hko_rh_pct"),
    ("HKO", "MSLP", "hko_pressure_hpa"),
    ("HKO", "CLD", "hko_cloud_pct"),
    ("KP", "SUN", "kp_sun_hr"),
    ("KP", "WSPD", "kp_wind_kmh"),
]


def parse_row(row: list[str], is_rain: bool) -> tuple[str, str] | None:
    """Return (iso date, cleaned value) or None for header/footer rows."""
    if len(row) < 4:
        return None
    try:
        y, m, d = int(row[0]), int(row[1]), int(row[2])
        iso = datetime.date(y, m, d).isoformat()  # also rejects e.g. 1900-02-29
    except ValueError:
        return None  # multilingual headers/footers land here
    v = row[3].strip()
    if v == "***" or v == "":
        return (iso, "")
    if is_rain and v == "Trace":  # <0.05 mm
        return (iso, "0.0")
    try:
        float(v)
    except ValueError:
        return (iso, "")
    return (iso, v)


def download(url: str, path: str) -> None:
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 86400:
        print(f"cached {path}")
        return
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (hko-daily-fetch)"})
    try:
        with urllib.request.urlopen(req) as r, open(path, "wb") as f:
            f.write(r.read())
    except urllib.error.URLError as e:
        raise RuntimeError(f"download failed: {url}: {e}") from e
    print(f"fetched {path}")


def load_series(path: str, is_rain: bool) -> dict[str, str]:
    series: dict[str, str] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            parsed = parse_row(row, is_rain)
            if parsed:
                series[parsed[0]] = parsed[1]
    return series


def main() -> None:
    os.makedirs(RAW_DIR, exist_ok=True)
    data: dict[str, dict[str, str]] = {}
    latest = START
    for i, (stn, code, col) in enumerate(SOURCES):
        url = BASE.format(stn=stn, code=code)
        path = os.path.join(RAW_DIR, f"{stn}_{code}.csv")
        download(url, path)
        if i:
            time.sleep(1)
        for iso, val in load_series(path, is_rain=(code == "RF")).items():
            day = datetime.date.fromisoformat(iso)
            if day >= START:
                data.setdefault(iso, {})[col] = val
                latest = max(latest, day)
    cols = [c for _, _, c in SOURCES]
    rows = []
    day = START
    while day <= latest:
        iso = day.isoformat()
        rows.append([iso] + [data.get(iso, {}).get(c, "") for c in cols])
        day += datetime.timedelta(days=1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date"] + cols)
        w.writerows(rows)
    print(f"rows={len(rows)} range={START}..{latest}")
    for j, c in enumerate(cols):
        print(f"empty {c}: {sum(1 for r in rows if r[j + 1] == '')}")


if __name__ == "__main__":
    main()
