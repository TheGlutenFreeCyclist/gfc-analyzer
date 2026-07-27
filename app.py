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
ATHLETE_CONTEXT = os.environ.get(
    "ATHLETE_CONTEXT",
    "The athlete trains indoors on Zwift twice a day, every day: a Zone 2 session "
    "in the morning, and in the evening alternates VO2max sessions with Zone 2 "
    "sessions. They race outdoors from March to September.",
)

app.secret_key = SECRET_KEY

DAYS_BACK = 20          # recent health / freshness window
SEASON_DAYS_BACK = 90   # longer window for periodization / polarization analysis

LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAASwAAAFNCAMAAACNC6K4AAAB/lBMVEXeqJuvr6/42aneeYGfjHedopx/f396rsGZ1NwiY4ZhLTZRQzt3Z1X22s0aKC5joK2UZ2eFP0f/f3//qqrvv8Dl5eUAAAATFSL5+fkkgqkGBxEQExzlaGtWwdp6fIX///+Eho4nKDHn6OocgahzdHtnaHBHR1DV1tkrd5bHyMunqKwkfqk4OkSUlZq0tbkbe6VUlq/+/v59gIj+/v5VvdcyMzsoa4sTIzNZWmPZ8vRSU1oWN00mWXIbd5vT5ekeW3TocnabnKJmxdrRaW9jyeMuZHna3eFax+H7+/u8vMEzQ079/f38/Py1xctPKDAbRFj9/f1upriJuMYcSWReYWkSLEMtGyQ1gp2AfogqFBtzPEOMR06WxdBIi6NpuM2x09z72KlHhpkNDiFXpbixXGS42eIiS2WnVlydoaX1zprZcndDeo1pNTtjnLC6Ymh1Q0mZUlhUNDMkCxTg3uJYq8L30JtDPkdgXmegnqXAvsNw0uWz6O1CHSZXvuFmVUyO2uUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB/DSNVAAAAgHRSTlP/A/////8C//////////////8CA/8KAP/+////////BP//////////////////////Kf9R///////////////////////////P//9wr////5D//////////////////////////////////////////////////////////////3evlWoAAD6hSURBVHja7Z2JX9tIsvjZ6+273/tdI9OdCEnosGRJEA/CjgAHk+CMmUAmGULITJLZJHNkk7lnd67dffuv/7qqW1Lrsg3YBnaiz0zigG2sL1XVdXX1wltvromvhTcI3sB6A+sNrDew3sB6A+sNgssKa0lc+YdvYFVyOtE3fpGwkMY/icfX3n73vTt37rzzDvvjvXffvrZ0kYgtXBRxQkzvNEqXhOzc9XLhYnB6704Fp+x6586FELKFc+W0tFQtTjXE3mPEls6R2ML8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"

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
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 24px;
}

.logo-img {
  width: 180px;
  height: auto;
  margin-bottom: 18px;
}

.login-box {
  background: var(--panel);
  border: 1px solid var(--white);
  padding: 36px 32px;
  width: 100%;
  max-width: 360px;
  text-align: center;
}

.login-box h1 {
  font-size: 22px;
  margin: 0 0 24px 0;
  color: var(--white);
  font-weight: 400;
  letter-spacing: 0.04em;
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
  margin: 4px 0 2px 0;
  line-height: 1;
}

.powered-by {
  font-style: italic;
  color: var(--white);
  font-size: 14px;
  margin: 0 0 4px 0;
}

.subtitle {
  color: var(--grey-zone);
  margin-bottom: 28px;
  font-size: 13px;
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

.stat-sub {
  font-size: 11px;
  color: var(--grey-zone);
  margin-top: 4px;
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
    <img class="logo-img" src="data:image/png;base64,{{ logo }}" alt="The Gluten Free Cyclist">
    <div class="login-box">
      <h1>Please Log In</h1>
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
    <p class="powered-by">Powered by Andrea, The Gluten Free Cyclist</p>
    <p class="subtitle">Recent window: last {{ days }} days &middot; Season window: last {{ season_days }} days &middot; Intervals.icu data analyzed by AI</p>

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
    </div>

    <div class="section">
      <h2 class="section-title display">Season</h2>
      <p class="subtitle" style="margin-bottom:16px;">Based on the last {{ season_days }} days of activity data</p>
      <div class="stat-row">
        <div class="stat-card">
          <div class="stat-label">Total Time</div>
          <div class="stat-value">{{ data.season_hours }}h</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Low Intensity</div>
          <div class="stat-value">{{ data.zone_low_pct }}%</div>
          <div class="stat-sub">easy / endurance</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">High Intensity</div>
          <div class="stat-value">{{ data.zone_high_pct }}%</div>
          <div class="stat-sub">VO2 / anaerobic</div>
        </div>
      </div>
      <div class="prose-card">
        <h3>Training Distribution</h3>
        <p>{{ data.season_distribution }}</p>
      </div>
      <div class="prose-card">
        <h3>Seasonal Outlook</h3>
        <p>{{ data.season_outlook }}</p>
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
    return render_template_string(LOGIN_PAGE, error=error, css=BASE_CSS, logo=LOGO_B64)


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
        data=None, error=None, css=BASE_CSS,
    )


def get_intervals_headers():
    credentials = f"API_KEY:{ICU_API_KEY}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {encoded}"}


