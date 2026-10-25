import json
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

df = pd.read_csv("data/processed/rain_monthly_ph.csv", parse_dates=["Date"])


def label(r):
    return "Punjab" if r.startswith("Punjab") else "Haryana region"


df["Label"] = df["Region"].map(label)
series = {}
for lab, g in df.groupby("Label"):
    s = g.sort_values("Date").set_index("Date")["Rain_mm"].asfreq("MS")
    assert s.isna().sum() == 0 and len(s) == 1380
    series[lab] = s

yearly = df.groupby(["Label", "Year"])["Rain_mm"].sum().reset_index()
yearly["Decade"] = yearly["Year"] // 10 * 10
print("Average yearly rain in mm by decade (1900s has 9 years, 2010s has 6 years):")
print(yearly.groupby(["Decade", "Label"])["Rain_mm"].mean().unstack().round(0).to_string())

WINDOWS = {"Climatology, all years": None, "Climatology, last 30 years": 360,
           "Climatology, last 20 years": 240}
SAR = "SARIMA(0,0,1)(0,1,1,12) on sqrt rain"
FULL = "Climatology, all years"


def clim_table(hist, months_back):
    h = hist if months_back is None else hist.iloc[-months_back:]
    return h.groupby(h.index.month).mean()


def forecast(name, s, year):
    hist = s[:pd.Timestamp(f"{year - 1}-12-01")]
    months = pd.date_range(f"{year}-01-01", periods=12, freq="MS")
    if name in WINDOWS:
        mm = clim_table(hist, WINDOWS[name])
        return np.array([mm[m.month] for m in months])
    fit = SARIMAX(np.sqrt(hist.iloc[-480:].to_numpy()), order=(0, 0, 1), seasonal_order=(0, 1, 1, 12),
                  enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
    return np.clip(fit.forecast(12), 0, None) ** 2


def evaluate(s, names, years):
    actual, store = [], {n: [] for n in names}
    for y in years:
        actual.append(s[f"{y}-01-01":f"{y}-12-01"].to_numpy())
        for n in names:
            store[n].append(forecast(n, s, y))
    A = np.array(actual)
    return {n: {"mae": float(np.abs(np.array(store[n]) - A).mean()),
                "monsoon_mae": float(np.abs(np.array(store[n])[:, 5:9].sum(1) - A[:, 5:9].sum(1)).mean())}
            for n in names}


def show(res, ref):
    base = res[ref]["mae"]
    t = pd.DataFrame([{"Model": n, "Monthly MAE mm": round(v["mae"], 2),
                       f"Skill vs '{ref}' %": round(100 * (1 - v["mae"] / base), 1),
                       "Jun-Sep total MAE mm": round(v["monsoon_mae"], 1)} for n, v in res.items()])
    print(t.to_string(index=False))


def coverage(s, years, months_back):
    hit = []
    for y in years:
        hist = s[:pd.Timestamp(f"{y - 1}-12-01")]
        h = hist if months_back is None else hist.iloc[-months_back:]
        g = h.groupby(h.index.month)
        q10, q90 = g.quantile(0.10), g.quantile(0.90)
        act = s[f"{y}-01-01":f"{y}-12-01"]
        for m, v in zip(act.index.month, act.to_numpy()):
            hit.append(bool(q10[m] <= v <= q90[m]))
    return float(100 * np.mean(hit))


VAL, TEST = range(1971, 2006), range(2006, 2016)
out, rows = {}, []
print("\nThis takes about 5 to 10 minutes. Please do not close the terminal.")
for lab, s in series.items():
    print("\n" + "=" * 70)
    print(lab, "- VALIDATION, forecast years 1971 to 2005")
    val = evaluate(s, list(WINDOWS) + [SAR], VAL)
    show(val, FULL)
    best_clim = min(WINDOWS, key=lambda n: val[n]["mae"])
    gain = 100 * (1 - val[best_clim]["mae"] / val[FULL]["mae"])
    chosen = best_clim if gain >= 2.0 else FULL
    sar_gain = 100 * (1 - val[SAR]["mae"] / val[chosen]["mae"])
    sar_ok = sar_gain >= 2.0
    print(f"Best climatology: {best_clim} (gain {gain:.1f}% over all-years). Chosen: {chosen}")
    print(f"SARIMA gain over chosen climatology: {sar_gain:.1f}% -> "
          f"{'ACCEPTED' if sar_ok else 'NOT accepted'}")
    print(lab, "- TEST, forecast years 2006 to 2015 (second look, no longer untouched)")
    test = evaluate(s, list(WINDOWS) + [SAR], TEST)
    show(test, FULL)
    cov = coverage(s, TEST, WINDOWS[chosen])
    print(f"Share of test months inside the 10 to 90 range ({chosen}): {cov:.1f}%")
    out[lab] = {"chosen_climatology": chosen, "sarima_accepted": bool(sar_ok),
                "validation": val, "test": test, "range_coverage_test_pct": round(cov, 1)}
    mb = WINDOWS[chosen]
    h = s if mb is None else s.iloc[-mb:]
    g = h.groupby(h.index.month)
    for m in range(1, 13):
        v = g.get_group(m)
        rows.append({"Region": lab, "Month": m, "Mean_mm": round(v.mean(), 1), "Median_mm": round(v.median(), 1),
                     "P10_mm": round(v.quantile(0.10), 1), "P90_mm": round(v.quantile(0.90), 1),
                     "Window": chosen})

pd.DataFrame(rows).to_csv("data/processed/rain_climatology.csv", index=False)
with open("models/rain_metrics_v2.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1)
print("\nSaved data/processed/rain_climatology.csv and models/rain_metrics_v2.json")