import pandas as pd

THRESH = 0.02
y = pd.read_csv("data/processed/yield_ph.csv")
y["Season"] = y["Season"].str.strip()
y = y[(y["Crop_Year"] >= 2010) & (y["Area"] > 0)].copy()

key = ["State", "District", "Season"]
tot = y.groupby(key + ["Crop_Year"])["Area"].sum().rename("Tot").reset_index()
y = y.merge(tot, on=key + ["Crop_Year"])
y["Share"] = y["Area"] / y["Tot"]
nyears = tot.groupby(key)["Crop_Year"].nunique().rename("NYears").reset_index()

cs = y.groupby(key + ["Crop"])["Share"].sum().rename("ShareSum").reset_index().merge(nyears, on=key)
cs["MeanShare"] = cs["ShareSum"] / cs["NYears"]

# Only compare crops that are actually reported in that state and season (at least 3 districts)
cnt = y.groupby(["State", "Season", "Crop"])["District"].nunique().reset_index(name="D")
cand = cnt[cnt["D"] >= 3][["State", "Season", "Crop"]]
units = y[key].drop_duplicates()
grid = units.merge(cand, on=["State", "Season"])
grid = grid.merge(cs[key + ["Crop", "MeanShare"]], on=key + ["Crop"], how="left")
grid["MeanShare"] = grid["MeanShare"].fillna(0.0)
grid["Major"] = (grid["MeanShare"] >= THRESH).astype(int)

c = pd.read_csv("data/processed/climate_district_monthly.csv")


def mean_of(col, months, name):
    return c[c["Month"].isin(list(months))].groupby(["State", "District"])[col].mean().rename(name)


clim = pd.concat([
    mean_of("Temp_mean_C", range(1, 13), "T_annual"),
    mean_of("Temp_max_C", [4, 5, 6], "T_hot_max"),
    mean_of("Temp_min_C", [12, 1, 2], "T_cold_min"),
    mean_of("Temp_mean_C", [6, 7, 8, 9, 10], "T_kharif"),
    mean_of("Temp_mean_C", [11, 12, 1, 2, 3], "T_rabi"),
    mean_of("Humidity_pct", range(1, 13), "RH_annual"),
    mean_of("Humidity_pct", [7, 8, 9], "RH_monsoon"),
    mean_of("Humidity_pct", [12, 1, 2], "RH_winter"),
], axis=1).reset_index()

yt = pd.read_csv("data/processed/yield_model_table.csv")
rain = yt.groupby(["State", "District"])[["Rain_Annual_Normal", "Rain_JunSep_Normal"]].mean().reset_index()

out = grid.merge(clim, on=["State", "District"], how="left").merge(rain, on=["State", "District"], how="left")
feat = [col for col in out.columns if col.startswith(("T_", "RH_", "Rain_"))]
bad = out[out[feat].isna().any(axis=1)][["State", "District"]].drop_duplicates()
print("Districts with missing climate or rain features:", bad.to_string(index=False) if len(bad) else "none")

out.to_csv("data/processed/crop_suitability_table.csv", index=False)
print("\nRows:", len(out), "| districts:", out["District"].nunique(), "| share of Major=1:",
      round(100 * out["Major"].mean(), 1), "%")

for th in (0.01, 0.02, 0.05):
    print(f"Share of Major at threshold {int(th * 100)}%:", round(100 * (out["MeanShare"] >= th).mean(), 1), "%")

t = out.groupby(["Season", "Crop", "State"]).agg(Districts=("District", "nunique"),
                                                 Major=("Major", "sum")).reset_index()
t["Major %"] = (100 * t["Major"] / t["Districts"]).round(0)
print("\nHow many districts have each crop as a major crop (2% rule):")
print(t.to_string(index=False))
print("Saved data/processed/crop_suitability_table.csv")
