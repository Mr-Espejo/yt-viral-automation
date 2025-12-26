"""
Scheduler Service - Phase 10
Handles upload windows and timezones.
"""

import logging
import yaml
from datetime import datetime, time
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class Scheduler:
    """
    Manages allowed upload windows and timing.
    """

    def __init__(self, config_path: Path):
        self._config = self._load_config(config_path)
        self._windows = self._config.get('schedule', {}).get('windows', [])
        self._limit = self._config.get('schedule', {}).get('upload_limit_per_day', 5)

    def _load_config(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def is_in_window(self) -> bool:
        """Checks if current time is within an allowed upload window."""
        now = datetime.now().time()
        for window in self._windows:
            start = datetime.strptime(window['start'], "%H:%M").time()
            end = datetime.strptime(window['end'], "%H:%M").time()
            if start <= now <= end:
                return True
        return False

    def get_next_available_slot(self) -> datetime:
        """
        Determines the next time an upload can occur.
        Simple implementation: next start of a window if not in one.
        """
        # For MVP, we just return current time if in window, 
        # or mock the wait.
        return datetime.now()

    @property
    def daily_limit(self) -> int:
        return self._limit
