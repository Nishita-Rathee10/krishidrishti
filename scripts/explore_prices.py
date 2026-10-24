import glob
import pandas as pd

files = glob.glob("data/raw/prices_small/*.csv") + glob.glob("data/raw/prices_main/*.csv")
for path in files:
    print("=" * 60)
    print(path)
    try:
        df = pd.read_csv(path)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1")
    df.columns = df.columns.str.strip()
    print("Rows and columns:", df.shape)
    print("Columns:", list(df.columns))
    print(df.head(3).to_string())

    date_cols = [c for c in df.columns if "date" in c.lower()]
    state_cols = [c for c in df.columns if "state" in c.lower()]
    com_cols = [c for c in df.columns if "commodity" in c.lower()]
    if date_cols:
        d = pd.to_datetime(df[date_cols[0]], errors="coerce", dayfirst=True)
        print("\nDate column:", date_cols[0], "| from", d.min(), "to", d.max(),
              "| unreadable dates:", int(d.isna().sum()))
    if state_cols:
        sc = state_cols[0]
        print("Number of states:", df[sc].nunique())
        m = df[sc].astype(str).str.contains("punjab|haryana", case=False, na=False)
        print("Punjab and Haryana rows:", int(m.sum()))
        if m.sum() and com_cols:
            print(df.loc[m, com_cols[0]].value_counts().head(15).to_string())
            if date_cols:
                dd = pd.to_datetime(df.loc[m, date_cols[0]], errors="coerce", dayfirst=True)
                print("Punjab and Haryana dates:", dd.min(), "to", dd.max())