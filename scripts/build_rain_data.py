import json
import os

import numpy as np
import pandas as pd

df = pd.read_csv("data/processed/rain_monthly_ph.csv")
df["Label"] = np.where(df["Region"].str.startswith("Punjab"), "Punjab", "Haryana region")
clim = pd.read_csv("data/processed/rain_climatology.csv")
met = json.load(open("models/rain_metrics_v2.json", encoding="utf-8"))

SAR = "SARIMA(0,0,1)(0,1,1,12) on sqrt rain"
NAMES = {
    "Climatology, all years": "Usual rain, all years (1901 to the year before)",
    "Climatology, last 30 years": "Usual rain, last 30 years only",
    "Climatology, last 20 years": "Usual rain, last 20 years only",
    SAR: "Seasonal time-series model (SARIMA)",
}
REGION = {"Punjab": ("punjab", "Punjab"), "Haryana region": ("haryana", "Haryana")}
VAL_YEARS, TEST_YEARS = "1971 to 2005", "2006 to 2015"

regions = {}
for label, g in df.groupby("Label"):
    slug, name = REGION[label]
    assert (g.groupby("Year").size() == 12).all(), label
    yearly = g.groupby("Year")["Rain_mm"].sum()
    monsoon = g[g["Month"].between(6, 9)].groupby("Year")["Rain_mm"].sum()
    years = [int(y) for y in yearly.index]
    assert years == list(range(1901, 2016)), "Years are not 1901 to 2015"

    c = clim[clim["Region"] == label].sort_values("Month")
    assert len(c) == 12, label
    m = met[label]
    assert c["Window"].iloc[0] == m["chosen_climatology"], "Climatology window differs from the metrics file"
    ref = m["chosen_climatology"]

    models = []
    for key in (list(NAMES)):
        v, t = m["validation"][key], m["test"][key]
        models.append({
            "key": key, "name": NAMES[key], "is_sarima": key == SAR, "is_reference": key == ref,
            "val_mae": round(v["mae"], 1), "test_mae": round(t["mae"], 1),
            "val_gain": round(100 * (1 - v["mae"] / m["validation"][ref]["mae"]), 1),
            "test_gain": round(100 * (1 - t["mae"] / m["test"][ref]["mae"]), 1),
            "val_monsoon": round(v["monsoon_mae"]), "test_monsoon": round(t["monsoon_mae"]),
        })
    miss = [x for mm in models for x in (mm["val_monsoon"], mm["test_monsoon"])]
    p10, p90 = np.percentile(yearly, [10, 90])
    regions[slug] = {
        "name": name, "window": ref,
        "months": [{"month": int(r["Month"]), "mean": float(r["Mean_mm"]), "median": float(r["Median_mm"]),
                    "p10": float(r["P10_mm"]), "p90": float(r["P90_mm"])} for _, r in c.iterrows()],
        "years": years, "annual": [round(float(v), 0) for v in yearly], "monsoon": [round(float(v), 0) for v in monsoon],
        "annual_mean": round(float(yearly.mean())), "annual_p10": round(float(p10)), "annual_p90": round(float(p90)),
        "driest": {"year": int(yearly.idxmin()), "mm": round(float(yearly.min()))},
        "wettest": {"year": int(yearly.idxmax()), "mm": round(float(yearly.max()))},
        "monsoon_share": round(100 * float(monsoon.mean() / yearly.mean())),
        "models": models, "sarima_accepted": bool(m["sarima_accepted"]),
        "coverage": m["range_coverage_test_pct"],
        "monsoon_miss_low": min(miss), "monsoon_miss_high": max(miss),
    }

out = {"val_years": VAL_YEARS, "test_years": TEST_YEARS, "regions": regions}
with open("data/processed/rain_data.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))

for slug, r in regions.items():
    print("\n" + r["name"], "| window:", r["window"])
    print(f"  Yearly rain: average {r['annual_mean']} mm, 8 in 10 years between {r['annual_p10']} and {r['annual_p90']} mm")
    print(f"  Driest {r['driest']}, wettest {r['wettest']}, June to September share {r['monsoon_share']}%")
    print(f"  Usual month: {round(r['annual_mean'] / 12)} mm | range coverage in test years: {r['coverage']}%")
    print(pd.DataFrame(r["models"])[["name", "val_mae", "val_gain", "test_mae", "test_gain", "val_monsoon", "test_monsoon"]].to_string(index=False))
print("\nSaved data/processed/rain_data.json,", round(os.path.getsize("data/processed/rain_data.json") / 1e3), "KB")
