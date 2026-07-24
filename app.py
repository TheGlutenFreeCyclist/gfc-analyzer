def fetch_intervals_data():
    """Scarica eventi (attività) e dati di benessere usando l'endpoint /events."""
    oldest = (date.today() - timedelta(days=DAYS_BACK)).isoformat()
    newest = date.today().isoformat()
    auth = ("API_KEY", ICU_API_KEY)

    # Endpoint EVENTS: restituisce direttamente tutti i dettagli (watt, moving_time, icu_training_load)
    events_url = (
        f"https://intervals.icu/api/v1/athlete/{ICU_ATHLETE_ID}/events"
        f"?oldest={oldest}&newest={newest}"
    )
    wellness_url = (
        f"https://intervals.icu/api/v1/athlete/{ICU_ATHLETE_ID}/wellness"
        f"?oldest={oldest}&newest={newest}"
    )

    ev_resp = requests.get(events_url, auth=auth, timeout=30)
    ev_resp.raise_for_status()
    raw_events = ev_resp.json()

    # Filtriamo tenendo solo gli eventi che sono effettive attività (type == 'Activity')
    activities = [e for e in raw_events if e.get("type") == "Activity" or e.get("moving_time")]

    wel_resp = requests.get(wellness_url, auth=auth, timeout=30)
    wel_resp.raise_for_status()

    return activities, wel_resp.json()
