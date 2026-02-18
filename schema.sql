CREATE TABLE IF NOT EXISTS upcoming_matches (
    id SERIAL PRIMARY KEY,
    league TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    match_time TIMESTAMP NOT NULL,
    home_odds FLOAT,
    draw_odds FLOAT,
    away_odds FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_match_time ON upcoming_matches(match_time);
CREATE INDEX IF NOT EXISTS idx_league ON upcoming_matches(league);
