"""
YouTube Viral Automation - Edit Pipeline
Phases 7, 8, 9 & 10 (Metadata & Scoring)
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
from video_optimizer import VideoOptimizer
from metadata_enricher import MetadataEnricher
from scoring.video_scorer import VideoScorer


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
    logger.info("Starting Phases 7-9 (Normalization -> Optimization -> Scoring)")
    logger.info("="*60)
    
    # ... (Config loading and storage init same as before)
    # 1. Load Configuration
    config_path = project_root / "mining_pipeline" / "config.yaml"
    try:
        loader = ConfigLoader(config_path)
        config = loader.load()
        logger.info(f"Configuration loaded from {config_path}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # 2. Instantiate Storage Manager
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

    # 4. Phase 7: Video Normalization
    logger.info("="*60)
    logger.info("PHASE 7: Video Processing & Normalization")
    logger.info("="*60)
    processor = VideoProcessor(config, storage)
    norm_processed_count = processor.process_all()
    logger.info(f"Phase 7 complete: {norm_processed_count} videos normalized.")

    # 5. Phase 8: AI Video Optimization (Shorts Agent)
    logger.info("="*60)
    logger.info("PHASE 8: AI Video Optimization Agent")
    logger.info("="*60)
    optimizer = VideoOptimizer(config, storage)
    video_count = optimizer.optimize_all()
    
    # 6. Metadata Enrichment
    logger.info("="*60)
    logger.info("METADATA: Enrichment & Marketing Prep")
    logger.info("="*60)
    enricher = MetadataEnricher(storage)
    bundle_count = enricher.enrich_all()
    
    # 7. Phase 9: AI Scoring & Decision Agent
    logger.info("="*60)
    logger.info("PHASE 9: AI Scoring & Decision Agent")
    logger.info("="*60)
    scorer = VideoScorer(storage)
    scored_count = scorer.score_all_variants()

    # 8. Final Summary
    logger.info("="*60)
    logger.info(f"✅ Edit Pipeline execution complete")
    logger.info(f"  - Normalized: {norm_processed_count} videos")
    logger.info(f"  - Optimized for Shorts: {video_count} videos")
    logger.info(f"  - Scored & Ranked: {scored_count} variants")
    logger.info(f"Scoring Data:  data/scoring/video_scores.csv")
    logger.info("="*60)
    
    print(f"\n✅ Edit Pipeline complete — {scored_count} variants ready for the Upload Pipeline.")


if __name__ == "__main__":
    main()
