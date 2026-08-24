"""
Pitch-design recommendations.

The stuff model grades a pitch. This asks the inverse question: what small,
physically realistic change would most improve a given pitch's grade?

Method: take a pitcher's pitch (its average physical profile), then sweep
each tunable physical trait across a realistic range, re-score every variant
with the trained model, and report the single change that yields the biggest
Stuff+ gain. This turns the model from descriptive into prescriptive - the
"how do we make this pitch nastier" question a pitching lab actually asks.

Writes design suggestions per pitcher-pitch to a serving file.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

MODEL_DIR = Path("model/artifacts")
SERVE_DIR = Path("dashboard/data")

# Traits we allow the lab to "design" and realistic nudge ranges (in the
# model's feature units). Movement in inches, velo in mph.
DESIGN_KNOBS = {
    "pfx_x_in": (-3.0, 3.0),     # horizontal break
    "pfx_z_in": (-3.0, 3.0),     # vertical break
    "release_speed": (-1.5, 2.0),  # velocity
    "velo_sep": (-2.0, 2.0),     # separation off fastball
}
STUFF_MEAN_STD = None  # filled from graded data for consistent Stuff+ scale


def _stuff_plus(pred_rv, mean_rv, std_rv):
    return 100 - 10 * (pred_rv - mean_rv) / std_rv


def build():
    model = joblib.load(MODEL_DIR / "stuff_model.joblib")
    features = joblib.load(MODEL_DIR / "feature_list.joblib")

    feats = pd.read_parquet("data/gold/features.parquet")
    feats = feats.dropna(subset=features)

    # league RV mean/std for the Stuff+ scale (matches interpret.py)
    all_rv = model.predict(feats[features])
    mean_rv, std_rv = all_rv.mean(), all_rv.std()

    # average each pitcher's pitch to a representative profile (2024 only)
    profile = (
        feats[feats["game_year"] == 2024]
        .groupby(["pitcher", "player_name", "pitch_type"])[features]
        .mean()
        .reset_index()
    )
    # only meaningful sample sizes
    counts = (feats[feats["game_year"] == 2024]
              .groupby(["pitcher", "pitch_type"]).size())
    profile = profile[profile.apply(
        lambda r: counts.get((r["pitcher"], r["pitch_type"]), 0) >= 50, axis=1)]

    print(f"designing for {len(profile):,} pitcher-pitch profiles...")

    base_rv = model.predict(profile[features])
    base_stuff = _stuff_plus(base_rv, mean_rv, std_rv)

    recs = []
    for knob, (lo, hi) in DESIGN_KNOBS.items():
        for delta in (lo, hi):
            variant = profile.copy()
            variant[knob] = variant[knob] + delta
            # keep dependent features consistent where obvious
            if knob in ("pfx_x_in", "pfx_z_in"):
                variant["movement_mag"] = np.sqrt(
                    variant["pfx_x_in"] ** 2 + variant["pfx_z_in"] ** 2)
            new_rv = model.predict(variant[features])
            new_stuff = _stuff_plus(new_rv, mean_rv, std_rv)
            gain = new_stuff - base_stuff
            for i, g in enumerate(gain):
                recs.append((i, knob, delta, g))

    rec_df = pd.DataFrame(recs, columns=["idx", "knob", "delta", "gain"])
    # best single change per pitch
    best = rec_df.loc[rec_df.groupby("idx")["gain"].idxmax()]

    out = profile[["pitcher", "player_name", "pitch_type"]].reset_index(drop=True)
    out["base_stuff"] = base_stuff.round(1)
    out["best_knob"] = best.set_index("idx")["knob"]
    out["best_delta"] = best.set_index("idx")["delta"].round(1)
    out["projected_gain"] = best.set_index("idx")["gain"].round(1)
    out = out[out["projected_gain"] > 0.3]  # only real, positive suggestions

    SERVE_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(SERVE_DIR / "pitch_design.parquet", index=False)

    print(f"wrote {len(out):,} pitch-design suggestions")
    print("\nsample (biggest projected gains):")
    label = {"pfx_x_in": "horizontal break", "pfx_z_in": "vertical break",
             "release_speed": "velocity", "velo_sep": "velo separation"}
    top = out.nlargest(10, "projected_gain")
    for _, r in top.iterrows():
        direction = "more" if r["best_delta"] > 0 else "less"
        print(f"  {r['player_name']:22s} {r['pitch_type']}: "
              f"{direction} {label[r['best_knob']]} "
              f"({r['best_delta']:+.1f}) -> +{r['projected_gain']:.1f} Stuff+")


if __name__ == "__main__":
    build()