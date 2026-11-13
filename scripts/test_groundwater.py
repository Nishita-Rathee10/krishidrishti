"""Honest test: does adding the groundwater number help the crop model?

The rule was written BEFORE running this:
  Groundwater counts as "helping" only if, with districts the model never saw,
  the average within-crop AUC goes up by at least 0.03 AND it is better in at least 4 of 5 repeats.
Whatever the result is, it goes on the Methods page.

Run from the project folder:  python scripts/test_groundwater.py
Takes about 2 to 3 minutes. Writes data/processed/groundwater_test.json
"""
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.getcwd())
from croplib import CropEnsemble  # noqa: E402

warnings.filterwarnings("ignore")
REPEATS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
BAR_GAIN, BAR_REPEATS = 0.03, 4

# Same table, same crops and same settings as scripts/train_crop.py
df = pd.read_csv("data/processed/crop_suitability_table.csv")
df["Item"] = df["Crop"] + " (" + df["Season"] + ")"
CLIMATE = [c for c in df.columns if c.startswith(("T_", "RH_", "Rain_"))]
st = df.groupby("Item")["Major"].agg(pos="sum", n="count")
st["neg"] = st["n"] - st["pos"]
keep = st[(st["pos"] >= 3) & (st["neg"] >= 3)].index.tolist()
gw = pd.read_csv("data/processed/groundwater_district.csv")[["State", "District", "Stage_pct"]]
d = df[df["Item"].isin(keep)].merge(gw, on=["State", "District"], how="left").reset_index(drop=True)
assert d["Stage_pct"].notna().all(), "some districts have no groundwater number"
d["GW_stage"] = np.log(d["Stage_pct"])  # a ratio, so use its log; 50% and 200% sit at equal distances from 100%
params = json.load(open("models/crop_metrics.json"))["params"]
trusted = {"Bajra (Kharif)", "Cotton (Kharif)", "Guar seed (Kharif)", "Jowar (Kharif)", "Maize (Kharif)",
           "Rapeseed and Mustard (Rabi)"}
print("Rows:", len(d), "| crops:", len(keep), "| districts:", d["District"].nunique(), "| settings:", params)


def folds_for(seed):  # same as train_crop.py
    ds = np.random.RandomState(seed).permutation(d["District"].unique())
    m = {x: i % 5 for i, x in enumerate(ds)}
    return d["District"].map(m).to_numpy()


def macro_auc(p, items=None):
    v = []
    for item, g in d.assign(p=p).groupby("Item"):
        if (items is None or item in items) and g["Major"].nunique() == 2:
            v.append(roc_auc_score(g["Major"], g["p"]))
    return float(np.mean(v))


def run(cols, seed):
    fa = folds_for(seed)
    p = np.zeros(len(d))
    for f in range(5):
        p[fa == f] = CropEnsemble(cols, **params).fit(d[fa != f]).predict_proba(d[fa == f])
    return p


res = {"climate only": [], "climate + groundwater": []}
res_t = {"climate only": [], "climate + groundwater": []}
for seed in range(REPEATS):
    for name, cols in (("climate only", CLIMATE), ("climate + groundwater", CLIMATE + ["GW_stage"])):
        p = run(cols, seed)
        res[name].append(macro_auc(p))
        res_t[name].append(macro_auc(p, trusted))
    print(f"  repeat {seed + 1} of {REPEATS} done")

out = {}
for label, r in (("all tested crops", res), ("the crops we show", res_t)):
    a, b = np.array(r["climate only"]), np.array(r["climate + groundwater"])
    gain, better = float((b - a).mean()), int((b > a).sum())
    passes = gain >= BAR_GAIN and better >= BAR_REPEATS
    out[label] = {"climate_only": round(float(a.mean()), 3), "with_groundwater": round(float(b.mean()), 3),
                  "gain": round(gain, 3), "better_in_repeats": better, "repeats": REPEATS, "passes": passes}
    print(f"\n{label}: climate only {a.mean():.3f} | with groundwater {b.mean():.3f} | "
          f"gain {gain:+.3f} | better in {better} of {REPEATS} -> {'PASSES our bar' if passes else 'does NOT pass our bar'}")
print(f"\nOur bar: gain of at least {BAR_GAIN} and better in at least {BAR_REPEATS} repeats.")
with open("data/processed/groundwater_test.json", "w", encoding="utf-8") as fh:
    json.dump({"bar_gain": BAR_GAIN, "bar_repeats": BAR_REPEATS, "results": out}, fh, indent=1)
print("Saved data/processed/groundwater_test.json")
