import os
import requests
import psycopg2
from datetime import datetime
import time

# ==========================================
# CONFIG
# ==========================================

DATABASE_URL = os.environ.get("DATABASE_URL")

PROXY_BASE_URL = "https://odds-proxy-u4wg.onrender.com"

LEAGUES = {
    "EPL": "soccer_epl",
    "LaLiga": "soccer_spain_la_liga",
    "SerieA": "soccer_italy_serie_a",
    "Bundesliga": "soccer_germany_bundesliga",
    "Ligue1": "soccer_france_ligue_one"
}

# ==========================================
# DATABASE
# ==========================================

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def clear_old_matches(conn):
    print("Clearing old upcoming matches...")
    with conn.cursor() as cur:
        cur.execute("DELETE FROM upcoming_matches;")
    conn.commit()

def insert_match(conn, league, home, away, match_time, home_odds, draw_odds, away_odds):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO upcoming_matches
            (league, home_team, away_team, match_time, home_odds, draw_odds, away_odds)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (league, home, away, match_time, home_odds, draw_odds, away_odds))

# ==========================================
# ODDS EXTRACTION
# ==========================================

def extract_odds(bookmakers):
    if not bookmakers:
        return None, None, None

    for bookmaker in bookmakers:
        markets = bookmaker.get("markets", [])
        for market in markets:
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

# ==========================================
# FETCH FROM PROXY
# ==========================================

def fetch_league(league_key):
    print(f"Fetching {league_key}...")
    response = requests.get(
        f"{PROXY_BASE_URL}/odds",
        params={"league": league_key},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# ==========================================
# MAIN
# ==========================================

def main():
    print("Starting upcoming matches update...")

    conn = get_connection()
    clear_old_matches(conn)

    total_inserted = 0

    for league_name, league_key in LEAGUES.items():
        print(f"\n=== {league_name} ===")

        try:
            matches = fetch_league(league_key)
        except Exception as e:
            print(f"FAILED {league_name}: {e}")
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

            insert_match(
                conn,
                league_name,
                home,
                away,
                dt,
                home_odds,
                draw_odds,
                away_odds
            )

            total_inserted += 1

        conn.commit()

    conn.close()

    print(f"\nTOTAL INSERTED: {total_inserted}")
    print("Done.")

if __name__ == "__main__":
    main()
