import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

df = pd.read_csv("data/processed/yield_ph.csv")
os.makedirs("reports/figures", exist_ok=True)
COLORS = {"Punjab": "#2f6b4f", "Haryana": "#b2602c"}

# Chart 1: median yield by year for four main crops
crops = ["Wheat", "Rice", "Maize", "Cotton"]
fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
for ax, crop in zip(axes.ravel(), crops):
    g = df[df["Crop"] == crop]
    for state, gs in g.groupby("State"):
        s = gs.groupby("Crop_Year")["Yield"].median()
        ax.plot(s.index, s.values, label=state, color=COLORS[state], linewidth=2)
    ax.set_title(crop)
    ax.set_ylabel("Median yield per hectare")
    ax.grid(alpha=0.25)
axes[0, 0].legend()
fig.suptitle("Median district yield by year (units differ by crop)")
fig.tight_layout()
fig.savefig("reports/figures/01_yield_by_year.png", dpi=130)
plt.close(fig)

# Chart 2: median wheat yield in each district
w = (df[df["Crop"] == "Wheat"].groupby(["State", "District"])["Yield"]
     .median().reset_index().sort_values("Yield"))
fig, ax = plt.subplots(figsize=(8, 9))
ax.barh(w["District"], w["Yield"], color=[COLORS[s] for s in w["State"]])
ax.set_xlabel("Median wheat yield (tonnes per hectare)")
ax.set_title("Wheat yield by district, 1997 to 2019 (green Punjab, brown Haryana)")
ax.grid(axis="x", alpha=0.25)
fig.tight_layout()
fig.savefig("reports/figures/02_wheat_by_district.png", dpi=130)
plt.close(fig)

# Chart 3: how spread out the yield is for six crops
order = ["Wheat", "Rice", "Maize", "Bajra", "Gram", "Rapeseed and Mustard"]
data = [df[df["Crop"] == c]["Yield"] for c in order]
fig, ax = plt.subplots(figsize=(10, 5))
ax.boxplot(data)
ax.set_xticklabels(order, rotation=15)
ax.set_ylabel("Yield per hectare")
ax.set_title("Spread of yield for six crops (dots are unusual values)")
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig("reports/figures/03_yield_spread.png", dpi=130)
plt.close(fig)

print("Median yield by state and crop:")
table = df.groupby(["State", "Crop"])["Yield"].median().unstack(0)
print(table.loc[["Wheat", "Rice", "Maize", "Cotton", "Sugarcane", "Potato"]].round(2))
print("\nCharts saved in reports/figures")