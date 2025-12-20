"""
Storage Manager for YouTube Viral Automation
Phase 6: Storage Management
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Service responsible for managing local storage and organizing project files.
    
    Responsibilities:
    - Create and validate storage directory structure.
    - Organize videos, metadata, and analysis logs.
    - Provide canonical paths for all storage components.
    - Abstract filesystem operations for future scalability.
    """

    def __init__(self, storage_root: str = "./storage", keep_local_copy: bool = True):
        """
        Initialize the StorageManager.
        
        Args:
            storage_root (str): The base directory for all storage.
            keep_local_copy (bool): Whether to copy or move files from the pipeline.
        """
        self._root = Path(storage_root).resolve()
        self._keep_local_copy = keep_local_copy
        
        # Define subdirectories
        self._videos_dir = self._root / "videos" / "viral"
        self._metadata_dir = self._root / "metadata"
        self._analysis_dir = self._root / "analysis"
        self._logs_dir = self._root / "logs"
        
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensures that all required storage directories exist."""
        dirs = [
            self._videos_dir,
            self._metadata_dir,
            self._analysis_dir,
            self._logs_dir
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Storage directory verified: {d}")

    @property
    def videos_path(self) -> Path:
        return self._videos_dir

    @property
    def metadata_path(self) -> Path:
        return self._metadata_dir

    @property
    def analysis_path(self) -> Path:
        return self._analysis_dir

    @property
    def logs_path(self) -> Path:
        return self._logs_dir

    def persist_metadata(self, source_path: Path) -> bool:
        """
        Persists metadata files (CSV, etc.) to the storage/metadata directory.
        """
        return self._persist_file(source_path, self._metadata_dir)

    def persist_video(self, source_path: Path) -> bool:
        """
        Persists video files to the storage/videos/viral directory.
        """
        return self._persist_file(source_path, self._videos_dir)

    def _persist_file(self, source: Path, destination_dir: Path) -> bool:
        """
        Moves or copies a file to the specified storage directory.
        """
        if not source.exists():
            logger.warning(f"Source file does not exist: {source}")
            return False
        
        if source.stat().st_size == 0:
            logger.warning(f"Source file is empty (0 bytes): {source}")
            return False

        destination = destination_dir / source.name
        
        if destination.exists():
            logger.warning(f"Destination already exists, skipping: {destination}")
            return False

        try:
            if self._keep_local_copy:
                shutil.copy2(source, destination)
                logger.info(f"✓ File copied to storage: {destination.name}")
            else:
                shutil.move(str(source), str(destination))
                logger.info(f"✓ File moved to storage: {destination.name}")
            return True
        except Exception as e:
            logger.error(f"Error persisting file {source.name}: {e}")
            return False

    def __repr__(self):
        return f"StorageManager(root={self._root})"
