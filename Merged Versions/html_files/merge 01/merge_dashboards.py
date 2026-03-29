#!/usr/bin/env python3
"""
Merge Sander's and Emma's SignalCare dashboards into a single HTML file.

Reads embedded data from sander's HTML and emma's dashboard_data.js,
merges patients by PID, and generates a unified dashboard with features
from both projects.
"""

import json
import re
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SANDER_HTML = os.path.join(
    BASE,
    "sander",
    "Mental-Health-BioSignal-Tracker-sander-random",
    "signalcare_dashboard.html",
)
EMMA_JS = os.path.join(
    BASE,
    "emma",
    "Mental-Health-BioSignal-Tracker-emma",
    "dashboard",
    "data",
    "dashboard_data.js",
)
OUTPUT = os.path.join(BASE, "signalcare_merged_dashboard.html")


def extract_sander_data(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        text = f.read()

    m = re.search(r"const DATA = ({.*?});", text, re.DOTALL)
    if not m:
        raise ValueError("Could not find DATA in sander HTML")
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
    if not m:
        raise ValueError("Could not find SIGNALCARE_DATA in emma JS")
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


def build_html(merged_data, survey_by_pid, cluster_survey):
    data_json = json.dumps(merged_data, separators=(",", ":"))
    survey_json = json.dumps(survey_by_pid, separators=(",", ":"))
    cluster_survey_json = json.dumps(cluster_survey, separators=(",", ":"))

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SignalCare — Merged Dashboard</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root{{
      --bg:#f4f6f6;--surface:#ffffff;--muted:#6b7280;--border:#dde1e1;--teal:#00534a;--teal-2:#00695c;
      --blue:#2196F3;--red:#E53935;--orange:#FB8C00;--green:#00897B;--violet:#7E57C2;
    }}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:Segoe UI,Arial,sans-serif;background:var(--bg);color:#1f2937}}
    .app-header{{background:linear-gradient(135deg,var(--teal),#003d36);padding:14px 28px;color:#fff;display:flex;justify-content:space-between;align-items:center}}
    .brand{{font-size:18px;font-weight:700}}
    .brand-sub{{font-size:11px;opacity:.7;margin-left:8px;font-weight:400}}
    .user{{font-size:13px;opacity:.9}}
    .breadcrumb{{background:#e4edeb;border-bottom:1px solid #c8d8d5;padding:10px 28px;font-size:12px;font-weight:700;color:var(--teal-2);text-transform:uppercase;letter-spacing:.4px}}
    .wrap{{max-width:1400px;margin:0 auto;padding:22px 22px 34px}}
    .title h1{{margin:0;font-size:24px}}
    .title p{{margin:8px 0 0;color:#555}}
    .filters{{display:grid;grid-template-columns:2.2fr 1.2fr 1.2fr 1.2fr 140px;gap:16px;margin-top:16px}}
    .field label{{display:block;font-size:12px;font-weight:700;color:#444;text-transform:uppercase;letter-spacing:.45px;margin-bottom:8px}}
    .field input,.field select,.field button{{width:100%;height:44px;border-radius:10px;border:1px solid var(--border);background:#fff;padding:0 14px;font-size:14px}}
    .field button{{cursor:pointer;font-weight:700;transition:background .15s}}
    .field button:hover{{background:#e8f0ef}}
    .section-hdr{{margin-top:24px;border-bottom:2px solid var(--teal-2);padding-bottom:8px;font-size:14px;font-weight:800;text-transform:uppercase;letter-spacing:.5px}}
    .table-wrap{{margin-top:10px;background:#fff;border:1px solid var(--border);border-radius:10px;overflow:auto}}
    table{{width:100%;min-width:1200px;border-collapse:collapse}}
    thead th{{background:#eef1f1;font-size:11px;text-transform:uppercase;letter-spacing:.6px;padding:12px;border-bottom:2px solid #cfd5d4;text-align:left;cursor:pointer;user-select:none}}
    thead th:hover{{background:#e5ebea}}
    thead th .sub{{display:block;font-size:10px;font-weight:400;color:#888;text-transform:none;letter-spacing:0;margin-top:2px}}
    thead th .sort{{display:inline-block;margin-left:6px;font-size:10px;color:#a3a3a3}}
    thead th.active .sort{{color:#00695c}}
    tbody td{{padding:12px;border-bottom:1px solid #eaeded;white-space:nowrap}}
    tbody tr{{cursor:pointer}}
    tbody tr:hover{{background:#e8f0ef}}
    .metric{{display:flex;align-items:center;gap:8px}}
    .metric .val{{font-weight:700;font-size:14px}}
    .dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px}}
    .dot.declining{{background:#E53935}}.dot.stable{{background:#FFA726}}.dot.improving{{background:#43A047}}
    .status{{display:inline-flex;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700}}
    .status.declining{{background:#fde8e8;color:#c62828}}
    .status.stable{{background:#fff3e0;color:#e65100}}
    .status.improving{{background:#e8f5e9;color:#2e7d32}}
    .badge{{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;font-size:12px;font-weight:700}}
    .badge.red{{background:#E53935;color:#fff}}.badge.zero{{color:#999}}
    .hidden{{display:none !important}}
    .top-row{{display:flex;justify-content:space-between;align-items:center;margin-top:12px}}
    .back-btn{{height:40px;padding:0 14px;border-radius:10px;border:1px solid var(--border);background:#fff;cursor:pointer;font-weight:700}}
    .back-btn:hover{{background:#e8f0ef}}
    .patient-banner{{background:#fff;border:1px solid var(--border);border-radius:10px;padding:18px 22px;margin-top:14px;display:flex;gap:22px;align-items:center;flex-wrap:wrap}}
    .pid{{font-size:22px;font-weight:800;color:var(--teal-2)}}
    .stat{{font-size:14px;color:#555}}
    .mini-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:12px;margin-top:12px}}
    .mini{{background:#fff;border:1px solid var(--border);border-radius:10px;padding:14px 16px}}
    .mini .k{{font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:800;letter-spacing:.5px;margin-bottom:6px}}
    .mini .v{{font-size:24px;font-weight:800}}
    .content{{display:grid;grid-template-columns:1.6fr .95fr;gap:16px;margin-top:12px}}
    .card{{background:#fff;border:1px solid var(--border);border-radius:10px;padding:14px;margin-top:0}}
    .card+.card{{margin-top:12px}}
    .card h3{{margin:0 0 10px;font-size:13px;color:var(--teal-2);text-transform:uppercase;letter-spacing:.35px}}
    .chart-card{{padding:14px 14px 10px}}
    .chart-title{{font-size:14px;font-weight:800;margin:2px 0 10px}}
    .fact{{background:#f8fafb;border:1px solid #e5eaec;border-radius:8px;padding:10px 12px;margin-top:8px}}
    .fact strong{{display:block;font-size:12px;color:#374151;margin-bottom:4px}}
    .fact span{{font-size:13px;line-height:1.55}}
    .chip-wrap{{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}}
    .chip{{display:inline-flex;padding:6px 10px;border-radius:999px;font-size:12px;font-weight:700}}
    .chip.risk{{background:#fff5f5;color:#b42318;border:1px solid #f3d1d1}}
    .chip.protective{{background:#f3fbf8;color:#0f766e;border:1px solid #cfe9df}}
    .alert-row{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;padding:10px 12px;border:1px solid #f0d3d3;background:#fff7f7;border-radius:8px;margin-top:8px}}
    .alert-title{{font-size:13px;font-weight:800;color:#b42318}}
    .alert-meta{{font-size:12px;color:#6b7280;margin-top:3px}}
    .alert-pill{{padding:4px 8px;border-radius:999px;background:#fde8e8;color:#c62828;font-size:11px;font-weight:800;text-transform:uppercase}}
    .neighbor{{display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border:1px solid #e5eaec;border-radius:8px;background:#fff;margin-top:8px;cursor:pointer}}
    .neighbor:hover{{background:#f7fbfa;border-color:#dbe8e5}}
    .neighbor-left{{display:flex;align-items:center;gap:10px}}
    .rank{{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:#e8f0ef;color:var(--teal-2);font-size:12px;font-weight:800}}
    .neighbor a{{color:#00796B;text-decoration:none;font-weight:800}}
    .neighbor a:hover{{text-decoration:underline}}
    .muted{{font-size:12px;color:#6b7280}}
    .section-title{{font-size:12px;font-weight:800;color:#6b7280;text-transform:uppercase;letter-spacing:.45px;margin:10px 0 6px}}
    .footer{{margin-top:22px;padding-top:14px;border-top:1px solid #dde1e1;font-size:12px;color:#6b7280}}
    .plotly-chart{{width:100%;height:320px}}
    .plotly-chart.small{{height:280px}}
    .plotly-chart.forecast{{height:300px}}
    .small-multiples{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
    .small-plot{{border:1px solid #e6ebeb;border-radius:8px;padding:10px;background:#fcfdfd}}
    .small-plot h4{{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.45px;color:#4b5563;display:flex;align-items:center;gap:6px}}
    .small-plot .plot{{height:180px;width:100%}}
    .help-wrap{{position:relative;display:inline-flex;align-items:center}}
    .help-dot{{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border-radius:50%;background:#e6f3f1;color:var(--teal-2);font-size:12px;font-weight:800;cursor:help;margin-left:6px}}
    .help-popover{{position:absolute;left:22px;top:-4px;min-width:220px;max-width:300px;background:#0f172a;color:#fff;border-radius:8px;padding:8px 10px;font-size:11px;line-height:1.4;opacity:0;transform:translateY(2px);pointer-events:none;transition:opacity .08s ease,transform .08s ease;z-index:20;text-transform:none;letter-spacing:0;font-weight:500}}
    .help-wrap:hover .help-popover,.help-wrap:focus-within .help-popover{{opacity:1;transform:translateY(0)}}
    .tab-bar{{display:flex;gap:0;border-bottom:2px solid var(--border);margin-bottom:12px}}
    .tab{{padding:8px 16px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;transition:all .15s}}
    .tab:hover{{color:var(--teal-2)}}
    .tab.active{{color:var(--teal-2);border-bottom-color:var(--teal-2)}}
    .tab-panel{{display:none}}
    .tab-panel.active{{display:block}}
    @media (max-width: 1200px){{
      .filters{{grid-template-columns:1fr 1fr}}
      .mini-grid{{grid-template-columns:repeat(4,1fr)}}
      .content{{grid-template-columns:1fr}}
    }}
    @media (max-width: 900px){{
      .small-multiples{{grid-template-columns:1fr 1fr}}
      .mini-grid{{grid-template-columns:repeat(3,1fr)}}
    }}
    @media (max-width: 640px){{
      .small-multiples{{grid-template-columns:1fr}}
      .mini-grid{{grid-template-columns:1fr 1fr}}
      .wrap{{padding:16px}}
    }}
  </style>
</head>
<body>
  <div class="app-header">
    <div class="brand">SignalCare<span class="brand-sub">Merged Dashboard</span></div>
    <div class="user">Clinician Dashboard</div>
  </div>
  <div class="breadcrumb" id="breadcrumb">Dashboard &rsaquo; Mental Health BioSignal Monitoring</div>
  <div class="wrap">
    <div id="list-view">
      <div class="title">
        <h1>Mental Health BioSignal Monitoring</h1>
        <p>Unified clinician view — stress scoring, physiology trends, mental health forecasts, clustering, and clinical context.</p>
      </div>
      <div class="filters">
        <div class="field">
          <label for="search">Search by patient ID</label>
          <input id="search" placeholder="e.g. am77" />
        </div>
        <div class="field">
          <label for="statusFilter">Status</label>
          <select id="statusFilter">
            <option value="">NO FILTER</option>
            <option value="declining">Declining</option>
            <option value="stable">Stable</option>
            <option value="improving">Improving</option>
          </select>
        </div>
        <div class="field">
          <label for="clusterFilter">Cluster</label>
          <select id="clusterFilter">
            <option value="">NO FILTER</option>
            <option value="0">Autonomically flexible</option>
            <option value="1">Low-reactivity</option>
            <option value="2">Dysregulated</option>
          </select>
        </div>
        <div class="field">
          <label for="alertFilter">Alerts</label>
          <select id="alertFilter">
            <option value="">NO FILTER</option>
            <option value="has">Has Alerts</option>
            <option value="none">No Alerts</option>
          </select>
        </div>
        <div class="field">
          <label>&nbsp;</label>
          <button id="resetBtn">Reset</button>
        </div>
      </div>
      <div class="section-hdr">Patients</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th data-sort="pid">Patient ID<span class="sort">&#9650;&#9660;</span></th>
              <th data-sort="hrv">HRV (RMSSD)<span class="sort">&#9650;&#9660;</span><span class="sub">2 wk trend &middot; Last reading</span></th>
              <th data-sort="hr">Heart Rate<span class="sort">&#9650;&#9660;</span><span class="sub">2 wk trend &middot; Last reading</span></th>
              <th data-sort="stress">Stress<span class="sort">&#9650;&#9660;</span><span class="sub">2 wk trend &middot; Last score</span></th>
              <th data-sort="isi">ISI<span class="sort">&#9650;&#9660;</span><span class="sub">Insomnia</span></th>
              <th data-sort="phq9">PHQ-9<span class="sort">&#9650;&#9660;</span><span class="sub">Depression</span></th>
              <th data-sort="gad7">GAD-7<span class="sort">&#9650;&#9660;</span><span class="sub">Anxiety</span></th>
              <th data-sort="alerts">Alerts<span class="sort">&#9650;&#9660;</span></th>
              <th data-sort="status_order">Status<span class="sort">&#9650;&#9660;</span></th>
            </tr>
          </thead>
          <tbody id="patient-table-body"></tbody>
        </table>
      </div>
    </div>

    <div id="detail-view" class="hidden">
      <div class="top-row">
        <button class="back-btn" id="backBtn">&larr; Back to patient list</button>
      </div>
      <div class="patient-banner" id="patient-banner"></div>
      <div class="mini-grid" id="mini-grid"></div>
      <div class="content">
        <div>
          <!-- Tabs for chart groups -->
          <div class="card chart-card">
            <div class="tab-bar" id="chart-tabs">
              <div class="tab active" data-tab="physiology">Physiology</div>
              <div class="tab" data-tab="stress">Stress &amp; Sleep</div>
              <div class="tab" data-tab="mental">Mental Health</div>
              <div class="tab" data-tab="survey">Survey</div>
            </div>

            <!-- Physiology tab: small multiples (from emma) -->
            <div class="tab-panel active" id="panel-physiology">
              <div class="chart-title">Individual Physiology Trends</div>
              <div class="small-multiples">
                <div class="small-plot"><h4>Heart Rate <span class="help-wrap"><span class="help-dot">?</span><span class="help-popover">Nightly mean heart rate in BPM. Persistent upward shifts can reflect strain, arousal, or poor recovery.</span></span></h4><div id="plot-hr" class="plot"></div></div>
                <div class="small-plot"><h4>RMSSD <span class="help-wrap"><span class="help-dot">?</span><span class="help-popover">Nightly vagal HRV marker in ms. Lower RMSSD over time can suggest reduced parasympathetic recovery.</span></span></h4><div id="plot-rmssd" class="plot"></div></div>
                <div class="small-plot"><h4>LF/HF <span class="help-wrap"><span class="help-dot">?</span><span class="help-popover">Sympathovagal balance proxy. Sustained increases can indicate sympathetic dominance.</span></span></h4><div id="plot-lfhf" class="plot"></div></div>
                <div class="small-plot"><h4>Sleep Hours <span class="help-wrap"><span class="help-dot">?</span><span class="help-popover">Total sleep duration per night. Large reductions may precede worsening symptoms.</span></span></h4><div id="plot-sleep-hrs" class="plot"></div></div>
                <div class="small-plot"><h4>Light Avg <span class="help-wrap"><span class="help-dot">?</span><span class="help-popover">Daily average ambient light exposure. Proxy for circadian rhythm regularity.</span></span></h4><div id="plot-light" class="plot"></div></div>
                <div class="small-plot"><h4>Calories <span class="help-wrap"><span class="help-dot">?</span><span class="help-popover">Daily total calories burned from all sensor segments.</span></span></h4><div id="plot-cal" class="plot"></div></div>
              </div>
            </div>

            <!-- Stress & Sleep tab (from sander) -->
            <div class="tab-panel" id="panel-stress">
              <div class="chart-title">HRV &amp; Stress Trajectory</div>
              <div id="chart-main" class="plotly-chart"></div>
              <div class="chart-title" style="margin-top:16px">Sleep Quality Trend</div>
              <div id="chart-sleep" class="plotly-chart small"></div>
              <div id="forecast-panel">
                <div class="chart-title" style="margin-top:16px">Stress Forecast vs Observed</div>
                <div id="chart-forecast" class="plotly-chart forecast"></div>
              </div>
            </div>

            <!-- Mental Health tab (from emma) -->
            <div class="tab-panel" id="panel-mental">
              <div class="chart-title">Mental Health Trajectory (Solid = Historical, Dotted = Forecast)</div>
              <div id="chart-mental" class="plotly-chart"></div>
            </div>

            <!-- Survey tab (from sander) -->
            <div class="tab-panel" id="panel-survey">
              <div class="chart-title">Survey Trajectory (ISI, PHQ-9, GAD-7)</div>
              <div id="chart-survey" class="plotly-chart forecast"></div>
            </div>
          </div>
        </div>
        <div>
          <div class="card">
            <h3>Cluster Profile</h3>
            <div id="cluster-card"></div>
          </div>
          <div class="card">
            <h3>Alerts</h3>
            <div id="alerts-card"></div>
          </div>
          <div class="card">
            <h3>Clinical Explanation</h3>
            <div id="explain-card"></div>
          </div>
          <div class="card">
            <h3>Similar Patients</h3>
            <div id="neighbors-card"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="footer">Screening support only — outputs are associated signals, not diagnoses. &nbsp;|&nbsp; Merged from Sander + Emma pipelines.</div>
  </div>

  <script>
    const DATA = {data_json};
    const SURVEY_BY_PID = {survey_json};
    const CLUSTER_SURVEY_TRAJECTORIES = {cluster_survey_json};

    const CLUSTER_META = {{
      0: {{
        name: "Autonomically flexible / resilient",
        insight: "High heart rate variability driven by strong parasympathetic (vagal) activity, combined with the ability to mount sympathetic responses — indicating a well-regulated and adaptive autonomic nervous system."
      }},
      1: {{
        name: "Low-reactivity / fragmented sleep",
        insight: "Reduced overall HRV and low spectral power, indicating a blunted or low-reactivity autonomic profile. Despite adequate sleep duration, these patients show fragmented sleep with frequent night-time wake events."
      }},
      2: {{
        name: "Dysregulated / sleep-impaired",
        insight: "Reduced vagal tone alongside a shift toward parasympathetic dominance, suggesting an imbalanced and less adaptive autonomic state. Worst sleep efficiency and highest insomnia severity in the cohort."
      }}
    }};

    const SURVEY_TIMEPOINTS = ["t0", "t2w", "t4w"];
    const STATE = {{ sortKey: "status_order", sortDir: "asc", selected: null }};

    function badge(n) {{
      return n ? `<span class="badge red">${{n}}</span>` : `<span class="badge zero">0</span>`;
    }}
    function statusPill(status) {{
      return `<span class="status ${{status}}">${{status.charAt(0).toUpperCase() + status.slice(1)}}</span>`;
    }}
    function dot(status) {{
      return `<span class="dot ${{status}}"></span>`;
    }}
    function esc(str) {{
      return String(str).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
    }}
    function chips(text, kind) {{
      const parts = String(text || "").split(";").map(s => s.trim()).filter(Boolean);
      if (!parts.length) return "";
      return `<div class="chip-wrap">${{parts.map(p => `<span class="chip ${{kind}}">${{esc(p)}}</span>`).join("")}}</div>`;
    }}
    function fmt(value, digits) {{
      if (digits === undefined) digits = 1;
      const num = Number(value);
      return Number.isFinite(num) ? num.toFixed(digits) : "N/A";
    }}
    function getCluster(p) {{
      const raw = p.cluster;
      const num = Number(raw);
      if (Number.isInteger(num) && num >= 0 && num <= 2) return num;
      return 0;
    }}
    function clusterMeta(idx) {{
      return CLUSTER_META[idx] || CLUSTER_META[0];
    }}

    const SORT_GETTERS = {{
      pid: p => p.pid.toLowerCase(),
      hrv: p => Number(p.metrics.hrv) || -1,
      hr: p => Number(p.metrics.hr) || -1,
      stress: p => Number(p.metrics.stress) || -1,
      isi: p => Number(p.metrics.isi) || -1,
      phq9: p => Number(p.metrics.phq9) || -1,
      gad7: p => Number(p.metrics.gad7) || -1,
      alerts: p => Number(p.alerts),
      status_order: p => Number(p.status_order)
    }};

    function renderSortHeaders() {{
      document.querySelectorAll("thead th[data-sort]").forEach(th => {{
        th.classList.remove("active");
        const icon = th.querySelector(".sort");
        if (!icon) return;
        if (th.dataset.sort === STATE.sortKey) {{
          th.classList.add("active");
          icon.textContent = STATE.sortDir === "asc" ? "\\u25B2" : "\\u25BC";
        }} else {{
          icon.textContent = "\\u25B2\\u25BC";
        }}
      }});
    }}

    function getFilteredPatients() {{
      const q = document.getElementById("search").value.trim().toLowerCase();
      const status = document.getElementById("statusFilter").value;
      const cluster = document.getElementById("clusterFilter").value;
      const alerts = document.getElementById("alertFilter").value;
      let rows = [...DATA.patients];
      if (q) rows = rows.filter(p => p.pid.toLowerCase().includes(q));
      if (status) rows = rows.filter(p => p.status === status);
      if (cluster !== "") rows = rows.filter(p => getCluster(p) === Number(cluster));
      if (alerts === "has") rows = rows.filter(p => p.alerts > 0);
      if (alerts === "none") rows = rows.filter(p => p.alerts === 0);
      const getter = SORT_GETTERS[STATE.sortKey] || SORT_GETTERS.status_order;
      rows.sort((a, b) => {{
        const ka = getter(a);
        const kb = getter(b);
        if (ka < kb) return STATE.sortDir === "asc" ? -1 : 1;
        if (ka > kb) return STATE.sortDir === "asc" ? 1 : -1;
        return 0;
      }});
      return rows;
    }}

    function renderTable() {{
      const body = document.getElementById("patient-table-body");
      const rows = getFilteredPatients();
      renderSortHeaders();
      body.innerHTML = rows.map(p => `
        <tr data-pid="${{p.pid}}">
          <td>${{dot(p.status)}}<span style="font-weight:800;color:#00796B">${{p.pid}}</span></td>
          <td><div class="metric">${{p.sparks.hrv||""}}<span class="val">${{fmt(p.metrics.hrv)}}</span></div></td>
          <td><div class="metric">${{p.sparks.hr||""}}<span class="val">${{fmt(p.metrics.hr)}}</span></div></td>
          <td><div class="metric">${{p.sparks.stress||""}}<span class="val">${{fmt(p.metrics.stress,3)}}</span></div></td>
          <td><div class="metric">${{p.sparks.isi||""}}<span class="val">${{fmt(p.metrics.isi)}}</span></div></td>
          <td><div class="metric">${{p.sparks.phq9||""}}<span class="val">${{fmt(p.metrics.phq9)}}</span></div></td>
          <td><div class="metric">${{p.sparks.gad7||""}}<span class="val">${{fmt(p.metrics.gad7)}}</span></div></td>
          <td style="text-align:center">${{badge(p.alerts)}}</td>
          <td>${{statusPill(p.status)}}</td>
        </tr>
      `).join("");
      body.querySelectorAll("tr").forEach(row => {{
        row.addEventListener("click", () => openPatient(row.dataset.pid));
      }});
    }}

    /* ── Charts ── */
    const plotBase = {{
      paper_bgcolor: "#fff", plot_bgcolor: "#fff", template: "plotly_white",
      margin: {{ t: 44, b: 40, l: 50, r: 50 }},
      legend: {{ orientation: "h", y: 1.16, x: 0 }}
    }};

    function drawSmallPlot(targetId, days, values, color, yTitle) {{
      if (!values || !values.length) return;
      Plotly.newPlot(targetId, [{{
        x: days, y: values, mode: "lines+markers",
        line: {{ color, width: 2 }}, marker: {{ size: 4 }},
        connectgaps: false, hovertemplate: "Day %{{x}}<br>Value %{{y}}<extra></extra>"
      }}], {{
        ...plotBase, margin: {{ t: 6, b: 30, l: 38, r: 12 }},
        height: 180, showlegend: false,
        xaxis: {{ title: "Day", tickfont: {{ size: 10 }}, titlefont: {{ size: 11 }} }},
        yaxis: {{ title: yTitle, tickfont: {{ size: 10 }}, titlefont: {{ size: 11 }} }}
      }}, {{ displayModeBar: false, responsive: true }});
    }}

    function drawPhysioSmallMultiples(p) {{
      const es = p.emma_series || {{}};
      const days = es.days || p.sander_series.days || [];
      drawSmallPlot("plot-hr", days, es.heart_rate || [], "#E53935", "Heart Rate");
      drawSmallPlot("plot-rmssd", days, es.rmssd || [], "#2196F3", "RMSSD");
      drawSmallPlot("plot-lfhf", days, es.lf_hf || [], "#00897B", "LF/HF");
      drawSmallPlot("plot-sleep-hrs", days, es.sleep_hours || [], "#00695C", "Sleep Hours");
      drawSmallPlot("plot-light", days, es.light_avg || [], "#FB8C00", "Light Avg");
      drawSmallPlot("plot-cal", days, es.calories || [], "#7E57C2", "Calories");
    }}

    function drawDualChart(days, leftSeries, rightSeries) {{
      if (!days || !days.length) return;
      Plotly.newPlot("chart-main", [
        {{ x: days, y: leftSeries, name: "HRV (RMSSD)", line: {{ color: "#2196F3", width: 2 }}, mode: "lines+markers", marker: {{ size: 4 }}, type: "scatter" }},
        {{ x: days, y: rightSeries, name: "Stress Score", line: {{ color: "#FF9800", width: 2 }}, mode: "lines+markers", marker: {{ size: 4 }}, type: "scatter", yaxis: "y2" }}
      ], {{
        ...plotBase, height: 320,
        xaxis: {{ title: "Day" }},
        yaxis: {{ title: "RMSSD (ms)" }},
        yaxis2: {{ title: "Stress Score", overlaying: "y", side: "right", range: [0, 1] }}
      }}, {{ displayModeBar: false, responsive: true }});
    }}

    function drawSleepChart(days, series) {{
      if (!days || !days.length) return;
      Plotly.newPlot("chart-sleep", [{{
        x: days, y: series, name: "Sleep Rest Proxy",
        line: {{ color: "#00897B", width: 2 }}, mode: "lines+markers",
        marker: {{ size: 4 }}, fill: "tozeroy", fillcolor: "rgba(0,137,123,0.08)", type: "scatter"
      }}], {{
        ...plotBase, height: 280,
        xaxis: {{ title: "Day" }}, yaxis: {{ title: "Rest Proxy" }}
      }}, {{ displayModeBar: false, responsive: true }});
    }}

    function drawForecastChart(forecastSeries) {{
      const panel = document.getElementById("forecast-panel");
      const horizons = Object.keys(forecastSeries || {{}});
      if (!horizons.length) {{ panel.classList.add("hidden"); return; }}
      panel.classList.remove("hidden");
      const colors = {{ "1": "#43A047", "3": "#FF9800", "7": "#E53935" }};
      const traces = [];
      horizons.sort((a,b) => Number(a) - Number(b)).forEach(h => {{
        const rows = forecastSeries[h] || [];
        traces.push({{ x: rows.map(r => r.day), y: rows.map(r => r.pred), name: `+${{h}}d Forecast`, mode: "lines+markers", marker: {{ size: 3 }}, line: {{ width: 2, color: colors[h] || "#999" }}, type: "scatter" }});
      }});
      const obsBase = (forecastSeries[horizons[0]] || []);
      traces.push({{ x: obsBase.map(r => r.day), y: obsBase.map(r => r.true), name: "Observed", mode: "lines", line: {{ color: "#333", width: 2, dash: "dot" }}, opacity: 0.5, type: "scatter" }});
      Plotly.newPlot("chart-forecast", traces, {{
        ...plotBase, height: 300, xaxis: {{ title: "Day" }}, yaxis: {{ title: "Stress Score" }}
      }}, {{ displayModeBar: false, responsive: true }});
    }}

    function drawMentalChart(p) {{
      const es = p.emma_series || {{}};
      const chartDays = es.chart_days || es.days || [];
      if (!chartDays.length) return;
      const histISI = es.isi_historical_chart || es.isi || [];
      const histPHQ9 = es.phq9_historical_chart || es.phq9 || [];
      const histGAD7 = es.gad7_historical_chart || es.gad7 || [];
      const foreISI = es.isi_forecast_chart || [];
      const forePHQ9 = es.phq9_forecast_chart || [];
      const foreGAD7 = es.gad7_forecast_chart || [];
      const surveyMask = es.survey_day_mask_chart || es.survey_day_mask || [];
      const forecastDays = (p.emma_forecast && p.emma_forecast.forecast_days) || [];

      function surveyPoints(values) {{
        const x = [], y = [];
        for (let i = 0; i < chartDays.length; i++) {{
          if (!surveyMask[i]) continue;
          const v = values[i];
          if (v === null || v === undefined || !Number.isFinite(v)) continue;
          x.push(chartDays[i]); y.push(v);
        }}
        return {{ x, y }};
      }}
      function validNumbers(values) {{
        return (values || []).filter(v => v !== null && v !== undefined && Number.isFinite(v));
      }}
      const yValues = [...validNumbers(histISI),...validNumbers(histPHQ9),...validNumbers(histGAD7),...validNumbers(foreISI),...validNumbers(forePHQ9),...validNumbers(foreGAD7)];
      const yRange = (() => {{
        if (!yValues.length) return [0,10];
        const ymin = Math.min(...yValues), ymax = Math.max(...yValues);
        const spread = Math.max(1, ymax - ymin);
        const pad = Math.max(1.0, spread * 0.2);
        const lower = Math.max(0, Math.floor((ymin - pad) * 10) / 10);
        let upper = Math.ceil((ymax + pad + 0.5) * 10) / 10;
        if (upper <= lower) upper = lower + 1;
        return [lower, upper];
      }})();
      function surveySeries(values, color, name) {{
        const pts = surveyPoints(values);
        return {{ x: pts.x, y: pts.y, name: `${{name}} (Survey)`, mode: "markers", marker: {{ size: 10, symbol: "diamond-open", color, line: {{ width: 2 }} }}, hovertemplate: "%{{x}}: %{{y}}<extra>Survey</extra>" }};
      }}
      Plotly.newPlot("chart-mental", [
        {{ x: chartDays, y: histISI, name: "ISI Historical", mode: "lines+markers", line: {{ color: "#7E57C2", width: 2 }}, marker: {{ size: 4 }}, connectgaps: false }},
        {{ x: chartDays, y: foreISI, name: "ISI Forecast", mode: "lines+markers", line: {{ color: "#7E57C2", width: 2, dash: "dot" }}, marker: {{ size: 4 }}, connectgaps: false }},
        {{ x: chartDays, y: histPHQ9, name: "PHQ-9 Historical", mode: "lines+markers", line: {{ color: "#FB8C00", width: 2 }}, marker: {{ size: 4 }}, connectgaps: false }},
        {{ x: chartDays, y: forePHQ9, name: "PHQ-9 Forecast", mode: "lines+markers", line: {{ color: "#FB8C00", width: 2, dash: "dot" }}, marker: {{ size: 4 }}, connectgaps: false }},
        {{ x: chartDays, y: histGAD7, name: "GAD-7 Historical", mode: "lines+markers", line: {{ color: "#00897B", width: 2 }}, marker: {{ size: 4 }}, connectgaps: false }},
        {{ x: chartDays, y: foreGAD7, name: "GAD-7 Forecast", mode: "lines+markers", line: {{ color: "#00897B", width: 2, dash: "dot" }}, marker: {{ size: 4 }}, connectgaps: false }},
        surveySeries(histISI, "#7E57C2", "ISI"),
        surveySeries(histPHQ9, "#FB8C00", "PHQ-9"),
        surveySeries(histGAD7, "#00897B", "GAD-7")
      ], {{
        ...plotBase, height: 320,
        xaxis: {{ title: "Day", range: [1, 36], dtick: 2 }},
        yaxis: {{ title: "Score", range: yRange }},
        shapes: (() => {{
          if (!forecastDays.length) return [];
          const fd = Math.min(...forecastDays);
          return [{{ type: "line", x0: fd-1, x1: fd-1, y0: 0, y1: 1, xref: "x", yref: "paper", line: {{ color: "#9CA3AF", dash: "dot" }} }}];
        }})(),
        annotations: (() => {{
          if (!forecastDays.length) return [];
          const fd = Math.min(...forecastDays);
          return [{{ x: fd-1, y: 1.06, xref: "x", yref: "paper", text: "Forecast starts", showarrow: false, font: {{ size: 11, color: "#6b7280" }} }}];
        }})()
      }}, {{ displayModeBar: false, responsive: true }});
    }}

    function drawSurveyChart(patient) {{
      const patientSurvey = SURVEY_BY_PID[patient.pid];
      const chartEl = document.getElementById("chart-survey");
      if (!patientSurvey) {{
        chartEl.innerHTML = '<div class="fact" style="margin-top:20px"><strong>No survey data</strong><span>Survey responses are not available for this patient.</span></div>';
        return;
      }}
      const clusterIndex = getCluster(patient);
      const traces = [];
      const clusterTrajectory = CLUSTER_SURVEY_TRAJECTORIES[String(clusterIndex)];
      if (clusterTrajectory) {{
        ["ISI","PHQ9","GAD7"].forEach((metric, idx) => {{
          traces.push({{
            x: SURVEY_TIMEPOINTS, y: clusterTrajectory[metric],
            name: "Cluster trajectory", legendgroup: "cluster-trajectory",
            mode: "lines", line: {{ color: "#B0BEC5", width: 1.8 }},
            opacity: 0.8, showlegend: idx === 0, type: "scatter"
          }});
        }});
      }}
      traces.push({{ x: SURVEY_TIMEPOINTS, y: patientSurvey.ISI, name: "Patient ISI", mode: "lines+markers", line: {{ color: "#3949AB", width: 3 }}, marker: {{ size: 6 }}, type: "scatter" }});
      traces.push({{ x: SURVEY_TIMEPOINTS, y: patientSurvey.PHQ9, name: "Patient PHQ-9", mode: "lines+markers", line: {{ color: "#D84315", width: 3 }}, marker: {{ size: 6 }}, type: "scatter" }});
      traces.push({{ x: SURVEY_TIMEPOINTS, y: patientSurvey.GAD7, name: "Patient GAD-7", mode: "lines+markers", line: {{ color: "#00897B", width: 3 }}, marker: {{ size: 6 }}, type: "scatter" }});
      Plotly.newPlot("chart-survey", traces, {{
        ...plotBase, height: 320,
        xaxis: {{ title: "Timepoint", type: "category" }},
        yaxis: {{ title: "Score" }},
        legend: {{ orientation: "h", y: 1.22, x: 0 }}
      }}, {{ displayModeBar: false, responsive: true }});
    }}

    /* ── Tabs ── */
    function initTabs() {{
      document.querySelectorAll("#chart-tabs .tab").forEach(tab => {{
        tab.addEventListener("click", () => {{
          document.querySelectorAll("#chart-tabs .tab").forEach(t => t.classList.remove("active"));
          document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
          tab.classList.add("active");
          document.getElementById("panel-" + tab.dataset.tab).classList.add("active");
        }});
      }});
    }}

    /* ── Detail view ── */
    function openPatient(pid) {{
      const p = DATA.patients.find(x => x.pid === pid);
      if (!p) return;
      const ci = getCluster(p);
      const cm = clusterMeta(ci);
      STATE.selected = pid;
      document.getElementById("list-view").classList.add("hidden");
      document.getElementById("detail-view").classList.remove("hidden");
      document.getElementById("breadcrumb").innerHTML = `Dashboard &rsaquo; Patients &rsaquo; ${{p.pid}}`;

      document.getElementById("patient-banner").innerHTML = `
        <div class="pid">${{dot(p.status)}} ${{p.pid}}</div>
        <div class="stat"><b>Status:</b> ${{statusPill(p.status)}}</div>
        <div class="stat"><b>Cluster:</b> ${{esc(cm.name)}}</div>
        <div class="stat"><b>Days recorded:</b> ${{p.days}}</div>
        <div class="stat"><b>Alerts:</b> ${{badge(p.alerts)}}</div>
      `;
      document.getElementById("mini-grid").innerHTML = `
        <div class="mini"><div class="k">Stress</div><div class="v">${{fmt(p.metrics.stress,3)}}</div></div>
        <div class="mini"><div class="k">HRV (RMSSD)</div><div class="v">${{fmt(p.metrics.hrv)}}</div></div>
        <div class="mini"><div class="k">Heart Rate</div><div class="v">${{fmt(p.metrics.hr)}}</div></div>
        <div class="mini"><div class="k">Sleep Quality</div><div class="v">${{fmt(p.metrics.sleep,2)}}</div></div>
        <div class="mini"><div class="k">ISI</div><div class="v">${{fmt(p.metrics.isi)}}</div></div>
        <div class="mini"><div class="k">PHQ-9</div><div class="v">${{fmt(p.metrics.phq9)}}</div></div>
        <div class="mini"><div class="k">GAD-7</div><div class="v">${{fmt(p.metrics.gad7)}}</div></div>
      `;

      // Cluster card
      document.getElementById("cluster-card").innerHTML = `
        <div class="fact"><strong>${{esc(cm.name)}}</strong><span>${{esc(cm.insight)}}</span></div>
      `;

      // Alerts
      const alertsCard = document.getElementById("alerts-card");
      const sanderAlerts = (p.forecast && p.forecast.alerts) || [];
      const emmaAlerts = (p.emma_forecast && p.emma_forecast.alerts) || [];
      if (!sanderAlerts.length && !emmaAlerts.length) {{
        alertsCard.innerHTML = `<div class="fact"><strong>Current alert state</strong><span style="color:#2e7d32">No alerts — all metrics within expected thresholds</span></div>`;
      }} else {{
        let html = `<div class="fact"><strong>Current alert state</strong><span style="color:#c62828;font-weight:700">Alerts detected</span></div>`;
        sanderAlerts.forEach(a => {{
          html += `<div class="alert-row"><div><div class="alert-title">Day ${{a.day}} +${{a.horizon}}d forecast</div><div class="alert-meta">Predicted stress score ${{a.pred}}</div></div><div class="alert-pill">${{esc(a.band)}}</div></div>`;
        }});
        emmaAlerts.forEach(a => {{
          html += `<div class="alert-row"><div><div class="alert-title">Day ${{a.day}} (${{a.source || "model"}})</div><div class="alert-meta">${{esc(a.reason || "")}}</div></div><div class="alert-pill">Alert</div></div>`;
        }});
        alertsCard.innerHTML = html;
      }}

      // Explanation — merge both sources
      const sex = p.explanation || {{}};
      const eex = p.emma_explanation || {{}};
      let explainHtml = "";
      if (sex.risk || sex.protective) {{
        explainHtml += `<div class="section-title">Risk factors</div>${{chips(sex.risk || eex.risk, "risk")}}`;
        explainHtml += `<div class="section-title">Protective factors</div>${{chips(sex.protective || eex.protective, "protective")}}`;
        if (sex.trajectory) explainHtml += `<div class="fact"><strong>Trajectory</strong><span>${{esc(sex.trajectory)}}</span></div>`;
        if (sex.comment) explainHtml += `<div class="fact"><strong>Clinical comment</strong><span>${{esc(sex.comment)}}</span></div>`;
      }} else if (eex.risk || eex.protective) {{
        explainHtml += `<div class="fact"><strong>Risk context</strong><span>${{esc(eex.risk || "No additional risk note.")}}</span></div>`;
        explainHtml += `<div class="fact"><strong>Protective context</strong><span>${{esc(eex.protective || "No protective note available.")}}</span></div>`;
      }} else {{
        explainHtml = `<div class="fact"><strong>Explanation</strong><span>No explanation data available for this patient.</span></div>`;
      }}
      document.getElementById("explain-card").innerHTML = explainHtml;

      // Similar patients
      const neighbors = p.neighbors || [];
      document.getElementById("neighbors-card").innerHTML = neighbors.length ? neighbors.map(n => `
        <div class="neighbor" data-neighbor="${{n.pid}}" role="button" tabindex="0">
          <div class="neighbor-left">
            <span class="rank">#${{n.rank}}</span>
            <div><a href="#" data-neighbor-link="${{n.pid}}">${{n.pid}}</a><div class="muted">Distance: ${{n.distance}}</div></div>
          </div>
          <div class="muted">View profile</div>
        </div>
      `).join("") : `<div class="fact"><strong>Similarity</strong><span>No neighbors found</span></div>`;
      document.querySelectorAll("[data-neighbor]").forEach(el => {{
        el.addEventListener("click", () => openPatient(el.dataset.neighbor));
        el.addEventListener("keydown", (e) => {{
          if (e.key === "Enter" || e.key === " ") {{ e.preventDefault(); openPatient(el.dataset.neighbor); }}
        }});
      }});
      document.querySelectorAll("[data-neighbor-link]").forEach(el => el.addEventListener("click", (e) => {{
        e.preventDefault(); e.stopPropagation(); openPatient(el.dataset.neighborLink);
      }}));

      // Reset to first tab
      document.querySelectorAll("#chart-tabs .tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
      document.querySelector('#chart-tabs .tab[data-tab="physiology"]').classList.add("active");
      document.getElementById("panel-physiology").classList.add("active");

      // Draw all charts
      const ss = p.sander_series || {{}};
      drawPhysioSmallMultiples(p);
      drawDualChart(ss.days || [], ss.hrv || [], ss.stress || []);
      drawSleepChart(ss.days || [], ss.sleep || []);
      drawForecastChart((p.forecast && p.forecast.series) || {{}});
      drawMentalChart(p);
      drawSurveyChart(p);

      window.scrollTo({{ top: 0, behavior: "smooth" }});
    }}

    function goList() {{
      STATE.selected = null;
      document.getElementById("detail-view").classList.add("hidden");
      document.getElementById("list-view").classList.remove("hidden");
      document.getElementById("breadcrumb").innerHTML = "Dashboard &rsaquo; Mental Health BioSignal Monitoring";
      window.scrollTo({{ top: 0, behavior: "smooth" }});
    }}

    /* ── Event listeners ── */
    document.getElementById("search").addEventListener("input", renderTable);
    document.getElementById("statusFilter").addEventListener("change", renderTable);
    document.getElementById("clusterFilter").addEventListener("change", renderTable);
    document.getElementById("alertFilter").addEventListener("change", renderTable);
    document.getElementById("resetBtn").addEventListener("click", () => {{
      document.getElementById("search").value = "";
      document.getElementById("statusFilter").value = "";
      document.getElementById("clusterFilter").value = "";
      document.getElementById("alertFilter").value = "";
      STATE.sortKey = "status_order";
      STATE.sortDir = "asc";
      renderTable();
    }});
    document.querySelectorAll("thead th[data-sort]").forEach(th => {{
      th.addEventListener("click", () => {{
        const key = th.dataset.sort;
        if (STATE.sortKey === key) STATE.sortDir = STATE.sortDir === "asc" ? "desc" : "asc";
        else {{ STATE.sortKey = key; STATE.sortDir = "asc"; }}
        renderTable();
      }});
    }});
    document.getElementById("backBtn").addEventListener("click", goList);

    initTabs();
    renderTable();
  </script>
</body>
</html>'''


def main():
    print("Extracting Sander data...")
    sander_data, cluster_by_pid, survey_by_pid, cluster_survey = extract_sander_data(
        SANDER_HTML
    )
    print(f"  → {len(sander_data['patients'])} patients from Sander")

    print("Extracting Emma data...")
    emma_data = extract_emma_data(EMMA_JS)
    print(f"  → {len(emma_data['patients'])} patients from Emma")

    print("Merging patient data...")
    merged = merge_patients(sander_data, emma_data, cluster_by_pid)
    print(f"  → {len(merged['patients'])} merged patients")

    print("Generating HTML...")
    html = build_html(merged, survey_by_pid, cluster_survey)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"Done! Output: {OUTPUT} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
