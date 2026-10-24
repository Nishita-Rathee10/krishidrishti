import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("data/processed/yield_model_table.csv")
keys = ["State", "District", "Crop", "Season"]

# Yield of the same district, crop and season 1, 2 and 3 years earlier
base = df[keys + ["Crop_Year", "Yield"]]
for k in (1, 2, 3):
    p = base.copy()
    p["Crop_Year"] = p["Crop_Year"] + k
    p = p.rename(columns={"Yield": f"prev{k}"})
    df = df.merge(p, on=keys + ["Crop_Year"], how="left")

df["prev_mean"] = df[["prev1", "prev2", "prev3"]].mean(axis=1)
have = df["prev_mean"].notna()
print("Rows with at least one earlier year:", int(have.sum()), "of", len(df))
df = df[have].copy()
df["prev1"] = df["prev1"].fillna(df["prev_mean"])
df["log_prev1"] = np.log(df["prev1"])
df["log_prev_mean"] = np.log(df["prev_mean"])

train = df[df["Split"] == "train"].reset_index(drop=True)
valid = df[df["Split"] == "validation"].reset_index(drop=True)
print("Train rows:", len(train), "| Validation rows:", len(valid))

CAT = ["State", "District", "Crop", "Season"]
NUM_A = ["Crop_Year", "Rain_Annual_Normal", "Rain_JunSep_Normal"]
NUM_B = NUM_A + ["log_prev1", "log_prev_mean"]


def scores(y_true, y_pred):
    ape = np.abs(y_pred - y_true) / y_true
    return {"Median error %": round(100 * np.median(ape), 1),
            "Mean error %": round(100 * ape.mean(), 1),
            "Within 25% of real": round(100 * (ape <= 0.25).mean(), 1)}


def make(model, num):
    prep = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
        ("num", StandardScaler(), num),
    ])
    return Pipeline([("prep", prep), ("model", model)])


y_valid = valid["Yield"].to_numpy()
rows = []
rows.append(("Rule: same as last year", scores(y_valid, valid["prev1"].to_numpy())))
rows.append(("Rule: mean of last 3 years", scores(y_valid, valid["prev_mean"].to_numpy())))
med = train.groupby(["Crop", "District"])["Yield"].median().rename("pred").reset_index()
pred = valid[["Crop", "District"]].merge(med, on=["Crop", "District"], how="left")["pred"].to_numpy()
pred = np.where(np.isnan(pred), valid["prev_mean"].to_numpy(), pred)
rows.append(("Rule: crop and district median", scores(y_valid, pred)))

y_log = np.log(train["Yield"])
for label, num in (("without history", NUM_A), ("with history", NUM_B)):
    for name, model in (
        ("Random forest", RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1)),
        ("Gradient boosting", HistGradientBoostingRegressor(random_state=42)),
    ):
        pipe = make(model, num).fit(train[CAT + num], y_log)
        p = np.exp(pipe.predict(valid[CAT + num]))
        rows.append((f"{name} {label}", scores(y_valid, p)))

table = pd.DataFrame([{"Method": n, **s} for n, s in rows]).sort_values("Median error %")
print("\nVALIDATION (2015 to 2016), same rows for every method:")
print(table.to_string(index=False))