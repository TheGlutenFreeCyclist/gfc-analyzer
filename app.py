import os
from datetime import date, timedelta

import requests
from flask import Flask, session, request, redirect, url_for, render_template_string

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configurazione: TUTTE queste vengono lette da variabili d'ambiente.
# Non scrivere MAI qui dentro chiavi o password: si impostano su Render,
# nella sezione "Environment" del tuo servizio.
# ---------------------------------------------------------------------------
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-questa-chiave")
ICU_API_KEY = os.environ.get("ICU_API_KEY", "")
ICU_ATHLETE_ID = os.environ.get("ICU_ATHLETE_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

app.secret_key = SECRET_KEY

DAYS_BACK = 14  # quanti giorni di storico analizzare

# ---------------------------------------------------------------------------
# Pagine HTML semplici, incluse direttamente qui dentro (niente file separati)
# ---------------------------------------------------------------------------

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
             background:#e0722f; color:white; font-size:16px; font-weight:600; }
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
             background:#e0722f; color:white; font-size:16px; font-weight:600; width:100%; }
    .result { white-space:pre-wrap; background:#1c1c1c; padding:20px; border-radius:12px;
               margin-top:20px; line-height:1.5; }
    a.logout { color:#888; font-size:13px; float:right; }
    .loading { color:#888; margin-top:16px; }
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


def fetch_intervals_data():
    """Scarica attività e dati di benessere dagli ultimi DAYS_BACK giorni."""
    oldest = (date.today() - timedelta(days=DAYS_BACK)).isoformat()
    newest = date.today().isoformat()
    auth = ("API_KEY", ICU_API_KEY)

    # Chiediamo esplicitamente i campi necessari per le attività a Intervals.icu
    fields = "id,start_date_local,name,type,moving_time,elapsed_time,icu_training_load,icu_weighted_avg_watts,average_watts,icu_average_watts,average_heartrate"

    activities_url = (
        f"https://intervals.icu/api/v1/athlete/{ICU_ATHLETE_ID}/activities"
        f"?oldest={oldest}&newest={newest}&fields={fields}"
    )
    wellness_url = (
        f"https://intervals.icu/api/v1/athlete/{ICU_ATHLETE_ID}/wellness"
        f"?oldest={oldest}&newest={newest}"
    )

    act_resp = requests.get(activities_url, auth=auth, timeout=30)
    act_resp.raise_for_status()
    wel_resp = requests.get(wellness_url, auth=auth, timeout=30)
    wel_resp.raise_for_status()

    return act_resp.json(), wel_resp.json()


def build_summary_text(activities, wellness):
    lines = ["ATTIVITA':"]
    if not activities:
        lines.append(
            "(nessuna attività trovata su Intervals.icu in questo periodo - "
            "verificare che Zwift/Garmin stiano sincronizzando correttamente)"
        )
    for a in activities:
        duration_sec = a.get("moving_time") or a.get("elapsed_time") or 0
        power = (
            a.get("icu_weighted_avg_watts")
            or a.get("average_watts")
            or a.get("icu_average_watts")
            or "n/d"
        )
        lines.append(
            "- {date} | {name} | {type} | durata {dur} min | "
            "carico {load} | potenza media {pwr} | FC media {hr}".format(
                date=str(a.get("start_date_local", ""))[:10],
                name=a.get("name", ""),
                type=a.get("type", ""),
                dur=round(duration_sec / 60),
                load=a.get("icu_training_load", "n/d"),
                pwr=power,
                hr=a.get("average_heartrate", "n/d"),
            )
        )

    lines.append("\nBENESSERE:")
    for w in wellness:
        lines.append(
            "- {date} | FC riposo {rhr} | HRV {hrv} | sonno {sleep} h | peso {weight}".format(
                date=w.get("id", ""),
                rhr=w.get("restingHR", "n/d"),
                hrv=w.get("hrv", "n/d"),
                sleep=round((w.get("sleepSecs") or 0) / 3600, 1) if w.get("sleepSecs") else "n/d",
                weight=w.get("weight", "n/d"),
            )
        )

    return "\n".join(lines)


def ask_claude(summary_text):
    prompt = (
        "Sei un coach di ciclismo esperto. L'atleta si allena indoor su Zwift due volte "
        "al giorno tutti i giorni: seduta Z2 al mattino, e la sera alterna sedute VO2max "
        "a sedute Z2. Gareggia su strada da marzo a settembre. Analizza i seguenti dati "
        "delle ultime due settimane ed evidenzia in italiano: 1) come sta andando il carico "
        "di allenamento, 2) eventuali segnali di affaticamento o necessità di recupero "
        "(da FC a riposo, HRV, sonno), 3) un suggerimento pratico per i prossimi giorni. "
        "Sii diretto e sintetico (max 200 parole).\n\n" + summary_text
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
            "max_tokens": 700,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return "".join(block.get("text", "") for block in data.get("content", []))


@app.route("/analyze", methods=["POST"])
def analyze():
    if not require_login():
        return redirect(url_for("login"))

    error = None
    result = None
    debug = None
    try:
        activities, wellness = fetch_intervals_data()
        debug = "Attività ricevute dalla API: {}".format(len(activities))
        if activities:
            first = activities[0]
            debug += "\nCampi del primo elemento: " + ", ".join(sorted(first.keys()))
            debug += "\nEsempio valori: name={}, type={}, moving_time={}, icu_training_load={}".format(
                first.get("name"), first.get("type"),
                first.get("moving_time"), first.get("icu_training_load"),
            )
        summary = build_summary_text(activities, wellness)
        result = ask_claude(summary)
    except requests.HTTPError as e:
        error = f"Errore chiamando un servizio esterno: {e}"
    except Exception as e:
        error = f"Errore imprevisto: {e}"

    if debug:
        result = "[DEBUG]\n" + debug + "\n\n[ANALISI]\n" + (result or "")

    return render_template_string(HOME_PAGE, days=DAYS_BACK, result=result, error=error)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