def fetch_intervals_data():
    """Fetch SEASON_DAYS_BACK days of activities (with zone times) plus
    DAYS_BACK days of wellness. The recent-window activities are simply the
    tail end of the season list, so we only hit the activities endpoint once."""
    season_oldest = (date.today() - timedelta(days=SEASON_DAYS_BACK)).isoformat()
    recent_oldest = (date.today() - timedelta(days=DAYS_BACK)).isoformat()
    newest = date.today().isoformat()
    headers = get_intervals_headers()

    activities_fields = (
        "id,name,type,start_date_local,moving_time,elapsed_time,distance,"
        "icu_training_load,icu_weighted_avg_watts,average_watts,average_heartrate,"
        "icu_zone_times"
    )
    activities_url = (
        f"https://intervals.icu/api/v1/athlete/{ICU_ATHLETE_ID}/activities"
        f"?oldest={season_oldest}&newest={newest}&fields={activities_fields}"
    )

    wellness_fields = "id,restingHR,hrv,sleepSecs,weight,ctl,atl,rampRate,comments"
    wellness_url = (
        f"https://intervals.icu/api/v1/athlete/{ICU_ATHLETE_ID}/wellness"
        f"?oldest={recent_oldest}&newest={newest}&fields={wellness_fields}"
    )

    act_resp = requests.get(activities_url, headers=headers, timeout=30)
    act_resp.raise_for_status()
    wel_resp = requests.get(wellness_url, headers=headers, timeout=30)
    wel_resp.raise_for_status()

    season_activities = act_resp.json()
    season_activities = [
        a for a in season_activities if a.get("start_date_local", "")[:10] >= season_oldest
    ]
    recent_activities = [
        a for a in season_activities if a.get("start_date_local", "")[:10] >= recent_oldest
    ]

    wellness = wel_resp.json()
    return recent_activities, season_activities, wellness


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


