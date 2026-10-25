import json
import time
import urllib.parse
import urllib.request

import pandas as pd

d = pd.read_csv("data/processed/rain_district_normals_ph.csv")
cols = {c.lower(): c for c in d.columns}
if "state" not in cols or "district" not in cols:
    print("Columns found:", list(d.columns))
    raise SystemExit("This script needs State and District columns. Send me the list above.")
S, D = cols["state"], cols["district"]
districts = d[[S, D]].drop_duplicates().reset_index(drop=True)
print("Districts to look up:", len(districts))

ALIAS = {
    "Shahid Bhagat Singh Nagar": ["Nawanshahr"],
    "Sahibzada Ajit Singh Nagar": ["Mohali", "S.A.S. Nagar"],
    "S.A.S Nagar": ["Mohali"],
    "SAS Nagar": ["Mohali"],
    "Rupnagar": ["Ropar"],
    "Firozpur": ["Ferozepur"],
    "Ferozepur": ["Firozpur"],
    "Gurugram": ["Gurgaon"],
    "Gurgaon": ["Gurugram"],
    "Mewat": ["Nuh"],
    "Nuh": ["Mewat"],
    "Charki Dadri": ["Charkhi Dadri"],
    "Muktsar": ["Sri Muktsar Sahib"],
    "Sri Muktsar Sahib": ["Muktsar"],
    "Tarn Taran": ["Tarn Taran Sahib"],
    "Fatehgarh Sahib": ["Sirhind"],
    "Yamuna Nagar": ["Yamunanagar", "Jagadhri"],
    "Yamunanagar": ["Jagadhri"],
}
RANK = {"PPLA2": 0, "PPLA": 1, "PPLA3": 2, "PPLC": 3, "PPL": 4}


def search(name):
    url = ("https://geocoding-api.open-meteo.com/v1/search?"
           + urllib.parse.urlencode({"name": name, "count": 10, "language": "en", "format": "json"}))
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp).get("results", [])


rows, missing = [], []
for _, row in districts.iterrows():
    state, name = str(row[S]).strip(), str(row[D]).strip()
    queries = [name] + ALIAS.get(name, [])
    found = None
    for q in queries:
        try:
            res = search(q)
        except Exception as e:
            print("  request failed for", q, "->", e)
            res = []
        time.sleep(0.25)
        ok = [r for r in res
              if r.get("country_code") == "IN"
              and str(r.get("admin1", "")).lower() == state.lower()
              and 27.5 <= r["latitude"] <= 32.7 and 73.8 <= r["longitude"] <= 77.7]
        if ok:
            ok.sort(key=lambda r: (RANK.get(r.get("feature_code"), 9), -(r.get("population") or 0)))
            found = (q, ok[0])
            break
    if found:
        q, r = found
        rows.append({"State": state, "District": name, "Lat": round(r["latitude"], 3),
                     "Lon": round(r["longitude"], 3), "Matched_query": q,
                     "Matched_place": r["name"], "Feature": r.get("feature_code", "")})
    else:
        missing.append((state, name))
        rows.append({"State": state, "District": name, "Lat": None, "Lon": None,
                     "Matched_query": "", "Matched_place": "", "Feature": ""})

out = pd.DataFrame(rows)
out.to_csv("data/processed/district_coords.csv", index=False)
print(out.to_string(index=False))
print("\nNot found:", missing if missing else "none")
print("Saved data/processed/district_coords.csv")