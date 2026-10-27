# Krishi Drishti

A college project on supervised learning. It looks at farm data for the districts of Punjab and Haryana: yield, rain, and the crops a district's climate may suit. Live site: https://krishidrishti-ivr4.onrender.com

![Tile map of the 44 districts](docs/home.png)

## What it does

| Page | What it shows | How it was tested |
|---|---|---|
| Districts | A tile map of 44 districts, with a page for each: temperature and rain through the year, major crops, and crops the climate may suit. | Figures come straight from the data. Crop suggestions come from the crops model. |
| Crop yield | Yield of 16 crops from 1998 to 2019, and how close a random forest came on 2017 to 2019. | Trained on 1998 to 2016, tested once on 2017 to 2019, compared with simple rules. |
| Rain | Usual rain for each month, rain of each year from 1901 to 2015, and a comparison of methods. | Each year, every method got the records up to the year before and guessed all 12 months. |
| Crops | Which crops may suit a district, how reliable that is, and what the model looks at. | Each district was judged by a model that never saw it. |

## What we found

We tested every model against a simple rule, and we report where the rule did as well.

- **Yield.** The forest missed by 9.7% in the middle on every test row, against 18.3% for the district's usual yield. Where last year's yield was known, repeating it missed by 8.4% and the forest by 9.1%. The model does not beat last year's number. It helps only when there is no history to copy.
- **Rain.** A seasonal model (SARIMA) beat the usual monthly pattern by 2.5% in Punjab and 2.1% in Haryana on the years used to choose methods, and by 8.5% and 7.8% on the later test years. The gain is small next to the size of the misses (about 22 mm for a month that usually has 44 to 50 mm), so the site shows the usual pattern and its range and does not promise the rain of a coming month.
- **Crops.** Across crops, the model ranked the right district higher 79 times out of 100. Its Brier score was 0.114 against 0.216 for always saying the average. It was off by 8 points or more in 3 of 6 probability groups. We show 6 crops that passed our own bar and explain why others are left out.

## What it leaves out

- Fertilizer advice: it needs soil test data that we do not have in a usable form.
- Market prices: the price files we found were too messy or too short to test a forecast fairly.
- Water, soil and seed. The models see rain, temperature and humidity only.

## Data

The raw files are not in this repository. To run the scripts, put them in `data/raw` with these names.

| File | What it holds |
|---|---|
| `APY.csv` | Area and yield of each crop by district and season |
| `rainfall in india 1901-2015.csv` | Monthly rain by region, from the India Meteorological Department |
| `district wise rainfall normal.csv` | Usual rain of each district |

Temperature and humidity come from NASA POWER and are downloaded by `scripts/download_climate.py`. The cleaned tables the site uses are in `data/processed`.

## Run it on your computer

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python app.py
```

Then open http://127.0.0.1:5000. The site only reads the files in `data/processed`, so it needs just Flask. The other packages are for rebuilding the tables and models.

## Rebuild the tables and models

The main steps, in order:

1. Yield: `clean_yield.py`, `build_yield_table.py`, `train_yield.py`, `build_yield_data.py`
2. Rain: `clean_rain.py`, `rain_models_v2.py`, `build_rain_data.py`
3. Crops: `geocode_districts.py`, `fix_coords.py`, `download_climate.py`, `build_crop_table.py`, `train_crop.py`, `build_crop_site_table.py`, `explain_crop.py`, `save_shap.py`, `build_crops_data.py`
4. Site: `build_site_data.py`, `build_district_pages.py`

Run each as `python scripts\name.py` from the project folder. The files `explore_*`, `yield_models_v1.py` to `v4`, `crop_models_v1.py`, `crop_models_v2.py` and `rain_models.py` are the earlier steps and experiments that led to the final choices. We kept them for the record.

## Folders

```
app.py            the website (Flask)
croplib.py        the crops model (logistic regression and random forest, averaged)
templates/        page templates
static/           styles, map script, icon
scripts/          every step from raw data to the site's data files
data/processed/   the cleaned tables and the JSON files the site reads
models/           saved models and their test results
reports/figures/  charts from the exploration and explanation steps
```

## Techniques

Random forest regression, rolling-year validation, simple baselines, AR, MA, ARIMA and SARIMA, logistic regression, leave-one-district-out validation, AUC, Brier score and calibration, SHAP and LIME.

## Screenshots

![A district page](docs/district.png)
![Crop yield](docs/yield.png)
![Rain](docs/rain.png)

## Notes

This is a college project and not advice for farmers. Data belongs to the bodies that published it.
