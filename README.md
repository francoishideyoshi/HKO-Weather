# HKO Weather — Hong Kong daily weather 2000–present

Interactive charts of Hong Kong Observatory daily data. Live page: https://francoishideyoshi.github.io/HKO-Weather/

## What's inside

- `index.html` — chart viewer (Plotly.js via CDN, no build step)
- `fetch.py` — downloads HKO open-data CSVs, merges to `data/daily.csv`
- `test_fetch.py` — sanity checks on `data/daily.csv`
- `data/daily.csv` — one row per day, 2000-03-01 → latest

Three views: full timeline; same day-of-year across years; same month across years with daily drill-down.

| Column | Meaning | Unit | Station |
|---|---|---|---|
| hko_max_c | daily max temperature | °C | HKO |
| hko_min_c | daily min temperature | °C | HKO |
| hko_mean_c | daily mean temperature | °C | HKO |
| kp_max_c | daily max temperature | °C | King's Park |
| kp_min_c | daily min temperature | °C | King's Park |
| kp_mean_c | daily mean temperature | °C | King's Park |
| hko_rain_mm | daily total rainfall | mm | HKO |
| hko_rh_pct | daily mean relative humidity | % | HKO |
| hko_pressure_hpa | daily mean sea-level pressure | hPa | HKO |
| hko_cloud_pct | daily mean cloud cover | % | HKO |
| kp_sun_hr | daily total sunshine | h | King's Park |
| kp_wind_kmh | daily mean wind speed | km/h | King's Park |
| kp_hkhi_mean | daily mean Hong Kong heat index | HKHI | King's Park |
| kp_hkhi_max | daily max Hong Kong heat index | HKHI | King's Park |

Stations: HKO (Tsim Sha Tsui HQ) and King's Park.

## Data

Source: `https://data.weather.gov.hk/weatherAPI/cis/csvfile/{STN}/ALL/daily_{STN}_{CODE}_ALL.csv`

Heat index source (different path): `https://data.weather.gov.hk/weatherAPI/hko_data/csdi/dataset/daily_{STN}_{CODE}_ALL.csv` (King's Park MEANHKHI/MAXHKHI, starts 2014-05-30; empty cells before that).

Notes: "Trace" rainfall stored as 0.0; missing values are empty cells; files lag ~1 month. Wind direction is not available as a daily CSV.

## Refresh data

```sh
python3 fetch.py && python3 test_fetch.py
```

Stdlib only, Python 3.9+.

View locally: `python3 -m http.server`, then open http://localhost:8000.

## Attribution & licence

Data © Hong Kong Observatory, obtained from DATA.GOV.HK — subject to https://data.gov.hk/en/terms-and-conditions.

Code is MIT (see LICENSE); MIT covers code only, not the data. Unofficial project, not affiliated with or endorsed by HKO.
