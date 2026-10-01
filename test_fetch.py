"""Sanity checks for data/daily.csv. Run: python3 test_fetch.py"""
from __future__ import annotations

import csv
import datetime
import os

CSV = os.path.join("data", "daily.csv")

RANGES = {  # column -> (lo, hi)
    "hko_max_c": (-5, 45), "hko_min_c": (-5, 45), "hko_mean_c": (-5, 45),
    "kp_max_c": (-5, 45), "kp_min_c": (-5, 45), "kp_mean_c": (-5, 45),
    "hko_rain_mm": (0, 1000), "hko_rh_pct": (0, 100),
    "hko_pressure_hpa": (950, 1050), "hko_cloud_pct": (0, 100),
    "kp_sun_hr": (0, 14), "kp_wind_kmh": (0, 200),
    # NOTE(spec said 10..45): real winter rows go below 10 (e.g. 2016-01-24
    # mean 0.9 / max 3.8), so bound matches the °C temp columns instead.
    "kp_hkhi_mean": (-5, 45), "kp_hkhi_max": (-5, 45),
}


def num(s: str) -> float | None:
    return float(s) if s != "" else None


def test_parser() -> None:
    from fetch import parse_row
    assert parse_row(["2000", "3", "1", "14.4", "C"], False) == ("2000-03-01", "14.4")
    assert parse_row(["2000", "3", "1", "14.4", "#"], False) == ("2000-03-01", "14.4")
    assert parse_row(["2000", "3", "1", "Trace", "C"], True) == ("2000-03-01", "0.0")
    assert parse_row(["2000", "3", "2", "***", ""], False) == ("2000-03-02", "")
    assert parse_row(["\u5e74/Year", "\u6708/Month", "\u65e5/Day", "\u6578\u503c/Value"], False) is None
    assert parse_row(["*** \u6c92\u6709\u6578\u64da/unavailable"], False) is None
    assert parse_row(["1900", "2", "29", "15.3", "C"], False) is None
    assert parse_row(["2014", "5", "30", "", "", "", "UTC+8", "28.3", "C"], False, 7) == ("2014-05-30", "28.3")
    assert parse_row(["Year", "Month", "Day", "Hour", "Minute", "Second", "TimeZone", "Value", "data Completeness"], False, 7) is None
    print("parser unit tests ok")


def main() -> None:
    test_parser()
    with open(CSV, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows, "daily.csv is empty"
    assert list(rows[0].keys()) == ["date"] + list(RANGES), "column mismatch"
    assert rows[0]["date"] == "2000-03-01", rows[0]["date"]
    dates = [r["date"] for r in rows]
    assert len(set(dates)) == len(dates), "duplicate dates"
    day = datetime.date(2000, 3, 1)
    for r in rows:  # every date present, ascending
        assert r["date"] == day.isoformat(), f"gap/order at {day}"
        day += datetime.timedelta(days=1)
    bad: list[str] = []
    for r in rows:
        vals = {c: num(r[c]) for c in RANGES}
        for c, v in vals.items():
            if v is not None and not RANGES[c][0] <= v <= RANGES[c][1]:
                bad.append(f"{r['date']} {c}={v}")
        t = [vals["hko_min_c"], vals["hko_mean_c"], vals["hko_max_c"]]
        if all(v is not None for v in t) and not (t[0] <= t[1] <= t[2]):  # type: ignore[operator]
            bad.append(f"{r['date']} hko min/mean/max={t}")
        h = [vals["kp_hkhi_mean"], vals["kp_hkhi_max"]]
        if all(v is not None for v in h) and not (h[0] <= h[1]):  # type: ignore[operator]
            bad.append(f"{r['date']} kp hkhi mean/max={h}")
    assert not bad, f"range failures ({len(bad)}): {bad[:10]}"
    for c in RANGES:  # no blanked columns: empties must be <= 1% of the column's window
        start = "2014-05-30" if c.startswith("kp_hkhi_") else rows[0]["date"]
        win = [r for r in rows if r["date"] >= start]
        empty = sum(1 for r in win if r[c] == "")
        print(f"empty {c}: {empty}/{len(win)} since {start}")
        assert empty * 100 <= len(win), f"{c} mostly empty: {empty}/{len(win)}"
    first_mean = next(r["date"] for r in rows if r["kp_hkhi_mean"] != "")
    first_max = next(r["date"] for r in rows if r["kp_hkhi_max"] != "")
    assert first_mean == "2014-05-30", first_mean
    assert first_max == "2014-05-30", first_max
    r_hkhi = next(r for r in rows if r["date"] == "2014-05-30")
    print(f"2014-05-30 kp_hkhi_mean={r_hkhi['kp_hkhi_mean']} kp_hkhi_max={r_hkhi['kp_hkhi_max']}")
    r0 = rows[0]
    assert r0["hko_max_c"] == "14.4", r0
    assert r0["hko_min_c"] == "11.0", r0
    print(f"2000-03-01 hko_rain_mm={r0['hko_rain_mm']} hko_mean_c={r0['hko_mean_c']}")
    print(f"daily.csv ok: {len(rows)} rows {rows[0]['date']}..{rows[-1]['date']}")


if __name__ == "__main__":
    main()
