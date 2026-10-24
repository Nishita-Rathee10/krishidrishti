import pandas as pd

df = pd.read_csv("data/raw/APY.csv")
df.columns = df.columns.str.strip()
for col in ["State", "District", "Crop", "Season"]:
    df[col] = df[col].astype(str).str.strip()
ph = df[df["State"].isin(["Punjab", "Haryana"])].copy()

zero = ph[ph["Yield"] == 0]
print("Zero-yield rows:", len(zero))
print("  Area is 0:", int((zero["Area"] == 0).sum()))
print("  Area above 0:", int((zero["Area"] > 0).sum()))
print("  Production missing:", int(zero["Production"].isna().sum()))

print("\nZero-yield rows by crop (top 10):")
print(zero["Crop"].value_counts().head(10).to_string())

print("\nZero-yield rows by year:")
print(zero["Crop_Year"].value_counts().sort_index().to_string())

print("\nSample zero-yield rows with Area above 0:")
print(zero[zero["Area"] > 0].head(8).to_string())

ok = ph[ph["Yield"] > 0]
print("\nYield for main crops (rows, median, min, max):")
for crop in ["Wheat", "Rice", "Maize", "Sugarcane", "Cotton(lint)", "Potato", "Bajra", "Gram", "Rapeseed &Mustard"]:
    g = ok[ok["Crop"] == crop]
    if len(g):
        print(f"{crop:20s} rows={len(g):4d} median={g['Yield'].median():8.2f} min={g['Yield'].min():8.2f} max={g['Yield'].max():8.2f}")

w = ok[(ok["Crop"] == "Wheat") & ok["Production"].notna()]
diff = ((w["Production"] / w["Area"]) - w["Yield"]).abs().median()
print("\nWheat: typical gap between Production/Area and Yield:", round(diff, 3))