def bucket_zone_seconds(zone_seconds):
    """Given an ordered list of seconds-per-zone (easiest to hardest), bucket
    into Low / Moderate / High using common Coggan-style zone groupings."""
    n = len(zone_seconds)
    if n == 0:
        return 0, 0, 0
    if n == 3:
        low, mod, high = zone_seconds[0], zone_seconds[1], zone_seconds[2]
    elif n in (5, 6):
        low = sum(zone_seconds[0:2])
        mod = zone_seconds[2] if n == 5 else sum(zone_seconds[2:4])
        high = sum(zone_seconds[3:]) if n == 5 else sum(zone_seconds[4:])
    elif n == 7:
        low = sum(zone_seconds[0:2])
        mod = sum(zone_seconds[2:4])
        high = sum(zone_seconds[4:])
    else:
        third = max(1, n // 3)
        low = sum(zone_seconds[0:third])
        mod = sum(zone_seconds[third:2 * third])
        high = sum(zone_seconds[2 * third:])
    return low, mod, high


def compute_season_stats(season_activities):
    total_secs = 0
    low_secs = mod_secs = high_secs = 0
    total_load = 0

    for a in season_activities:
        total_secs += a.get("moving_time") or a.get("elapsed_time") or 0
        total_load += a.get("icu_training_load") or 0
        zt = a.get("icu_zone_times")
        if zt:
            secs_list = [z.get("secs", 0) for z in zt]
            low, mod, high = bucket_zone_seconds(secs_list)
            low_secs += low
            mod_secs += mod
            high_secs += high

    zone_total = low_secs + mod_secs + high_secs
    if zone_total > 0:
        low_pct = round(100 * low_secs / zone_total)
        mod_pct = round(100 * mod_secs / zone_total)
        high_pct = round(100 * high_secs / zone_total)
    else:
        low_pct = mod_pct = high_pct = None

    return {
        "season_hours": round(total_secs / 3600, 1),
        "season_total_load": round(total_load),
        "zone_low_pct": low_pct if low_pct is not None else "n/a",
        "zone_mod_pct": mod_pct if mod_pct is not None else "n/a",
        "zone_high_pct": high_pct if high_pct is not None else "n/a",
    }


def compute_metrics(wellness):
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


def build_data_text(recent_activities, wellness, season_stats):
    lines = ["RECENT ACTIVITIES (last {} days):".format(DAYS_BACK)]
    if not recent_activities:
        lines.append("(no activities found on Intervals.icu for this period)")
    for a in recent_activities:
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

    lines.append("\nSEASON SUMMARY (last {} days, time-in-zone based):".format(SEASON_DAYS_BACK))
    lines.append(
        "- Total training time: {}h | Total load: {} | "
        "Low intensity: {}% | Moderate intensity: {}% | High intensity: {}%".format(
            season_stats["season_hours"], season_stats["season_total_load"],
            season_stats["zone_low_pct"], season_stats["zone_mod_pct"], season_stats["zone_high_pct"],
        )
    )

    lines.append("\nWELLNESS (last {} days):".format(DAYS_BACK))
    for w in sorted(wellness, key=lambda x: x.get("id", "")):
        line = (
            "- {date} | RHR {rhr} | HRV {hrv} | sleep {sleep}h | CTL {ctl} | ATL {atl}".format(
                date=w.get("id", ""),
                rhr=w.get("restingHR", "n/a"),
                hrv=w.get("hrv", "n/a"),
                sleep=round(w["sleepSecs"] / 3600, 1) if w.get("sleepSecs") else "n/a",
                ctl=round(w["ctl"], 1) if w.get("ctl") is not None else "n/a",
                atl=round(w["atl"], 1) if w.get("atl") is not None else "n/a",
            )
        )
        if w.get("comments"):
            line += " | note: {}".format(w["comments"])
        lines.append(line)

    return "\n".join(lines)


def ask_claude(data_text, metrics):
    prompt = (
        "You are an expert cycling coach. {athlete_context} "
        "They currently have Fitness (CTL) = {ctl} [{fitness_zone} zone], "
        "Fatigue (ATL) = {atl} [{fatigue_zone} zone], Form (TSB) = {tsb} [{form_zone} zone]. "
        "Analyze the following data. Some wellness entries may include a free-text note "
        "(e.g. reporting an injury, illness or soreness) — if present, factor it explicitly "
        "into fatigue_signals and into the recommendation. The SEASON SUMMARY gives real "
        "time-in-zone percentages (not average power, which is misleading for interval "
        "sessions) — use those percentages, not the recent activity list, to judge whether "
        "training is polarized (mostly low + high intensity, little moderate), pyramidal "
        "(low > moderate > high, but a meaningful moderate chunk), or threshold/sweetspot-heavy "
        "(a large moderate-intensity share).\n\n"
        "Respond ONLY with valid JSON (no markdown fences, no extra text) with exactly these "
        "keys, each a plain-prose string with no bullet points, no markdown symbols, no line "
        "breaks:\n"
        '- "training_load": 2-3 sentences on how recent training load and volume (last {days} '
        "days) have been trending\n"
        '- "season_distribution": 2-3 sentences classifying the {season_days}-day training '
        "distribution (polarized / pyramidal / threshold-heavy) using the real zone percentages, "
        "with brief reasoning\n"
        '- "season_outlook": 3-4 sentences on whether this {season_days}-day pattern is likely '
        "to keep producing improvements given the athlete's race season, and what to adjust if not\n"
        '- "fatigue_signals": 2-3 sentences on resting HR, HRV, sleep trends and any logged notes\n'
        '- "recommendation": a detailed, specific recommendation (4-6 sentences) for the next '
        "3-5 days of training, referencing the actual numbers above\n\n"
        "DATA:\n{data_text}"
    ).format(
        athlete_context=ATHLETE_CONTEXT,
        ctl=metrics["ctl"], fitness_zone=metrics["fitness_zone"],
        atl=metrics["atl"], fatigue_zone=metrics["fatigue_zone"],
        tsb=metrics["tsb"], form_zone=metrics["form_zone"],
        days=DAYS_BACK, season_days=SEASON_DAYS_BACK, data_text=data_text,
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
            "max_tokens": 1100,
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
        recent_activities, season_activities, wellness = fetch_intervals_data()
        metrics = compute_metrics(wellness)
        season_stats = compute_season_stats(season_activities)
        data_text = build_data_text(recent_activities, wellness, season_stats)
        analysis = ask_claude(data_text, metrics)
        data = {**metrics, **season_stats, **analysis}
    except requests.HTTPError as e:
        error = f"Error calling an external service: {e}"
    except (json.JSONDecodeError, KeyError) as e:
        error = f"The AI response could not be parsed: {e}"
    except Exception as e:
        error = f"Unexpected error: {e}"

    return render_template_string(
        HOME_PAGE, days=DAYS_BACK, season_days=SEASON_DAYS_BACK,
        data=data, error=error, css=BASE_CSS,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
