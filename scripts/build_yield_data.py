import json

import joblib
import numpy as np
import pandas as pd

bundle = joblib.load("models/yield_model.joblib")
model, CAT, NUM = bundle["model"], bundle["cat"], bundle["num"]
band_all, band_crop = bundle["band_all"], bundle["band_crop"]
TRAINED_THROUGH = bundle["trained_through"]

df = pd.read_csv("data/processed/yield_model_table.csv")
keys = ["State", "District", "Crop", "Season"]
sites = json.load(open("data/processed/districts.json", encoding="utf-8"))["districts"]
site_of = {(d["state"], d["source_name"]): d for d in sites}

CROP_NAME = {
    "Arhar/Tur": "Arhar (tur)",
    "Rapeseed and Mustard": "Mustard and rapeseed",
}


def crop_label(c):
    return CROP_NAME.get(c, c)


def crop_slug(c):
    return crop_label(c).lower().replace(" (", "-").replace(")", "").replace(" ", "-")


# Same "last year" rule as train_yield.py: last year's yield, or the mean of the last 3 years if last year is missing
full = df.copy()
base = full[keys + ["Crop_Year", "Yield"]]
for k in (1, 2, 3):
    p = base.copy()
    p["Crop_Year"] = p["Crop_Year"] + k
    full = full.merge(p.rename(columns={"Yield": f"prev{k}"}), on=keys + ["Crop_Year"], how="left")
full["prev_mean"] = full[["prev1", "prev2", "prev3"]].mean(axis=1)
full["prev1"] = full["prev1"].fillna(full["prev_mean"])

test = full[full["Crop_Year"] > TRAINED_THROUGH].reset_index(drop=True)
test["pred"] = model.predict(test[CAT + NUM])
lo, hi = [], []
for _, r in test.iterrows():
    b = band_crop.get(r["Crop"], band_all)
    lo.append(r["pred"] * np.exp(b["q10"]))
    hi.append(r["pred"] * np.exp(b["q90"]))
test["lo"], test["hi"] = lo, hi
test["ape_forest"] = (test["pred"] - test["Yield"]).abs() / test["Yield"]
test["ape_last"] = (test["prev1"] - test["Yield"]).abs() / test["Yield"]
test["inside"] = (test["Yield"] >= test["lo"]) & (test["Yield"] <= test["hi"])

# Check: must match the numbers saved by train_yield.py
check = round(100 * test["ape_forest"].median(), 1)
saved = [t for t in json.load(open("models/yield_metrics.json"))["test"] if t["Method"] == "Forest, all test rows"][0]
print("Forest median error on test rows:", check, "| saved by train_yield.py:", saved["Median error %"])
assert abs(check - saved["Median error %"]) < 0.11, "Does not match the saved metrics"

# One series for every district, crop and season
series = {}
skipped = 0
for (state, district, crop, season), g in full.groupby(keys):
    site = site_of.get((state, district))
    if site is None:
        skipped += 1
        continue
    g = g.sort_values("Crop_Year")
    t = test[(test["State"] == state) & (test["District"] == district) & (test["Crop"] == crop) & (test["Season"] == season)]
    sid = f'{site["slug"]}|{crop_slug(crop)}|{season.lower()}'
    series[sid] = {
        "district": site["slug"], "crop": crop_slug(crop), "season": season,
        "years": [int(y) for y in g["Crop_Year"]],
        "yield": [round(float(v), 2) for v in g["Yield"]],
        "test": [{"year": int(r["Crop_Year"]), "actual": round(float(r["Yield"]), 2), "pred": round(float(r["pred"]), 2),
                  "lo": round(float(r["lo"]), 2), "hi": round(float(r["hi"]), 2),
                  "last": None if pd.isna(r["prev1"]) else round(float(r["prev1"]), 2)} for _, r in t.iterrows()],
    }

# Numbers for each crop
crops = []
for crop, g in test.groupby("Crop"):
    h = g[g["prev_mean"].notna()]
    b = band_crop.get(crop, band_all)
    crops.append({
        "slug": crop_slug(crop), "name": crop_label(crop),
        "test_rows": int(len(g)), "history_rows": int(len(h)),
        "forest_error": round(100 * float(g["ape_forest"].median()), 1),
        "forest_error_history": round(100 * float(h["ape_forest"].median()), 1) if len(h) else None,
        "last_year_error_history": round(100 * float(h["ape_last"].median()), 1) if len(h) else None,
        "range_low_pct": round(100 * (float(np.exp(b["q10"])) - 1)),
        "range_high_pct": round(100 * (float(np.exp(b["q90"])) - 1)),
        "inside_pct": round(100 * float(g["inside"].mean()), 1),
    })
crops.sort(key=lambda c: c["name"])

summary = json.load(open("models/yield_metrics.json"))["test"]
out = {"trained_through": TRAINED_THROUGH, "test_years": sorted(int(y) for y in test["Crop_Year"].unique()),
       "inside_pct_all": round(100 * float(test["inside"].mean()), 1),
       "summary": summary, "crops": crops, "series": series}
with open("data/processed/yield_data.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))

import os
print("\nSeries:", len(series), "| rows skipped (district not in the 44):", skipped)
multi = pd.Series([s.split("|")[0] + "|" + s.split("|")[1] for s in series]).value_counts()
print("District and crop pairs with more than one season:", int((multi > 1).sum()))
print("Test years:", out["test_years"], "| share of true yields inside the likely range:", out["inside_pct_all"], "%")
print("\nMedian yield by crop (to check the unit):")
print(df.groupby("Crop")["Yield"].median().round(2).to_string())
print("\nBy crop (test years):")
print(pd.DataFrame(crops)[["name", "test_rows", "forest_error", "forest_error_history", "last_year_error_history",
                           "range_low_pct", "range_high_pct", "inside_pct"]].to_string(index=False))
print("\nSaved data/processed/yield_data.json,", round(os.path.getsize("data/processed/yield_data.json") / 1e3), "KB")
