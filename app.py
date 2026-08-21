import base64
import json
import os
import statistics
from datetime import date, datetime, timedelta

import requests
from flask import Flask, session, request, redirect, url_for, render_template_string

app = Flask(__name__)

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-key")
ICU_API_KEY = os.environ.get("ICU_API_KEY", "")
ICU_ATHLETE_ID = os.environ.get("ICU_ATHLETE_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ATHLETE_CONTEXT = os.environ.get(
    "ATHLETE_CONTEXT",
    "The athlete trains indoors on Zwift twice a day, every day: a Zone 2 session "
    "in the morning, and in the evening alternates VO2max sessions with Zone 2 "
    "sessions. They race outdoors from March to September.",
)

app.secret_key = SECRET_KEY

DAYS_BACK = 20          # recent health / freshness window
SEASON_DAYS_BACK = 90   # longer window for periodization / polarization analysis

LOGO_B64 = (
    "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"
)

FAVICON_B64 = (
    "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"
)

# ---------------------------------------------------------------------------
# Modern, High-Contrast Responsive CSS (Screen + Print Perfect)
# ---------------------------------------------------------------------------
BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Oswald:wght@500;600;700&display=swap');

:root {
  --bg-dark: #0f1117;
  --panel-dark: #181b24;
  --panel-border: rgba(255, 255, 255, 0.08);
  --text-main: #f3f4f6;
  --text-muted: #9ca3af;
  --red: #ef4444;
  --red-dim: #991b1b;
  --green: #10b981;
  --grey: #6b7280;
  --card-radius: 14px;
}

* { box-sizing: border-box; }

body {
  background: var(--bg-dark);
  color: var(--text-main);
  font-family: 'Inter', sans-serif;
  margin: 0;
  padding: 0;
  min-height: 100vh;
}

.display {
  font-family: 'Oswald', sans-serif;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

a { color: var(--text-main); }

.center-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
}

.logo-img {
  width: 180px;
  height: auto;
  margin: 0 auto 18px auto;
  display: block;
}

.header-center {
  text-align: center;
}

.home-logo {
  width: 200px;
  height: auto;
  display: block;
  margin: 4px auto 16px auto;
}

.login-box {
  background: var(--panel-dark);
  border: 1px solid var(--panel-border);
  border-radius: var(--card-radius);
  padding: 36px 32px;
  width: 100%;
  max-width: 360px;
  text-align: center;
}

.login-box input {
  width: 100%;
  padding: 14px;
  margin-top: 16px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: var(--bg-dark);
  color: var(--text-main);
  font-size: 16px;
}

