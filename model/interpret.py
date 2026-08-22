"""
Interpretability + the Stuff+ grade.

Two outputs that turn the model into scouting insight:

1. STUFF+ GRADE: rescale the model's run-value predictions to a 0-100+ scale
   where 100 = league average and higher = nastier (the industry convention,
   e.g. Stuff+). A pitch grading 130 has stuff ~30% better than average.

2. SHAP: explain which physical traits drive a pitch's grade, globally
   (which features matter most across all pitches) and per-pitch (why THIS
   slider grades elite). This is the "disseminate insight to leadership"
   piece - it makes the model legible.

Saves a graded pitch table + SHAP importances.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import shap

GOLD = Path("data/gold/features.parquet")
MODEL_DIR = Path("model/artifacts")


def build():
    print("loading model + features...")
    model = joblib.load(MODEL_DIR / "stuff_model.joblib")
    features = joblib.load(MODEL_DIR / "feature_list.joblib")
    df = pd.read_parquet(GOLD).dropna(subset=features)

    # predict run value for every pitch
    df["pred_rv"] = model.predict(df[features])

    # --- Stuff+ grade ---------------------------------------------------
    # Lower predicted run value = better stuff. Invert and standardize so
    # league average = 100, one std = 10 points (like OPS+/Stuff+ convention).
    mean_rv = df["pred_rv"].mean()
    std_rv = df["pred_rv"].std()
    # negative sign: better (lower) RV -> higher grade
    df["stuff_plus"] = 100 - 10 * (df["pred_rv"] - mean_rv) / std_rv

    print("\nStuff+ distribution (100 = league average):")
    print(df["stuff_plus"].describe().round(1).to_string())

    print("\nAverage Stuff+ by pitch type:")
    print(df.groupby("pitch_type")["stuff_plus"].mean().sort_values(ascending=False).round(1).to_string())

    # --- SHAP global importance -----------------------------------------
    print("\ncomputing SHAP values (on a 30k sample for speed)...")
    sample = df[features].sample(n=min(30000, len(df)), random_state=42)
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(sample)

    importance = (
        pd.DataFrame({"feature": features,
                      "mean_abs_shap": np.abs(shap_vals).mean(axis=0)})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    print("\nGlobal feature importance (what drives stuff, by SHAP):")
    print(importance.round(5).to_string(index=False))

    # save graded pitches (slim) + importances
    keep = ["pitcher", "player_name", "game_year", "pitch_type",
            "release_speed", "velo_sep", "movement_mag", "mov_diff_mag",
            "pred_rv", "stuff_plus"]
    df[keep].to_parquet(MODEL_DIR / "graded_pitches.parquet", index=False)
    importance.to_parquet(MODEL_DIR / "shap_importance.parquet", index=False)
    print(f"\nsaved graded pitches + SHAP importances -> {MODEL_DIR}/")


if __name__ == "__main__":
    build()