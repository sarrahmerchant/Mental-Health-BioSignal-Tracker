#!/usr/bin/env python3
"""
Merge 02: Combines Sander + Emma data/charts (from merge 01) with Sarrah's
workflow features (sidebar, triage, patient directory, access codes, patient portal).

Output: a single self-contained HTML file.
"""

import json
import re
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SANDER_HTML = os.path.join(
    BASE, "backend_02_sander", "Mental-Health-BioSignal-Tracker-sander-random",
    "signalcare_dashboard.html",
)
EMMA_JS = os.path.join(
    BASE, "backend_01_emma", "Mental-Health-BioSignal-Tracker-emma",
    "dashboard", "data", "dashboard_data.js",
)
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "signalcare_dashboard.html")


def extract_sander_data(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"const DATA = ({.*?});", text, re.DOTALL)
    data = json.loads(m.group(1))
    m2 = re.search(r"const CLUSTER_BY_PID = ({.*?});", text, re.DOTALL)
    cluster_by_pid = json.loads(m2.group(1)) if m2 else {}
    m3 = re.search(r"const SURVEY_BY_PID = ({.*?});", text, re.DOTALL)
    survey_by_pid = json.loads(m3.group(1)) if m3 else {}
    m4 = re.search(r"const CLUSTER_SURVEY_TRAJECTORIES = ({.*?});", text, re.DOTALL)
    cluster_survey = json.loads(m4.group(1)) if m4 else {}
    return data, cluster_by_pid, survey_by_pid, cluster_survey


def extract_emma_data(js_path):
    with open(js_path, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"window\.SIGNALCARE_DATA = ({.*})", text, re.DOTALL)
    return json.loads(m.group(1))


def merge_patients(sander_data, emma_data, cluster_by_pid):
    sander_by_pid = {p["pid"]: p for p in sander_data["patients"]}
    emma_by_pid = {p["pid"]: p for p in emma_data["patients"]}
    all_pids = list(dict.fromkeys(
        [p["pid"] for p in sander_data["patients"]]
        + [p["pid"] for p in emma_data["patients"]]
    ))
    merged = []
    for pid in all_pids:
        sp = sander_by_pid.get(pid, {})
        ep = emma_by_pid.get(pid, {})
        sm = sp.get("metrics", {})
        em = ep.get("metrics", {})
        s_sparks = sp.get("sparks", {})
        e_sparks = ep.get("sparks", {})
        patient = {
            "pid": pid,
            "status": sp.get("status", ep.get("status", "stable")),
            "status_order": sp.get("status_order", ep.get("status_order", 1)),
            "alerts": sp.get("alerts", ep.get("alerts", 0)),
            "days": sp.get("days", ep.get("days", 0)),
            "cluster": cluster_by_pid.get(pid, 0),
            "metrics": {
                "stress": sm.get("stress", "N/A"),
                "hrv": sm.get("hrv", em.get("rmssd", "N/A")),
                "hr": sm.get("hr", em.get("hr", "N/A")),
                "sleep": sm.get("sleep", "N/A"),
                "isi": em.get("isi", "N/A"),
                "phq9": em.get("phq9", "N/A"),
                "gad7": em.get("gad7", "N/A"),
                "rmssd": em.get("rmssd", sm.get("hrv", "N/A")),
                "lf_hf": em.get("lf_hf", "N/A"),
            },
            "sparks": {
                "hrv": s_sparks.get("hrv", e_sparks.get("rmssd", "")),
                "hr": s_sparks.get("hr", e_sparks.get("hr", "")),
                "stress": s_sparks.get("stress", ""),
                "sleep": s_sparks.get("sleep", ""),
                "isi": e_sparks.get("isi", ""),
                "phq9": e_sparks.get("phq9", ""),
                "gad7": e_sparks.get("gad7", ""),
                "rmssd": e_sparks.get("rmssd", s_sparks.get("hrv", "")),
            },
            "series": {**sp.get("series", {}), **ep.get("series", {})},
            "sander_series": sp.get("series", {}),
            "emma_series": ep.get("series", {}),
            "forecast": sp.get("forecast", ep.get("forecast", {"alerts": []})),
            "emma_forecast": ep.get("forecast", {}),
            "explanation": sp.get("explanation", ep.get("explanation", {})),
            "emma_explanation": ep.get("explanation", {}),
            "neighbors": sp.get("neighbors", []),
        }
        merged.append(patient)
    return {"patients": merged, "metadata": emma_data.get("metadata", {})}


TEMPLATE_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "template.html")


def build_html(merged_data, survey_by_pid, cluster_survey):
    d = json.dumps(merged_data, separators=(",", ":"))
    s = json.dumps(survey_by_pid, separators=(",", ":"))
    cs = json.dumps(cluster_survey, separators=(",", ":"))

    with open(TEMPLATE_HTML, "r", encoding="utf-8") as f:
        tmpl = f.read()

    return (tmpl
            .replace("__DATA_JSON__", d)
            .replace("__SURVEY_JSON__", s)
            .replace("__CSUR_JSON__", cs))



def main():
    print("Extracting Sander data...")
    sander_data, cluster_by_pid, survey_by_pid, cluster_survey = extract_sander_data(SANDER_HTML)
    print(f"  {len(sander_data['patients'])} patients")
    print("Extracting Emma data...")
    emma_data = extract_emma_data(EMMA_JS)
    print(f"  {len(emma_data['patients'])} patients")
    print("Merging patient data...")
    merged = merge_patients(sander_data, emma_data, cluster_by_pid)
    print(f"  {len(merged['patients'])} merged patients")
    print("Generating HTML (merge 02: sander + emma + sarrah)...")
    html = build_html(merged, survey_by_pid, cluster_survey)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"Done! Output: {OUTPUT} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
