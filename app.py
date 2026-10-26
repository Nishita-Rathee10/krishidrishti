import json
import math
import os

from flask import Flask, abort, redirect, render_template, url_for

BASE = os.path.dirname(os.path.abspath(__file__))
SITE_NAME = "Krishi Drishti"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]

app = Flask(__name__)


def load(name):
    with open(os.path.join(BASE, "data", "processed", name), encoding="utf-8") as fh:
        return json.load(fh)


DISTRICTS = load("districts.json")
PAGES = load("district_pages.json")
BY_SLUG = {d["slug"]: d for d in DISTRICTS["districts"]}


def temp_chart(values):
    top = 40.0
    return [{"month": MONTHS[i], "letter": MONTHS[i][0], "value": v, "label": f"{v:.0f}",
             "pct": round(max(v, 0) / top * 100, 1)} for i, v in enumerate(values)], int(top)


def rain_chart(rows):
    top = max(math.ceil(max(r["p90"] for r in rows) / 50.0) * 50, 50)
    out = []
    for r in rows:
        out.append({"month": MONTHS[r["month"] - 1], "letter": MONTHS[r["month"] - 1][0],
                    "mean": r["mean"], "p10": r["p10"], "p90": r["p90"],
                    "mean_pct": round(r["mean"] / top * 100, 1),
                    "lo_pct": round(r["p10"] / top * 100, 1),
                    "hi_pct": round((r["p90"] - r["p10"]) / top * 100, 1)})
    return out, top


@app.context_processor
def inject_site():
    return {"site_name": SITE_NAME, "site_url": os.environ.get("SITE_URL", "").rstrip("/")}


@app.route("/")
def index():
    return render_template("index.html", map_data=DISTRICTS)


@app.route("/district/<slug>")
def district(slug):
    d = BY_SLUG.get(slug)
    if d is None:
        abort(404)
    page = PAGES["districts"][slug]
    temps, temp_top = temp_chart(page["temp"])
    rain_rows, rain_top = rain_chart(PAGES["rain"][d["state"]]["rows"])
    near = [{"slug": n["slug"], "name": BY_SLUG[n["slug"]]["name"], "km": n["km"]} for n in page["near"]]
    return render_template("district.html", d=d, page=page, temps=temps, temp_top=temp_top,
                           rain_rows=rain_rows, rain_top=rain_top, near=near, months=MONTHS)


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
