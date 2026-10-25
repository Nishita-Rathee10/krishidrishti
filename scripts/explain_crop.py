import json
import os
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from lime.lime_tabular import LimeTabularExplainer

sys.path.insert(0, os.getcwd())
from croplib import CropEnsemble  # noqa: E402

warnings.filterwarnings("ignore")

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
print("Trusted crops:", trusted)

# 1. SHAP on the forest part of the final model
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
imp = pd.DataFrame({"f": group, "v": np.abs(sv1).mean(axis=0)}).groupby("f")["v"].sum().sort_values()
print("\nSHAP: average size of push on the answer (forest part, all rows):")
print(imp.sort_values(ascending=False).round(3).to_string())
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.barh(imp.index, imp.values, color="#2f6b4f")
ax.set_xlabel("Average push on the forest answer (SHAP)")
plt.tight_layout()
os.makedirs("reports/figures", exist_ok=True)
plt.savefig("reports/figures/06_shap_importance.png", dpi=130)
plt.close()
print("Saved reports/figures/06_shap_importance.png")

num_idx = [i for i, n in enumerate(names) if not n.startswith("Item_")]
print("\nSHAP: top 3 weather features for each trusted crop (forest part):")
for item in trusted:
    m = (d["Item"] == item).to_numpy()
    v = np.abs(sv1[m][:, num_idx]).mean(axis=0)
    top = np.argsort(-v)[:3]
    print(f"  {item}: " + ", ".join(f"{names[num_idx[j]]} ({v[j]:.3f})" for j in top))


def fn_ensemble(model, item):
    def fn(A):
        t = pd.DataFrame(A, columns=NUM)
        t["Item"] = item
        p = model.predict_proba(t)
        return np.column_stack([1 - p, p])
    return fn


def fn_forest(model, item):
    def fn(A):
        t = pd.DataFrame(A, columns=NUM)
        t["Item"] = item
        p = model.p_rf(t)
        return np.column_stack([1 - p, p])
    return fn


def lime_explainer(train_x):
    return LimeTabularExplainer(train_x, feature_names=NUM, class_names=["not major", "major"],
                                mode="classification", random_state=0)


# 2. LIME reasons, each district explained by a model that never saw it
rows = []
dists = d["District"].unique()
print("\nLIME for every district and trusted crop. About 2 to 4 minutes...")
for i, dist in enumerate(dists, 1):
    mask = (d["District"] == dist).to_numpy()
    model = CropEnsemble(NUM, **params).fit(d[~mask])
    te = d[mask]
    for _, r in te[te["Item"].isin(trusted)].iterrows():
        item = r["Item"]
        train_x = d.loc[~mask & (d["Item"] == item).to_numpy(), NUM].to_numpy()
        exp = lime_explainer(train_x).explain_instance(r[NUM].to_numpy(dtype=float), fn_ensemble(model, item),
                                                       num_features=3, num_samples=1000)
        for rank, ((idx, w), (rule, _)) in enumerate(zip(exp.as_map()[1], exp.as_list(label=1)), start=1):
            rows.append({"State": r["State"], "District": dist, "Item": item, "Rank": rank,
                         "Feature": NUM[idx], "Rule": rule, "Weight": round(float(w), 4),
                         "District_value": round(float(r[NUM[idx]]), 2)})
    if i % 11 == 0:
        print(f"  {i}/{len(dists)} districts done")
reasons = pd.DataFrame(rows)
reasons.to_csv("data/processed/crop_reasons.csv", index=False)
print("Saved data/processed/crop_reasons.csv with", len(reasons), "rows")
print("\nMost common top-1 reason per trusted crop (LIME):")
print(reasons[reasons["Rank"] == 1].groupby(["Item", "Feature"]).size().rename("Cases").reset_index()
      .sort_values(["Item", "Cases"], ascending=[True, False]).groupby("Item").head(2).to_string(index=False))

# 3. Do SHAP and LIME agree? (forest part only, 40 random trusted rows)
sample = d[d["Item"].isin(trusted)].sample(40, random_state=0)
overlap = []
for ix, r in sample.iterrows():
    item = r["Item"]
    train_x = d.loc[d["Item"] == item, NUM].to_numpy()
    exp = lime_explainer(train_x).explain_instance(r[NUM].to_numpy(dtype=float), fn_forest(full, item),
                                                   num_features=3, num_samples=1000)
    lime_top = {NUM[i] for i, _ in exp.as_map()[1]}
    row = sv1[ix][num_idx]
    shap_top = {names[num_idx[j]] for j in np.argsort(-np.abs(row))[:3]}
    overlap.append(len(lime_top & shap_top))
overlap = np.array(overlap)
print("\nSHAP vs LIME top-3 agreement on 40 cases (forest part):")
print("  average number of shared features out of 3:", round(float(overlap.mean()), 2))
print("  cases sharing at least 2 of 3:", round(100 * float((overlap >= 2).mean()), 1), "%")
print("  cases sharing none:", round(100 * float((overlap == 0).mean()), 1), "%")