import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import make_scorer
from sklearn.model_selection import RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("data/processed/yield_model_table.csv")
keys = ["State", "District", "Crop", "Season"]
CAT = keys
NUM = ["Crop_Year", "Rain_Annual_Normal", "Rain_JunSep_Normal"]

d = df[df["Crop_Year"] <= 2016].reset_index(drop=True)
test = df[df["Crop_Year"] >= 2017].reset_index(drop=True)
print("Rows for tuning and training:", len(d), "| test rows (kept aside):", len(test))


def med_ape(y, p):
    return float(np.median(np.abs(p - y) / y))


def build(model):
    prep = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
        ("num", StandardScaler(), NUM),
    ])
    pipe = Pipeline([("prep", prep), ("model", model)])
    return TransformedTargetRegressor(regressor=pipe, func=np.log, inverse_func=np.exp)


folds = [(np.where(d["Crop_Year"] < yr)[0], np.where(d["Crop_Year"] == yr)[0]) for yr in range(2012, 2017)]
space = {
    "regressor__model__n_estimators": [100, 200, 300],
    "regressor__model__min_samples_leaf": [1, 2, 3, 5, 8],
    "regressor__model__max_features": [0.3, 0.5, 0.7, 1.0],
    "regressor__model__max_depth": [None, 12, 20],
}
search = RandomizedSearchCV(
    build(RandomForestRegressor(random_state=42, n_jobs=-1)), space, n_iter=20, cv=folds,
    scoring=make_scorer(med_ape, greater_is_better=False), random_state=42, n_jobs=1)
print("Searching 20 settings over 5 rolling years. This takes a few minutes...")
search.fit(d[CAT + NUM], d["Yield"])

res = pd.DataFrame(search.cv_results_)
res["Median error %"] = (-res["mean_test_score"] * 100).round(2)
cols = ["Median error %"] + [c for c in res.columns if c.startswith("param_")]
top = res.sort_values("Median error %")[cols].head(5)
top.columns = [c.replace("param_regressor__model__", "") for c in top.columns]
print("\nBest 5 settings (rolling years 2012 to 2016):")
print(top.to_string(index=False))
print("Best settings:", search.best_params_)
best = search.best_estimator_

# Error range from the rolling years, for the 'likely range' on the website
log_err, crops = [], []
for tr_i, te_i in folds:
    m = clone(best).fit(d.loc[tr_i, CAT + NUM], d.loc[tr_i, "Yield"])
    p = m.predict(d.loc[te_i, CAT + NUM])
    log_err.extend(np.log(d.loc[te_i, "Yield"].to_numpy()) - np.log(p))
    crops.extend(d.loc[te_i, "Crop"].tolist())
err = pd.DataFrame({"Crop": crops, "e": log_err})
band_all = {"q10": float(err["e"].quantile(0.10)), "q90": float(err["e"].quantile(0.90))}
band_crop = {}
for crop, g in err.groupby("Crop"):
    if len(g) >= 30:
        band_crop[crop] = {"q10": float(g["e"].quantile(0.10)), "q90": float(g["e"].quantile(0.90))}
print("\nShare of rolling-year results inside the 10 to 90 range:",
      round(100 * ((err["e"] >= band_all["q10"]) & (err["e"] <= band_all["q90"])).mean(), 1), "%")

# Final check on the test years, looked at once
full = df.copy()
base = full[keys + ["Crop_Year", "Yield"]]
for k in (1, 2, 3):
    p = base.copy()
    p["Crop_Year"] = p["Crop_Year"] + k
    full = full.merge(p.rename(columns={"Yield": f"prev{k}"}), on=keys + ["Crop_Year"], how="left")
full["prev_mean"] = full[["prev1", "prev2", "prev3"]].mean(axis=1)
full["prev1"] = full["prev1"].fillna(full["prev_mean"])
full = full[full["Crop_Year"] >= 2017].reset_index(drop=True)

med = d.groupby(["Crop", "District"])["Yield"].median().rename("pred").reset_index()
crop_med = d.groupby("Crop")["Yield"].median()


def rule_cd(frame):
    pr = frame[["Crop", "District"]].merge(med, on=["Crop", "District"], how="left")["pred"].to_numpy()
    return np.where(np.isnan(pr), frame["Crop"].map(crop_med).to_numpy(), pr)


def line(name, y, p):
    ape = np.abs(p - y) / y
    return {"Method": name, "Rows": len(y), "Median error %": round(100 * np.median(ape), 1),
            "Within 25%": round(100 * (ape <= 0.25).mean(), 1)}


y_all = test["Yield"].to_numpy()
rows = [line("Forest, all test rows", y_all, best.predict(test[CAT + NUM])),
        line("Rule crop and district median, all test rows", y_all, rule_cd(test))]
h = full[full["prev_mean"].notna()]
y_h = h["Yield"].to_numpy()
rows += [line("Forest, rows with history", y_h, best.predict(h[CAT + NUM])),
         line("Rule same as last year, rows with history", y_h, h["prev1"].to_numpy()),
         line("Rule mean of last 3 years, rows with history", y_h, h["prev_mean"].to_numpy())]
test_table = pd.DataFrame(rows)
print("\nTEST 2017 to 2019 (looked at once):")
print(test_table.to_string(index=False))

os.makedirs("models", exist_ok=True)
bundle = {"model": best, "cat": CAT, "num": NUM, "band_all": band_all, "band_crop": band_crop,
          "trained_through": 2016, "crops": sorted(d["Crop"].unique().tolist()),
          "best_params": {k: (None if v is None else v) for k, v in search.best_params_.items()}}
joblib.dump(bundle, "models/yield_model.joblib", compress=3)
print("\nSaved models/yield_model.joblib,", round(os.path.getsize("models/yield_model.joblib") / 1e6, 1), "MB")

metrics = {"best_params": {k: (None if v is None else float(v) if isinstance(v, float) else int(v))
                           for k, v in search.best_params_.items()},
           "cv_best_median_error_pct": float(res["Median error %"].min()),
           "band_all": band_all, "band_crop": band_crop,
           "test": test_table.to_dict(orient="records")}
with open("models/yield_metrics.json", "w", encoding="utf-8") as fh:
    json.dump(metrics, fh, indent=1)
print("Saved models/yield_metrics.json")