"""
Gold layer: assign every pitch a run value, producing the modeling table.

Applies the learned tables from run_value.py:
- Non-terminal pitches (ball/strike/foul that continue the AB) are valued by
  how they moved the count: RV = count_value(new count) - count_value(old count).
- Terminal pitches (ball put in play, strikeout, walk, HBP) take the
  outcome's linear weight.

All run values are pitcher-perspective: negative = the pitcher gained.
This 'pitch_run_value' column is the target the physics model will predict.

Reads silver + the gold value tables, writes data/gold/modeling.parquet.
"""
from pathlib import Path
import numpy as np
import pandas as pd

SILVER = Path("data/silver/silver.parquet")
GOLD_DIR = Path("data/gold")

# descriptions that mean the pitch ended the plate appearance in-play
INPLAY_DESCRIPTIONS = {"hit_into_play"}
# descriptions that continue the at-bat (non-terminal)
BALL_DESCRIPTIONS = {"ball", "blocked_ball", "pitchout"}
STRIKE_DESCRIPTIONS = {
    "called_strike", "swinging_strike", "swinging_strike_blocked",
    "foul", "foul_tip", "foul_bunt", "missed_bunt", "swinging_pitchout",
}


def _new_count(balls, strikes, desc):
    """Where the count goes after a non-terminal pitch."""
    if desc in BALL_DESCRIPTIONS:
        return min(balls + 1, 3), strikes
    if desc in STRIKE_DESCRIPTIONS:
        # fouls don't add a third strike
        if desc.startswith("foul") and strikes == 2:
            return balls, 2
        return balls, min(strikes + 1, 2)
    return balls, strikes


def build_gold():
    print("loading silver + value tables...")
    df = pd.read_parquet(SILVER)
    count_val = pd.read_parquet(GOLD_DIR / "count_value.parquet")
    outcome_val = pd.read_parquet(GOLD_DIR / "outcome_value.parquet")

    # lookup dicts
    cv = {(r.balls, r.strikes): r.count_value for r in count_val.itertuples()}
    ov = {r.events: r.outcome_value for r in outcome_val.itertuples()}

    balls = df["balls"].clip(upper=3).to_numpy()
    strikes = df["strikes"].clip(upper=2).to_numpy()
    desc = df["description"].to_numpy()
    events = df["events"].to_numpy()

    run_values = np.empty(len(df), dtype=float)

    for i in range(len(df)):
        d = desc[i]
        if d in INPLAY_DESCRIPTIONS or (events[i] in ov and d not in BALL_DESCRIPTIONS and d not in STRIKE_DESCRIPTIONS):
            # terminal: use the outcome's linear weight (default 0 if unknown)
            run_values[i] = ov.get(events[i], 0.0)
        else:
            # non-terminal: value the count change
            b, s = int(balls[i]), int(strikes[i])
            nb, ns = _new_count(b, s, d)
            run_values[i] = cv.get((nb, ns), 0.0) - cv.get((b, s), 0.0)

    df["pitch_run_value"] = run_values

    out = GOLD_DIR / "modeling.parquet"
    df.to_parquet(out, index=False)

    print(f"\ngold: {len(df):,} pitches with run values -> {out}")
    print(f"\nmean pitch run value: {df['pitch_run_value'].mean():.4f} "
          f"(should be near 0)")
    print("\naverage run value by pitch type (negative = better for pitcher):")
    print(df.groupby("pitch_type")["pitch_run_value"].mean().sort_values().round(4).to_string())


if __name__ == "__main__":
    build_gold()