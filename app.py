import json
import os

from flask import Flask, redirect, render_template, url_for

BASE = os.path.dirname(os.path.abspath(__file__))
SITE_NAME = "Krishi Drishti"

app = Flask(__name__)

with open(os.path.join(BASE, "data", "processed", "districts.json"), encoding="utf-8") as fh:
    DISTRICTS = json.load(fh)


@app.context_processor
def inject_site():
    return {"site_name": SITE_NAME, "site_url": os.environ.get("SITE_URL", "").rstrip("/")}


@app.route("/")
def index():
    return render_template("index.html", map_data=DISTRICTS)


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