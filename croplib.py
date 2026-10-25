import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


class CropEnsemble:
    """Average of (a) one small logistic regression per crop and (b) one shared random forest.
    Input: a table with columns Item and the climate columns in `num`. Output: chance (0 to 1)
    that the crop is a major crop (at least 2 percent of area) in that district and season."""

    def __init__(self, num, C=1.0, leaf=3, max_features=1.0, n_estimators=200, seed=42):
        self.num = list(num)
        self.C = C
        self.leaf = leaf
        self.max_features = max_features
        self.n_estimators = n_estimators
        self.seed = seed

    def fit_logit(self, tr):
        self.prev_ = tr.groupby("Item")["Major"].mean().to_dict()
        self.global_prev_ = float(tr["Major"].mean())
        self.logit_ = {}
        for item, a in tr.groupby("Item"):
            if a["Major"].nunique() < 2:
                continue
            sc = StandardScaler().fit(a[self.num])
            lr = LogisticRegression(C=self.C, max_iter=2000).fit(sc.transform(a[self.num]), a["Major"])
            self.logit_[item] = (sc, lr)
        return self

    def fit_rf(self, tr):
        prep = ColumnTransformer([
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["Item"]),
            ("num", StandardScaler(), self.num)])
        rf = RandomForestClassifier(n_estimators=self.n_estimators, min_samples_leaf=self.leaf,
                                    max_features=self.max_features, random_state=self.seed, n_jobs=1)
        self.rf_ = Pipeline([("prep", prep), ("model", rf)]).fit(tr[["Item"] + self.num], tr["Major"])
        return self

    def fit(self, tr):
        return self.fit_logit(tr).fit_rf(tr)

    def p_logit(self, te):
        out = np.array([self.prev_.get(i, self.global_prev_) for i in te["Item"]], dtype=float)
        for item, (sc, lr) in self.logit_.items():
            mask = (te["Item"] == item).to_numpy()
            if mask.any():
                out[mask] = lr.predict_proba(sc.transform(te.loc[mask, self.num]))[:, 1]
        return out

    def p_rf(self, te):
        return self.rf_.predict_proba(te[["Item"] + self.num])[:, 1]

    def predict_proba(self, te):
        return (self.p_logit(te) + self.p_rf(te)) / 2