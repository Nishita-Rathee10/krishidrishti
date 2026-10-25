import json
import time
import urllib.request

import pandas as pd

coords = pd.read_csv("data/processed/district_coords.csv")
assert coords["Lat"].notna().all(), "Fix missing coordinates first"
PARAMS = ["T2M", "T2M_MAX", "T2M_MIN", "RH2M"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def fetch(lat, lon):
    url = ("https://power.larc.nasa.gov/api/temporal/climatology/point?"
           f"parameters={','.join(PARAMS)}&community=AG&longitude={lon}&latitude={lat}&format=JSON")
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=90) as resp:
                return json.load(resp)
        except Exception as e:
            last = e
            time.sleep(3)
    raise RuntimeError(f"Request failed 3 times: {last}")


rows = []
for i, r in coords.iterrows():
    data = fetch(r["Lat"], r["Lon"])
    try:
        par = data["properties"]["parameter"]
        for k, m in enumerate(MONTHS, start=1):
            row = {"State": r["State"], "District": r["District"], "Month": k}
            for p in PARAMS:
                v = par[p][m]
                row[p] = None if v == -999 else v
            rows.append(row)
    except Exception as e:
        print("Unexpected response for", r["District"], "->", e)
        print(str(data)[:600])
        raise SystemExit("Send me the text above.")
    if i == 0:
        print("Header of first response (shows the climatology period):")
        print(json.dumps(data.get("header", {}), indent=1)[:700])
    print(f"{i + 1}/{len(coords)} done: {r['District']}")
    time.sleep(1)

out = pd.DataFrame(rows).rename(columns={"T2M": "Temp_mean_C", "T2M_MAX": "Temp_max_C",
                                          "T2M_MIN": "Temp_min_C", "RH2M": "Humidity_pct"})
out.to_csv("data/processed/climate_district_monthly.csv", index=False)
print("\nRows:", len(out), "| missing values:", int(out.isna().sum().sum()))
chk = out.groupby(["State", "Month"])[["Temp_mean_C", "Humidity_pct"]].mean().round(1)
print(chk.loc[(slice(None), [1, 6, 7]), :].to_string())
print("Saved data/processed/climate_district_monthly.csv")