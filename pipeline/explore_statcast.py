"""
Quick exploration: pull one day of real Statcast pitch data and look at it.
Not part of the pipeline - just to see the raw material we're working with.
"""
from pybaseball import statcast

# One day of the 2024 regular season. Statcast has every tracked pitch:
# velocity, spin, movement, release point, outcome - the raw physics.
print("Fetching Statcast data (this hits MLB's servers, takes ~20-30s)...")
df = statcast(start_dt="2024-06-15", end_dt="2024-06-15")

print(f"\nPulled {len(df):,} pitches from one day of MLB games.")
print(f"Columns available: {len(df.columns)}")

# Show the physics columns that matter for a stuff model
physics_cols = [
    "player_name", "pitch_type", "release_speed",
    "pfx_x", "pfx_z", "release_spin_rate",
    "release_pos_x", "release_pos_z", "description",
]
available = [c for c in physics_cols if c in df.columns]

print("\nSample of the physics data (the raw material for the stuff model):")
print(df[available].head(15).to_string())

print("\nPitch types in this day's data:")
print(df["pitch_type"].value_counts().head(10))