"""
Bronze layer: pull raw Statcast pitch data, one season at a time, and save
it untouched to Parquet.

Design notes (real-world data engineering):
- Statcast can't be queried a whole season at once, so we pull month by
  month and concatenate.
- Each month is cached to disk; re-running skips months already pulled, so
  a failed run resumes instead of restarting (MLB's servers do time out).
- Bronze = raw source of truth. No cleaning here; that's the silver layer.
"""
import os
from pathlib import Path
import pandas as pd
from pybaseball import statcast

BRONZE_DIR = Path("data/bronze")

# MLB regular season roughly spans these months. We pull Apr-Oct.
SEASON_MONTHS = [
    ("04-01", "04-30"), ("05-01", "05-31"), ("06-01", "06-30"),
    ("07-01", "07-31"), ("08-01", "08-31"), ("09-01", "09-30"),
    ("10-01", "10-31"),
]


def pull_season(year: int) -> Path:
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    season_frames = []

    for start_md, end_md in SEASON_MONTHS:
        month_tag = start_md[:2]
        cache_file = BRONZE_DIR / f"{year}-{month_tag}.parquet"

        if cache_file.exists():
            print(f"  {year}-{month_tag}: cached, loading from disk")
            season_frames.append(pd.read_parquet(cache_file))
            continue

        start = f"{year}-{start_md}"
        end = f"{year}-{end_md}"
        print(f"  {year}-{month_tag}: pulling {start} -> {end} from Statcast...")
        try:
            month_df = statcast(start_dt=start, end_dt=end)
        except Exception as e:
            print(f"    ! failed ({e}); skipping this month for now")
            continue

        if month_df is None or len(month_df) == 0:
            print(f"    (no data for {year}-{month_tag})")
            continue

        month_df.to_parquet(cache_file, index=False)
        print(f"    saved {len(month_df):,} pitches to {cache_file.name}")
        season_frames.append(month_df)

    if not season_frames:
        raise RuntimeError(f"No data pulled for {year}")

    season = pd.concat(season_frames, ignore_index=True)
    out = BRONZE_DIR / f"season_{year}.parquet"
    season.to_parquet(out, index=False)
    print(f"{year}: {len(season):,} total pitches -> {out.name}")
    return out


if __name__ == "__main__":
    import sys
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    pull_season(year)