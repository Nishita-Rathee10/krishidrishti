import os
import pandas as pd

df = pd.read_csv("data/raw/APY.csv")
df.columns = df.columns.str.strip()
for col in ["State", "District", "Crop", "Season"]:
    df[col] = df[col].astype(str).str.strip()


def step(label, frame):
    print(f"{label:40s} {len(frame):7d} rows")


step("1. Whole India file", df)
ph = df[df["State"].isin(["Punjab", "Haryana"])].copy()
step("2. Punjab and Haryana only", ph)

ph = ph[ph["Crop"] != "nan"]
step("3. Crop name present", ph)

ph = ph[ph["Production"].notna()]
step("4. Production recorded", ph)

ph = ph[ph["Yield"] > 0]
step("5. Yield above zero", ph)

ph = ph[ph["Area"] > 0]
step("6. Area above zero", ph)

ph = ph.drop_duplicates(subset=["State", "District", "Crop", "Crop_Year", "Season"])
step("7. No duplicate rows", ph)

ph["Crop"] = ph["Crop"].replace({
    "Rapeseed &Mustard": "Rapeseed and Mustard",
    "Peas & beans (Pulses)": "Peas and beans",
    "Cotton(lint)": "Cotton",
    "Moong(Green Gram)": "Moong",
})
ph["District"] = ph["District"].str.title().replace({"S Nagar": "SAS Nagar"})

os.makedirs("data/processed", exist_ok=True)
ph.to_csv("data/processed/yield_ph.csv", index=False)
print("\nSaved data/processed/yield_ph.csv")

print("\nRows per crop after cleaning:")
print(ph["Crop"].value_counts().to_string())