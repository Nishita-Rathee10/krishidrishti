import json
import os
import sys
import warnings

import joblib
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
rare = st[st["pos"] < 3].index.tolist()
keep = st[(st["pos"] >= 3) & (st["neg"] >= 3)].index.tolist()
d = df[df["Item"].isin(keep)].reset_index(drop=True)
print("Rows:", len(d), "| crops:", len(keep), "| districts:", d["District"].nunique())


def macro_auc(p):
    v = [roc_auc_score(g["Major"], g["p"]) for _, g in d.assign(p=p).groupby("Item")
         if g["Major"].nunique() == 2]
    return float(np.mean(v))


def folds_for(seed):
    ds = np.random.RandomState(seed).permutation(d["District"].unique())
    m = {x: i % 5 for i, x in enumerate(ds)}
    return d["District"].map(m).to_numpy()


# 1. Final choice of settings (3 repeats of district-wise 5-fold checks on all 44 districts)
print("\nChoosing final settings. About 2 minutes...")
logit_opts = [0.1, 0.3, 1.0, 3.0]
rf_opts = [(leaf, mf) for leaf in (1, 3, 5) for mf in (0.6, 1.0)]
score_l = {c: [] for c in logit_opts}
score_r = {o: [] for o in rf_opts}
for seed in range(3):
    fa = folds_for(seed)
    for c in logit_opts:
        p = np.zeros(len(d))
        for f in range(5):
            p[fa == f] = CropEnsemble(NUM, C=c).fit_logit(d[fa != f]).p_logit(d[fa == f])
        score_l[c].append(macro_auc(p))
    for o in rf_opts:
        p = np.zeros(len(d))
        for f in range(5):
            p[fa == f] = CropEnsemble(NUM, leaf=o[0], max_features=o[1]).fit_rf(d[fa != f]).p_rf(d[fa == f])
        score_r[o].append(macro_auc(p))
best_c = max(logit_opts, key=lambda c: np.mean(score_l[c]))
best_rf = max(rf_opts, key=lambda o: np.mean(score_r[o]))
print("Logistic C:", {c: round(float(np.mean(v)), 3) for c, v in score_l.items()}, "-> chosen", best_c)
print("Forest (leaf, max_features):", {o: round(float(np.mean(v)), 3) for o, v in score_r.items()},
      "-> chosen", best_rf)
params = {"C": best_c, "leaf": best_rf[0], "max_features": best_rf[1]}

# 2. Out-of-district predictions with the final settings (each row predicted without its district)
P = np.zeros((5, len(d)))
for seed in range(5):
    fa = folds_for(seed)
    for f in range(5):
        P[seed, fa == f] = CropEnsemble(NUM, **params).fit(d[fa != f]).predict_proba(d[fa == f])
d["P_suitable"] = P.mean(axis=0).round(3)
aucs = [macro_auc(P[s]) for s in range(5)]
print("\nWithin-crop AUC per repeat:", [round(a, 3) for a in aucs], "| mean", round(float(np.mean(aucs)), 3),
      "(a little optimistic, because settings were chosen on the same districts)")

# 3. Calibration: do the percentages mean what they say?
bins = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0001]
d["Bin"] = pd.cut(d["P_suitable"], bins, right=False)
cal = d.groupby("Bin", observed=True).agg(Rows=("Major", "size"), Mean_predicted=("P_suitable", "mean"),
                                          Actual_major_rate=("Major", "mean")).round(2)
print("\nCalibration (predicted chance vs how often it was really a major crop):")
print(cal.to_string())
brier = brier_score_loss(d["Major"], d["P_suitable"])
brier_base = brier_score_loss(d["Major"], np.full(len(d), d["Major"].mean()))
print(f"Brier score {brier:.3f} (lower is better; always guessing the average gives {brier_base:.3f})")

# 4. Table for the website and the explore list
out = d[["State", "District", "Season", "Crop", "Item", "MeanShare", "Major", "P_suitable"]]
out.to_csv("data/processed/crop_suitability_predictions.csv", index=False)
print("\nTop 15 'climate suits, but not a major crop now' (check if they make sense):")
cand = out[out["Major"] == 0].sort_values("P_suitable", ascending=False).head(15)
print(cand.to_string(index=False))

# 5. Save the final model, fitted on all 44 districts
model = CropEnsemble(NUM, **params).fit(d)
os.makedirs("models", exist_ok=True)
bundle = {"model": model, "num": NUM, "items": keep, "widely_grown": widely, "rare": rare,
          "params": params, "within_crop_auc_oof": float(np.mean(aucs)), "brier": float(brier)}
joblib.dump(bundle, "models/crop_model.joblib", compress=3)
print("\nSaved models/crop_model.joblib,", round(os.path.getsize("models/crop_model.joblib") / 1e6, 2), "MB")
with open("models/crop_metrics.json", "w", encoding="utf-8") as fh:
    json.dump({"params": params, "within_crop_auc_oof": float(np.mean(aucs)), "brier": float(brier),
               "brier_always_average": float(brier_base), "widely_grown": widely, "rare": rare,
               "calibration": cal.reset_index().astype(str).to_dict(orient="records")}, fh, indent=1)
print("Saved models/crop_metrics.json and data/processed/crop_suitability_predictions.csv")