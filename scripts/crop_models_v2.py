import warnings
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
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
keep = st[(st["pos"] >= 3) & (st["neg"] >= 3)].index.tolist()
d = df[df["Item"].isin(keep)].copy()
coords = pd.read_csv("data/processed/district_coords.csv")[["State", "District", "Lat", "Lon"]]
d = d.merge(coords, on=["State", "District"], how="left").reset_index(drop=True)
assert d["Lat"].notna().all()
print("Rows:", len(d), "| crops:", len(keep), "| districts:", d["District"].nunique())


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


def p_logit(C):
    def f(tr, te):
        out, base = np.zeros(len(te)), p_crop(tr, te)
        for item in te["Item"].unique():
            a = tr[tr["Item"] == item]
            mask = (te["Item"] == item).to_numpy()
            if a["Major"].nunique() < 2:
                out[mask] = base[mask]
                continue
            sc = StandardScaler().fit(a[NUM])
            lr = LogisticRegression(C=C, max_iter=2000).fit(sc.transform(a[NUM]), a["Major"])
            out[mask] = lr.predict_proba(sc.transform(te.loc[mask, NUM]))[:, 1]
        return out
    return f


def p_rf(leaf, mf):
    def f(tr, te):
        rf = RandomForestClassifier(n_estimators=200, min_samples_leaf=leaf, max_features=mf,
                                    random_state=42, n_jobs=-1)
        return make(rf).fit(tr[CAT + NUM], tr["Major"]).predict_proba(te[CAT + NUM])[:, 1]
    return f


LOGIT_OPTS = {f"C={c}": p_logit(c) for c in [0.05, 0.1, 0.3, 1, 3]}
RF_OPTS = {f"leaf={l}, max_features={mf}": p_rf(l, mf) for l in [1, 3, 5] for mf in [0.3, 0.6, 1.0]}


def macro_auc(frame, p):
    v = []
    for _, g in frame.assign(p=p).groupby("Item"):
        if g["Major"].nunique() == 2:
            v.append(roc_auc_score(g["Major"], g["p"]))
    return float(np.mean(v)) if v else 0.5


def score(p):
    y = d["Major"].to_numpy()
    pred = (p >= 0.5).astype(int)
    return {"AUC within crop": macro_auc(d, p), "PR-AUC": average_precision_score(y, p),
            "F1": f1_score(y, pred), "Precision": precision_score(y, pred, zero_division=0),
            "Recall": recall_score(y, pred)}


def inner_pick(tr, options, seed):
    tr = tr.reset_index(drop=True)
    ds = np.random.RandomState(seed).permutation(tr["District"].unique())
    m = {x: i % 3 for i, x in enumerate(ds)}
    fa = tr["District"].map(m).to_numpy()
    best, best_s = None, -1.0
    for name, fn in options.items():
        p = np.zeros(len(tr))
        for f in range(3):
            p[fa == f] = fn(tr[fa != f], tr[fa == f])
        s = macro_auc(tr, p)
        if s > best_s:
            best, best_s = name, s
    return best


def folds_for(seed):
    ds = np.random.RandomState(seed).permutation(d["District"].unique())
    m = {x: i % 5 for i, x in enumerate(ds)}
    return d["District"].map(m).to_numpy()


NAMES = ["Baseline: crop x state chalan", "Logistic C=0.5 (v1)", "Logistic tuned", "Random forest tuned",
         "Average of both tuned"]
res = {n: [] for n in NAMES}
pick_l, pick_r = Counter(), Counter()
print("\nNested tuning, 5 repeats x 5 folds. About 5 to 10 minutes. Please do not close the terminal.")
for seed in range(5):
    fa = folds_for(seed)
    P = {n: np.zeros(len(d)) for n in NAMES}
    for f in range(5):
        tr, te, msk = d[fa != f], d[fa == f], (fa == f)
        P[NAMES[0]][msk] = p_crop_state(tr, te)
        P[NAMES[1]][msk] = p_logit(0.5)(tr, te)
        nl = inner_pick(tr, LOGIT_OPTS, seed * 10 + f)
        nr = inner_pick(tr, RF_OPTS, seed * 10 + f)
        pick_l[nl] += 1
        pick_r[nr] += 1
        pl, pr = LOGIT_OPTS[nl](tr, te), RF_OPTS[nr](tr, te)
        P[NAMES[2]][msk], P[NAMES[3]][msk], P[NAMES[4]][msk] = pl, pr, (pl + pr) / 2
    for n in NAMES:
        res[n].append(score(P[n]))
    print(f"  repeat {seed + 1} of 5 done")

rows = []
for n, lst in res.items():
    t = pd.DataFrame(lst)
    rows.append({"Model": n, **{c: f"{t[c].mean():.3f} +/- {t[c].std():.3f}" for c in t.columns}})
print("\nNested results (districts never seen in training):")
print(pd.DataFrame(rows).to_string(index=False))

print("\nRule check against 'Logistic C=0.5 (v1)' (needs +0.01 and 4 of 5 repeats):")
ref = np.array([r["AUC within crop"] for r in res[NAMES[1]]])
for n in NAMES[2:]:
    a = np.array([r["AUC within crop"] for r in res[n]])
    ok = (a - ref).mean() >= 0.01 and (a > ref).sum() >= 4
    print(f"  {n}: difference {np.mean(a - ref):+.3f}, better in {(a > ref).sum()} of 5 -> "
          f"{'PASSES' if ok else 'does not pass'}")
print("\nSettings chosen inside the folds (out of 25):")
print("  Logistic:", dict(pick_l))
print("  Forest:", dict(pick_r))

# Harder test: hold out a whole geographic block of districts
dist = d.drop_duplicates("District")[["District", "Lat", "Lon"]].reset_index(drop=True)
km = KMeans(5, n_init=10, random_state=0).fit(dist[["Lat", "Lon"]])
blocks = dict(zip(dist["District"], km.labels_))
fa = d["District"].map(blocks).to_numpy()
print("\nGeographic blocks (districts per block):", dict(Counter(blocks.values())))
SP = {NAMES[0]: p_crop_state, NAMES[1]: p_logit(0.5),
      "Random forest (leaf=3, max_features=0.6)": p_rf(3, 0.6)}
sp, rows = {}, []
for n, fn in SP.items():
    p = np.zeros(len(d))
    for f in range(5):
        p[fa == f] = fn(d[fa != f], d[fa == f])
    sp[n] = p
sp["Average of logistic and forest"] = (sp[NAMES[1]] + sp["Random forest (leaf=3, max_features=0.6)"]) / 2
for n, p in sp.items():
    s = score(p)
    rows.append({"Model": n, **{c: round(v, 3) for c, v in s.items()}})
print("\nWHOLE-BLOCK-OUT test (a whole region is unseen). Baseline AUC below 0.5 is a known artifact:")
print(pd.DataFrame(rows).to_string(index=False))