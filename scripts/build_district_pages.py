import json
import math

import pandas as pd
from sklearn.metrics import roc_auc_score

sites = json.load(open("data/processed/districts.json", encoding="utf-8"))["districts"]
by_key = {(d["state"], d["source_name"]): d for d in sites}
assert len(by_key) == 44

CROP_NAME = {
    "Rapeseed and Mustard": "Mustard and rapeseed",
    "Arhar/Tur": "Arhar (tur)",
    "Guar seed": "Guar",
    "other oilseeds": "Other oilseeds",
}
SEASON_NAME = {"Kharif": "Kharif", "Rabi": "Rabi", "Whole Year": "Whole year"}
SEASON_ORDER = {"Kharif": 0, "Rabi": 1, "Whole Year": 2}
FEATURE_TEXT = {
    "T_annual": ("Yearly average temperature", "°C"),
    "T_hot_max": ("Peak summer heat", "°C"),
    "T_cold_min": ("Lowest winter temperature", "°C"),
    "T_kharif": ("Temperature from June to October", "°C"),
    "T_rabi": ("Winter temperature", "°C"),
    "RH_annual": ("Yearly humidity", "%"),
    "RH_monsoon": ("Humidity from July to September", "%"),
    "RH_winter": ("Winter humidity", "%"),
    "Rain_Annual_Normal": ("Yearly rain", "mm"),
    "Rain_JunSep_Normal": ("Rain from June to September", "mm"),
}


def crop_name(c):
    return CROP_NAME.get(c, c)


# Monthly climate of each district
clim = pd.read_csv("data/processed/climate_district_monthly.csv").sort_values(["State", "District", "Month"])
monthly = {}
for (state, name), g in clim.groupby(["State", "District"]):
    assert len(g) == 12, (state, name)
    monthly[(state, name)] = {"temp": [round(float(v), 1) for v in g["Temp_mean_C"]],
                              "humidity": [int(round(float(v))) for v in g["Humidity_pct"]]}

# Crops
site = pd.read_csv("data/processed/crop_site_table.csv")
site["Trusted"] = site["Trusted"].astype(bool)
auc = {}
for item, g in site[site["P_lodo"].notna()].groupby("Item"):
    if g["Major"].nunique() == 2:
        auc[item] = float(roc_auc_score(g["Major"], g["P_lodo"]))

reasons = pd.read_csv("data/processed/crop_reasons.csv")

# Nearby districts
nearest = {}
for a in sites:
    ds = []
    for b in sites:
        if a["slug"] == b["slug"]:
            continue
        dy = (a["lat"] - b["lat"]) * 111.0
        dx = (a["lon"] - b["lon"]) * 111.0 * math.cos(math.radians(30.5))
        ds.append((math.hypot(dx, dy), b["slug"]))
    ds.sort()
    nearest[a["slug"]] = [{"slug": s, "km": int(round(k))} for k, s in ds[:4]]

pages = {}
for (state, name), d in by_key.items():
    s = site[(site["State"] == state) & (site["District"] == name)]
    major = s[s["Status"] == "Major crop now"].copy()
    major["so"] = major["Season"].map(SEASON_ORDER)
    major = major.sort_values(["so", "MeanShare"], ascending=[True, False])
    major_list = [{"crop": crop_name(r["Crop"]), "season": SEASON_NAME[r["Season"]],
                   "share": round(float(r["MeanShare"]) * 100, 1)} for _, r in major.iterrows()]

    ex = s[(s["Status"] == "Climate suits, not major now") & (s["Item"] != "Guar seed (Whole Year)")]
    ex = ex.sort_values("P_lodo", ascending=False)
    explore = []
    for _, r in ex.iterrows():
        rs = reasons[(reasons["State"] == state) & (reasons["District"] == name) & (reasons["Item"] == r["Item"])]
        rs = rs[rs["Weight"] > 0].sort_values("Rank").head(3)
        why = []
        for _, q in rs.iterrows():
            label, unit = FEATURE_TEXT[q["Feature"]]
            v = float(q["District_value"])
            why.append(f"{label} of {v:,.0f} {unit}" if unit == "mm" else f"{label} of {v:.1f} {unit}")
        explore.append({"crop": crop_name(r["Crop"]), "season": SEASON_NAME[r["Season"]],
                        "share": round(float(r["MeanShare"]) * 100, 1), "p": round(float(r["P_lodo"]), 2),
                        "auc_in_100": int(round(100 * auc[r["Item"]])), "why": why})
    pages[d["slug"]] = {"temp": monthly[(state, name)]["temp"], "humidity": monthly[(state, name)]["humidity"],
                        "major": major_list, "explore": explore, "near": nearest[d["slug"]]}

# Monthly rain pattern for each state (Haryana includes Delhi and Chandigarh in the source data)
rc = pd.read_csv("data/processed/rain_climatology.csv").sort_values(["Region", "Month"])
rain = {}
for region, key in (("Punjab", "Punjab"), ("Haryana region", "Haryana")):
    g = rc[rc["Region"] == region]
    assert len(g) == 12, region
    rain[key] = {"window": str(g["Window"].iloc[0]),
                 "rows": [{"month": int(r["Month"]), "mean": float(r["Mean_mm"]), "p10": float(r["P10_mm"]),
                           "p90": float(r["P90_mm"])} for _, r in g.iterrows()]}

with open("data/processed/district_pages.json", "w", encoding="utf-8") as fh:
    json.dump({"districts": pages, "rain": rain}, fh, indent=1, ensure_ascii=False)

print("Pages:", len(pages))
print("Rain window used:", {k: v["window"] for k, v in rain.items()})
print("Trusted crops with accuracy:", {k: round(v, 3) for k, v in auc.items()})
n_ex = sum(len(p["explore"]) for p in pages.values())
print("Total 'climate suits' suggestions:", n_ex)
for slug in ("ludhiana", "moga"):
    p = pages[slug]
    print(f"\n{slug}: major crops {len(p['major'])}, suggestions {len(p['explore'])}")
    print("  major:", [(m["crop"], m["season"], m["share"]) for m in p["major"]][:6])
    for e in p["explore"]:
        print("  suggest:", e)
print("Saved data/processed/district_pages.json")
