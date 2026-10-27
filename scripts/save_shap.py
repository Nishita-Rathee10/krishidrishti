import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
import shap

sys.path.insert(0, os.getcwd())
from croplib import CropEnsemble  # noqa: E402

warnings.filterwarnings("ignore")

FEATURE_TEXT = {
    "T_annual": "Yearly average temperature", "T_hot_max": "Peak summer heat", "T_cold_min": "Lowest winter temperature",
    "T_kharif": "Temperature from June to October", "T_rabi": "Winter temperature", "RH_annual": "Yearly humidity",
    "RH_monsoon": "Humidity from July to September", "RH_winter": "Winter humidity", "Rain_Annual_Normal": "Yearly rain",
    "Rain_JunSep_Normal": "Rain from June to September",
}

site = pd.read_csv("data/processed/crop_site_table.csv")
df = pd.read_csv("data/processed/crop_suitability_table.csv")
df["Item"] = df["Crop"] + " (" + df["Season"] + ")"
NUM = [c for c in df.columns if c.startswith(("T_", "RH_", "Rain_"))]
st = df.groupby("Item")["Major"].agg(pos="sum", n="count")
st["neg"] = st["n"] - st["pos"]
keep = st[(st["pos"] >= 3) & (st["neg"] >= 3)].index.tolist()
d = df[df["Item"].isin(keep)].reset_index(drop=True)
params = json.load(open("models/crop_metrics.json", encoding="utf-8"))["params"]
trusted = site.loc[site["Trusted"].astype(bool), "Item"].unique().tolist()

# Same SHAP step as explain_crop.py (forest part of the final model), saved as numbers
full = CropEnsemble(NUM, **params).fit(d)
prep = full.rf_.named_steps["prep"]
rf = full.rf_.named_steps["model"]
X = prep.transform(d[["Item"] + NUM])
names = [n.split("__", 1)[1] for n in prep.get_feature_names_out()]
sv = shap.TreeExplainer(rf).shap_values(X)
if isinstance(sv, list):
    sv1 = sv[1]
elif getattr(sv, "ndim", 2) == 3:
    sv1 = sv[:, :, 1]
else:
    sv1 = sv
group = ["Crop identity" if n.startswith("Item_") else n for n in names]
imp = pd.DataFrame({"f": group, "v": np.abs(sv1).mean(axis=0)}).groupby("f")["v"].sum().sort_values(ascending=False)
total = float(imp.sum())
glob = [{"feature": f, "label": FEATURE_TEXT.get(f, f), "value": round(float(v), 4), "share": round(100 * float(v) / total, 1)}
        for f, v in imp.items()]

num_idx = [i for i, n in enumerate(names) if not n.startswith("Item_")]
crops = {}
for item in trusted:
    m = (d["Item"] == item).to_numpy()
    v = np.abs(sv1[m][:, num_idx]).mean(axis=0)
    top = np.argsort(-v)[:3]
    crops[item] = [{"feature": names[num_idx[j]], "label": FEATURE_TEXT.get(names[num_idx[j]], names[num_idx[j]]),
                    "value": round(float(v[j]), 4)} for j in top]

with open("data/processed/crop_shap.json", "w", encoding="utf-8") as fh:
    json.dump({"rows": int(len(d)), "items": len(keep), "global": glob, "crops": crops}, fh, ensure_ascii=False, indent=1)
print("Rows used:", len(d), "| crops used:", len(keep))
print(pd.DataFrame(glob)[["label", "value", "share"]].to_string(index=False))
for k, v in crops.items():
    print(k, "->", ", ".join(x["label"] for x in v))
print("Saved data/processed/crop_shap.json")
