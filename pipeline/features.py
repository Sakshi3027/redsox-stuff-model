"""
Feature engineering: turn raw pitch physics into the features a stuff model
actually reasons about.

The core idea a real stuff model encodes: a pitch's nastiness is RELATIVE to
the pitcher's own fastball. A slider at 88 is ordinary - unless the pitcher
throws 98, where the 10 mph gap wrecks timing. So for each pitcher we
establish their primary-fastball baseline (velo, movement, release) and
express every pitch relative to it, alongside the raw physics.

Feature groups:
  raw physics        - velocity, movement, spin, release, extension
  pitcher-relative   - velo separation vs fastball, movement diff vs
                       fastball, release consistency (tunneling)
  derived            - total movement magnitude, spin-to-movement efficiency

Reads data/gold/modeling.parquet, writes data/gold/features.parquet.
"""
from pathlib import Path
import numpy as np
import pandas as pd

GOLD_DIR = Path("data/gold")

# Which pitch types count as a pitcher's "fastball" for the baseline.
FASTBALLS = {"FF", "SI", "FC"}


def build_features():
    print("loading gold modeling table...")
    df = pd.read_parquet(GOLD_DIR / "modeling.parquet")

    # --- total movement magnitude (inches; pfx is in feet) --------------
    df["pfx_x_in"] = df["pfx_x"] * 12.0
    df["pfx_z_in"] = df["pfx_z"] * 12.0
    df["movement_mag"] = np.sqrt(df["pfx_x_in"] ** 2 + df["pfx_z_in"] ** 2)

    # --- establish each pitcher's fastball baseline per season ----------
    # (per season, so a pitcher who added velo year over year is handled)
    fb = df[df["pitch_type"].isin(FASTBALLS)]
    fb_base = (
        fb.groupby(["pitcher", "game_year"])
        .agg(
            fb_velo=("release_speed", "mean"),
            fb_pfx_x_in=("pfx_x_in", "mean"),
            fb_pfx_z_in=("pfx_z_in", "mean"),
            fb_rel_x=("release_pos_x", "mean"),
            fb_rel_z=("release_pos_z", "mean"),
        )
        .reset_index()
    )

    df = df.merge(fb_base, on=["pitcher", "game_year"], how="left")

    # --- pitcher-relative features --------------------------------------
    # velo separation: how much slower than the fastball (positive = slower)
    df["velo_sep"] = df["fb_velo"] - df["release_speed"]

    # movement difference vs the fastball (the deception dimension)
    df["mov_diff_x"] = df["pfx_x_in"] - df["fb_pfx_x_in"]
    df["mov_diff_z"] = df["pfx_z_in"] - df["fb_pfx_z_in"]
    df["mov_diff_mag"] = np.sqrt(df["mov_diff_x"] ** 2 + df["mov_diff_z"] ** 2)

    # release consistency (tunneling): distance of this pitch's release from
    # the fastball's release. Small = harder to distinguish out of the hand.
    df["rel_dist_from_fb"] = np.sqrt(
        (df["release_pos_x"] - df["fb_rel_x"]) ** 2
        + (df["release_pos_z"] - df["fb_rel_z"]) ** 2
    )

    # --- spin efficiency proxy ------------------------------------------
    # movement per 1000 rpm - how much the spin actually translates to break
    df["spin_to_move"] = df["movement_mag"] / (df["release_spin_rate"] / 1000.0 + 1e-6)

    # drop rows where we couldn't establish a fastball baseline (pitchers
    # with no tracked fastball that season - rare)
    before = len(df)
    df = df.dropna(subset=["fb_velo"])
    print(f"  {before:,} -> {len(df):,} pitches with a fastball baseline")

    out = GOLD_DIR / "features.parquet"
    df.to_parquet(out, index=False)
    print(f"\nfeatures: {len(df):,} pitches -> {out}")
    print("\nsample of engineered features (first breaking balls):")
    cols = ["pitch_type", "release_speed", "velo_sep", "movement_mag",
            "mov_diff_mag", "rel_dist_from_fb", "pitch_run_value"]
    print(df[df["pitch_type"] == "SL"][cols].head(8).round(2).to_string(index=False))


if __name__ == "__main__":
    build_features()