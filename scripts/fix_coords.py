import pandas as pd

d = pd.read_csv("data/processed/district_coords.csv")
fix = {"Rupnagar": (30.966, 76.533, "Rupnagar (Ropar) city"),
       "Firozepur": (30.933, 74.622, "Ferozepur city")}
for name, (lat, lon, place) in fix.items():
    m = d["District"] == name
    assert m.sum() == 1, name
    d.loc[m, "Lat"] = lat
    d.loc[m, "Lon"] = lon
    d.loc[m, "Matched_query"] = "manual"
    d.loc[m, "Matched_place"] = place
    d.loc[m, "Feature"] = "manual"
d.to_csv("data/processed/district_coords.csv", index=False)

print("Missing coordinates:", int(d["Lat"].isna().sum()))
bad = d[~d["Lat"].between(27.5, 32.7) | ~d["Lon"].between(73.8, 77.7)]
print("Outside Punjab/Haryana box:", len(bad))
print("Duplicate coordinates:", int(d.duplicated(["Lat", "Lon"]).sum()))
print(d[d["Feature"] == "manual"].to_string(index=False))