"""
Pitcher similarity - "find arms like this one".

Represents each 2024 pitcher as a vector describing their arsenal's physics:
overall Stuff+, and the velocity / movement / spin / usage of their primary
and secondary pitches. Standardizes the features and uses nearest-neighbor
search (cosine distance) to find the most physically similar pitchers.

A scouting-comp tool: given a pitcher, who throws the most similar stuff?
Writes dashboard/data/similarity.parquet (top-6 comps per pitcher).
"""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors

DATA = Path("dashboard/data")


def build():
    arsenal = pd.read_parquet(DATA / "arsenal.parquet")
    pitchers = pd.read_parquet(DATA / "pitchers.parquet")

    ars = arsenal[arsenal["game_year"] == 2024].copy()
    pit = pitchers[(pitchers["game_year"] == 2024) &
                   (pitchers["total_pitches"] >= 300)].copy()

    # for each pitcher, take their top-2 pitches by usage as primary/secondary
    ars = ars.sort_values(["pitcher", "pitches"], ascending=[True, False])
    feats = []
    for pid, grp in ars.groupby("pitcher"):
        if pid not in set(pit["pitcher"]):
            continue
        g = grp.head(2)
        row = {"pitcher": pid, "player_name": g["player_name"].iloc[0]}
        # primary pitch
        p1 = g.iloc[0]
        row.update({
            "p1_velo": p1["avg_velo"], "p1_move": p1["avg_movement"],
            "p1_spin": p1["avg_spin"], "p1_stuff": p1["stuff_plus"],
        })
        # secondary pitch (fall back to primary if only one)
        p2 = g.iloc[1] if len(g) > 1 else p1
        row.update({
            "p2_velo": p2["avg_velo"], "p2_move": p2["avg_movement"],
            "p2_spin": p2["avg_spin"], "p2_stuff": p2["stuff_plus"],
            "velo_gap": p1["avg_velo"] - p2["avg_velo"],
        })
        feats.append(row)

    df = pd.DataFrame(feats).dropna()
    print(f"built arsenal vectors for {len(df):,} pitchers")

    feat_cols = ["p1_velo", "p1_move", "p1_spin", "p1_stuff",
                 "p2_velo", "p2_move", "p2_spin", "p2_stuff", "velo_gap"]
    X = StandardScaler().fit_transform(df[feat_cols])

    n_neighbors = min(7, len(df))
    nn = NearestNeighbors(n_neighbors=n_neighbors, metric="cosine").fit(X)
    dist, idx = nn.kneighbors(X)

    rows = []
    names = df["player_name"].values
    pids = df["pitcher"].values
    for i in range(len(df)):
        for j, d in zip(idx[i][1:], dist[i][1:]):  # skip self
            rows.append({
                "pitcher": int(pids[i]),
                "player_name": names[i],
                "similar_pitcher": int(pids[j]),
                "similar_name": names[j],
                "similarity": round(float(1 - d), 3),
            })
    out = pd.DataFrame(rows)
    out.to_parquet(DATA / "similarity.parquet", index=False)
    print(f"wrote {len(out):,} similarity pairs "
          f"({n_neighbors - 1} comps per pitcher)")

    # spot-check a nasty arm
    print("\nSpot check - most similar to Emmanuel Clase:")
    clase = df[df["player_name"].str.contains("Clase")]
    if not clase.empty:
        cid = int(clase["pitcher"].iloc[0])
        comps = out[out["pitcher"] == cid]
        for _, r in comps.iterrows():
            print(f"  {r['similar_name']:22s} similarity {r['similarity']:.3f}")


if __name__ == "__main__":
    build()