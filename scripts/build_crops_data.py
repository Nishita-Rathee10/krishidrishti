import json
import os

import pandas as pd
from sklearn.metrics import roc_auc_score

site = pd.read_csv("data/processed/crop_site_table.csv")
site["Trusted"] = site["Trusted"].astype(bool)
met = json.load(open("models/crop_metrics.json", encoding="utf-8"))
shap = json.load(open("data/processed/crop_shap.json", encoding="utf-8"))
sites = json.load(open("data/processed/districts.json", encoding="utf-8"))["districts"]
by_key = {(d["state"], d["source_name"]): d for d in sites}

CROP_NAME = {"Rapeseed and Mustard": "Mustard and rapeseed", "Arhar/Tur": "Arhar (tur)", "Guar seed": "Guar",
             "other oilseeds": "Other oilseeds"}
SEASON_NAME = {"Kharif": "Kharif", "Rabi": "Rabi", "Whole Year": "Whole year"}
HIDE = {"Guar seed (Whole Year)"}  # same choice as the district pages


def label_of(item):
    crop, season = item[:-1].rsplit(" (", 1)
    return CROP_NAME.get(crop, crop), SEASON_NAME.get(season, season)


# One entry for every crop that was tested
tested = []
for item, g in site.groupby("Item"):
    t = g[g["P_lodo"].notna()]
    if t.empty:
        continue
    n_yes, n_no = int(t["Major"].sum()), int((1 - t["Major"]).sum())
    auc = float(roc_auc_score(t["Major"], t["P_lodo"])) if n_yes and n_no else None
    flag = bool(g["Trusted"].any())
    rule = auc is not None and auc >= 0.70 and n_yes >= 5 and n_no >= 5
    if rule != flag:
        print("WARNING: rule and saved flag differ for", item, "| rule:", rule, "| flag:", flag)
    name, season = label_of(item)
    entry = {"item": item, "name": name, "season": season, "n_major": n_yes, "n_not": n_no,
             "auc": None if auc is None else round(auc, 3), "auc_in_100": None if auc is None else int(round(100 * auc)),
             "trusted": flag}
    if not flag:
        entry["why"] = ("Too few districts to test it fairly" if n_yes < 5 or n_no < 5
                        else "Its test score was below our bar of 70 in 100")
    else:
        major = g[g["Status"] == "Major crop now"]
        suits = g[g["Status"] == "Climate suits, not major now"].sort_values("P_lodo", ascending=False)
        entry["major_now"] = sorted(({"slug": by_key[(r["State"], r["District"])]["slug"],
                                      "name": by_key[(r["State"], r["District"])]["name"]} for _, r in major.iterrows()),
                                    key=lambda x: x["name"])
        entry["suits"] = [{"slug": by_key[(r["State"], r["District"])]["slug"],
                           "name": by_key[(r["State"], r["District"])]["name"],
                           "share": round(float(r["MeanShare"]) * 100, 1), "p": round(float(r["P_lodo"]), 2)}
                          for _, r in suits.iterrows()]
        entry["factors"] = [f["label"] for f in shap["crops"].get(item, [])]
    tested.append(entry)
tested.sort(key=lambda e: (e["name"], e["season"]))

shown = [e for e in tested if e["trusted"] and e["item"] not in HIDE]
not_shown = [e for e in tested if not e["trusted"]]


def labels(items):
    return sorted(f"{label_of(i)[0]} ({label_of(i)[1].lower()})" for i in items)


cal = [{"bin": c["Bin"], "rows": int(c["Rows"]), "said": round(100 * float(c["Mean_predicted"])),
        "real": round(100 * float(c["Actual_major_rate"]))} for c in met["calibration"]]
off = [c for c in cal if abs(c["said"] - c["real"]) >= 8]

out = {"auc": round(met["within_crop_auc_oof"], 3), "auc_in_100": int(round(100 * met["within_crop_auc_oof"])),
       "brier": round(met["brier"], 3), "brier_base": round(met["brier_always_average"], 3),
       "calibration": cal, "off_bins": off, "shown": shown, "not_shown": not_shown,
       "widely_grown": labels(met["widely_grown"]), "rare": labels(met["rare"]),
       "districts": len(sites), "shap": {"rows": shap["rows"], "items": shap["items"], "global": shap["global"]}}
with open("data/processed/crops_data.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))

print("Crops tested:", len(tested), "| shown on the page:", len(shown), "| tested but not shown:", len(not_shown))
print("\nShown:")
for e in shown:
    print(f"  {e['name']} ({e['season']}): {e['auc_in_100']} in 100, major in {e['n_major']} districts, "
          f"{len(e['suits'])} suggestions: {[s['name'] for s in e['suits']]}, factors: {e['factors']}")
print("\nTested but not shown:")
for e in not_shown:
    print(f"  {e['name']} ({e['season']}): major {e['n_major']}, not {e['n_not']}, AUC {e['auc']} | {e['why']}")
print("\nCalibration bins off by 8 points or more:", off)
print("Saved data/processed/crops_data.json,", round(os.path.getsize("data/processed/crops_data.json") / 1e3), "KB")
