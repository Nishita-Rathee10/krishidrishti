import json
import math
import os
import re

from flask import Flask, abort, g, redirect, render_template, request, url_for

from i18n import tr

BASE = os.path.dirname(os.path.abspath(__file__))
SITE_NAME = "Krishi Drishti"
REPO_URL = "https://github.com/Nishita-Rathee10/krishidrishti"
FEEDBACK_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdAii2_v0d6XWRrVR7DLFfgW_5ac7wQ57DOckoCccmeGHz3Sw/viewform"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

app = Flask(__name__)


def page(path):
    """Register a page twice: at its English address and under /hi/ for Hindi."""
    def deco(fn):
        app.add_url_rule(path, endpoint=fn.__name__, view_func=fn)
        app.add_url_rule("/hi/" if path == "/" else "/hi" + path, endpoint=fn.__name__ + "_hi", view_func=fn)
        return fn
    return deco


@app.before_request
def pick_language():
    g.lang = "hi" if request.path == "/hi" or request.path.startswith("/hi/") else "en"


def lurl(endpoint, **values):
    if g.lang == "hi":
        endpoint += "_hi"
    return url_for(endpoint, **values)


def month_labels(i):
    letter = MONTHS[i][0] if g.lang == "en" else tr("letter:" + MONTH_ABBR[i])
    return {"month": tr(MONTHS[i]), "abbr": tr(MONTH_ABBR[i]), "letter": letter}


def season_label(s):
    s = "Whole year" if str(s).lower() == "whole year" else str(s)
    return tr(s)


WHY_RE = re.compile(r"^(.+) of ([0-9,.]+) (mm|\u00b0C|%)$")


def why_text(w):
    m = WHY_RE.match(w)
    if not m:
        return tr(w)
    label, value, unit = m.groups()
    return tr("{label} of {value} {unit}", label=tr(label), value=value, unit=tr(unit))


app.jinja_env.globals.update({"_": tr, "lurl": lurl, "season_label": season_label, "why_text": why_text})
app.jinja_env.filters["tr"] = tr


def load(name):
    with open(os.path.join(BASE, "data", "processed", name), encoding="utf-8") as fh:
        return json.load(fh)


DISTRICTS = load("districts.json")
PAGES = load("district_pages.json")
BY_SLUG = {d["slug"]: d for d in DISTRICTS["districts"]}
RAIN = load("rain_data.json")
CROPS = load("crops_data.json")
YIELD = load("yield_data.json")
CHECK = load("check_data.json")
GW = {}
with open(os.path.join(BASE, "data", "processed", "groundwater_district.csv"), encoding="utf-8") as _fh:
    import csv
    _by = {(d["state"], d["source_name"]): d["slug"] for d in DISTRICTS["districts"]}
    for _r in csv.DictReader(_fh):
        _slug = _by[(_r["State"], _r["District"])]
        _cat = _r["Category"]
        GW[_slug] = {"slug": _slug, "pct": float(_r["Stage_pct"]), "category": _cat, "year": _r["Assessed_as_on_March"],
                     "key": {"Over-exploited": "over", "Critical": "critical", "Semi-critical": "semi", "Safe": "safe"}[_cat]}
assert len(GW) == 44
CHECK_BY = {c["slug"]: c for c in CHECK["crops"]}
CROP_BY_SLUG = {c["slug"]: c for c in YIELD["crops"]}
SERIES_BY = {}
for _s in YIELD["series"].values():
    SERIES_BY.setdefault((_s["district"], _s["crop"]), {})[_s["season"]] = _s
YIELD_DISTRICTS = {}
for _slug in sorted({k[0] for k in SERIES_BY}, key=lambda x: BY_SLUG[x]["name"]):
    YIELD_DISTRICTS.setdefault(BY_SLUG[_slug]["state"], []).append({"slug": _slug, "name": BY_SLUG[_slug]["name"]})
