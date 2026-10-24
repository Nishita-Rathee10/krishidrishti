import pandas as pd

try:
    df = pd.read_csv("data/raw/APY.csv")
except UnicodeDecodeError:
    df = pd.read_csv("data/raw/APY.csv", encoding="latin-1")

print("Rows and columns:", df.shape)
print("\nColumn names:", list(df.columns))

print("\nFirst 5 rows:")
print(df.head().to_string())

print("\nMissing values in each column:")
print(df.isna().sum())

state_cols = [c for c in df.columns if "state" in c.lower()]
if state_cols:
    sc = state_cols[0]
    states = sorted(df[sc].astype(str).str.strip().unique())
    print("\nNumber of states:", len(states))
    print("States:", states)

    mask = df[sc].astype(str).str.contains("punjab|haryana", case=False, na=False)
    print("\nPunjab and Haryana rows:", mask.sum())
    print(df.loc[mask, sc].value_counts())
else:
    print("\nNo column with 'state' in its name. Send me the column names above.")