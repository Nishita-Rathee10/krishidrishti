import pandas as pd

df = pd.read_csv("data/processed/yield_ph.csv")
print("Start:", len(df), "rows")

# 1. Keep crops with at least 300 clean rows
counts = df["Crop"].value_counts()
keep_crops = counts[counts >= 300].index.tolist()
df = df[df["Crop"].isin(keep_crops)].copy()
print("Crops kept:", len(keep_crops), "->", len(df), "rows")
print(sorted(keep_crops))

# 2. Remove extreme outliers inside each crop (more than 3 IQR outside the box)
q1 = df.groupby("Crop")["Yield"].transform(lambda s: s.quantile(0.25))
q3 = df.groupby("Crop")["Yield"].transform(lambda s: s.quantile(0.75))
iqr = q3 - q1
far = (df["Yield"] < q1 - 3 * iqr) | (df["Yield"] > q3 + 3 * iqr)
print("\nExtreme outliers removed:", int(far.sum()))
print(df[far].groupby("Crop").size().sort_values(ascending=False).to_string())
print("\nLowest and highest removed values:")
removed = df[far].sort_values("Yield")
print(removed[["State", "District", "Crop", "Crop_Year", "Yield"]].head(4).to_string())
print(removed[["State", "District", "Crop", "Crop_Year", "Yield"]].tail(4).to_string())
df = df[~far].copy()

# 3. Add district normal rainfall
rain = pd.read_csv("data/processed/rain_district_normals_ph.csv")
rain = rain[["State", "District", "ANNUAL", "Jun-Sep"]].rename(
    columns={"ANNUAL": "Rain_Annual_Normal", "Jun-Sep": "Rain_JunSep_Normal"})
df = df.merge(rain, on=["State", "District"], how="left")
print("\nRows without a rainfall normal:", int(df["Rain_Annual_Normal"].isna().sum()))


# 4. Split by year
def split(year):
    if year <= 2014:
        return "train"
    if year <= 2016:
        return "validation"
    return "test"


df["Split"] = df["Crop_Year"].apply(split)
print("\nRows per split:")
print(df["Split"].value_counts().to_string())
print("\nRows per crop in each split:")
print(pd.crosstab(df["Crop"], df["Split"]).to_string())

cols = ["State", "District", "Crop", "Season", "Crop_Year",
        "Rain_Annual_Normal", "Rain_JunSep_Normal", "Yield", "Split"]
df[cols].to_csv("data/processed/yield_model_table.csv", index=False)
print("\nSaved data/processed/yield_model_table.csv with", len(df), "rows")