SEASON_ORDER = {"Kharif": 0, "Rabi": 1, "Summer": 2, "Whole Year": 3}
MAX_RANGE_TOP = 100  # a likely range is shown only if its top end is at most this many percent above the guess


def temp_chart(values):
    top = 40.0
    return [dict(month_labels(i), value=v, label=f"{v:.0f}", pct=round(max(v, 0) / top * 100, 1))
            for i, v in enumerate(values)], int(top)


def rain_chart(rows):
    top = max(math.ceil(max(r["p90"] for r in rows) / 50.0) * 50, 50)
    out = []
    for r in rows:
        out.append({**month_labels(r["month"] - 1),
                    "mean": r["mean"], "p10": r["p10"], "p90": r["p90"],
                    "mean_pct": round(r["mean"] / top * 100, 1),
                    "lo_pct": round(r["p10"] / top * 100, 1),
                    "hi_pct": round((r["p90"] - r["p10"]) / top * 100, 1)})
    return out, top


def nice_axis(vmax):
    raw = vmax / 4.0
    mag = 10 ** math.floor(math.log10(raw))
    step = 10 * mag
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            step = m * mag
            break
    n = math.ceil(vmax / step)
    return step, n * step


def num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def yield_chart(series, show_range):
    w, h, left, right, top_m, bottom_m = 760, 340, 56, 14, 16, 44
    x0, x1 = 1998, 2019
    vals = list(series["yield"])
    for t in series["test"]:
        vals += [t["pred"]] + ([t["hi"]] if show_range else [])
    step, ymax = nice_axis(max(vals) * 1.05)
    inner_w, inner_h = w - left - right, h - top_m - bottom_m

    def sx(year):
        return round(left + (year - (x0 - 0.5)) / (x1 - x0 + 1) * inner_w, 1)

    def sy(v):
        return round(top_m + inner_h - v / ymax * inner_h, 1)

    unit = inner_w / (x1 - x0 + 1)
    ticks = [{"y": sy(i * step), "label": num(i * step)} for i in range(int(round(ymax / step)) + 1)]
    xticks = [{"x": sx(y), "label": str(y)} for y in (2000, 2005, 2010, 2015, 2019)]
    path, pts, prev = [], [], None
    for yr, v in zip(series["years"], series["yield"]):
        cmd = "L" if prev is not None and yr - prev == 1 else "M"
        path.append(f"{cmd}{sx(yr)} {sy(v)}")
        pts.append({"x": sx(yr), "y": sy(v), "year": yr, "v": v})
        prev = yr
    marks, ranges = [], []
    for t in series["test"]:
        marks.append({"x1": round(sx(t["year"]) - unit * 0.38, 1), "x2": round(sx(t["year"]) + unit * 0.38, 1), "y": sy(t["pred"])})
        if show_range:
            ranges.append({"x": round(sx(t["year"]) - unit * 0.38, 1), "y": sy(t["hi"]), "w": round(unit * 0.76, 1),
                           "h": round(sy(t["lo"]) - sy(t["hi"]), 1)})
    return {"w": w, "h": h, "left": left, "right": w - right, "base": sy(0), "ticks": ticks, "xticks": xticks,
            "path": " ".join(path), "pts": pts, "marks": marks, "ranges": ranges,
            "zone_x": round(sx(2017) - unit / 2, 1), "zone_w": round(unit * 3, 1), "top": top_m}


def rain_year_chart(r):
    w, h, left, right, top_m, bottom_m = 760, 300, 56, 14, 16, 36
    step, ymax = nice_axis(max(r["annual"]) * 1.04)
    inner_w, inner_h = w - left - right, h - top_m - bottom_m
    n = len(r["years"])
    slot = inner_w / n

    def sy(v):
        return round(top_m + inner_h - v / ymax * inner_h, 1)

    bars = [{"x": round(left + i * slot + slot * 0.12, 1), "w": round(slot * 0.76, 1), "y": sy(v),
             "h": round(v / ymax * inner_h, 1), "year": yr, "v": int(v)}
            for i, (yr, v) in enumerate(zip(r["years"], r["annual"]))]
    ticks = [{"y": sy(i * step), "label": num(i * step)} for i in range(int(round(ymax / step)) + 1)]
    xticks = [{"x": round(left + (yr - r["years"][0] + 0.5) * slot, 1), "label": str(yr)} for yr in (1910, 1930, 1950, 1970, 1990, 2010)]
    return {"w": w, "h": h, "left": left, "right": w - right, "base": sy(0), "bars": bars, "ticks": ticks, "xticks": xticks,
            "mean_y": sy(r["annual_mean"]), "band_y": sy(r["annual_p90"]), "band_h": round(sy(r["annual_p10"]) - sy(r["annual_p90"]), 1)}


