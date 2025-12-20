"""
YouTube Viral Automation - Mining Pipeline
Phase 6: Storage Management Integration
"""

import logging
import sys
from pathlib import Path

# Add project root to sys.path to allow imports from 'shared'
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.config import ConfigLoader, AppConfig
from core.config.config_loader import ConfigValidationError
from core.youtube import YouTubeClient, ChannelInfo
from core.youtube.youtube_client import ChannelResolutionError
from core.youtube.metadata_miner import VideoMetadataMiner
from core.analysis import ViralAnalyzer
from core.downloader import VideoDownloader
from shared.storage.storage_manager import StorageManager


def setup_logging():
    """Configure logging with file and console handlers."""
    # Ensure logs directory exists
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / "app.log"
    
    # Configure logging format
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def load_configuration(logger: logging.Logger) -> AppConfig:
    """Load and validate application configuration."""
    base_dir = Path(__file__).parent
    config_path = base_dir / "config.yaml"
    
    logger.info(f"Loading configuration from: {config_path}")
    
    try:
        loader = ConfigLoader(config_path)
        config = loader.load()
        
        logger.info("Configuration validated successfully")
        logger.info(f"  Channel: {config.channel}")
        logger.info(f"  Min Views: {config.min_views:,}")
        logger.info(f"  Min Engagement: {config.min_engagement:.2%}")
        logger.info(f"  Max Videos: {config.max_videos if config.max_videos else 'unlimited'}")
        logger.info(f"  Storage Mode: {config.storage_mode}")
        
        return config
        
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        sys.exit(1)
    except ConfigValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}")
        sys.exit(1)


def resolve_channel(logger: logging.Logger, config: AppConfig) -> ChannelInfo:
    """Resolve channel from configuration using YouTube API."""
    logger.info(f"Resolving channel: {config.channel}")
    try:
        youtube_client = YouTubeClient(config.api_key)
        channel_info = youtube_client.resolve_channel(config.channel)
        
        logger.info("Channel resolved successfully")
        logger.info(f"  Title: {channel_info.title}")
        logger.info(f"  Channel ID: {channel_info.channel_id}")
        
        return channel_info
    except ChannelResolutionError as e:
        logger.error(f"Channel resolution failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error resolving channel: {e}")
        sys.exit(1)


def main():
    """Main execution entry for the Mining Pipeline."""
    logger = setup_logging()
    
    logger.info("="*60)
    logger.info("YouTube Viral Automation - MINING PIPELINE")
    logger.info("="*60)
    
    # Phase 1: Load and validate configuration
    config = load_configuration(logger)
    
    # 🔥 Initialize Storage Manager at the start
    # Resolve storage root relative to project root (yt_viral_automation/)
    storage_root = Path(config.storage_root)
    if not storage_root.is_absolute():
        # Path(__file__).parent.parent is the project root (yt_viral_automation/)
        storage_root = (Path(__file__).parent.parent / storage_root).resolve()
    
    storage = StorageManager(str(storage_root), config.keep_local_copy)
    
    # Phase 2: Resolve channel
    channel_info = resolve_channel(logger, config)
    
    # Phase 3: Video Metadata Mining
    logger.info("="*60)
    logger.info("Phase 3: Video Metadata Mining")
    logger.info("="*60)
    
    youtube_client = YouTubeClient(config.api_key)
    # Pass storage.metadata_path
    miner = VideoMetadataMiner(youtube_client, channel_info, config, storage.metadata_path)
    mined_videos = miner.mine_all_videos()
    
    logger.info(f"Phase 3 complete: {len(mined_videos)} videos collected.")
    
    # Phase 4: Viral Analysis & Filtering
    logger.info("="*60)
    logger.info("Phase 4: Viral Analysis & Filtering")
    logger.info("="*60)
    
    # Pass storage.metadata_path
    analyzer = ViralAnalyzer(config, storage.metadata_path)
    viral_df = analyzer.analyze()
    
    logger.info(f"Phase 4 complete: {len(viral_df)} viral videos identified.")
    
    # Phase 5: Viral Video Downloading
    logger.info("="*60)
    logger.info("Phase 5: Viral Video Downloading")
    logger.info("="*60)
    
    # Pass storage.metadata_path AND storage.videos_path
    downloader = VideoDownloader(config, storage.metadata_path, storage.videos_path)
    download_count = downloader.download_viral_videos()
    
    logger.info(f"Phase 5 complete: {download_count} videos downloaded.")
    
    # Phase 6: Storage Management Completion
    logger.info("="*60)
    logger.info("Phase 6: Storage Management - Persistence Complete")
    logger.info("="*60)
    
    # Optional: Still persist log file to storage
    log_source = Path("logs/app.log")
    if log_source.exists():
        storage._persist_file(log_source, storage.logs_path)

    print("\n" + "="*60)
    print(f"✅ Mining Pipeline Complete")
    print(f"📂 Metadata stored in: {storage.metadata_path}")
    print(f"🎬 Videos stored in: {storage.videos_path}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