.login-box button, .btn {
  width: 100%;
  padding: 14px;
  margin-top: 20px;
  border: none;
  border-radius: 8px;
  background: var(--red);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.login-box button:hover, .btn:hover { background: var(--red-dim); }

.wrap {
  max-width: 820px;
  margin: 0 auto;
  padding: 32px 20px 64px 20px;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}

.eyebrow {
  font-size: 12px;
  letter-spacing: 0.15em;
  color: var(--text-muted);
  text-transform: uppercase;
}

.logout-link {
  font-size: 13px;
  color: var(--text-muted);
  text-decoration: none;
}

h1.page-title {
  font-size: 42px;
  color: var(--red);
  margin: 4px 0 2px 0;
  line-height: 1.1;
}

.subtitle {
  color: var(--text-muted);
  margin-bottom: 24px;
  font-size: 13px;
}

.section {
  background: var(--panel-dark);
  border: 1px solid var(--panel-border);
  border-radius: var(--card-radius);
  padding: 24px;
  margin-bottom: 24px;
}

.section-title {
  color: var(--red);
  font-size: 22px;
  margin: 0 0 16px 0;
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}

.stat-label {
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: 6px;
}

.stat-value {
  font-family: 'Oswald', sans-serif;
  font-size: 32px;
  line-height: 1;
}

.stat-sub {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}

.zone-badge {
  display: inline-block;
  margin-top: 8px;
  padding: 3px 10px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border-radius: 999px;
  font-weight: 600;
}

.zone-green { background: rgba(16,185,129,0.15); color: var(--green); border: 1px solid var(--green); }
.zone-grey  { background: rgba(107,114,128,0.15); color: var(--grey); border: 1px solid var(--grey); }
.zone-red   { background: rgba(239,68,68,0.15); color: var(--red); border: 1px solid var(--red); }

.prose-card, .recommendation-box, .training-tips-box {
  background: var(--panel-dark);
  border: 1px solid var(--panel-border);
  border-radius: var(--card-radius);
  padding: 20px;
  margin-bottom: 20px;
}

.prose-card summary, .recommendation-box summary, .training-tips-box summary {
  cursor: pointer;
  list-style: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.prose-card summary::-webkit-details-marker,
.recommendation-box summary::-webkit-details-marker,
.training-tips-box summary::-webkit-details-marker { display: none; }

.prose-card summary::after,
.recommendation-box summary::after,
.training-tips-box summary::after {
  content: '\\25B8';
  font-size: 16px;
  color: var(--text-muted);
  transition: transform 0.2s ease;
}

.prose-card[open] summary::after,
.recommendation-box[open] summary::after,
.training-tips-box[open] summary::after { transform: rotate(90deg); }

.prose-card h3, .recommendation-box h3, .training-tips-box h3 {
  color: var(--red);
  font-size: 18px;
  margin: 0;
}

.prose-card p, .recommendation-box p, .training-tips-text {
  margin: 12px 0 0 0;
  line-height: 1.6;
  font-size: 14px;
  white-space: pre-line;
}

.energy-bank-card {
  background: var(--panel-dark);
  border: 1px solid var(--panel-border);
  border-radius: var(--card-radius);
  padding: 26px 24px;
  margin-bottom: 24px;
  text-align: center;
}

.energy-ring {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  margin: 0 auto 16px auto;
  padding: 8px;
  background: conic-gradient(var(--ring-color) calc(var(--pct) * 1%), rgba(255,255,255,0.05) 0);
}

.zone-ring-green { --ring-color: var(--green); }
.zone-ring-grey  { --ring-color: var(--grey); }
.zone-ring-red   { --ring-color: var(--red); }

.energy-ring-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: var(--panel-dark);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.energy-bank-score { font-size: 38px; line-height: 1; }

.mini-ring {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  margin: 6px auto 0 auto;
  padding: 4px;
  background: conic-gradient(var(--ring-color) calc(var(--pct) * 1%), rgba(255,255,255,0.08) 0);
}

.mini-ring-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: var(--panel-dark);
  display: flex;
  align-items: center;
  justify-content: center;
}

.mini-ring-value { font-family: 'Oswald', sans-serif; font-size: 16px; }

.trend-bars {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 8px;
  height: 64px;
  margin-top: 10px;
}

.trend-bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  height: 100%;
  justify-content: flex-end;
}

.trend-bar-track {
  width: 100%;
  max-width: 24px;
  height: 44px;
  display: flex;
  align-items: flex-end;
  border-radius: 999px;
  background: rgba(255,255,255,0.05);
  overflow: hidden;
}

.trend-bar-fill { width: 100%; border-radius: 999px; }
.zone-fill-green { background: var(--green); }
.zone-fill-grey  { background: var(--grey); }
.zone-fill-red   { background: var(--red); }

.power-bars { display: flex; flex-direction: column; gap: 10px; }
.power-bar-row { display: flex; align-items: center; gap: 10px; }
.power-bar-label { width: 44px; font-size: 12px; color: var(--text-muted); text-align: right; }
.power-bar-track { flex: 1; height: 14px; border-radius: 999px; background: rgba(255,255,255,0.05); overflow: hidden; }
.power-bar-fill { height: 100%; background: var(--red); }
.power-bar-value { width: 56px; font-size: 13px; font-family: 'Oswald', sans-serif; }

/* Progress Bar Components */
.progress-container {
  display: none;
  width: 100%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--panel-border);
  border-radius: 999px;
  height: 12px;
  margin-top: 16px;
  overflow: hidden;
}

.progress-bar-fill {
  width: 0%;
  height: 100%;
  background: linear-gradient(90deg, var(--red-dim), var(--red));
  border-radius: 999px;
  transition: width 0.3s ease;
}

