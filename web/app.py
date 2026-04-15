"""
app.py — Flask server for bullets editor

Run:   python app.py
Open:  http://localhost:5000
"""

import os
import shutil
from flask import Flask, jsonify, request, send_from_directory
from lua_parser import read_bullets, read_proficiency_keys, lua_serialize
from reindex import reindex_from_cache

STATIC_DIR   = os.path.join(os.path.dirname(__file__), "static")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BULLETS_PATH = os.path.join(PROJECT_ROOT, "data", "bullets.lua")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "editor.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.dirname(__file__), "favicon.ico")


@app.route("/api/bullets", methods=["GET"])
def get_bullets():
    bullets = read_bullets()
    keys    = read_proficiency_keys()
    return jsonify({"bullets": bullets, "pm_keys": keys["pm"], "pmm_keys": keys["pmm"]})


@app.route("/api/bullets", methods=["POST"])
def save_bullets():
    data       = request.get_json(force=True)
    new_bullets = data.get("bullets", [])

    # Read old bullets (with cached_idx) before overwriting
    old_bullets = read_bullets()

    shutil.copy2(BULLETS_PATH, BULLETS_PATH + ".bak")

    # Diff indices, patch tex files, inject updated cached_idx
    updated, changes = reindex_from_cache(old_bullets, new_bullets)

    with open(BULLETS_PATH, "w") as f:
        f.write(lua_serialize(updated))

    return jsonify({"ok": True, "reindex": {
        tex: {cmd: {"from": old, "to": new} for cmd, (old, new) in cmds.items()}
        for tex, cmds in changes.items()
    }})


if __name__ == "__main__":
    print("Bullets editor → http://localhost:5001")
    app.run(debug=True, port=5001)
