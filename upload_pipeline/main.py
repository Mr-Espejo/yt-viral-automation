"""
YouTube Viral Automation - Upload Pipeline
Phase 10: Upload, Scheduling & Experimentation
"""

import logging
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from mining_pipeline.core.config import ConfigLoader
from shared.storage.storage_manager import StorageManager
from upload_pipeline.core.upload_manager import UploadManager


def setup_logging():
    """Configure logging for the Upload Pipeline."""
    logs_dir = project_root / "storage" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure performance dir exists
    (project_root / "data" / "performance").mkdir(parents=True, exist_ok=True)
    
    log_file = logs_dir / "upload_pipeline.log"
    
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
    """Main execution entry for the Upload Pipeline."""
    import argparse
    parser = argparse.ArgumentParser(description="YouTube Viral Automation - Upload Pipeline")
    parser.add_argument("--mode", type=str, choices=["auto", "composed", "priority"], default="auto", 
                        help="Upload mode: 'composed' for new edits, 'priority' for optimized originals, 'auto' for best guess.")
    parser.add_argument("--limit", type=int, default=9, help="Max uploads for this session.")
    args = parser.parse_args()

    logger = setup_logging()
    
    logger.info("="*60)
    logger.info("YouTube Viral Automation - UPLOAD PIPELINE")
    logger.info(f"Mode: {args.mode.upper()} | Limit: {args.limit}")
    logger.info("="*60)
    
    # 1. Load Configuration
    config_path = project_root / "mining_pipeline" / "config.yaml"
    try:
        loader = ConfigLoader(config_path)
        config = loader.load()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # 2. Instantiate Storage Manager
    storage_root = Path(config.storage_root)
    if not storage_root.is_absolute():
        storage_root = (project_root / storage_root).resolve()
        
    storage = StorageManager(str(storage_root), config.keep_local_copy)

    # 3. Execute Upload Manager
    uploader = UploadManager(storage, project_root / "upload_pipeline" / "config")
    published_count = uploader.execute_upload_pipeline(max_uploads=args.limit, mode=args.mode)

    # 4. Summary
    logger.info("="*60)
    logger.info(f"✅ Upload Pipeline execution complete")
    logger.info(f"  - Successfully Published: {published_count} videos")
    logger.info("="*60)
    
    print(f"\n✅ Upload Pipeline complete — {published_count} videos processed.")


if __name__ == "__main__":
    main()
