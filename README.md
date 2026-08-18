# Stuff Model — Pitch Quality from Physics

A "stuff model" that grades how nasty an MLB pitch is based purely on its
physical characteristics — velocity, movement, spin, and release — using
real Statcast pitch-by-pitch data.

The model predicts the run value of a pitch from its physics alone,
deliberately excluding location and count, so it measures the pitch's
inherent quality rather than the pitcher's command or the game situation.
This is how modern MLB front offices quantify "stuff."

## Approach

1. Ingest real Statcast data (via pybaseball), season by season, through a
   bronze -> silver -> gold pipeline into a DuckDB warehouse.
2. Build a run-expectancy foundation and assign each pitch a run value.
3. Engineer pitcher-relative physics features (movement vs. the pitcher's
   own fastball, velocity separation, spin efficiency, release consistency).
4. Model run value from those features, validated on held-out future seasons.
5. Explain each pitch's grade with SHAP, and serve it through a
   front-office-style scouting dashboard.

## Stack

Python (pandas, pybaseball, scikit-learn, XGBoost, SHAP) · DuckDB ·
R (statistical validation) · Next.js + FastAPI · deployed live

## Status

Early — building the ingestion pipeline.