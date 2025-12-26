"""
Upload Manager - Phase 10
Main orchestrator for video publication and experimentation.
"""

import logging
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from .scheduler import Scheduler
from .ab_test_manager import ABTestManager

logger = logging.getLogger(__name__)

class UploadManager:
    """
    Coordinates scheduling, A/B testing, and publication.
    """

    def __init__(self, storage_manager, config_dir: Path):
        self._storage = storage_manager
        self._priority_file = Path("data/scoring/upload_priority.json")
        self._log_file = Path("data/performance/uploads_log.csv")
        self._config_dir = config_dir
        
        # Components
        self._scheduler = Scheduler(self._config_dir / "schedule.yaml")
        # For MVP, we enable A/B test by default
        self._ab_manager = ABTestManager(ab_test_enabled=True)

    def execute_upload_pipeline(self) -> int:
        """
        Processes the priority queue and executes uploads.
        """
        if not self._priority_file.exists():
            logger.error("Upload priority file not found.")
            return 0

        with open(self._priority_file, 'r', encoding='utf-8') as f:
            priority_data = json.load(f)
            queue = priority_data.get("upload_order", [])

        if not queue:
            logger.warning("Upload queue is empty.")
            return 0

        # Check Window
        if not self._scheduler.is_in_window():
            logger.info("Current time is outside allowed upload windows. Waiting...")
            return 0

        uploads_done = 0
        limit = self._scheduler.daily_limit
        
        for item in queue:
            if uploads_done >= limit:
                logger.info(f"Daily upload limit reached ({limit}).")
                break
                
            video_id = item["video_id"]
            variant = item["variant"]
            score = item["score"]
            priority = item["priority_rank"]

            # 1. Determine A/B Test Group
            exp_meta = self._ab_manager.get_experiment_metadata(video_id, variant)
            
            # 2. Mock Physical Upload
            success = self._perform_upload(video_id, variant, exp_meta)
            
            if success:
                uploads_done += 1
                self._log_upload(video_id, variant, score, exp_meta)
                logger.info(f"Published: {video_id} ({variant}) - Rank: {priority} - Group: {exp_meta['group']}")
            
        return uploads_done

    def _perform_upload(self, video_id: str, variant: str, experiment: Dict[str, Any]) -> bool:
        """
        Mocks the actual API call to YouTube.
        In a real deployment, this would use a Refresh Token to hit videos().insert.
        """
        # Logic: Check if file exists in optimized storage
        file_path = self._storage._root / "videos" / "optimized" / video_id / f"{variant}.mp4"
        if not file_path.exists():
            logger.error(f"Source file not found for upload: {file_path}")
            return False
            
        # --- MOCKING API CALL ---
        logger.info(f"--> MOCK UPLOAD: {file_path.name} to YouTube...")
        return True

    def _log_upload(self, video_id: str, variant: str, score: float, experiment: Dict[str, Any]):
        """Records upload event in CSV."""
        log_entry = {
            "video_id": video_id,
            "variant": variant,
            "score": score,
            "group": experiment.get("group"),
            "test_id": experiment.get("test_id", ""),
            "timestamp": datetime.now().isoformat(),
            "status": "published"
        }
        
        df = pd.DataFrame([log_entry])
        if self._log_file.exists():
            df.to_csv(self._log_file, mode='a', header=False, index=False)
        else:
            df.to_csv(self._log_file, index=False)
