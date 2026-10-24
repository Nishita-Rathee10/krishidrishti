import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
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

# Rainfall of the real year compared with normal, for each region
rain = pd.read_csv("data/processed/rain_monthly_ph.csv")
rain["Part"] = np.select(
    [rain["Month"].between(6, 9), rain["Month"] >= 10, rain["Month"] <= 3],
    ["JunSep", "OctDec", "JanMar"], default="AprMay")
parts = rain.pivot_table(index=["Region", "Year"], columns="Part", values="Rain_mm", aggfunc="sum").reset_index()
norm = parts[parts["Year"].between(1986, 2015)].groupby("Region")[["JunSep", "OctDec", "JanMar"]].mean()
norm.columns = [c + "_norm" for c in norm.columns]
parts = parts.merge(norm, left_on="Region", right_index=True)
nxt = parts[["Region", "Year", "JanMar"]].copy()
nxt["Year"] = nxt["Year"] - 1
nxt = nxt.rename(columns={"JanMar": "JanMar_next"})
parts = parts.merge(nxt, on=["Region", "Year"], how="left")
parts["a_kharif"] = parts["JunSep"] / parts["JunSep_norm"] - 1
parts["a_rabi"] = (parts["OctDec"] + parts["JanMar_next"]) / (parts["OctDec_norm"] + parts["JanMar_norm"]) - 1
print("Rainfall compared with normal (0.10 means 10 percent above), 2008 to 2015:")
print(parts[parts["Year"].between(2008, 2015)][["Region", "Year", "a_kharif", "a_rabi"]].round(2).to_string(index=False))

REGION = {"Punjab": "Punjab", "Haryana": "Haryana, Delhi and Chandigarh"}
df["Region"] = df["State"].map(REGION)
df = df.merge(parts[["Region", "Year", "a_kharif", "a_rabi"]],
              left_on=["Region", "Crop_Year"], right_on=["Region", "Year"], how="left")
df = df[df["a_rabi"].notna()].copy()
print("\nRows used:", len(df), "| years", df["Crop_Year"].min(), "to", df["Crop_Year"].max())

CAT = ["State", "District", "Crop", "Season"]
NUM_A = ["Crop_Year", "Rain_Annual_Normal", "Rain_JunSep_Normal"]
NUM_W = NUM_A + ["a_kharif", "a_rabi"]
NUM_RW = NUM_W + ["log_prev_mean", "delta1"]


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


methods = ["Rule: mean of last 3 years", "Rule: same as last year",
           "Random forest, no weather of the year", "Random forest, with weather of the year",
           "Gradient boosting, with weather of the year", "Random forest on change, with weather"]
res = {m: [] for m in methods}
years = list(range(2008, 2015))

for year in years:
    tr = df[df["Crop_Year"] < year]
    te = df[df["Crop_Year"] == year]
    y = te["Yield"].to_numpy()
    res[methods[0]].append(med_err(y, te["prev_mean"].to_numpy()))
    res[methods[1]].append(med_err(y, te["prev1"].to_numpy()))
    for name, model, num in ((methods[2], forest(), NUM_A), (methods[3], forest(), NUM_W),
                             (methods[4], HistGradientBoostingRegressor(random_state=42), NUM_W)):
        pipe = make(model, num).fit(tr[CAT + num], np.log(tr["Yield"]))
        res[name].append(med_err(y, np.exp(pipe.predict(te[CAT + num]))))
    target = np.log(tr["Yield"]) - tr["log_prev_mean"]
    pipe = make(forest(), NUM_RW).fit(tr[CAT + NUM_RW], target)
    pred = te["prev_mean"].to_numpy() * np.exp(pipe.predict(te[CAT + NUM_RW]))
    res[methods[5]].append(med_err(y, pred))

without = np.array(res[methods[2]])
out = []
for m in methods:
    a = np.array(res[m])
    out.append({"Method": m, "Average median error %": round(a.mean(), 1),
                "Worst year %": round(a.max(), 1),
                "Years better than forest without weather": int((a < without).sum())})
print("\nAcross 7 rolling years (2008 to 2014):")
print(pd.DataFrame(out).sort_values("Average median error %").to_string(index=False))
print("\nMedian error % in each year:")
print(pd.DataFrame(res, index=years).round(1).to_string())