import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("data/processed/yield_model_table.csv")
train = df[df["Split"] == "train"].reset_index(drop=True)
valid = df[df["Split"] == "validation"].reset_index(drop=True)
test = df[df["Split"] == "test"].reset_index(drop=True)

CAT = ["State", "District", "Crop", "Season"]
NUM = ["Crop_Year", "Rain_Annual_Normal", "Rain_JunSep_Normal"]


def scores(y_true, y_pred):
    ape = np.abs(y_pred - y_true) / y_true
    return {"Median error %": round(100 * np.median(ape), 1),
            "Mean error %": round(100 * ape.mean(), 1),
            "Within 25% of real": round(100 * (ape <= 0.25).mean(), 1)}


def baseline(frame, keys):
    med = train.groupby(keys)["Yield"].median().rename("pred").reset_index()
    pred = frame[keys].merge(med, on=keys, how="left")["pred"].to_numpy()
    crop_med = frame["Crop"].map(train.groupby("Crop")["Yield"].median()).to_numpy()
    return np.where(np.isnan(pred), crop_med, pred)


def make(model):
    prep = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
        ("num", StandardScaler(), NUM),
    ])
    return Pipeline([("prep", prep), ("model", model)])


MODELS = {
    "Linear regression": LinearRegression(),
    "Ridge": Ridge(alpha=1.0),
    "Random forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1),
    "Gradient boosting": HistGradientBoostingRegressor(random_state=42),
}

rows = []
rows.append(("Rule: crop median", scores(valid["Yield"].to_numpy(), baseline(valid, ["Crop"]))))
rows.append(("Rule: crop and state median", scores(valid["Yield"].to_numpy(), baseline(valid, ["Crop", "State"]))))
rows.append(("Rule: crop and district median", scores(valid["Yield"].to_numpy(), baseline(valid, ["Crop", "District"]))))

fitted = {}
y_log = np.log(train["Yield"])
for name, model in MODELS.items():
    pipe = make(model).fit(train[CAT + NUM], y_log)
    fitted[name] = pipe
    pred = np.exp(pipe.predict(valid[CAT + NUM]))
    rows.append((name, scores(valid["Yield"].to_numpy(), pred)))

table = pd.DataFrame([{"Method": n, **s} for n, s in rows]).sort_values("Median error %")
print("VALIDATION (2015 to 2016), lower error is better:")
print(table.to_string(index=False))

best = min(MODELS, key=lambda n: scores(valid["Yield"].to_numpy(), np.exp(fitted[n].predict(valid[CAT + NUM])))["Median error %"])
print("\nBest model on validation:", best)

y_test = test["Yield"].to_numpy()
best_pred = np.exp(fitted[best].predict(test[CAT + NUM]))
rule_pred = baseline(test, ["Crop", "District"])
print("\nTEST (2017 to 2019), looked at once:")
print(pd.DataFrame([{"Method": best, **scores(y_test, best_pred)},
                    {"Method": "Rule: crop and district median", **scores(y_test, rule_pred)}]).to_string(index=False))

t = test.copy()
t["model_err"] = np.abs(best_pred - y_test) / y_test * 100
t["rule_err"] = np.abs(rule_pred - y_test) / y_test * 100
print("\nMedian error % by crop on test (model, rule):")
print(t.groupby("Crop")[["model_err", "rule_err"]].median().round(1).to_string())