import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("data/processed/yield_model_table.csv")
keys = ["State", "District", "Crop", "Season"]

base = df[keys + ["Crop_Year", "Yield"]]
for k in (1, 2, 3):
    p = base.copy()
    p["Crop_Year"] = p["Crop_Year"] + k
    p = p.rename(columns={"Yield": f"prev{k}"})
    df = df.merge(p, on=keys + ["Crop_Year"], how="left")

df["prev_mean"] = df[["prev1", "prev2", "prev3"]].mean(axis=1)
df = df[df["prev_mean"].notna()].copy()
df["prev1"] = df["prev1"].fillna(df["prev_mean"])
df["log_prev_mean"] = np.log(df["prev_mean"])
df["delta1"] = np.log(df["prev1"]) - df["log_prev_mean"]

# The test years (2017 to 2019) are not used anywhere in this script
df = df[df["Crop_Year"] <= 2016].copy()
print("Rows used:", len(df))

CAT = ["State", "District", "Crop", "Season"]
NUM_A = ["Crop_Year", "Rain_Annual_Normal", "Rain_JunSep_Normal"]
NUM_R = NUM_A + ["log_prev_mean", "delta1"]


def med_err(y, p):
    return 100 * np.median(np.abs(p - y) / y)


def make(model, num):
    prep = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
        ("num", StandardScaler(), num),
    ])
    return Pipeline([("prep", prep), ("model", model)])


def forest():
    return RandomForestRegressor(n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=-1)


methods = ["Rule: mean of last 3 years", "Rule: same as last year", "Random forest direct",
           "Random forest on change", "Gradient boosting on change", "Ridge on change"]
res = {m: [] for m in methods}
years = list(range(2010, 2017))

for year in years:
    tr = df[df["Crop_Year"] < year]
    te = df[df["Crop_Year"] == year]
    y = te["Yield"].to_numpy()
    res["Rule: mean of last 3 years"].append(med_err(y, te["prev_mean"].to_numpy()))
    res["Rule: same as last year"].append(med_err(y, te["prev1"].to_numpy()))

    pipe = make(forest(), NUM_A).fit(tr[CAT + NUM_A], np.log(tr["Yield"]))
    res["Random forest direct"].append(med_err(y, np.exp(pipe.predict(te[CAT + NUM_A]))))

    target = np.log(tr["Yield"]) - tr["log_prev_mean"]
    for name, model in (("Random forest on change", forest()),
                        ("Gradient boosting on change", HistGradientBoostingRegressor(random_state=42)),
                        ("Ridge on change", Ridge(alpha=10.0))):
        pipe = make(model, NUM_R).fit(tr[CAT + NUM_R], target)
        pred = te["prev_mean"].to_numpy() * np.exp(pipe.predict(te[CAT + NUM_R]))
        res[name].append(med_err(y, pred))

rule = np.array(res["Rule: mean of last 3 years"])
out = []
for m in methods:
    a = np.array(res[m])
    out.append({"Method": m, "Average median error %": round(a.mean(), 1),
                "Worst year %": round(a.max(), 1),
                "Years better than 3-year rule": int((a < rule).sum())})
print("\nAcross 7 rolling years (2010 to 2016), lower error is better:")
print(pd.DataFrame(out).sort_values("Average median error %").to_string(index=False))
print("\nMedian error % in each year:")
print(pd.DataFrame(res, index=years).round(1).to_string())