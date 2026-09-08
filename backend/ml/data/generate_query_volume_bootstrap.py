"""
generate_query_volume_bootstrap.py — Query volume forecasting

monitoring_service.py's metrics.db logs every real query with a
timestamp — in principle, real data to forecast from. In practice, this
dev environment only has a handful of real logged queries so far (check
yourself: it was 5 rows at the time this was written), nowhere near
enough to fit a seasonal time-series model. So: same pattern as Phase 1 —
a synthetic-but-plausible bootstrap, clearly labeled, with the training
script (train_query_forecast.py) checking the real row count at run time
and reporting honestly which source it used. No fabricated claim that
this reflects real usage patterns.

Synthetic seasonality assumptions (a designer's guess, not measured):
  - Peak usage 18:00-21:00 (people free after work/farm)
  - Moderate midday, low overnight (00:00-06:00)
  - Slightly higher on weekends
  - Gradual overall upward trend over the simulated window (adoption growth)
  - Gaussian noise on top

Output: backend/ml/data/query_volume_bootstrap.csv (hour_start, day_of_week, is_weekend, query_count)
"""

from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(11)

DAYS_SIMULATED = 60


def hourly_shape(hour: int) -> float:
    """Relative demand multiplier by hour of day (0-23), peaking evening."""
    # Two soft peaks: late morning + evening, trough overnight.
    return (
        0.15
        + 0.55 * math.exp(-((hour - 19) ** 2) / 8)   # evening peak ~19:00
        + 0.25 * math.exp(-((hour - 11) ** 2) / 10)  # late-morning bump ~11:00
    )


def main():
    rows = []
    start = datetime.now() - timedelta(days=DAYS_SIMULATED)
    base_volume = 8.0

    for day in range(DAYS_SIMULATED):
        date = start + timedelta(days=day)
        dow = date.weekday()  # 0=Mon
        is_weekend = dow >= 5
        trend = 1.0 + 0.4 * (day / DAYS_SIMULATED)  # gradual adoption growth
        weekend_boost = 1.15 if is_weekend else 1.0

        for hour in range(24):
            expected = base_volume * trend * weekend_boost * hourly_shape(hour)
            noisy = max(0, round(random.gauss(expected, expected * 0.25 + 0.5)))
            rows.append({
                "hour_start": (date.replace(hour=hour, minute=0, second=0, microsecond=0)).isoformat(),
                "hour_of_day": hour,
                "day_of_week": dow,
                "is_weekend": int(is_weekend),
                "query_count": noisy,
            })

    out_path = Path(__file__).resolve().parent / "query_volume_bootstrap.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    total = sum(r["query_count"] for r in rows)
    print(f"Wrote {len(rows)} SYNTHETIC hourly rows ({DAYS_SIMULATED} simulated days) to {out_path}")
    print(f"Total simulated queries: {total}, avg/hour: {total/len(rows):.1f}")


if __name__ == "__main__":
    main()
