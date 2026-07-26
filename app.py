import base64
import json
import os
import statistics
from datetime import date, timedelta

import requests
from flask import Flask, session, request, redirect, url_for, render_template_string

app = Flask(__name__)

APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-key")
ICU_API_KEY = os.environ.get("ICU_API_KEY", "")
ICU_ATHLETE_ID = os.environ.get("ICU_ATHLETE_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

app.secret_key = SECRET_KEY

DAYS_BACK = 20

# ---------------------------------------------------------------------------
# Shared CSS
# ---------------------------------------------------------------------------
BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bayon&family=Inter:wght@400;500;600;700&display=swap');

:root {
  --black: #0a0a0a;
  --panel: #141414;
  --white: #f5f5f5;
  --red: #d81e2c;
  --red-dim: #7a1017;
  --green: #3fb95f;
  --grey-zone: #8a8a8a;
}

* { box-sizing: border-box; }

body {
  background: var(--black);
  color: var(--white);
  font-family: 'Inter', sans-serif;
  margin: 0;
  padding: 0;
  min-height: 100vh;
}

.display {
  font-family: 'Bayon', sans-serif;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

a { color: var(--white); }

.center-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
}

.login-box {
  background: var(--panel);
  border: 1px solid var(--white);
  padding: 40px 32px;
  width: 100%;
  max-width: 360px;
  text-align: center;
}

.login-box h1 {
  font-size: 30px;
  margin: 0 0 24px 0;
  color: var(--red);
}

.login-box input {
  width: 100%;
  padding: 14px;
  margin-top: 16px;
  border: 1px solid var(--white);
  background: var(--black);
  color: var(--white);
  font-family: 'Inter', sans-serif;
  font-size: 16px;
}

.login-box button, .btn {
  width: 100%;
  padding: 14px;
  margin-top: 20px;
  border: 1px solid var(--red);
  background: var(--red);
  color: var(--white);
  font-family: 'Bayon', sans-serif;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-size: 16px;
  cursor: pointer;
}

.login-box button:hover, .btn:hover { background: var(--red-dim); }

.error-msg {
  color: var(--red);
  margin-top: 14px;
  font-size: 14px;
}

.wrap {
  max-width: 760px;
  margin: 0 auto;
  padding: 32px 20px 64px 20px;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}

.eyebrow {
  font-size: 13px;
  letter-spacing: 0.15em;
  color: var(--grey-zone);
  text-transform: uppercase;
}

.logout-link {
  font-size: 13px;
  color: var(--grey-zone);
  text-decoration: none;
}

h1.page-title {
  font-size: 46px;
  color: var(--red);
  margin: 4px 0 6px 0;
  line-height: 1;
}

.subtitle {
  color: var(--grey-zone);
  margin-bottom: 28px;
  font-size: 15px;
}

.section {
  border: 1px solid var(--white);
  padding: 24px;
  margin-bottom: 24px;
}

.section-title {
  color: var(--red);
  font-size: 22px;
  margin: 0 0 18px 0;
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

@media (max-width: 560px) {
  .stat-row { grid-template-columns: 1fr; }
}

.stat-card {
  border: 1px solid var(--white);
  padding: 16px;
  text-align: center;
}

.stat-label {
  font-size: 12px;
  letter-spacing: 0.1em;
  color: var(--grey-zone);
  text-transform: uppercase;
  margin-bottom: 6px;
}

.stat-value {
  font-family: 'Bayon', sans-serif;
  font-size: 32px;
  line-height: 1;
}

.zone-badge {
  display: inline-block;
  margin-top: 8px;
  padding: 3px 10px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-family: 'Bayon', sans-serif;
  border: 1px solid currentColor;
}

.zone-green { color: var(--green); }
.zone-grey  { color: var(--grey-zone); }
.zone-red   { color: var(--red); }

.prose-card {
  border: 1px solid var(--white);
  padding: 18px;
  margin-bottom: 14px;
}

.prose-card:last-child { margin-bottom: 0; }

.prose-card h3 {
  font-family: 'Bayon', sans-serif;
  color: var(--red);
  font-size: 16px;
  margin: 0 0 10px 0;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.prose-card p {
  margin: 0;
  line-height: 1.6;
  font-size: 15px;
}

.recommendation-box {
  border: 2px solid var(--red);
  padding: 22px;
}

.recommendation-box h3 {
  font-family: 'Bayon', sans-serif;
  color: var(--red);
  font-size: 20px;
  margin: 0 0 12px 0;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.recommendation-box p {
  margin: 0;
  line-height: 1.65;
  font-size: 15px;
}

.error-panel {
  border: 1px solid var(--red);
  color: var(--red);
  padding: 18px;
  margin-bottom: 20px;
  font-size: 14px;
}
"""

LOGIN_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The Gluten Free Cyclist - Health Snapshot</title>
  <style>{{ css }}</style>
</head>
<body>
  <div class="center-screen">
    <div class="login-box">
      <h1 class="display">Private Access</h1>
      <form method="post">
        <input type="password" name="password" placeholder="Password" autofocus required>
        <button type="submit" class="display">Enter</button>
      </form>
      {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
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
  <style>{{ css }}</style>
</head>
<body>
  <div class="wrap">
    <div class="top-bar">
      <span class="eyebrow">The Gluten Free Cyclist</span>
      <a class="logout-link" href="{{ url_for('logout') }}">Log out</a>
    </div>
    <h1 class="page-title display">Health Snapshot</h1>
    <p class="subtitle">Last {{ days }} days &middot; Intervals.icu data analyzed by AI</p>

    <form method="post" action="{{ url_for('analyze') }}">
      <button type="submit" class="btn display">Generate Snapshot</button>
    </form>

    {% if error %}
    <div class="error-panel">{{ error }}</div>
    {% endif %}

    {% if data %}
    <div class="section">
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
      <div class="prose-card">
        <h3>Training Load</h3>
        <p>{{ data.training_load }}</p>
      </div>
      <div class="prose-card">
        <h3>Training Distribution</h3>
        <p>{{ data.training_distribution }}</p>
      </div>
    </div>

    <div class="section">
      <h2 class="section-title display">Health</h2>
      <div class="stat-row">
        <div class="stat-card">
          <div class="stat-label">Resting HR</div>
          <div class="stat-value">{{ data.latest_rhr }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">HRV</div>
          <div class="stat-value">{{ data.latest_hrv }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Avg Sleep</div>
          <div class="stat-value">{{ data.avg_sleep }}</div>
        </div>
      </div>
      <div class="prose-card">
        <h3>Fatigue Signals</h3>
        <p>{{ data.fatigue_signals }}</p>
      </div>
    </div>

    <div class="recommendation-box">
      <h3 class="display">Recommendation</h3>
      <p>{{ data.recommendation }}</p>
    </div>
    {% endif %}
  </div>
</body>
</html>
"""


def require_login():
    return session.get("logged_in") is True


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if not APP_PASSWORD:
            error = "APP_PASSWORD is not configured on the server."
        elif request.form.get("password") == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("home"))
        else:
            error = "Incorrect password."
    return render_template_string(LOGIN_PAGE, error=error, css=BASE_CSS)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def home():
    if not require_login():
        return redirect(url_for("login"))
    return render_template_string(HOME_PAGE, days=DAYS_BACK, data=None, error=None, css=BASE_CSS)


def get_intervals_headers():
    credentials = f"API_KEY:{ICU_API_KEY}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {encoded}"}


def fetch_intervals_data():
    oldest = (date.today() - timedelta(days=DAYS_BACK)).isoformat()
    newest = date.today().isoformat()
    headers = get_intervals_headers()

    activities_fields = (
        "id,name,type,start_date_local,moving_time,elapsed_time,distance,"
        "icu_training_load,icu_weighted_avg_watts,average_watts,average_heartrate"
    )
    activities_url = (
        f"https://intervals.icu/api/v1/athlete/{ICU_ATHLETE_ID}/activities"
        f"?oldest={oldest}&newest={newest}&fields={activities_fields}"
    )

    wellness_fields = "id,restingHR,hrv,sleepSecs,weight,ctl,atl,rampRate"
    wellness_url = (
        f"https://intervals.icu/api/v1/athlete/{ICU_ATHLETE_ID}/wellness"
        f"?oldest={oldest}&newest={newest}&fields={wellness_fields}"
    )

    act_resp = requests.get(activities_url, headers=headers, timeout=30)
    act_resp.raise_for_status()
    wel_resp = requests.get(wellness_url, headers=headers, timeout=30)
    wel_resp.raise_for_status()

    activities = act_resp.json()
    activities = [a for a in activities if a.get("start_date_local", "")[:10] >= oldest]

    wellness = wel_resp.json()
    return activities, wellness


def classify_form(tsb):
    if tsb is None:
        return "grey"
    if tsb >= 5:
        return "green"
    if tsb <= -10:
        return "red"
    return "grey"


def classify_fatigue(atl, ctl):
    if atl is None or ctl is None:
        return "grey"
    if ctl == 0:
        return "grey"
    ratio = atl / ctl
    if ratio >= 1.15:
        return "red"
    if ratio <= 0.95:
        return "green"
    return "grey"


def classify_fitness_trend(wellness):
    ctl_values = [(w.get("id"), w.get("ctl")) for w in wellness if w.get("ctl") is not None]
    ctl_values.sort(key=lambda x: x[0])
    if len(ctl_values) < 2:
        return "grey"
    change = ctl_values[-1][1] - ctl_values[0][1]
    if change >= 2:
        return "green"
    if change <= -2:
        return "red"
    return "grey"


def compute_metrics(activities, wellness):
    sorted_wellness = sorted(wellness, key=lambda w: w.get("id", ""))
    latest = sorted_wellness[-1] if sorted_wellness else {}

    ctl = latest.get("ctl")
    atl = latest.get("atl")
    tsb = round(ctl - atl, 1) if (ctl is not None and atl is not None) else None

    sleep_values = [w["sleepSecs"] / 3600 for w in wellness if w.get("sleepSecs")]
    avg_sleep = round(statistics.mean(sleep_values), 1) if sleep_values else None

    return {
        "ctl": round(ctl, 1) if ctl is not None else "n/a",
        "atl": round(atl, 1) if atl is not None else "n/a",
        "tsb": tsb if tsb is not None else "n/a",
        "fitness_zone": classify_fitness_trend(wellness),
        "fatigue_zone": classify_fatigue(atl, ctl),
        "form_zone": classify_form(tsb),
        "latest_rhr": latest.get("restingHR", "n/a"),
        "latest_hrv": latest.get("hrv", "n/a"),
        "avg_sleep": f"{avg_sleep}h" if avg_sleep is not None else "n/a",
    }


def build_data_text(activities, wellness):
    lines = ["ACTIVITIES:"]
    if not activities:
        lines.append("(no activities found on Intervals.icu for this period)")
    for a in activities:
        duration_sec = a.get("moving_time") or a.get("elapsed_time") or 0
        power = a.get("icu_weighted_avg_watts") or a.get("average_watts") or "n/a"
        lines.append(
            "- {date} | {name} | {type} | {dur} min | load {load} | "
            "power {pwr} | HR {hr}".format(
                date=a.get("start_date_local", "")[:10],
                name=a.get("name", ""),
                type=a.get("type", ""),
                dur=round(duration_sec / 60),
                load=a.get("icu_training_load", "n/a"),
                pwr=power,
                hr=a.get("average_heartrate", "n/a"),
            )
        )

    lines.append("\nWELLNESS:")
    for w in sorted(wellness, key=lambda x: x.get("id", "")):
        lines.append(
            "- {date} | RHR {rhr} | HRV {hrv} | sleep {sleep}h | CTL {ctl} | ATL {atl}".format(
                date=w.get("id", ""),
                rhr=w.get("restingHR", "n/a"),
                hrv=w.get("hrv", "n/a"),
                sleep=round(w["sleepSecs"] / 3600, 1) if w.get("sleepSecs") else "n/a",
                ctl=round(w["ctl"], 1) if w.get("ctl") is not None else "n/a",
                atl=round(w["atl"], 1) if w.get("atl") is not None else "n/a",
            )
        )

    return "\n".join(lines)


def ask_claude(data_text, metrics):
    prompt = (
        "You are an expert cycling coach. The athlete trains indoors on Zwift twice a day, "
        "every day: a Zone 2 session in the morning, and in the evening alternates VO2max "
        "sessions with Zone 2 sessions. They race outdoors from March to September. "
        "They currently have Fitness (CTL) = {ctl} [{fitness_zone} zone], "
        "Fatigue (ATL) = {atl} [{fatigue_zone} zone], Form (TSB) = {tsb} [{form_zone} zone]. "
        "Analyze the following data from the last {days} days.\n\n"
        "Respond ONLY with valid JSON (no markdown fences, no extra text) with exactly these "
        "keys, each a plain-prose string with no bullet points, no markdown symbols, no line "
        "breaks:\n"
        '- "training_load": 2-3 sentences on how training load and volume have been trending\n'
        '- "training_distribution": 2-3 sentences identifying whether the training mix looks '
        "polarized, pyramidal, threshold-heavy or sweetspot-heavy, based on the session types "
        "and loads shown, with brief reasoning\n"
        '- "fatigue_signals": 2-3 sentences on resting HR, HRV and sleep trends and what they '
        "suggest about recovery\n"
        '- "recommendation": a detailed, specific recommendation (4-6 sentences) for the next '
        "3-5 days of training, referencing the actual numbers above\n\n"
        "DATA:\n{data_text}"
    ).format(
        ctl=metrics["ctl"], fitness_zone=metrics["fitness_zone"],
        atl=metrics["atl"], fatigue_zone=metrics["fatigue_zone"],
        tsb=metrics["tsb"], form_zone=metrics["form_zone"],
        days=DAYS_BACK, data_text=data_text,
    )

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 900,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    resp_data = resp.json()
    text = "".join(block.get("text", "") for block in resp_data.get("content", []))

    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


@app.route("/analyze", methods=["POST"])
def analyze():
    if not require_login():
        return redirect(url_for("login"))

    error = None
    data = None
    try:
        activities, wellness = fetch_intervals_data()
        metrics = compute_metrics(activities, wellness)
        data_text = build_data_text(activities, wellness)
        analysis = ask_claude(data_text, metrics)
        data = {**metrics, **analysis}
    except requests.HTTPError as e:
        error = f"Error calling an external service: {e}"
    except (json.JSONDecodeError, KeyError) as e:
        error = f"The AI response could not be parsed: {e}"
    except Exception as e:
        error = f"Unexpected error: {e}"

    return render_template_string(HOME_PAGE, days=DAYS_BACK, data=data, error=error, css=BASE_CSS)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
