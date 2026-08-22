"""
FastAPI backend for the stuff-model scouting dashboard.

Serves the graded data:
  GET /api/pitchers?year=2024   - leaderboard of pitchers by Stuff+
  GET /api/pitcher/{id}?year=   - one pitcher's full arsenal
  GET /api/drivers              - SHAP global feature importance
  GET /api/health
"""
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

DATA = Path("dashboard/data")
ART = Path("model/artifacts")

app = FastAPI(title="Stuff Model API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

# load once at startup
pitchers = pd.read_parquet(DATA / "pitchers.parquet")
arsenal = pd.read_parquet(DATA / "arsenal.parquet")
try:
    drivers = pd.read_parquet(ART / "shap_importance.parquet")
except Exception:
    drivers = pd.DataFrame(columns=["feature", "mean_abs_shap"])

# nice display names for pitch codes
PITCH_NAMES = {
    "FF": "Four-Seam", "SI": "Sinker", "FC": "Cutter", "SL": "Slider",
    "ST": "Sweeper", "SV": "Slurve", "CU": "Curveball", "KC": "Knuckle-Curve",
    "CH": "Changeup", "FS": "Splitter",
}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/pitchers")
def list_pitchers(year: int = 2024, limit: int = 100):
    df = pitchers[pitchers["game_year"] == year].copy()
    df = df[df["total_pitches"] >= 300]
    df = df.sort_values("overall_stuff", ascending=False).head(limit)
    return df.to_dict(orient="records")


@app.get("/api/pitcher/{pitcher_id}")
def get_pitcher(pitcher_id: int, year: int = 2024):
    ars = arsenal[(arsenal["pitcher"] == pitcher_id) &
                  (arsenal["game_year"] == year)].copy()
    if ars.empty:
        raise HTTPException(status_code=404, detail="Pitcher not found for that year")
    ars = ars.sort_values("pitches", ascending=False)
    ars["pitch_name"] = ars["pitch_type"].map(PITCH_NAMES).fillna(ars["pitch_type"])

    head = pitchers[(pitchers["pitcher"] == pitcher_id) &
                    (pitchers["game_year"] == year)]
    return {
        "pitcher": pitcher_id,
        "name": ars["player_name"].iloc[0],
        "year": year,
        "overall_stuff": float(head["overall_stuff"].iloc[0]) if not head.empty else None,
        "total_pitches": int(ars["pitches"].sum()),
        "arsenal": ars[[
            "pitch_type", "pitch_name", "stuff_plus", "pitches",
            "avg_velo", "avg_movement", "avg_spin", "velo_sep",
        ]].to_dict(orient="records"),
    }


@app.get("/api/drivers")
def get_drivers():
    return drivers.head(12).to_dict(orient="records")