"""Download HKO daily CSVs and merge into data/daily.csv. Stdlib only."""
from __future__ import annotations

import csv
import datetime
import os
import time
import urllib.request

BASE = "https://data.weather.gov.hk/weatherAPI/cis/csvfile/{stn}/ALL/daily_{stn}_{code}_ALL.csv"
CSDI_BASE = "https://data.weather.gov.hk/weatherAPI/hko_data/csdi/dataset/daily_{stn}_{code}_ALL.csv"
RAW_DIR = os.path.join("data", "raw")
OUT = os.path.join("data", "daily.csv")
START = datetime.date(2000, 3, 1)
HKHI_START = datetime.date(2014, 5, 30)
HKHI_CODES = ("MEANHKHI", "MAXHKHI")
MIN_ROWS = 1000  # per-source floor of non-empty values in its window; below -> fail loudly
TIMEOUT = 120
RETRIES = 3
MIN_CACHE_BYTES = 1024  # smaller cached files are treated as missing (e.g. killed download)

# (station, code, output column, url template, value column index); column order = csv column order
SOURCES = [
    ("HKO", "MAXT", "hko_max_c", BASE, 3),
    ("HKO", "MINT", "hko_min_c", BASE, 3),
    ("HKO", "TEMP", "hko_mean_c", BASE, 3),
    ("KP", "MAXT", "kp_max_c", BASE, 3),
    ("KP", "MINT", "kp_min_c", BASE, 3),
    ("KP", "TEMP", "kp_mean_c", BASE, 3),
    ("HKO", "RF", "hko_rain_mm", BASE, 3),
    ("HKO", "RH", "hko_rh_pct", BASE, 3),
    ("HKO", "MSLP", "hko_pressure_hpa", BASE, 3),
    ("HKO", "CLD", "hko_cloud_pct", BASE, 3),
    ("KP", "SUN", "kp_sun_hr", BASE, 3),
    ("KP", "WSPD", "kp_wind_kmh", BASE, 3),
    ("KP", "MEANHKHI", "kp_hkhi_mean", CSDI_BASE, 7),
    ("KP", "MAXHKHI", "kp_hkhi_max", CSDI_BASE, 7),
]


def parse_row(row: list[str], is_rain: bool, vcol: int = 3) -> tuple[str, str] | None:
    """Return (iso date, cleaned value) or None for header/footer rows."""
    if len(row) <= vcol:
        return None
    try:
        y, m, d = int(row[0]), int(row[1]), int(row[2])
        iso = datetime.date(y, m, d).isoformat()  # also rejects e.g. 1900-02-29
    except ValueError:
        return None  # multilingual headers/footers land here
    v = row[vcol].strip()
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
    if (os.path.exists(path) and os.path.getsize(path) >= MIN_CACHE_BYTES
            and time.time() - os.path.getmtime(path) < 86400):
        print(f"cached {path}")
        return
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (hko-daily-fetch)"})
    part = path + ".part"
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r, open(part, "wb") as f:
                f.write(r.read())
            os.replace(part, path)  # atomic: final path is never partial
        except Exception as e:
            try:
                os.remove(part)
            except OSError:
                pass
            if attempt == RETRIES:
                raise RuntimeError(f"download failed: {url}: {e}") from e
            time.sleep(5)
            continue
        print(f"fetched {path}")
        return


def load_series(path: str, is_rain: bool, vcol: int = 3) -> dict[str, str]:
    series: dict[str, str] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            parsed = parse_row(row, is_rain, vcol)
            if parsed:
                series[parsed[0]] = parsed[1]
    return series


def main() -> None:
    os.makedirs(RAW_DIR, exist_ok=True)
    data: dict[str, dict[str, str]] = {}
    latest = START
    for i, (stn, code, col, base, vcol) in enumerate(SOURCES):
        url = base.format(stn=stn, code=code)
        path = os.path.join(RAW_DIR, f"{stn}_{code}.csv")
        download(url, path)
        if i:
            time.sleep(1)
        series = load_series(path, is_rain=(code == "RF"), vcol=vcol)
        win = HKHI_START if code in HKHI_CODES else START
        n = sum(1 for iso, val in series.items()
                if val != "" and datetime.date.fromisoformat(iso) >= win)
        if n < MIN_ROWS:
            raise RuntimeError(f"source {stn}_{code} ({col}) yielded only {n} values since {win}")
        for iso, val in series.items():
            day = datetime.date.fromisoformat(iso)
            if day >= START:
                data.setdefault(iso, {})[col] = val
                latest = max(latest, day)
    cols = [c for _, _, c, _, _ in SOURCES]
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
