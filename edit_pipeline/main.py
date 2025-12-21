"""
YouTube Viral Automation - Edit Pipeline
Phase 7: Video Processing & Normalization
"""

import logging
import sys
from pathlib import Path

# Add project root to sys.path to allow imports from 'shared' and 'mining_pipeline'
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from mining_pipeline.core.config import ConfigLoader
from shared.storage.storage_manager import StorageManager
from video_processor import VideoProcessor


def setup_logging():
    """Configure logging for the Edit Pipeline."""
    logs_dir = project_root / "storage" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = logs_dir / "edit_pipeline.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def main():
    """Main execution entry for the Edit Pipeline."""
    logger = setup_logging()
    
    logger.info("="*60)
    logger.info("YouTube Viral Automation - EDIT PIPELINE")
    logger.info("Phase 7: Video Processing & Normalization")
    logger.info("="*60)
    
    # 1. Load Configuration (from mining_pipeline folder for consistency)
    config_path = project_root / "mining_pipeline" / "config.yaml"
    try:
        loader = ConfigLoader(config_path)
        config = loader.load()
        logger.info(f"Configuration loaded from {config_path}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # 2. Instantiate Storage Manager
    # Resolve relative storage root to project root
    storage_root = Path(config.storage_root)
    if not storage_root.is_absolute():
        storage_root = (project_root / storage_root).resolve()
        
    storage = StorageManager(str(storage_root), config.keep_local_copy)
    logger.info(f"Storage Manager initialized at {storage_root}")

    # 3. Check for ffmpeg availability
    try:
        import subprocess
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        logger.info("✓ ffmpeg verification successful")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("✗ ffmpeg NOT FOUND. Please install ffmpeg and add it to your PATH.")
        sys.exit(1)

    # 4. Execute Video Processor
    processor = VideoProcessor(config, storage)
    processed_count = processor.process_all()

    # 5. Summary
    logger.info("="*60)
    logger.info(f"✅ Phase 7 complete — {processed_count} videos normalized and processed")
    logger.info(f"Assets stored in: {storage_root}/videos/")
    logger.info("="*60)
    
    print(f"\n✅ Phase 7 complete — {processed_count} videos processed.")


if __name__ == "__main__":
    main()