@app.context_processor
def inject_site():
    path = request.path
    if g.lang == "hi":
        en_path = path[3:] or "/"
        hi_path = path
    else:
        en_path = path
        hi_path = "/hi/" if path == "/" else "/hi" + path
    query = request.query_string.decode("utf-8")
    alt_path = (en_path if g.lang == "hi" else hi_path) + ("?" + query if query else "")
    site_url = os.environ.get("SITE_URL", "").rstrip("/")
    return {"repo_url": REPO_URL, "feedback_url": FEEDBACK_URL, "site_name": SITE_NAME, "site_url": site_url,
            "lang": g.lang, "alt_path": alt_path, "en_path": en_path, "hi_path": hi_path,
            "base_url": site_url or request.url_root.rstrip("/")}


def map_payload():
    districts = []
    for d in DISTRICTS["districts"]:
        districts.append(dict(d, name=str(tr(d["name"])), state_label=str(tr(d["state"]))))
    districts.sort(key=lambda x: x["name"])
    text = {k: str(tr(v)) for k, v in {
        "rain": "Yearly rain", "winter": "Winter temperature", "summer": "Peak summer heat", "mm": "mm",
        "note": "Rain is the average of 1986 to 2015. Temperatures come from a NASA model for 2001 to 2025. Peak summer heat is the highest temperature the model shows in April, May and June, so it reads far higher than a normal day.",
        "note_approx": "Rain for this district is copied from the district it was carved out of.",
        "open": "Open the {name} page", "empty": "Choose a district from the list, or select a square on the map."}.items()}
    return dict(DISTRICTS, districts=districts, text=text, prefix="/hi" if g.lang == "hi" else "")


@page("/")
def index():
    return render_template("index.html", map_data=map_payload())


@page("/district/<slug>")
def district(slug):
    d = BY_SLUG.get(slug)
    if d is None:
        abort(404)
    page = PAGES["districts"][slug]
    temps, temp_top = temp_chart(page["temp"])
    rain_rows, rain_top = rain_chart(PAGES["rain"][d["state"]]["rows"])
    near = [{"slug": n["slug"], "name": BY_SLUG[n["slug"]]["name"], "km": n["km"]} for n in page["near"]]
    return render_template("district.html", d=d, page=page, temps=temps, temp_top=temp_top,
                           rain_rows=rain_rows, rain_top=rain_top, near=near, months=MONTHS, gw=GW.get(slug))


@page("/yield")
def yield_page():
    dslug = request.args.get("district", "ludhiana")
    cslug = request.args.get("crop", "wheat")
    if dslug not in BY_SLUG:
        dslug = "ludhiana"
    if cslug not in CROP_BY_SLUG:
        cslug = "wheat"
    by_season = SERIES_BY.get((dslug, cslug), {})
    seasons = sorted(by_season, key=lambda x: SEASON_ORDER.get(x, 9))
    season = request.args.get("season", "")
    if season not in by_season and seasons:
        season = seasons[0]
    series = by_season.get(season)
    crop = CROP_BY_SLUG[cslug]
    show_range = crop["range_high_pct"] <= MAX_RANGE_TOP
    chart = yield_chart(series, show_range) if series else None
    available = sorted({CROP_BY_SLUG[k[1]]["name"] for k in SERIES_BY if k[0] == dslug})
    summary = {r["Method"]: r for r in YIELD["summary"]}
    rows = []
    for c in YIELD["crops"]:
        diff = (c["forest_error_history"] or 0) - (c["last_year_error_history"] or 0)
        better = "Model" if diff <= -0.5 else ("Last year" if diff >= 0.5 else "Tie")
        rows.append(dict(c, better=better, range_ok=c["range_high_pct"] <= MAX_RANGE_TOP))
    return render_template("yield.html", d=BY_SLUG[dslug], crop=crop, cslug=cslug, season=season, seasons=seasons,
                           series=series, chart=chart, show_range=show_range, available=available,
                           groups=YIELD_DISTRICTS, crops=YIELD["crops"], rows=rows, sm=summary, ydata=YIELD,
                           max_top=MAX_RANGE_TOP)


