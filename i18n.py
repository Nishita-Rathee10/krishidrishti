"""Small translation helper. English text is the key, translations/hi.json holds the Hindi."""
import json
import os

from flask import g
from markupsafe import Markup

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translations", "hi.json")
with open(_PATH, encoding="utf-8") as fh:
    HI = json.load(fh)

MISSING = set()  # English texts that were asked for in Hindi but have no translation yet


def tr(text, **values):
    """Return the text in the language of the current page. Values are filled into {name} spots and escaped."""
    text = str(text)
    if getattr(g, "lang", "en") == "hi":
        found = HI.get(text)
        if found is None:
            MISSING.add(text)
        else:
            text = found
    out = Markup(text)
    return out.format(**values) if values else out
