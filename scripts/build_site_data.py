import json

import pandas as pd

t = pd.read_csv("data/processed/crop_suitability_table.csv").drop_duplicates(["State", "District"])
c = pd.read_csv("data/processed/district_coords.csv")
m = t.merge(c[["State", "District", "Lat", "Lon"]], on=["State", "District"], how="inner").reset_index(drop=True)
assert len(m) == 44, f"Expected 44 districts, got {len(m)}"

# Names shown on the site, and the words used in web addresses
NAME = {
    "Charki Dadri": "Charkhi Dadri",
    "Gurgaon": "Gurugram",
    "Mewat": "Nuh",
    "Firozepur": "Ferozepur",
    "SAS Nagar": "SAS Nagar (Mohali)",
    "Shahid Bhagat Singh Nagar": "Shahid Bhagat Singh Nagar",
    "Rupnagar": "Rupnagar (Ropar)",
}
SLUG = {
    "Charki Dadri": "charkhi-dadri",
    "Gurgaon": "gurugram",
    "Mewat": "nuh",
    "Firozepur": "ferozepur",
    "SAS Nagar": "sas-nagar",
}
# New districts that use the rain figure of the district they were carved out of
APPROX_RAIN = {"Fazilka", "Pathankot", "Charki Dadri"}

# Tile map: one square per district, placed by latitude and longitude.
# A square is a little wider in longitude so the shape looks right on the ground.
LAT_STEP, LON_STEP = 0.25, 0.29
lat_top, lon_left = m["Lat"].max(), m["Lon"].min()
m["fc"] = (m["Lon"] - lon_left) / LON_STEP
m["fr"] = (lat_top - m["Lat"]) / LAT_STEP

taken, pos = set(), {}
for i in m.sort_values(["fr", "fc"]).index:
    fc, fr = m.at[i, "fc"], m.at[i, "fr"]
    best = None
    for radius in range(0, 6):
        cands = []
        for dc in range(-radius, radius + 1):
            for dr in range(-radius, radius + 1):
                if max(abs(dc), abs(dr)) != radius:
                    continue
                cc, rr = int(round(fc)) + dc, int(round(fr)) + dr
                if cc < 0 or rr < 0 or (cc, rr) in taken:
                    continue
                cands.append(((cc - fc) ** 2 + (rr - fr) ** 2, cc, rr))
        if cands:
            _, cc, rr = min(cands)
            best = (cc, rr)
            break
    assert best is not None, m.at[i, "District"]
    taken.add(best)
    pos[i] = best

# Remove empty columns and rows at the edges after nudging
min_c = min(p[0] for p in pos.values())
min_r = min(p[1] for p in pos.values())
out = []
for i, row in m.iterrows():
    d = row["District"]
    col, r = pos[i][0] - min_c, pos[i][1] - min_r
    out.append({
        "slug": SLUG.get(d, d.lower().replace(" ", "-")),
        "name": NAME.get(d, d),
        "source_name": d,
        "state": row["State"],
        "col": col,
        "row": r,
        "rain": round(float(row["Rain_Annual_Normal"]), 0),
        "t_winter": round(float(row["T_rabi"]), 1),
        "t_summer": round(float(row["T_hot_max"]), 1),
        "approx_rain": d in APPROX_RAIN,
        "lat": float(row["Lat"]),
        "lon": float(row["Lon"]),
    })
out.sort(key=lambda x: x["name"])
site = {
    "cols": max(x["col"] for x in out) + 1,
    "rows": max(x["row"] for x in out) + 1,
    "districts": out,
}
assert len({x["slug"] for x in out}) == 44, "Duplicate slugs"
with open("data/processed/districts.json", "w", encoding="utf-8") as fh:
    json.dump(site, fh, indent=1, ensure_ascii=False)

moved = sum(1 for i in m.index if abs(pos[i][0] - m.at[i, "fc"]) > 1 or abs(pos[i][1] - m.at[i, "fr"]) > 1)
print("Grid:", site["cols"], "columns x", site["rows"], "rows | districts:", len(out))
print("Squares moved more than one square from their true spot:", moved)
print(pd.DataFrame(out)[["slug", "name", "state", "col", "row", "rain", "t_winter", "t_summer"]].to_string(index=False))
print("Saved data/processed/districts.json")