import os
import pandas as pd

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# Part 1: month by month rainfall for the two IMD regions, 1901 to 2015
sub = pd.read_csv("data/raw/rainfall in india 1901-2015.csv")
sub.columns = sub.columns.str.strip()
sub["SUBDIVISION"] = sub["SUBDIVISION"].astype(str).str.strip()
keep = sub[sub["SUBDIVISION"].str.contains("PUNJAB|HARYANA", case=False)].copy()
keep["Region"] = keep["SUBDIVISION"].apply(
    lambda s: "Punjab" if "PUNJAB" in s.upper() else "Haryana, Delhi and Chandigarh")
print("Rows per region:", keep["Region"].value_counts().to_dict())
print("Missing monthly values:", int(keep[MONTHS].isna().sum().sum()))
print("Average yearly rainfall (mm):")
print(keep.groupby("Region")["ANNUAL"].mean().round(0).to_string())

long = keep.melt(id_vars=["Region", "YEAR"], value_vars=MONTHS, var_name="Month", value_name="Rain_mm")
long["Month"] = long["Month"].map({m: i + 1 for i, m in enumerate(MONTHS)})
long = long.rename(columns={"YEAR": "Year"}).sort_values(["Region", "Year", "Month"]).reset_index(drop=True)
long["Date"] = pd.to_datetime(dict(year=long["Year"], month=long["Month"], day=1))

os.makedirs("data/processed", exist_ok=True)
long.to_csv("data/processed/rain_monthly_ph.csv", index=False)
print("Saved rain_monthly_ph.csv with", len(long), "rows")

# Part 2: normal rainfall for each district
dist = pd.read_csv("data/raw/district wise rainfall normal.csv")
dist.columns = dist.columns.str.strip()
dist["STATE_UT_NAME"] = dist["STATE_UT_NAME"].astype(str).str.strip()
dist["DISTRICT"] = dist["DISTRICT"].astype(str).str.strip()
d = dist[dist["STATE_UT_NAME"].str.upper().isin(["PUNJAB", "HARYANA"])].copy()

rename = {
    "SONEPAT(RTK)": "Sonipat", "PALWAL(FRD)": "Palwal", "FEROZEPUR": "Firozepur",
    "NAWANSHAHR": "Shahid Bhagat Singh Nagar", "FATEHGARH SAH": "Fatehgarh Sahib",
    "SAS NAGAR(MGA)": "SAS Nagar",
}
d["District"] = d["DISTRICT"].map(lambda x: rename.get(x, x.title()))
d["State"] = d["STATE_UT_NAME"].str.title()
num_cols = MONTHS + ["ANNUAL", "Jun-Sep"]
for c in num_cols:
    d[c] = pd.to_numeric(d[c], errors="coerce")
d["Source"] = "district normal"

gap = (d[MONTHS].sum(axis=1) - d["ANNUAL"]).abs().max()
print("\nLargest gap between sum of months and ANNUAL (mm):", round(gap, 1))

# New districts are not in this file. Copy the parent district and mark it.
parents = {"Fazilka": ("Punjab", "Firozepur"), "Pathankot": ("Punjab", "Gurdaspur"),
           "Charki Dadri": ("Haryana", "Bhiwani")}
extra = []
for new, (state, parent) in parents.items():
    row = d[(d["State"] == state) & (d["District"] == parent)].copy()
    row["District"] = new
    row["Source"] = "copied from " + parent + " (new district, estimate)"
    extra.append(row)
d = pd.concat([d] + extra, ignore_index=True)

out = d[["State", "District"] + num_cols + ["Source"]].sort_values(["State", "District"])
out.to_csv("data/processed/rain_district_normals_ph.csv", index=False)
print("Saved rain_district_normals_ph.csv with", len(out), "districts")

# Check against the yield districts
y = pd.read_csv("data/processed/yield_ph.csv")
yd = set(zip(y["State"], y["District"]))
dd = set(zip(out["State"], out["District"]))
print("\nYield districts with no rainfall normal:", sorted(yd - dd))
print("Rainfall districts not in yield data:", sorted(dd - yd))
