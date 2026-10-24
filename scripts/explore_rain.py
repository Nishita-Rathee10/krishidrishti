import pandas as pd

sub = pd.read_csv("data/raw/rainfall in india 1901-2015.csv")
sub.columns = sub.columns.str.strip()
print("SUBDIVISION FILE")
print("Rows and columns:", sub.shape)
print("Columns:", list(sub.columns))
print(sub.head(3).to_string())

name_col = "SUBDIVISION" if "SUBDIVISION" in sub.columns else sub.columns[0]
year_col = next((c for c in sub.columns if c.lower() == "year"), None)
print("\nSubdivisions:", sorted(sub[name_col].astype(str).unique()))

mask = sub[name_col].astype(str).str.contains("punjab|haryana", case=False)
ph = sub[mask]
print("\nPunjab / Haryana rows:", len(ph))
for name, g in ph.groupby(name_col):
    years = f"{g[year_col].min()} to {g[year_col].max()}" if year_col else "year column not found"
    print(name, "| years", years, "| rows", len(g), "| missing cells:", int(g.isna().sum().sum()))

print("\nMissing values in the whole file:")
print(sub.isna().sum().to_string())

dist = pd.read_csv("data/raw/district wise rainfall normal.csv")
dist.columns = dist.columns.str.strip()
print("\n" + "=" * 50)
print("DISTRICT NORMAL FILE")
print("Rows and columns:", dist.shape)
print("Columns:", list(dist.columns))
print(dist.head(3).to_string())

state_cols = [c for c in dist.columns if "state" in c.lower()]
if state_cols:
    sc = state_cols[0]
    m = dist[sc].astype(str).str.contains("punjab|haryana", case=False)
    print("\nPunjab / Haryana rows:", int(m.sum()))
    print(dist[m].to_string())
else:
    print("\nNo state column found. Send me the column names above.")