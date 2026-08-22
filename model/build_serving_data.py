"""
Build the compact serving table the API and dashboard use.
Aggregates FIRST (collapsing millions of rows to thousands), then joins the
small results - avoids the memory blowup of merging raw pitch tables.
"""
from pathlib import Path
import pandas as pd

MODEL_DIR = Path("model/artifacts")
SERVE_DIR = Path("dashboard/data")
GROUP = ["pitcher", "player_name", "game_year", "pitch_type"]


def build():
    SERVE_DIR.mkdir(parents=True, exist_ok=True)

    print("aggregating graded pitches (Stuff+)...")
    graded = pd.read_parquet(MODEL_DIR / "graded_pitches.parquet")
    graded = graded[(graded["stuff_plus"] > 0) & (graded["stuff_plus"] < 200)]
    grp_stuff = (
        graded.groupby(GROUP)
        .agg(stuff_plus=("stuff_plus", "mean"),
             pitches=("stuff_plus", "size"))
        .reset_index()
    )
    del graded

    print("aggregating physics features...")
    feats = pd.read_parquet("data/gold/features.parquet", columns=[
        "pitcher", "game_year", "pitch_type",
        "release_speed", "movement_mag", "release_spin_rate", "velo_sep",
    ])
    grp_phys = (
        feats.groupby(["pitcher", "game_year", "pitch_type"])
        .agg(avg_velo=("release_speed", "mean"),
             avg_movement=("movement_mag", "mean"),
             avg_spin=("release_spin_rate", "mean"),
             velo_sep=("velo_sep", "mean"))
        .reset_index()
    )
    del feats

    print("joining small aggregates...")
    arsenal = grp_stuff.merge(
        grp_phys, on=["pitcher", "game_year", "pitch_type"], how="left"
    ).round(2)
    arsenal = arsenal[arsenal["pitches"] >= 25]

    # overall usage-weighted Stuff+ per pitcher-season
    arsenal["weighted_stuff"] = arsenal["stuff_plus"] * arsenal["pitches"]
    overall = (
        arsenal.groupby(["pitcher", "player_name", "game_year"])
        .agg(weighted_stuff=("weighted_stuff", "sum"),
             total_pitches=("pitches", "sum"),
             num_pitch_types=("pitch_type", "size"))
        .reset_index()
    )
    overall["overall_stuff"] = (overall["weighted_stuff"] / overall["total_pitches"]).round(1)
    overall = overall.drop(columns="weighted_stuff")
    arsenal = arsenal.drop(columns="weighted_stuff")

    arsenal.to_parquet(SERVE_DIR / "arsenal.parquet", index=False)
    overall.to_parquet(SERVE_DIR / "pitchers.parquet", index=False)

    print(f"\narsenal: {len(arsenal):,} pitcher-season-pitch rows")
    print(f"pitchers: {len(overall):,} pitcher-seasons")
    print("\ntop 10 pitchers by overall Stuff+ (2024, min 500 pitches):")
    top = overall[(overall.game_year == 2024) & (overall.total_pitches >= 500)]
    print(top.nlargest(10, "overall_stuff")[
        ["player_name", "overall_stuff", "total_pitches", "num_pitch_types"]
    ].to_string(index=False))


if __name__ == "__main__":
    build()