@page("/rain")
def rain_page():
    slug = request.args.get("region", "punjab")
    if slug not in RAIN["regions"]:
        slug = "punjab"
    r = RAIN["regions"][slug]
    month_rows, month_top = rain_chart(r["months"])
    sar = next(m for m in r["models"] if m["is_sarima"])
    return render_template("rain.html", r=r, slug=slug, regions=RAIN["regions"], month_rows=month_rows, month_top=month_top,
                           ychart=rain_year_chart(r), sar=sar, val_years=RAIN["val_years"], test_years=RAIN["test_years"],
                           usual_month=round(r["annual_mean"] / 12))


@page("/crops")
def crops_page():
    g = CROPS["shap"]["global"]
    top = max(x["value"] for x in g)
    bars = [{"label": x["label"], "pct": round(100 * x["value"] / top, 1), "share": x["share"]} for x in g]
    return render_template("crops.html", c=CROPS, bars=bars)


@page("/check")
def check_page():
    dslug = request.args.get("district", "")
    cslug = request.args.get("crop", "")
    asked = dslug in BY_SLUG and cslug in CHECK_BY
    d = BY_SLUG.get(dslug) or BY_SLUG["ludhiana"]
    crop = CHECK_BY.get(cslug) or CHECK["crops"][0]
    res = CHECK["districts"][d["slug"]].get(crop["slug"]) if asked else None
    return render_template("check.html", d=d, crop=crop, crops=CHECK["crops"], groups=YIELD_DISTRICTS,
                           asked=asked, res=res, gw=GW.get(d["slug"]))


@page("/methods")
def methods_page():
    ys = {r["Method"]: r for r in YIELD["summary"]}
    sar = {k: next(m for m in v["models"] if m["is_sarima"]) for k, v in RAIN["regions"].items()}
    return render_template("methods.html", ys=ys, sar=sar, rain=RAIN, c=CROPS, n_districts=len(DISTRICTS["districts"]))


@page("/about")
def about_page():
    return render_template("about.html")


@page("/privacy")
def privacy_page():
    return render_template("privacy.html")


@app.route("/robots.txt")
def robots():
    from flask import Response
    base = os.environ.get("SITE_URL", "").rstrip("/")
    lines = ["User-agent: *", "Allow: /"]
    if base:
        lines.append(f"Sitemap: {base}/sitemap.xml")
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    from flask import Response
    base = os.environ.get("SITE_URL", "").rstrip("/") or request.url_root.rstrip("/")
    paths = ["/", "/check", "/yield", "/rain", "/crops", "/methods", "/about", "/privacy"]
    paths += [f"/district/{d['slug']}" for d in DISTRICTS["districts"]]
    paths += ["/hi/" if p == "/" else "/hi" + p for p in paths]
    body = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    body += [f"<url><loc>{base}{p}</loc></url>" for p in paths]
    body.append("</urlset>")
    return Response("\n".join(body), mimetype="application/xml")


@app.route("/favicon.ico")
def favicon():
    return redirect(url_for("static", filename="img/favicon.svg"), code=301)


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500


@app.after_request
def add_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    return resp


if __name__ == "__main__":
    app.run(debug=True)
