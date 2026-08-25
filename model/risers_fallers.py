"""
Risers & Fallers - year-over-year stuff trends.

For pitchers who threw in both 2023 and 2024, compute the change in overall
Stuff+. Big gains flag development wins and breakouts; big drops flag possible
fatigue, aging, or injury - the kind of signal a player-development or medical
group would want surfaced early.

Uses the multi-season pitchers table we already built.
Writes dashboard/data/risers_fallers.parquet.
"""
from pathlib import Path
import pandas as pd

DATA = Path("dashboard/data")


def build():
    pitchers = pd.read_parquet(DATA / "pitchers.parquet")
    p = pitchers[pitchers["total_pitches"] >= 300]

    y23 = p[p["game_year"] == 2023][["pitcher", "player_name", "overall_stuff"]]
    y24 = p[p["game_year"] == 2024][["pitcher", "overall_stuff"]]

    m = y23.merge(y24, on="pitcher", suffixes=("_2023", "_2024"))
    m["delta"] = (m["overall_stuff_2024"] - m["overall_stuff_2023"]).round(1)
    m = m.sort_values("delta", ascending=False)

    m.to_parquet(DATA / "risers_fallers.parquet", index=False)

    print(f"tracked {len(m):,} pitchers across 2023 -> 2024")
    print("\nBiggest RISERS (stuff improved most):")
    for _, r in m.head(10).iterrows():
        print(f"  {r['player_name']:22s} {r['overall_stuff_2023']:5.1f} -> "
              f"{r['overall_stuff_2024']:5.1f}  (+{r['delta']:.1f})")
    print("\nBiggest FALLERS (stuff declined most):")
    for _, r in m.tail(10).iloc[::-1].iterrows():
        print(f"  {r['player_name']:22s} {r['overall_stuff_2023']:5.1f} -> "
              f"{r['overall_stuff_2024']:5.1f}  ({r['delta']:.1f})")


if __name__ == "__main__":
    build()