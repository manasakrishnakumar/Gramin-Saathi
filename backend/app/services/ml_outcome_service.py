"""
ml_outcome_service.py — Phase 3 (collection only, deliberately no model)

Stores REAL scheme-application outcomes (approved/rejected/pending) if
and when a trustworthy source reports them — a partner NGO, a scheme
administrator, or a verified in-app follow-up survey.

Deliberately does NOT train or serve any "approval likelihood" prediction.
See backend/ml/PHASE3_NOTES.md for why: presenting a model-derived
likelihood-of-approval score to someone deciding whether to pursue a
government welfare application is high-stakes, and doing that on
fabricated/synthetic labels (the only kind available right now) would be
actively misleading rather than merely imperfect. This service exists so
that IF real outcome data starts arriving, it has somewhere durable to
land — nothing more.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

try:
    from app.core.config import settings
    _DB_PATH = settings.DATA_DIR / "ml_events.db"  # same DB as ml_feedback_service, separate table
except Exception:
    _DB_PATH = Path(__file__).resolve().parents[3] / "data" / "ml_events.db"


class MLOutcomeService:

    def __init__(self, db_path: Path = _DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheme_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    logged_at DATETIME,
                    scheme_id TEXT,
                    profile_snapshot_json TEXT,
                    applied_at TEXT,
                    outcome TEXT,
                    outcome_reported_at TEXT,
                    source TEXT,
                    notes TEXT
                )
            """)

    def report_outcome(self, scheme_id: str, profile_snapshot: dict, outcome: str,
                        source: str, applied_at: str | None = None,
                        outcome_reported_at: str | None = None, notes: str = "") -> None:
        valid = {"approved", "rejected", "pending", "withdrawn"}
        if outcome not in valid:
            raise ValueError(f"outcome must be one of {sorted(valid)}")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO scheme_outcomes "
                "(logged_at, scheme_id, profile_snapshot_json, applied_at, outcome, outcome_reported_at, source, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (datetime.now(), scheme_id, json.dumps(profile_snapshot), applied_at,
                 outcome, outcome_reported_at, source, notes),
            )

    def count(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM scheme_outcomes").fetchone()[0]
            by_outcome = dict(conn.execute(
                "SELECT outcome, COUNT(*) FROM scheme_outcomes GROUP BY outcome"
            ).fetchall())
        return {
            "total_outcomes_collected": total,
            "by_outcome": by_outcome,
            "note": "Collection only — no prediction model is trained on this data. See ml/PHASE3_NOTES.md.",
        }


# Singleton
ml_outcome_service = MLOutcomeService()
