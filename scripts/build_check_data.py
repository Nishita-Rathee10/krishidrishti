"""Builds data/processed/check_data.json for the Crop check page.

Run from the project folder:  python scripts/build_check_data.py
Reads only files that are already in data/processed. Nothing is trained here.
"""
import json
import math

import pandas as pd

PROC = "data/processed/"
sites = json.load(open(PROC + "districts.json", encoding="utf-8"))["districts"]
by_key = {(d["state"], d["source_name"]): d for d in sites}
assert len(by_key) == 44

crops = json.load(open(PROC + "crops_data.json", encoding="utf-8"))
shown = crops["shown"]                      # same crops, same order as the Crops page
site = pd.read_csv(PROC + "crop_site_table.csv")
reasons = pd.read_csv(PROC + "crop_reasons.csv")

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

# Distance between district centres, in km
dist = {}
for a in sites:
    for b in sites:
        if a["slug"] != b["slug"]:
            dy = (a["lat"] - b["lat"]) * 111.0
            dx = (a["lon"] - b["lon"]) * 111.0 * math.cos(math.radians(30.5))
            dist[(a["slug"], b["slug"])] = math.hypot(dx, dy)

out_crops = []
for e in shown:
    out_crops.append({"item": e["item"], "slug": e["item"].lower().replace("(", "").replace(")", "").replace("/", "-").replace(" ", "-"),
                      "name": e["name"], "season": e["season"], "auc_in_100": e["auc_in_100"],
                      "n_tested": int(site[(site["Item"] == e["item"]) & site["Band"].notna()].shape[0])})

# Rows of the table by (district slug, item)
rows = {}
for _, r in site.iterrows():
    d = by_key[(r["State"], r["District"])]
    rows[(d["slug"], r["Item"])] = r

why = {}
for (state, name, item), g in reasons.groupby(["State", "District", "Item"]):
    slug = by_key[(state, name)]["slug"]
    lst = []
    for _, q in g.sort_values("Rank").head(3).iterrows():
        label, unit = FEATURE_TEXT[q["Feature"]]
        lst.append({"label": label, "unit": unit, "value": round(float(q["District_value"]), 1 if unit != "mm" else 0),
                    "helps": bool(q["Weight"] > 0)})
    why[(slug, item)] = lst

districts = {}
for d in sites:
    per = {}
    for c in out_crops:
        r = rows.get((d["slug"], c["item"]))
        if r is None or pd.isna(r["Band"]):
            continue                        # this crop was not tested in this district
        near = []
        for o in sorted((x for x in sites if x["slug"] != d["slug"]), key=lambda x: dist[(d["slug"], x["slug"])]):
            ro = rows.get((o["slug"], c["item"]))
            if ro is None or pd.isna(ro["Band"]):
                continue
            if ro["Status"] == "Major crop now" or ro["Band"] == "High":
                near.append({"slug": o["slug"], "name": o["name"], "km": int(round(dist[(d["slug"], o["slug"])])),
                             "major": bool(ro["Status"] == "Major crop now"),
                             "share": round(float(ro["MeanShare"]) * 100, 1), "band": str(ro["Band"])})
            if len(near) == 3:
                break
        per[c["slug"]] = {"band": str(r["Band"]), "major": bool(r["Status"] == "Major crop now"),
                          "share": round(float(r["MeanShare"]) * 100, 1), "status": str(r["Status"]),
                          "why": why.get((d["slug"], c["item"]), []), "near": near}
    districts[d["slug"]] = per

with open(PROC + "check_data.json", "w", encoding="utf-8") as fh:
    json.dump({"crops": out_crops, "districts": districts}, fh, indent=1, ensure_ascii=False)

print("Crops:", [(c["name"], c["season"], c["n_tested"]) for c in out_crops])
print("Districts:", len(districts), "| district-crop checks:", sum(len(v) for v in districts.values()))
