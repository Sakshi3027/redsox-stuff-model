"""
FastAPI backend for the stuff-model scouting dashboard.

Serves the graded data:
  GET /api/pitchers?year=2024   - leaderboard of pitchers by Stuff+
  GET /api/pitcher/{id}?year=   - one pitcher's full arsenal
  GET /api/design/{id}          - pitch-design suggestions for a pitcher
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
try:
    design = pd.read_parquet(DATA / "pitch_design.parquet")
except Exception:
    design = pd.DataFrame(columns=["pitcher", "pitch_type", "best_knob",
                                   "best_delta", "projected_gain", "base_stuff"])
try:
    undervalued = pd.read_parquet(DATA / "undervalued.parquet")
except Exception:
    undervalued = pd.DataFrame(columns=["pitcher", "player_name",
                                        "overall_stuff", "gap"])
try:
    risers = pd.read_parquet(DATA / "risers_fallers.parquet")
except Exception:
    risers = pd.DataFrame(columns=["pitcher", "player_name",
                                   "overall_stuff_2023", "overall_stuff_2024", "delta"])
try:
    similarity = pd.read_parquet(DATA / "similarity.parquet")
except Exception:
    similarity = pd.DataFrame(columns=["pitcher", "similar_pitcher",
                                       "similar_name", "similarity"])
            
# nice display names for pitch codes
PITCH_NAMES = {
    "FF": "Four-Seam", "SI": "Sinker", "FC": "Cutter", "SL": "Slider",
    "ST": "Sweeper", "SV": "Slurve", "CU": "Curveball", "KC": "Knuckle-Curve",
    "CH": "Changeup", "FS": "Splitter",
}

KNOB_LABELS = {
    "pfx_x_in": "horizontal break", "pfx_z_in": "vertical break",
    "release_speed": "velocity", "velo_sep": "separation off fastball",
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


@app.get("/api/design/{pitcher_id}")
def get_design(pitcher_id: int):
    d = design[design["pitcher"] == pitcher_id].copy()
    if d.empty:
        return {"pitcher": pitcher_id, "suggestions": []}
    d["knob_label"] = d["best_knob"].map(KNOB_LABELS).fillna(d["best_knob"])
    d["direction"] = d["best_delta"].apply(lambda x: "more" if x > 0 else "less")
    d["pitch_name"] = d["pitch_type"].map(PITCH_NAMES).fillna(d["pitch_type"])
    d = d.sort_values("projected_gain", ascending=False)
    return {
        "pitcher": pitcher_id,
        "suggestions": d[[
            "pitch_type", "pitch_name", "knob_label", "direction",
            "best_delta", "projected_gain", "base_stuff",
        ]].to_dict(orient="records"),
    }


@app.get("/api/drivers")
def get_drivers():
    return drivers.head(12).to_dict(orient="records")

@app.get("/api/undervalued")
def get_undervalued(limit: int = 12):
    df = undervalued.sort_values("gap", ascending=False)
    buy = df.head(limit)
    sell = df.tail(limit).iloc[::-1]
    cols = ["pitcher", "player_name", "overall_stuff",
            "stuff_pct", "results_pct", "gap"]
    return {
        "undervalued": buy[cols].to_dict(orient="records"),
        "overvalued": sell[cols].to_dict(orient="records"),
    }

@app.get("/api/trends")
def get_trends(limit: int = 12):
    df = risers.sort_values("delta", ascending=False)
    cols = ["pitcher", "player_name", "overall_stuff_2023",
            "overall_stuff_2024", "delta"]
    return {
        "risers": df.head(limit)[cols].to_dict(orient="records"),
        "fallers": df.tail(limit).iloc[::-1][cols].to_dict(orient="records"),
    }

@app.get("/api/similar/{pitcher_id}")
def get_similar(pitcher_id: int):
    s = similarity[similarity["pitcher"] == pitcher_id].copy()
    if s.empty:
        return {"pitcher": pitcher_id, "comps": []}
    s = s.sort_values("similarity", ascending=False)
    return {
        "pitcher": pitcher_id,
        "comps": s[["similar_pitcher", "similar_name", "similarity"]]
        .to_dict(orient="records"),
    }