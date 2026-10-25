import pandas as pd

df = pd.read_csv("data/processed/yield_ph.csv")
print("Columns:", list(df.columns))
if "Area" not in df.columns:
    raise SystemExit("No Area column. Send me the list of columns above.")

df["Season"] = df["Season"].str.strip()
recent = df[df["Crop_Year"] >= 2010]
print("\nRows from 2010:", len(recent), "| years:", recent["Crop_Year"].min(), "to", recent["Crop_Year"].max())

print("\nCrops by season: rows, share of area, districts where the crop exists (from 2010)")
for season, g in recent.groupby("Season"):
    t = g.groupby("Crop").agg(Rows=("Area", "size"), Area=("Area", "sum"),
                              Districts=("District", "nunique")).sort_values("Area", ascending=False)
    t["Area share %"] = (100 * t["Area"] / t["Area"].sum()).round(1)
    print(f"\n--- {season} ---")
    print(t[["Rows", "Districts", "Area share %"]].head(12).to_string())

key = ["State", "District", "Season", "Crop_Year"]
top = recent.loc[recent.groupby(key)["Area"].idxmax()]
print("\nBiggest crop by area, per district-season-year (count of cases):")
print(top.groupby(["Season", "Crop"]).size().unstack(0).fillna(0).astype(int).to_string())
print("\nBiggest crop by state and season (count of cases):")
print(top.groupby(["State", "Season", "Crop"]).size().to_string())