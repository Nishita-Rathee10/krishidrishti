import pandas as pd

path = "data/raw/prices_main/Agriculture_price_dataset_unclean_full_more_messy.csv"
df = pd.read_csv(path)
df.columns = df.columns.str.strip()
for c in ["Min_Price", "Max_Price", "Modal_Price"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
print("Rows:", len(df))

d = pd.to_datetime(df["Price Date"], errors="coerce", format="mixed", dayfirst=True)
df["date"] = d
print("Unreadable dates with mixed formats:", int(d.isna().sum()), "of", len(df))
print("Date range:", d.min(), "to", d.max())

st = df["STATE"].astype(str).str.strip().str.lower()
print("\nState spellings that contain punjab or haryana:")
print(st[st.str.contains("punjab|haryana", na=False)].value_counts().to_string())

ph = df[st.str.contains("punjab|haryana", na=False)].copy()
ph["commodity_clean"] = ph["Commodity"].astype(str).str.strip().str.lower()
print("\nPunjab and Haryana rows:", len(ph))
print("Commodity spellings:")
print(ph["commodity_clean"].value_counts().head(15).to_string())

print("\nMissing share of each column in these rows (percent):")
print((ph.isna().mean() * 100).round(1).to_string())
print("\nDuplicate rows in Punjab and Haryana:", int(ph.duplicated().sum()))

pot = ph[ph["commodity_clean"].str.contains("potato", na=False)]
pot = pot[pot["date"].notna() & pot["Modal_Price"].notna()]
print("\nPotato rows with a date and a modal price:", len(pot))
print("Modal price range (Rs per quintal): min", pot["Modal_Price"].min(), "max", pot["Modal_Price"].max())
monthly = pot.set_index("date")["Modal_Price"].resample("MS").agg(["count", "median"])
print(monthly.to_string())