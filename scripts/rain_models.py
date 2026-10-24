import json
import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

df = pd.read_csv("data/processed/rain_monthly_ph.csv", parse_dates=["Date"])
regions = sorted(df["Region"].unique())
series = {}
for r in regions:
    s = df[df["Region"] == r].sort_values("Date").set_index("Date")["Rain_mm"].asfreq("MS")
    assert s.isna().sum() == 0 and len(s) == 1380, r
    series[r] = s


def label(r):
    return "Punjab" if r.startswith("Punjab") else "Haryana region"


def anomalies(s):
    return s - s.groupby(s.index.month).transform("mean")


# 1. Stationarity check and ACF/PACF plots
print("ADF test (small p means the series is stationary):")
for r, s in series.items():
    print(f"  {label(r)}: p for raw rain = {adfuller(s)[1]:.4f}, "
          f"p after removing monthly average = {adfuller(anomalies(s))[1]:.4f}")

os.makedirs("reports/figures", exist_ok=True)
fig, axes = plt.subplots(len(regions), 3, figsize=(14, 3.6 * len(regions)))
for i, (r, s) in enumerate(series.items()):
    a = anomalies(s)
    plot_acf(s, lags=36, ax=axes[i, 0], title=f"{label(r)}: rain ACF")
    plot_acf(a, lags=36, ax=axes[i, 1], title=f"{label(r)}: after monthly average ACF")
    plot_pacf(a, lags=36, ax=axes[i, 2], title=f"{label(r)}: after monthly average PACF", method="ywm")
plt.tight_layout()
plt.savefig("reports/figures/04_rain_acf_pacf.png", dpi=130)
plt.close()
print("Saved reports/figures/04_rain_acf_pacf.png")

# 2. Models
ARIMA_SPECS = {
    "AR(2) on anomalies": (2, 0, 0),
    "MA(2) on anomalies": (0, 0, 2),
    "ARIMA(1,0,1) on anomalies": (1, 0, 1),
    "ARIMA(2,0,1) on anomalies": (2, 0, 1),
    "ARIMA(1,1,1) on anomalies": (1, 1, 1),
}
SARIMA_SPECS = {
    "SARIMA(1,0,1)(1,1,1,12) on sqrt rain": ((1, 0, 1), (1, 1, 1, 12)),
    "SARIMA(0,0,1)(0,1,1,12) on sqrt rain": ((0, 0, 1), (0, 1, 1, 12)),
}
BASE = ["Climatology", "Seasonal naive"]
CANDS = list(ARIMA_SPECS) + list(SARIMA_SPECS)


def forecast(name, s, year):
    hist = s[:pd.Timestamp(f"{year - 1}-12-01")]
    months = pd.date_range(f"{year}-01-01", periods=12, freq="MS")
    mm = hist.groupby(hist.index.month).mean()
    clim = np.array([mm[m.month] for m in months])
    if name == "Climatology":
        return clim
    if name == "Seasonal naive":
        return hist.iloc[-12:].to_numpy()
    window = hist.iloc[-480:]
    if name in SARIMA_SPECS:
        order, sorder = SARIMA_SPECS[name]
        fit = SARIMAX(np.sqrt(window.to_numpy()), order=order, seasonal_order=sorder,
                      enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
        return np.clip(fit.forecast(12), 0, None) ** 2
    anom = window.to_numpy() - mm.reindex(window.index.month).to_numpy()
    fit = ARIMA(anom, order=ARIMA_SPECS[name], trend="n").fit()
    return np.clip(clim + fit.forecast(12), 0, None)


def evaluate(s, names, years):
    actual, store = [], {n: [] for n in names}
    for y in years:
        actual.append(s[f"{y}-01-01":f"{y}-12-01"].to_numpy())
        for n in names:
            store[n].append(forecast(n, s, y))
    A = np.array(actual)
    out = {}
    for n in names:
        P = np.array(store[n])
        out[n] = {"mae": float(np.abs(P - A).mean()),
                  "monsoon_mae": float(np.abs(P[:, 5:9].sum(1) - A[:, 5:9].sum(1)).mean())}
    return out


def show(res):
    base = res["Climatology"]["mae"]
    t = pd.DataFrame([{"Model": n, "Monthly MAE mm": round(v["mae"], 2),
                       "Skill vs climatology %": round(100 * (1 - v["mae"] / base), 1),
                       "Jun-Sep total MAE mm": round(v["monsoon_mae"], 1)} for n, v in res.items()])
    print(t.to_string(index=False))


def coverage(s, years):
    hit = []
    for y in years:
        hist = s[:pd.Timestamp(f"{y - 1}-12-01")]
        g = hist.groupby(hist.index.month)
        q10, q90 = g.quantile(0.10), g.quantile(0.90)
        act = s[f"{y}-01-01":f"{y}-12-01"]
        for m, v in zip(act.index.month, act.to_numpy()):
            hit.append(bool(q10[m] <= v <= q90[m]))
    return float(100 * np.mean(hit))


VAL, TEST = range(1991, 2006), range(2006, 2016)
summary = {}
print("\nThis takes about 10 to 15 minutes. Please do not close the terminal.")
for r, s in series.items():
    print("\n" + "=" * 70)
    print(label(r), "- VALIDATION, forecast years 1991 to 2005 (12 months ahead)")
    val = evaluate(s, BASE + CANDS, VAL)
    show(val)
    best = min(CANDS, key=lambda n: val[n]["mae"])
    skill = 100 * (1 - val[best]["mae"] / val["Climatology"]["mae"])
    accepted = skill >= 2.0
    print(f"Best candidate: {best} (skill {skill:.1f}%). Rule needs 2.0% -> "
          f"{'ACCEPTED' if accepted else 'NOT accepted, climatology will be used'}")
    print(label(r), "- TEST, forecast years 2006 to 2015 (looked at once)")
    test = evaluate(s, BASE + [best], TEST)
    show(test)
    cov = coverage(s, TEST)
    print(f"Share of test months inside the 10 to 90 range of history: {cov:.1f}%")
    summary[label(r)] = {"best_candidate": best, "validation_skill_pct": round(skill, 2),
                         "accepted": bool(accepted), "validation": val, "test": test,
                         "range_10_90_coverage_test_pct": round(cov, 1)}

# 3. Climatology table for the website (all years 1901 to 2015)
rows = []
for r, s in series.items():
    g = s.groupby(s.index.month)
    for m in range(1, 13):
        v = g.get_group(m)
        rows.append({"Region": label(r), "Month": m, "Mean_mm": round(v.mean(), 1),
                     "Median_mm": round(v.median(), 1), "P10_mm": round(v.quantile(0.10), 1),
                     "P90_mm": round(v.quantile(0.90), 1)})
pd.DataFrame(rows).to_csv("data/processed/rain_climatology.csv", index=False)
os.makedirs("models", exist_ok=True)
with open("models/rain_metrics.json", "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=1)
print("\nSaved data/processed/rain_climatology.csv and models/rain_metrics.json")