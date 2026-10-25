import warnings

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")

df = pd.read_csv("data/processed/crop_suitability_table.csv")
df["Item"] = df["Crop"] + " (" + df["Season"] + ")"
NUM = [c for c in df.columns if c.startswith(("T_", "RH_", "Rain_"))]
CAT = ["Item"]

st = df.groupby("Item")["Major"].agg(pos="sum", n="count")
st["neg"] = st["n"] - st["pos"]
widely = st[st["neg"] < 3].index.tolist()
rare = st[st["pos"] < 3].index.tolist()
keep = st[(st["pos"] >= 3) & (st["neg"] >= 3)].index.tolist()
print("Widely grown, no model needed:", widely)
print("Rarely a major crop, not enough evidence:", rare)
print("Crops used for modelling:", len(keep))
d = df[df["Item"].isin(keep)].reset_index(drop=True)
print("Rows:", len(d), "| districts:", d["District"].nunique(), "| share Major:", round(100 * d["Major"].mean(), 1), "%")


def make(model):
    prep = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
                              ("num", StandardScaler(), NUM)])
    return Pipeline([("prep", prep), ("model", model)])


def p_crop(tr, te):
    m = tr.groupby("Item")["Major"].mean()
    return te["Item"].map(m).fillna(tr["Major"].mean()).to_numpy()


def p_crop_state(tr, te):
    m = tr.groupby(["Item", "State"])["Major"].mean()
    base = p_crop(tr, te)
    return np.array([m.get(k, b) for k, b in zip(zip(te["Item"], te["State"]), base)])


def p_logit(tr, te):
    out, base = np.zeros(len(te)), p_crop(tr, te)
    for item in te["Item"].unique():
        a = tr[tr["Item"] == item]
        mask = (te["Item"] == item).to_numpy()
        if a["Major"].nunique() < 2:
            out[mask] = base[mask]
            continue
        sc = StandardScaler().fit(a[NUM])
        lr = LogisticRegression(C=0.5, max_iter=2000).fit(sc.transform(a[NUM]), a["Major"])
        out[mask] = lr.predict_proba(sc.transform(te.loc[mask, NUM]))[:, 1]
    return out


def p_shared(model):
    def f(tr, te):
        return make(model).fit(tr[CAT + NUM], tr["Major"]).predict_proba(te[CAT + NUM])[:, 1]
    return f


MODELS = {
    "Baseline: crop chalan": p_crop,
    "Baseline: crop x state chalan": p_crop_state,
    "Logistic per crop": p_logit,
    "Random forest": p_shared(RandomForestClassifier(n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1)),
    "Gradient boosting": p_shared(GradientBoostingClassifier(n_estimators=150, max_depth=2, learning_rate=0.05, random_state=42)),
}


def folds_for(seed):
    rng = np.random.RandomState(seed)
    ds = rng.permutation(d["District"].unique())
    m = {x: i % 5 for i, x in enumerate(ds)}
    return d["District"].map(m).to_numpy()


def score(p):
    y = d["Major"].to_numpy()
    pred = (p >= 0.5).astype(int)
    per = {}
    for item, g in d.assign(p=p).groupby("Item"):
        if g["Major"].nunique() == 2:
            per[item] = roc_auc_score(g["Major"], g["p"])
    return {"AUC within crop": float(np.mean(list(per.values()))), "PR-AUC": average_precision_score(y, p),
            "F1": f1_score(y, pred), "Precision": precision_score(y, pred, zero_division=0),
            "Recall": recall_score(y, pred)}, per


SEEDS = range(5)
res = {n: [] for n in MODELS}
per_item = {n: [] for n in MODELS}
print("\nRunning 5 repeats of 5-fold district-wise checks. About 1 to 3 minutes...")
for seed in SEEDS:
    fa = folds_for(seed)
    for name, fn in MODELS.items():
        p = np.zeros(len(d))
        for f in range(5):
            tr, te = d[fa != f], d[fa == f]
            p[(fa == f)] = fn(tr, te)
        s, per = score(p)
        res[name].append(s)
        per_item[name].append(per)

rows = []
for n, lst in res.items():
    t = pd.DataFrame(lst)
    rows.append({"Model": n, **{c: f"{t[c].mean():.3f} +/- {t[c].std():.3f}" for c in t.columns}})
print("\nResults (mean +/- spread over 5 repeats, districts never seen in training):")
print(pd.DataFrame(rows).to_string(index=False))

print("\nRule check against 'Baseline: crop x state chalan' (needs +0.03 and 4 of 5 repeats):")
ref = np.array([r["AUC within crop"] for r in res["Baseline: crop x state chalan"]])
for n in ["Logistic per crop", "Random forest", "Gradient boosting"]:
    a = np.array([r["AUC within crop"] for r in res[n]])
    verdict = "PASSES" if (a - ref).mean() >= 0.03 and (a > ref).sum() >= 4 else "does not pass"
    print(f"  {n}: difference {np.mean(a - ref):+.3f}, better in {(a > ref).sum()} of 5 -> {verdict}")

print("\nWithin-crop AUC by crop (average over repeats):")
items = sorted(per_item["Random forest"][0].keys())
tab = pd.DataFrame({"Major districts": [int(st.loc[i, "pos"]) for i in items]}, index=items)
for n in ["Baseline: crop x state chalan", "Logistic per crop", "Random forest", "Gradient boosting"]:
    tab[n] = [np.mean([r.get(i, np.nan) for r in per_item[n]]) for i in items]
print(tab.round(2).to_string())