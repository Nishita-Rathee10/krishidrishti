import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

sys.path.insert(0, os.getcwd())
from croplib import CropEnsemble  # noqa: E402

warnings.filterwarnings("ignore")

df = pd.read_csv("data/processed/crop_suitability_table.csv")
df["Item"] = df["Crop"] + " (" + df["Season"] + ")"
NUM = [c for c in df.columns if c.startswith(("T_", "RH_", "Rain_"))]
st = df.groupby("Item")["Major"].agg(pos="sum", n="count")
st["neg"] = st["n"] - st["pos"]
widely = st[st["neg"] < 3].index.tolist()
keep = st[(st["pos"] >= 3) & (st["neg"] >= 3)].index.tolist()
d = df[df["Item"].isin(keep)].reset_index(drop=True)
params = json.load(open("models/crop_metrics.json", encoding="utf-8"))["params"]
print("Settings:", params, "| rows:", len(d), "| districts:", d["District"].nunique())

# 1. Leave-one-district-out: each district is predicted by a model that never saw it
P = np.zeros(len(d))
dists = d["District"].unique()
print("\nTraining 44 models, each without one district. About 1 to 3 minutes...")
for i, dist in enumerate(dists, 1):
    mask = (d["District"] == dist).to_numpy()
    P[mask] = CropEnsemble(NUM, **params).fit(d[~mask]).predict_proba(d[mask])
    if i % 11 == 0:
        print(f"  {i}/{len(dists)} districts done")
d["P_lodo"] = np.round(P, 3)

# 2. Which crops can we trust?  (rule fixed before: AUC >= 0.70, at least 5 yes and 5 no districts)
rows = []
for item, g in d.groupby("Item"):
    pos, neg = int(g["Major"].sum()), int(len(g) - g["Major"].sum())
    auc = float(roc_auc_score(g["Major"], g["P_lodo"]))
    rows.append({"Item": item, "Major districts": pos, "Not major": neg, "AUC": round(auc, 3),
                 "Trusted": bool(auc >= 0.70 and pos >= 5 and neg >= 5)})
trust = pd.DataFrame(rows).sort_values("AUC", ascending=False)
print("\nPer-crop check (each district predicted without being in training):")
print(trust.to_string(index=False))
d = d.merge(trust[["Item", "Trusted"]], on="Item")
print("\nMean within-crop AUC, all crops:", round(trust["AUC"].mean(), 3),
      "| trusted crops only:", round(trust.loc[trust["Trusted"], "AUC"].mean(), 3))

# 3. Calibration for the trusted crops
t = d[d["Trusted"]].copy()
bins = [0, 0.3, 0.7, 1.0001]
t["Band"] = pd.cut(t["P_lodo"], bins, right=False, labels=["Low", "Medium", "High"])
cal = t.groupby("Band", observed=True).agg(Rows=("Major", "size"), Mean_predicted=("P_lodo", "mean"),
                                           Actual_major_rate=("Major", "mean")).round(2)
print("\nCalibration of the Low / Medium / High bands (trusted crops):")
print(cal.to_string())
print("Brier score (trusted crops):", round(brier_score_loss(t["Major"], t["P_lodo"]), 3),
      "| always guessing the average:", round(brier_score_loss(t["Major"], np.full(len(t), t["Major"].mean())), 3))

# 4. Table for the website
d["Band"] = np.where(d["P_lodo"] >= 0.7, "High", np.where(d["P_lodo"] >= 0.3, "Medium", "Low"))
d["Status"] = np.where(d["Major"] == 1, "Major crop now",
                       np.where(d["Trusted"] & (d["P_lodo"] >= 0.7), "Climate suits, not major now", "Other"))
w = df[df["Item"].isin(widely)].copy()
w["P_lodo"], w["Trusted"], w["Band"] = np.nan, False, ""
w["Status"] = np.where(w["Major"] == 1, "Major crop now", "Other")
cols = ["State", "District", "Season", "Crop", "Item", "MeanShare", "Major", "P_lodo", "Trusted", "Band", "Status"]
site = pd.concat([d[cols], w[cols]], ignore_index=True).sort_values(["State", "District", "Season", "Crop"])
site["MeanShare"] = site["MeanShare"].round(4)
site.to_csv("data/processed/crop_site_table.csv", index=False)
print("\nStatus counts by state:")
print(site.groupby(["State", "Status"]).size().to_string())

ex = site[site["Status"] == "Climate suits, not major now"].sort_values("P_lodo", ascending=False)
print("\n'Climate suits, not major now' (trusted crops only):", len(ex), "cases. Top 20:")
print(ex.head(20)[["State", "District", "Item", "MeanShare", "P_lodo"]].to_string(index=False))
print("\nBy crop:")
print(ex.groupby("Item").size().sort_values(ascending=False).to_string())
print("Saved data/processed/crop_site_table.csv")