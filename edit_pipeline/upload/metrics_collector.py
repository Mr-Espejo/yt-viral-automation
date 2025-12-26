"""
Metrics Collector - Phase 10
Retrieves performance data for uploaded videos.
"""

import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MetricsCollector:
    """
    Simulates or collects metrics from the platform.
    """

    def __init__(self, performance_dir: Path):
        self._dir = performance_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def collect_metrics(self, video_id: str, upload_id: str) -> Dict[str, Any]:
        """
        Retrieves views, watch time, likes, etc.
        Mock implementation for now.
        """
        # In a real system, this would call YouTube API
        metrics = {
            "video_id": video_id,
            "upload_id": upload_id,
            "timestamp": datetime.now().isoformat(),
            "views": 0, # To be filled by actual API or simulation
            "watch_time_sec": 0,
            "retention_percent": 0.0,
            "likes": 0,
            "comments": 0
        }
        return metrics

    def save_metrics(self, metrics: List[Dict[str, Any]], interval_name: str):
        """Saves current metrics snapshot to CSV."""
        df = pd.DataFrame(metrics)
        file_path = self._dir / f"metrics_{interval_name}.csv"
        df.to_csv(file_path, index=False)
        logger.info(f"Metrics saved to {file_path}")
