#!/usr/bin/env python3
"""
SignalCare — locally hosted clinician dashboard (merge 03).
Run:  python app.py        → http://localhost:5050
"""

import json
import os
from flask import Flask, render_template, jsonify, request

from data_loader import load_or_generate

app = Flask(__name__)

print("Loading patient data...")
MERGED, SURVEY_BY_PID, CLUSTER_SURVEY = load_or_generate()
print(f"  {len(MERGED['patients'])} patients ready\n")

# ── Server-side stores (replace localStorage for demo) ──
NOTES = []
ACCESS_CODES = []
UPLOADS = []


@app.route("/")
def index():
    return render_template("index.html")


# ── Data API ──

@app.route("/api/patients")
def api_patients():
    return jsonify(MERGED)


@app.route("/api/survey")
def api_survey():
    return jsonify(SURVEY_BY_PID)


@app.route("/api/cluster-survey")
def api_cluster_survey():
    return jsonify(CLUSTER_SURVEY)


# ── Notes API ──

@app.route("/api/notes")
def api_notes():
    pid = request.args.get("pid")
    if pid:
        return jsonify([n for n in NOTES if n["patientId"] == pid])
    return jsonify(NOTES)


@app.route("/api/notes", methods=["POST"])
def api_add_note():
    note = request.get_json()
    NOTES.insert(0, note)
    return jsonify({"ok": True}), 201


@app.route("/api/notes/<note_id>", methods=["DELETE"])
def api_delete_note(note_id):
    global NOTES
    NOTES = [n for n in NOTES if n.get("id") != note_id]
    return jsonify({"ok": True})


# ── Access codes API ──

@app.route("/api/codes")
def api_codes():
    return jsonify(ACCESS_CODES)


@app.route("/api/codes", methods=["POST"])
def api_add_code():
    entry = request.get_json()
    ACCESS_CODES.insert(0, entry)
    return jsonify({"ok": True}), 201


@app.route("/api/codes/<code_id>/revoke", methods=["POST"])
def api_revoke_code(code_id):
    for c in ACCESS_CODES:
        if c.get("id") == code_id:
            c["revoked"] = True
    return jsonify({"ok": True})


@app.route("/api/codes/<code_id>/redeem", methods=["POST"])
def api_redeem_code(code_id):
    data = request.get_json() or {}
    for c in ACCESS_CODES:
        if c.get("id") == code_id:
            c["redeemedAt"] = data.get("redeemedAt")
    return jsonify({"ok": True})


@app.route("/api/codes/purge", methods=["POST"])
def api_purge_codes():
    ACCESS_CODES.clear()
    return jsonify({"ok": True})


# ── Uploads API ──

@app.route("/api/uploads")
def api_uploads():
    pid = request.args.get("pid")
    if pid:
        return jsonify([u for u in UPLOADS if u["patientId"] == pid])
    return jsonify(UPLOADS)


@app.route("/api/uploads", methods=["POST"])
def api_add_upload():
    entry = request.get_json()
    UPLOADS.insert(0, entry)
    return jsonify({"ok": True}), 201


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
