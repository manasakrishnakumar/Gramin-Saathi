import sqlite3
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

class MonitoringService:
    def __init__(self):
        self.db_path = settings.DATA_DIR / "metrics.db"
        self._init_db()

    def _init_db(self):
        """Initialize the metrics database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    query_text TEXT,
                    source TEXT,
                    latency_ms REAL,
                    language TEXT,
                    successful BOOLEAN
                )
            """)

    def log_query(self, query: str, source: str, latency_ms: float, language: str = "English", successful: bool = True):
        """Log a query execution metric."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO query_metrics (timestamp, query_text, source, latency_ms, language, successful) VALUES (?, ?, ?, ?, ?, ?)",
                    (datetime.now(), query, source, latency_ms, language, successful)
                )
        except Exception as e:
            logger.error(f"Failed to log metric: {e}")

    def get_todays_stats(self) -> Dict[str, Any]:
        """Aggregate stats for the dashboard."""
        stats = {
            "total_queries": 0,
            "avg_latency": 0.0,
            "cache_hit_rate": 0.0,
            "sources": {}
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Use Python date to ensure local timezone consistency
                today_str = datetime.now().strftime('%Y-%m-%d')
                
                # Total Queries
                cursor = conn.execute(
                    "SELECT COUNT(*), AVG(latency_ms) FROM query_metrics WHERE date(timestamp) = ?", 
                    (today_str,)
                )
                row = cursor.fetchone()
                if row:
                    stats["total_queries"] = row[0]
                    stats["avg_latency"] = round(row[1] or 0.0, 2)

                # Source Distribution
                cursor = conn.execute(
                    "SELECT source, COUNT(*) FROM query_metrics WHERE date(timestamp) = ? GROUP BY source",
                    (today_str,)
                )
                for source, count in cursor.fetchall():
                    stats["sources"][source] = count

                # Cache Hit Rate
                # 'RAG System' => Miss, anything else => Hit
                total = stats["total_queries"]
                if total > 0:
                    rag_count = stats["sources"].get("RAG System (Gemini + Pinecone)", 0)
                    hits = total - rag_count
                    stats["cache_hit_rate"] = round((hits / total) * 100, 1)

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
        
        return stats

    def get_recent_queries(self, limit: int = 10) -> List[Dict]:
        """Get recent logs for the table view."""
        queries = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT timestamp, query_text, source, latency_ms FROM query_metrics ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                for row in cursor.fetchall():
                    queries.append({
                        "Time": row[0],
                        "Query": row[1],
                        "Source": row[2],
                        "Latency (ms)": round(row[3], 0)
                    })
        except Exception as e:
            logger.error(f"Failed to fetch recent queries: {e}")
        return queries

monitoring_service = MonitoringService()
