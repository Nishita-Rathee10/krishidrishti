import pandas as pd

df = pd.read_csv("data/raw/APY.csv")
df.columns = df.columns.str.strip()
for col in ["State", "District", "Crop", "Season"]:
    df[col] = df[col].astype(str).str.strip()

ph = df[df["State"].isin(["Punjab", "Haryana"])].copy()
print("Total rows in India file:", len(df))
print("Punjab and Haryana rows:", len(ph))

for state, g in ph.groupby("State"):
    print("=" * 50)
    print(state)
    print("Rows:", len(g))
    print("Years:", g["Crop_Year"].min(), "to", g["Crop_Year"].max(),
          "| distinct years:", g["Crop_Year"].nunique())
    print("Districts:", g["District"].nunique())
    print("District names:", sorted(g["District"].unique()))
    print("Crops:", g["Crop"].nunique())
    print("Seasons:", g["Season"].value_counts().to_dict())
    print("Production missing:", int(g["Production"].isna().sum()))
    print("Yield equal to 0:", int((g["Yield"] == 0).sum()))
    print("Rows per year:")
    print(g["Crop_Year"].value_counts().sort_index().to_string())
    print("Top 12 crops by rows:")
    print(g["Crop"].value_counts().head(12).to_string())