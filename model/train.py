"""
Train the stuff model: predict a pitch's run value from its physics alone.

Design decisions that make this a real stuff model:
- TEMPORAL split: train on 2022-2023, test on the unseen 2024 season. Never
  a random split - that leaks the future and is wrong for time-series.
- PHYSICS-ONLY features: velocity, movement, spin, release, and the
  pitcher-relative features. Deliberately NO location, count, or batter, so
  we measure the pitch's inherent quality, not command or situation.
- Gradient boosting (XGBoost) on ~2M pitches.

Saves the trained model and prints honest evaluation.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error, r2_score
import joblib

GOLD = Path("data/gold/features.parquet")
MODEL_DIR = Path("model/artifacts")

# Physics-only feature set - the pitch's inherent characteristics.
FEATURES = [
    # raw physics
    "release_speed", "pfx_x_in", "pfx_z_in", "movement_mag",
    "release_spin_rate", "spin_axis",
    "release_pos_x", "release_pos_z", "release_extension",
    "vx0", "vy0", "vz0", "ax", "ay", "az",
    # pitcher-relative (the domain-knowledge features)
    "velo_sep", "mov_diff_x", "mov_diff_z", "mov_diff_mag",
    "rel_dist_from_fb", "spin_to_move",
]
TARGET = "pitch_run_value"


def train():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print("loading features...")
    df = pd.read_parquet(GOLD, columns=FEATURES + [TARGET, "game_year"])
    df = df.dropna(subset=FEATURES + [TARGET])

    # temporal split
    train_df = df[df["game_year"].isin([2022, 2023])]
    test_df = df[df["game_year"] == 2024]
    print(f"train (2022-23): {len(train_df):,} pitches")
    print(f"test  (2024):    {len(test_df):,} pitches")

    X_train, y_train = train_df[FEATURES], train_df[TARGET]
    X_test, y_test = test_df[FEATURES], test_df[TARGET]

    print("\ntraining XGBoost...")
    model = xgb.XGBRegressor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    # --- evaluation -----------------------------------------------------
    pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, pred))
    r2 = r2_score(y_test, pred)
    print(f"\nHeld-out 2024 RMSE: {rmse:.4f}")
    print(f"Held-out 2024 R^2:  {r2:.4f}")

    # The meaningful test: bin pitches by predicted stuff and check the
    # ACTUAL run value in each bin on the held-out season. A real stuff
    # model shows a monotonic relationship - better predicted grade, better
    # actual outcomes.
    test_eval = test_df.copy()
    test_eval["pred"] = pred
    test_eval["decile"] = pd.qcut(test_eval["pred"], 10, labels=False, duplicates="drop")
    by_decile = test_eval.groupby("decile")[TARGET].mean()
    print("\nActual run value by predicted-stuff decile (2024, held out):")
    print("(decile 0 = best predicted stuff -> should have lowest actual RV)")
    print(by_decile.round(4).to_string())

    joblib.dump(model, MODEL_DIR / "stuff_model.joblib")
    joblib.dump(FEATURES, MODEL_DIR / "feature_list.joblib")
    print(f"\nsaved model -> {MODEL_DIR}/stuff_model.joblib")


if __name__ == "__main__":
    train()