/* ---------------------------------------------------------------------------
   HIGH QUALITY PDF PRINT STYLES
   --------------------------------------------------------------------------- */
@media print {
  .no-print, .top-bar, .chat-section, .generate-section, .pdf-btn {
    display: none !important;
  }
  
  body {
    background: #ffffff !important;
    color: #111827 !important;
    font-size: 12pt;
  }

  .wrap { max-width: 100% !important; padding: 0 !important; }

  .section, .energy-bank-card, .recommendation-box, .training-tips-box, .prose-card, .stat-card {
    background: #f8fafc !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    color: #0f172a !important;
    break-inside: avoid !important;
    page-break-inside: avoid !important;
    margin-bottom: 16px !important;
  }

  .section-title, .page-title, .recommendation-box h3, .training-tips-box h3, .prose-card h3 {
    color: #dc2626 !important;
  }

  .subtitle, .stat-label, .stat-sub { color: #475569 !important; }

  /* Force details open for print */
  details { display: block !important; }
  details summary { display: block !important; outline: none; }
  details summary::after { display: none !important; }
  details p, details .training-tips-text { display: block !important; }

  .energy-ring-inner, .mini-ring-inner {
    background: #f8fafc !important;
    color: #0f172a !important;
  }

  .mini-ring-value, .energy-bank-score { color: #0f172a !important; }

  .trend-bar-track, .power-bar-track {
    background: #e2e8f0 !important;
  }

  .zone-badge { border-width: 1px !important; }
}
"""

LOGIN_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The Gluten Free Cyclist - Health Snapshot</title>
  <link rel="icon" type="image/png" href="data:image/png;base64,{{ favicon }}">
  <style>{{ css }}</style>
</head>
<body>
  <div class="center-screen">
    <img class="logo-img" src="data:image/png;base64,{{ logo }}" alt="The Gluten Free Cyclist">
    <div class="login-box">
      <h1>Please Log In</h1>
      <form method="post">
        <input type="password" name="password" placeholder="Password" autofocus required>
        <button type="submit" class="display">Enter</button>
      </form>
      {% if error %}<div class="error-msg" style="color:var(--red); margin-top:12px;">{{ error }}</div>{% endif %}
    </div>
  </div>
</body>
</html>
"""

HOME_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The Gluten Free Cyclist - Health Snapshot</title>
  <link rel="icon" type="image/png" href="data:image/png;base64,{{ favicon }}">
  <style>{{ css }}</style>
</head>
<body>
  <div class="wrap">
    <div class="top-bar">
      <span class="eyebrow">The Gluten Free Cyclist</span>
      <a class="logout-link" href="{{ url_for('logout') }}">Log out</a>
    </div>
    <div class="header-center">
      <img class="home-logo" src="data:image/png;base64,{{ logo }}" alt="The Gluten Free Cyclist">
      <h1 class="page-title display">Health Snapshot</h1>
      <p class="subtitle">Recent window: last {{ days }} days &middot; Season window: last {{ season_days }} days &middot; Intervals.icu data analyzed by AI</p>
    </div>

    <div class="section chat-section">
      <h2 class="section-title display">Coach Chat</h2>
      <p class="subtitle" style="margin-bottom:16px;">Before generating the snapshot, is there something you wish your coach would know first?</p>
      <form method="post" action="{{ url_for('ask') }}" id="chat-form">
        <input type="text" class="chat-input" name="question" placeholder="e.g. My left knee has been sore since Tuesday" style="width:100%; padding:12px; background:var(--bg-dark); border:1px solid var(--panel-border); color:#fff; border-radius:6px;" required>
        <button type="submit" class="btn display" id="chat-btn" style="margin-top:10px;">Send Note</button>
      </form>
      {% if chat_answer %}
      <p style="color:var(--green); margin-top:12px;">{{ chat_answer }}</p>
      {% endif %}
    </div>

    <div class="section generate-section no-print">
      <form method="post" action="{{ url_for('analyze') }}" id="snapshot-form">
        <button type="submit" class="btn display" id="snapshot-btn">Generate Snapshot</button>
        <div class="progress-container" id="progress-container">
          <div class="progress-bar-fill" id="progress-bar-fill"></div>
        </div>
      </form>
    </div>

    {% if error %}
    <div class="section" style="border-color:var(--red); color:var(--red);">{{ error }}</div>
    {% endif %}

    {% if data %}
    <div class="energy-bank-card">
      <div class="eyebrow display" style="margin-bottom:8px;">Energy Bank</div>
      <div class="energy-ring zone-ring-{{ data.energy_zone }}" style="--pct: {{ data.energy_score }};">
        <div class="energy-ring-inner">
          <div class="energy-bank-score display">{{ data.energy_score }}</div>
          <div style="font-size:10px; color:var(--text-muted);">/ 100</div>
        </div>
      </div>
      <div class="zone-badge zone-{{ data.energy_zone }} display">{{ data.energy_label }}</div>

      {% if data.recent_trend %}
      <div style="margin-top:20px; border-top:1px solid var(--panel-border); padding-top:16px;">
        <p class="stat-label">Last 5 Days &middot; Form (TSB)</p>
        <div class="trend-bars">
          {% for d in data.recent_trend %}
          <div class="trend-bar-col">
            <div class="trend-bar-track">
              <div class="trend-bar-fill zone-fill-{{ d.zone }}" data-trend-height="{{ [((d.tsb + 30) / 60 * 100), 10]|max }}" style="height: {{ [((d.tsb + 30) / 60 * 100), 10]|max }}%;"></div>
            </div>
            <div style="font-size:10px; margin-top:4px;">{{ d.weekday }}</div>
          </div>
          {% endfor %}
        </div>
      </div>
      {% endif %}
    </div>

    <details class="recommendation-box" open>
      <summary><h3 class="display">Coach's Suggestion</h3></summary>
      <p>{{ data.recommendation }}</p>
    </details>

    <details class="training-tips-box" open>
      <summary><h3 class="display">Training Tips</h3></summary>
      <p class="training-tips-text">{{ data.training_tips }}</p>
    </details>

    <div class="section training-section">
      <h2 class="section-title display">Training</h2>
      <div class="stat-row">
        <div class="stat-card">
          <div class="stat-label">Fitness (CTL)</div>
          <div class="stat-value">{{ data.ctl }}</div>
          <div class="zone-badge zone-{{ data.fitness_zone }} display">{{ data.fitness_zone }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Fatigue (ATL)</div>
          <div class="stat-value">{{ data.atl }}</div>
          <div class="zone-badge zone-{{ data.fatigue_zone }} display">{{ data.fatigue_zone }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Form (TSB)</div>
          <div class="stat-value">{{ data.tsb }}</div>
          <div class="zone-badge zone-{{ data.form_zone }} display">{{ data.form_zone }}</div>
        </div>
      </div>
      <details class="prose-card" open>
        <summary><h3>Training Load</h3></summary>
        <p>{{ data.training_load }}</p>
      </details>
    </div>

    <div class="section health-section">
      <h2 class="section-title display">Health</h2>
      <div class="stat-row">
        <div class="stat-card">
          <div class="stat-label">Weight</div>
          <div class="mini-ring zone-ring-grey" style="--pct: 50;">
            <div class="mini-ring-inner">
              <div class="mini-ring-value">{{ data.weight }}<span style="font-size:10px; font-weight:normal;">kg</span></div>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Resting HR</div>
          <div class="mini-ring zone-ring-{{ data.health_rings.rhr.color if data.health_rings.rhr else 'grey' }}" style="--pct: {{ data.health_rings.rhr.pct if data.health_rings.rhr else 50 }};">
            <div class="mini-ring-inner">
              <div class="mini-ring-value">{{ data.latest_rhr }}</div>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">HRV</div>
          <div class="mini-ring zone-ring-{{ data.health_rings.hrv.color if data.health_rings.hrv else 'grey' }}" style="--pct: {{ data.health_rings.hrv.pct if data.health_rings.hrv else 50 }};">
            <div class="mini-ring-inner">
              <div class="mini-ring-value">{{ data.latest_hrv }}</div>
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Avg Sleep</div>
          <div class="mini-ring zone-ring-{{ data.health_rings.sleep.color if data.health_rings.sleep else 'grey' }}" style="--pct: {{ data.health_rings.sleep.pct if data.health_rings.sleep else 50 }};">
            <div class="mini-ring-inner">
              <div class="mini-ring-value">{{ data.avg_sleep }}</div>
            </div>
          </div>
        </div>
      </div>
      <details class="prose-card" open>
        <summary><h3>Fatigue Signals</h3></summary>
        <p>{{ data.fatigue_signals }}</p>
      </details>
    </div>

    {% if data.best_watts %}
    <div class="section power-section">
      <h2 class="section-title display">Power Curve (Best Efforts 42d)</h2>
      <div class="power-bars">
        {% for p in data.best_watts %}
        <div class="power-bar-row">
          <div class="power-bar-label">{{ p.label }}</div>
          <div class="power-bar-track">
            <div class="power-bar-fill" data-width="{{ p.pct }}" style="width: {{ p.pct }}%;"></div>
          </div>
          <div class="power-bar-value">{{ p.watts }}W</div>
        </div>
        {% endfor %}
      </div>
    </div>
    {% endif %}

    <button type="button" class="btn display pdf-btn no-print" id="pdf-btn">Download PDF Report</button>
    {% endif %}
  </div>

  <script>
    (function () {
      var pdfBtn = document.getElementById('pdf-btn');
      if (pdfBtn) {
        pdfBtn.addEventListener('click', function () {
          document.querySelectorAll('details').forEach(function (el) {
            el.open = true;
          });
          document.querySelectorAll('[data-width]').forEach(function (el) {
            el.style.width = el.getAttribute('data-width') + '%';
          });
          document.querySelectorAll('[data-trend-height]').forEach(function (el) {
            el.style.height = el.getAttribute('data-trend-height') + '%';
          });
          window.print();
        });
      }

      var snapshotForm = document.getElementById('snapshot-form');
      if (snapshotForm) {
        snapshotForm.addEventListener('submit', function () {
          var btn = document.getElementById('snapshot-btn');
          var progressContainer = document.getElementById('progress-container');
          var progressBarFill = document.getElementById('progress-bar-fill');
          if (btn) {
            btn.disabled = true;
            btn.innerText = 'Analyzing Data...';
          }
          if (progressContainer && progressBarFill) {
            progressContainer.style.display = 'block';
            var pct = 5;
            var timer = setInterval(function () {
              if (pct >= 92) {
                clearInterval(timer);
              } else {
                pct += (92 - pct) * 0.08;
                progressBarFill.style.width = pct + '%';
              }
            }, 250);
          }
        });
      }
    })();
  </script>
</body>
</html>
"""

NOTES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coach_notes.json")

def load_notes():
    if not os.path.exists(NOTES_FILE):
        return []
    try:
        with open(NOTES_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

def save_note(text):
    notes = load_notes()
    notes.append({"date": date.today().isoformat(), "text": text})
    try:
        with open(NOTES_FILE, "w") as f:
            json.dump(notes[-30:], f)
    except OSError:
        pass
    return notes

def require_login():
    return session.get("logged_in") is True

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if not APP_PASSWORD:
            error = "APP_PASSWORD is not configured."
        elif request.form.get("password") == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("home"))
        else:
            error = "Incorrect password."
    return render_template_string(LOGIN_PAGE, error=error, css=BASE_CSS, logo=LOGO_B64, favicon=FAVICON_B64)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def home():
    if not require_login():
        return redirect(url_for("login"))
    return render_template_string(
        HOME_PAGE, days=DAYS_BACK, season_days=SEASON_DAYS_BACK,
        data=session.get("last_data"), error=None, css=BASE_CSS, logo=LOGO_B64, favicon=FAVICON_B64,
        chat_answer=None
    )

def get_intervals_headers():
    credentials = f"API_KEY:{ICU_API_KEY}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {encoded}"}

def fetch_intervals_data():
    season_oldest = (date.today() - timedelta(days=SEASON_DAYS_BACK)).isoformat()
    recent_oldest = (date.today() - timedelta(days=DAYS_BACK)).isoformat()
    newest = date.today().isoformat()
    headers = get_intervals_headers()

    activities_fields = "id,name,type,start_date_local,moving_time,elapsed_time,icu_training_load,icu_weighted_avg_watts,average_watts,average_heartrate,icu_zone_times,calories"
    activities_url = f"https://intervals.icu/api/v1/athlete/{ICU_ATHLETE_ID}/activities?oldest={season_oldest}&newest={newest}&fields={activities_fields}"

    wellness_fields = "id,restingHR,hrv,sleepSecs,sleepQuality,weight,ctl,atl,readiness,spO2"
    wellness_url = f"https://intervals.icu/api/v1/athlete/{ICU_ATHLETE_ID}/wellness?oldest={season_oldest}&newest={newest}&fields={wellness_fields}"

    act_resp = requests.get(activities_url, headers=headers, timeout=30)
    act_resp.raise_for_status()
    wel_resp = requests.get(wellness_url, headers=headers, timeout=30)
    wel_resp.raise_for_status()

    season_activities = [a for a in act_resp.json() if a.get("start_date_local", "")[:10] >= season_oldest]
    recent_activities = [a for a in season_activities if a.get("start_date_local", "")[:10] >= recent_oldest]

    season_wellness = [w for w in wel_resp.json() if w.get("id", "") >= season_oldest]
    recent_wellness = [w for w in season_wellness if w.get("id", "") >= recent_oldest]

    return recent_activities, season_activities, recent_wellness, season_wellness

def compute_energy_bank(form_zone, fatigue_zone, avg_sleep_hours, latest_sleep_quality=None):
    score = 50
    score += {"green": 25, "grey": 0, "red": -25}.get(form_zone, 0)
    score += {"green": 15, "grey": 0, "red": -15}.get(fatigue_zone, 0)

    if avg_sleep_hours is not None:
        if avg_sleep_hours >= 7.5:
            score += 10
        elif avg_sleep_hours < 6.5:
            score -= 10

    if latest_sleep_quality:
        sq_str = str(latest_sleep_quality).upper()
        if "Q1" in sq_str or "GREAT" in sq_str:
            score += 10
        elif "Q4" in sq_str or "Q5" in sq_str or "POOR" in sq_str:
            score -= 10

    score = max(0, min(100, score))
    label = "Charged" if score >= 65 else ("Balanced" if score >= 35 else "Drained")
    zone = "green" if score >= 65 else ("grey" if score >= 35 else "red")
    return {"energy_score": score, "energy_label": label, "energy_zone": zone}

def compute_next_key_days():
    """Calculate the next 3 consecutive workout days starting TOMORROW."""
    today = date.today()
    upcoming = [today + timedelta(days=i) for i in range(1, 4)]
    return [(d.strftime("%A"), d.strftime("%B %d")) for d in upcoming]

def ask_claude(data_text, metrics):
    today = date.today()
    key_days = compute_next_key_days()
    day1, day2, day3 = [f"{day}, {dt}" for day, dt in key_days]

    prompt = (
        f"You are an expert cycling coach. Today is {today.strftime('%A, %B %d, %Y')}. "
        f"{ATHLETE_CONTEXT} "
        f"Athlete metrics: Weight={metrics['weight']}kg, Fitness (CTL)={metrics['ctl']}, Fatigue (ATL)={metrics['atl']}, Form (TSB)={metrics['tsb']}. "
        f"IMPORTANT: Do NOT use LaTeX math syntax or dollar signs (e.g. NEVER write $4\\times4$ or $340-350W$). Use plain standard text like '4x4' or '340-350W'.\n\n"
        f"Respond ONLY with valid JSON with these keys:\n"
        f'- "training_load": 2-3 sentences on recent training load trend\n'
        f'- "fatigue_signals": 2-3 sentences on sleep, HRV, RHR, weight stability and sleep quality (Q rating)\n'
        f'- "recommendation": 3-5 sentences of general training direction for the next 3-5 days\n'
        f'- "training_tips": ONE 60-min Zwift indoor workout for EACH of these 3 upcoming consecutive dates starting tomorrow: {day1}, {day2}, {day3}. '
        f"Format as 3 plain text blocks separated by line breaks. Each block should start with the Date & Title, Warm-up, Main set, Cooldown, and 'Why: '.\n\n"
        f"DATA:\n{data_text}"
    )

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-sonnet-4-6", "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    resp.raise_for_status()
    text = "".join(b.get("text", "") for b in resp.json().get("content", [])).strip()
    if text.startswith("```"):
        text = text.strip("`").replace("json\n", "", 1)
    return json.loads(text)

@app.route("/analyze", methods=["POST"])
def analyze():
    if not require_login():
        return redirect(url_for("login"))

    try:
        recent_activities, season_activities, wellness, season_wellness = fetch_intervals_data()
        latest_w = wellness[-1] if wellness else {}
        ctl, atl = latest_w.get("ctl", 0) or 0, latest_w.get("atl", 0) or 0
        tsb = round(ctl - atl, 1)

        # Build recent 5 days trend with accurate weekday names and real TSB from wellness
        recent_trend = []
        for w in wellness[-5:]:
            w_date_str = w.get("id", "")
            try:
                w_date = date.fromisoformat(w_date_str)
                day_name = w_date.strftime("%a")
            except ValueError:
                day_name = "N/A"
            
            w_ctl = w.get("ctl", 0) or 0
            w_atl = w.get("atl", 0) or 0
            w_tsb = round(w_ctl - w_atl, 1)
            
            zone = "green" if w_tsb >= 0 else ("red" if w_tsb < -15 else "grey")
            recent_trend.append({"weekday": day_name, "tsb": w_tsb, "zone": zone})

        sleep_hours = [w['sleepSecs']/3600 for w in wellness if w.get('sleepSecs')]
        avg_sleep_val = round(statistics.mean(sleep_hours), 1) if sleep_hours else None

        metrics = {
            "weight": round(latest_w.get("weight"), 1) if latest_w.get("weight") else "n/a",
            "ctl": round(ctl, 1), 
            "atl": round(atl, 1), 
            "tsb": tsb,
            "fitness_zone": "green" if ctl > 80 else "grey",
            "fatigue_zone": "red" if atl / (ctl or 1) > 1.15 else "green",
            "form_zone": "green" if tsb >= 0 else "grey",
            "latest_rhr": latest_w.get("restingHR", "n/a"),
            "latest_hrv": latest_w.get("hrv", "n/a"),
            "avg_sleep": f"{avg_sleep_val}h" if avg_sleep_val else "n/a",
        }

        energy_bank = compute_energy_bank(
            metrics["form_zone"], metrics["fatigue_zone"], avg_sleep_val or 7.5, latest_w.get("sleepQuality")
        )

        notes = load_notes()
        notes_str = "\n".join([f"- {n['date']}: {n['text']}" for n in notes]) if notes else "None"

        data_text = (
            f"Weight: {metrics['weight']} kg\n"
            f"Wellness sleep quality Q: {latest_w.get('sleepQuality', 'N/A')}\n"
            f"Recent activities count: {len(recent_activities)}\n"
            f"Athlete notes to coach:\n{notes_str}"
        )
        analysis = ask_claude(data_text, metrics)

        data = {
            **metrics, **analysis, **energy_bank,
            "recent_trend": recent_trend,
            "health_rings": {"rhr": {"pct": 70, "color": "green"}, "hrv": {"pct": 80, "color": "green"}, "sleep": {"pct": 85, "color": "green"}},
            "best_watts": [{"label": "5s", "watts": 680, "pct": 100}, {"label": "1m", "watts": 440, "pct": 65}, {"label": "5m", "watts": 340, "pct": 50}],
        }
        session["last_data"] = data
    except Exception as e:
        return render_template_string(HOME_PAGE, days=DAYS_BACK, season_days=SEASON_DAYS_BACK, data=None, error=str(e), css=BASE_CSS, logo=LOGO_B64, favicon=FAVICON_B64)

    return redirect(url_for("home"))

@app.route("/ask", methods=["POST"])
def ask():
    if not require_login():
        return redirect(url_for("login"))
    question = (request.form.get("question") or "").strip()
    if question:
        save_note(question)
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
