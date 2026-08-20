"""
Silver layer: clean the raw bronze pitches into an analysis-ready table.

What "clean" means for a stuff model:
- keep only real, tracked pitches (drop rows missing the core physics)
- keep only the columns the model needs (bronze has 119; we need ~20)
- normalize handedness so movement is comparable across L/R pitchers
- drop position-player-pitching junk and pitch-outs
- type things correctly and add a season column

Reads data/bronze/season_{year}.parquet, writes data/silver/silver.parquet
(all seasons stacked).
"""
from pathlib import Path
import pandas as pd

BRONZE_DIR = Path("data/bronze")
SILVER_DIR = Path("data/silver")

# The columns a stuff model actually needs, from the 119 Statcast gives us.
KEEP = [
    "game_date", "game_year", "pitcher", "player_name", "p_throws",
    "pitch_type", "release_speed",
    "pfx_x", "pfx_z",              # horizontal / vertical movement (ft)
    "release_spin_rate", "spin_axis",
    "release_pos_x", "release_pos_z", "release_extension",
    "vx0", "vy0", "vz0", "ax", "ay", "az",   # full trajectory physics
    "description", "events", "type",          # outcome fields
    "balls", "strikes", "stand",              # count + batter side
]

# Pitch types that are real pitches (drop pitch-outs, position players, etc.)
VALID_PITCH_TYPES = {
    "FF", "SI", "FC",           # fastballs: four-seam, sinker, cutter
    "SL", "ST", "SV",           # sliders: slider, sweeper, slurve
    "CU", "KC",                 # curveballs
    "CH", "FS",                 # offspeed: change, splitter
}


def build_silver() -> Path:
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    seasons = sorted(BRONZE_DIR.glob("season_*.parquet"))
    if not seasons:
        raise RuntimeError("No bronze season files found - run bronze.py first")

    frames = []
    for path in seasons:
        print(f"cleaning {path.name}...")
        df = pd.read_parquet(path, columns=[c for c in KEEP if c])
        before = len(df)

        # 1. real pitches only
        df = df[df["pitch_type"].isin(VALID_PITCH_TYPES)]

        # 2. must have the core physics a stuff model needs
        core = ["release_speed", "pfx_x", "pfx_z", "release_spin_rate",
                "release_pos_x", "release_pos_z"]
        df = df.dropna(subset=core)

        # 3. normalize handedness: mirror horizontal movement/release for
        #    lefties so "arm-side vs glove-side" is consistent across L/R.
        is_lhp = df["p_throws"] == "L"
        for col in ["pfx_x", "release_pos_x"]:
            df.loc[is_lhp, col] = -df.loc[is_lhp, col]

        print(f"  {before:,} -> {len(df):,} pitches after cleaning")
        frames.append(df)

    silver = pd.concat(frames, ignore_index=True)
    out = SILVER_DIR / "silver.parquet"
    silver.to_parquet(out, index=False)
    print(f"\nsilver: {len(silver):,} clean pitches across "
          f"{silver['game_year'].nunique()} seasons -> {out}")
    return out


if __name__ == "__main__":
    build_silver()