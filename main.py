import os
import requests
import psycopg2
from datetime import datetime
from fastapi import FastAPI

app = FastAPI()

DATABASE_URL = os.environ.get("DATABASE_URL")
PROXY_BASE_URL = "https://odds-proxy-u4wg.onrender.com"

LEAGUES = {
    "EPL": "soccer_epl",
    "LaLiga": "soccer_spain_la_liga",
    "SerieA": "soccer_italy_serie_a",
    "Bundesliga": "soccer_germany_bundesliga",
    "Ligue1": "soccer_france_ligue_one"
}

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def extract_odds(bookmakers):
    if not bookmakers:
        return None, None, None

    for bookmaker in bookmakers:
        for market in bookmaker.get("markets", []):
            if market.get("key") == "h2h":
                outcomes = market.get("outcomes", [])
                home = draw = away = None

                for outcome in outcomes:
                    name = outcome.get("name", "").lower()
                    price = outcome.get("price")

                    if name == "draw":
                        draw = price
                    else:
                        if home is None:
                            home = price
                        else:
                            away = price

                return home, draw, away

    return None, None, None

@app.get("/")
def root():
    return {"status": "Updater is running"}

@app.get("/update")
def update_matches():
    conn = get_connection()
    total_inserted = 0

    with conn.cursor() as cur:
        cur.execute("DELETE FROM upcoming_matches;")
        conn.commit()

    for league_name, league_key in LEAGUES.items():
        try:
            response = requests.get(
                f"{PROXY_BASE_URL}/odds",
                params={"league": league_key},
                timeout=30
            )
            response.raise_for_status()
            matches = response.json()
        except Exception:
            continue

        for match in matches:
            home = match.get("home_team")
            away = match.get("away_team")
            commence_time = match.get("commence_time")

            home_odds, draw_odds, away_odds = extract_odds(
                match.get("bookmakers", [])
            )

            if not all([home, away, home_odds, away_odds]):
                continue

            try:
                dt = datetime.fromisoformat(
                    commence_time.replace("Z", "+00:00")
                )
            except:
                continue

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO upcoming_matches
                    (league, home_team, away_team, match_time, home_odds, draw_odds, away_odds)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    league_name,
                    home,
                    away,
                    dt,
                    home_odds,
                    draw_odds,
                    away_odds
                ))

            total_inserted += 1

        conn.commit()

    conn.close()

    return {"inserted": total_inserted}
