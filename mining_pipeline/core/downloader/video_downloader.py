"""
Video Downloader Service
Phase 5: Viral Video Downloading
"""

import logging
import pandas as pd
import subprocess
import re
from pathlib import Path
from typing import List

from ..config.app_config import AppConfig

logger = logging.getLogger(__name__)


class VideoDownloader:
    """
    Service responsible for downloading viral videos using yt-dlp.
    
    Responsibilities:
    - Load viral video metadata from Phase 4.
    - Sanitize filenames for local storage.
    - Execute yt-dlp via subprocess for high-quality MP4 downloads.
    - Manage sequential downloads and error handling.
    """

    def __init__(self, config: AppConfig, metadata_dir: Path, videos_dir: Path):
        """
        Initialize VideoDownloader with application configuration.
        
        Args:
            config: Application configuration.
            metadata_dir: Path to storage metadata.
            videos_dir: Path to storage videos.
        """
        self._config = config
        self._viral_file = metadata_dir / "viral_videos.csv"
        self._output_dir = videos_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def download_viral_videos(self) -> int:
        """
        Main execution flow for downloading selected videos.
        
        Returns:
            int: Total number of successfully downloaded videos.
        """
        logger.info("Starting Phase 5: Viral Video Downloading")
        
        if not self._viral_file.exists():
            logger.error(f"Viral videos metadata not found at {self._viral_file}")
            return 0

        # 1. Load data
        df = pd.read_csv(self._viral_file)
        if df.empty:
            logger.warning("No viral videos found in metadata to download.")
            return 0

        total_to_download = len(df)
        logger.info(f"Found {total_to_download} viral videos to download")

        success_count = 0

        # 2. Iterate and download
        for idx, row in df.iterrows():
            video_id = row['video_id']
            views = int(row['views'])
            title = str(row['title'])
            
            logger.info(f"[{success_count + 1}/{total_to_download}] Processing: {title}")
            
            if self._download_single_video(video_id, views, title):
                success_count += 1
            else:
                logger.warning(f"Failed to download video: {video_id}")

        logger.info(f"Phase 5 complete: {success_count} videos downloaded to {self._output_dir}")
        return success_count

    def _download_single_video(self, video_id: str, views: int, title: str) -> bool:
        """
        Downloads a single video using yt-dlp.
        
        Naming format: <views>_<video_id>_<sanitized_title>.mp4
        """
        sanitized_title = self._sanitize_filename(title)
        filename = f"{views}_{video_id}_{sanitized_title}.mp4"
        output_path = self._output_dir / filename
        
        # Skip if already exists
        if output_path.exists():
            logger.info(f"Video already exists, skipping: {filename}")
            return True

        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # yt-dlp command configuration
        # bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4 ensures MP4 container compatible with most tools
        command = [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
            "--merge-output-format", "mp4",
            "-o", str(output_path),
            "--no-playlist",
            url
        ]

        try:
            logger.info(f"Executing yt-dlp for {video_id}...")
            # subprocess.run waits for completion (sequential execution)
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=True
            )
            logger.info(f"Download successful: {filename}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"yt-dlp error for {video_id}: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("yt-dlp not found. Please ensure it is installed and in your PATH.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading {video_id}: {e}")
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """
        Removes special characters and keeps filename safe for Windows/Unix.
        """
        # Remove anything that isn't alphanumeric, space, or hyphen
        s = re.sub(r'[^\w\s-]', '', filename).strip()
        # Replace spaces/hyphens with underscores
        s = re.sub(r'[-\s]+', '_', s)
        # Limit length to avoid Windows path issues (max 255 total, leaving room for path)
        return s[:150]
