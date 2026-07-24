import base64
import os
from datetime import date, timedelta

import requests
from flask import Flask, session, request, redirect, url_for, render_template_string

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-questa-chiave")
ICU_API_KEY = os.environ.get("ICU_API_KEY", "")
ICU_ATHLETE_ID = os.environ.get("ICU_ATHLETE_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

app.secret_key = SECRET_KEY

DAYS_BACK = 14

LOGIN_PAGE = """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The Gluten Free Cyclist - Analisi</title>
  <style>
    body { font-family: -apple-system, sans-serif; background:#111; color:#eee;
           display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }
    .box { background:#1c1c1c; padding:32px; border-radius:12px; width:90%; max-width:340px; }
    input { width:100%; padding:12px; margin-top:12px; border-radius:8px; border:1px solid #444;
            background:#111; color:#eee; box-sizing:border-box; font-size:16px; }
    button { width:100%; padding:12px; margin-top:16px; border-radius:8px; border:none;
             background:#e0722f; color:white; font-size:16px; font-weight:600; cursor:pointer; }
    .error { color:#ff6b6b; margin-top:10px; font-size:14px; }
    h1 { font-size:20px; }
  </style>
</head>
<body>
  <div class="box">
    <h1>Accesso privato</h1>
    <form method="post">
      <input type="password" name="password" placeholder="Password" autofocus required>
      <button type="submit">Entra</button>
    </form>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
  </div>
</body>
</html>
"""

HOME_PAGE = """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The Gluten Free Cyclist - Analisi</title>
  <style>
    body { font-family: -apple-system, sans-serif; background:#111; color:#eee;
           margin:0; padding:24px; }
    .wrap { max-width:640px; margin:0 auto; }
    button { padding:14px 20px; border-radius:8px; border:none;
             background:#e0722f; color:white; font-size:16px; font-weight:600; width:100%; cursor:pointer; }
    .result { white-space:pre-wrap; background:#1c1c1c; padding:20px; border-radius:12px;
               margin-top:20px; line-height:1.5; font-family:monospace; font-size:13px; }
    a.logout { color:#888; font-size:13px; float:right; text-decoration:none; }
  </style>
</head>
<body>
  <div class="wrap">
    <a class="logout" href="{{ url_for('logout') }}">Esci</a>
    <h1>Analisi allenamento</h1>
    <p>Ultimi {{ days }} giorni da Intervals.icu, analizzati dall'AI.</p>
    <form method="post" action="{{ url_for('analyze') }}">
      <button type="submit">Analizza i miei dati</button>
    </form>
    {% if error %}<div class="result">⚠️ {{ error }}</div>{% endif %}
    {% if result %}<div class="result">{{ result }}</div>{% endif %}
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
            error = "APP_PASSWORD non configurata sul server."
        elif request.form.get("password") == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("home"))
        else:
            error = "Password sbagliata."
    return render_template_string(LOGIN_PAGE, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def home():
    if not require_login():
        return redirect(url_for("login"))
    return render_template_string(HOME_PAGE, days=DAYS_BACK, result=None, error=None)


def get_intervals_headers():
    credentials = f"API_KEY:{ICU_API_KEY}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {encoded}",
        "Accept": "application/json",
    }


def fetch_intervals_data():
    oldest = (date.today() - timedelta(days=DAYS_BACK)).isoformat()
    newest = date.today().isoformat()
    headers = get_intervals_headers()

    activities_url = (
        f"https://intervals.icu/api/v1/athlete/{ICU_ATHLETE_ID}/activities"
        f"?oldest={oldest}&newest={newest}"
    )
    wellness_url = (
        f"https://intervals.icu/api/v1/athlete/{ICU_ATHLETE_ID}/wellness"
        f"?oldest={oldest}&newest={newest}"
    )

    act_resp = requests.get(activities_url, headers=headers, timeout=30)
    act_resp.raise_for_status()

    wel_resp = requests.get(wellness_url, headers=headers, timeout=30)
    wel_resp.raise_for_status()

    return act_resp.json(), wel_resp.json()


@app.route("/analyze", methods=["POST"])
def analyze():
    if not require_login():
        return redirect(url_for("login"))

    error = None
    result = None
    try:
        activities, wellness = fetch_intervals_data()
        
        # Ispezioniamo esattamente cosa c'è dentro l'oggetto restituito da Intervals
        debug_info = f"NUMERO ATTIVITA' RICEVUTE: {len(activities)}\n\n"
        if activities:
            import json
            # Stampiamo per intero la PRIMA e l'ULTIMA attività ricevute
            debug_info += "=== PRIMA ATTIVITA' (JSON GREZZO) ===\n"
            debug_info += json.dumps(activities[0], indent=2)
            debug_info += "\n\n=== ULTIMA ATTIVITA' (JSON GREZZO) ===\n"
            debug_info += json.dumps(activities[-1], indent=2)
        else:
            debug_info += "Nessuna attività ricevuta nel range."

        result = debug_info

    except requests.HTTPError as e:
        error = f"Errore chiamando un servizio esterno: {e}"
    except Exception as e:
        error = f"Errore imprevisto: {e}"

    return render_template_string(HOME_PAGE, days=DAYS_BACK, result=result, error=error)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
