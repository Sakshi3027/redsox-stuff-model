"""
Undervalued arms - a Moneyball layer.

Thesis (justified by our own r=0.74 finding): stuff is a stable, repeatable
skill, while results are noisier and regress toward the underlying stuff. So
a pitcher whose STUFF is well above average but whose actual RESULTS lag is a
plausible buy-low target - the results should improve toward the stuff.

Fully self-contained (no external stats API): "stuff" is the model's Stuff+
grade; "results" is the pitcher's actual average run value allowed per pitch
(from data/gold/modeling.parquet). Both to percentiles; rank by the gap.

Writes dashboard/data/undervalued.parquet.
"""
from pathlib import Path
import pandas as pd

DATA = Path("dashboard/data")
GOLD = Path("data/gold/modeling.parquet")


def build():
    pitchers = pd.read_parquet(DATA / "pitchers.parquet")
    stuff24 = pitchers[(pitchers["game_year"] == 2024) &
                       (pitchers["total_pitches"] >= 300)].copy()

    print("computing actual results (run value allowed) from gold data...")
    gold = pd.read_parquet(GOLD, columns=["pitcher", "game_year",
                                          "pitch_run_value"])
    gold = gold[gold["game_year"] == 2024]
    results = (gold.groupby("pitcher")["pitch_run_value"]
               .mean().reset_index(name="actual_rv"))

    merged = stuff24.merge(results, on="pitcher", how="inner")

    # percentiles: high stuff = good; low run value allowed = good (invert)
    merged["stuff_pct"] = merged["overall_stuff"].rank(pct=True) * 100
    merged["results_pct"] = (1 - merged["actual_rv"].rank(pct=True)) * 100
    merged["gap"] = merged["stuff_pct"] - merged["results_pct"]

    out = merged[[
        "pitcher", "player_name", "overall_stuff", "actual_rv",
        "total_pitches", "stuff_pct", "results_pct", "gap",
    ]].copy().round(2).sort_values("gap", ascending=False)
    out.to_parquet(DATA / "undervalued.parquet", index=False)

    print(f"\nanalyzed {len(out):,} pitchers (300+ pitches, 2024)")
    print("\nMost UNDERVALUED (elite stuff, lagging results - buy-low):")
    for _, r in out.head(10).iterrows():
        print(f"  {r['player_name']:22s} Stuff+ {r['overall_stuff']:5.1f} "
              f"(pct {r['stuff_pct']:3.0f}) | results pct {r['results_pct']:3.0f} "
              f"| gap +{r['gap']:.0f}")

    print("\nMost OVERVALUED (results outrunning stuff - regression risk):")
    for _, r in out.tail(5).iloc[::-1].iterrows():
        print(f"  {r['player_name']:22s} Stuff+ {r['overall_stuff']:5.1f} "
              f"| results pct {r['results_pct']:3.0f} | gap {r['gap']:.0f}")


if __name__ == "__main__":
    build()