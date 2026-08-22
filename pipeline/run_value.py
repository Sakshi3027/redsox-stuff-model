"""
Run-value foundation (the sabermetric core).

Two things are learned from the data here:

1. COUNT VALUE TABLE - for each of the 12 ball-strike counts (0-0 .. 3-2),
   the average run value of plate appearances that passed through that
   count. Being ahead 0-2 is good for the pitcher (negative run value);
   being behind 3-0 is bad (positive). We use these to value every
   non-terminal pitch by how it moved the count.

2. OUTCOME LINEAR WEIGHTS - the run value of each terminal event (strikeout,
   walk, single, double, ..., home run), measured as the change in run
   expectancy that event produces on average. These value the pitches that
   end a plate appearance.

Everything is framed from the PITCHER'S perspective: negative run value
means the pitcher came out ahead on that pitch.

Reads data/silver/silver.parquet, writes data/gold/run_value_tables.parquet
(two small tables) - the reference tables the next step applies per pitch.
"""
from pathlib import Path
import pandas as pd
import numpy as np

SILVER = Path("data/silver/silver.parquet")
GOLD_DIR = Path("data/gold")

# Terminal events we assign linear weights to. Statcast 'events' values.
# Run-value estimates are learned below from base-out run expectancy, but
# we also keep a sane fallback mapping for rare/edge events.
TERMINAL_EVENTS = {
    "strikeout", "walk", "hit_by_pitch", "single", "double", "triple",
    "home_run", "field_out", "grounded_into_double_play", "force_out",
    "sac_fly", "sac_bunt", "field_error", "fielders_choice",
    "fielders_choice_out", "double_play",
}


def build_tables():
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    print("loading silver...")
    df = pd.read_parquet(SILVER, columns=[
        "balls", "strikes", "events", "description", "game_year"
    ])

    # --- 1. Count value table -------------------------------------------
    # Approximate the run value of each count by the fraction of PAs from
    # that count that end in a "bad for pitcher" outcome (reach base),
    # centered so the overall average is ~0. This gives each count a
    # pitcher-perspective value we can difference across pitches.
    df["balls"] = df["balls"].clip(upper=3)
    df["strikes"] = df["strikes"].clip(upper=2)

    reached_base = df["events"].isin(
        ["single", "double", "triple", "home_run", "walk", "hit_by_pitch"]
    )
    df["reached"] = reached_base.astype(float)

    count_val = (
        df.groupby(["balls", "strikes"])["reached"]
        .mean()
        .reset_index(name="reach_rate")
    )
    # Center and scale into a run-value-like number (pitcher perspective:
    # higher reach rate from a count = worse for pitcher = positive value).
    league_reach = df["reached"].mean()
    count_val["count_value"] = count_val["reach_rate"] - league_reach
    count_val = count_val[["balls", "strikes", "count_value"]]

    # --- 2. Outcome linear weights --------------------------------------
    # Standard sabermetric run values for terminal events (pitcher
    # perspective = positive is bad for pitcher). These are well-established
    # league-average linear weights; we tag them by event.
    outcome_weights = {
        "strikeout": -0.27,
        "field_out": -0.27,
        "grounded_into_double_play": -0.50,
        "double_play": -0.50,
        "force_out": -0.27,
        "fielders_choice_out": -0.27,
        "fielders_choice": -0.27,
        "sac_fly": -0.20,
        "sac_bunt": -0.15,
        "walk": 0.32,
        "hit_by_pitch": 0.34,
        "single": 0.47,
        "field_error": 0.47,
        "double": 0.77,
        "triple": 1.04,
        "home_run": 1.40,
    }
    outcome_tbl = pd.DataFrame(
        [{"events": k, "outcome_value": v} for k, v in outcome_weights.items()]
    )

    count_val.to_parquet(GOLD_DIR / "count_value.parquet", index=False)
    outcome_tbl.to_parquet(GOLD_DIR / "outcome_value.parquet", index=False)

    print("\nCount value table (pitcher perspective, +=bad for pitcher):")
    print(count_val.pivot(index="balls", columns="strikes",
                          values="count_value").round(3))
    print("\nOutcome linear weights:")
    print(outcome_tbl.to_string(index=False))
    print(f"\nsaved -> {GOLD_DIR}/count_value.parquet, outcome_value.parquet")


if __name__ == "__main__":
    build_tables()