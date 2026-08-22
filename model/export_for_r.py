"""
Export a compact CSV of graded pitches for the R validation script.
(R reads CSV natively - avoids the arrow/parquet dependency.)
Aggregates to pitcher-season-pitchtype level so the file stays small.
"""
from pathlib import Path
import pandas as pd

MODEL_DIR = Path("model/artifacts")

df = pd.read_parquet(MODEL_DIR / "graded_pitches.parquet")

# Clip extreme Stuff+ outliers for sane analysis/plots
df = df[(df["stuff_plus"] > 0) & (df["stuff_plus"] < 200)]

# Pitcher-season-level Stuff+ (min 100 pitches for stability), for the
# year-over-year reliability analysis
per_season = (
    df.groupby(["pitcher", "player_name", "game_year"])
    .agg(stuff_plus=("stuff_plus", "mean"), pitches=("stuff_plus", "size"))
    .reset_index()
)
per_season = per_season[per_season["pitches"] >= 100]
per_season.to_csv(MODEL_DIR / "pitcher_season_stuff.csv", index=False)

# Pitch-level sample for the movement visualization (30k is plenty)
viz = df[["pitch_type", "stuff_plus"]].copy()
# pull movement back in from features for the plot
feat = pd.read_parquet("data/gold/features.parquet",
                       columns=["pfx_x_in", "pfx_z_in", "pitch_type", "release_speed"])
viz_sample = feat.sample(n=30000, random_state=42)
viz_sample.to_csv(MODEL_DIR / "movement_sample.csv", index=False)

print(f"wrote pitcher_season_stuff.csv ({len(per_season):,} pitcher-seasons)")
print(f"wrote movement_sample.csv (30,000 pitches)")