"""
Video Downloader Service
Phase 5: Viral Video Downloading (Hotfix: Forced MP4 Merging)
"""

import logging
import pandas as pd
import re
import yt_dlp
from pathlib import Path
from typing import List

from ..config.app_config import AppConfig

logger = logging.getLogger(__name__)


class VideoDownloader:
    """
    Service responsible for downloading viral videos using yt-dlp Python API.
    
    Responsibilities:
    - Load viral video metadata from Phase 4.
    - Sanitize filenames for local storage.
    - Execute yt-dlp with forced MP4 merging (bv*+ba/b).
    - Manage sequential downloads and error handling.
    """

    def __init__(self, config: AppConfig, metadata_dir: Path, videos_dir: Path):
        """
        Initialize VideoDownloader with application configuration.
        """
        self._config = config
        self._viral_file = metadata_dir / "viral_videos.csv"
        self._output_dir = videos_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def download_viral_videos(self) -> int:
        """
        Main execution flow for downloading selected videos.
        """
        logger.info("Starting Phase 5: Viral Video Downloading")
        
        if not self._viral_file.exists():
            logger.error(f"Viral videos metadata not found at {self._viral_file}")
            return 0

        df = pd.read_csv(self._viral_file)
        if df.empty:
            logger.warning("No viral videos found in metadata to download.")
            return 0

        total_to_download = len(df)
        logger.info(f"Found {total_to_download} viral videos to download")

        success_count = 0

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
        Downloads a single video using yt-dlp Python API with forced merging.
        """
        sanitized_title = self._sanitize_filename(title)
        # Naming: <views>_<video_id>_<sanitized_title> (extension added by yt-dlp)
        base_filename = f"{views}_{video_id}_{sanitized_title}"
        final_path = self._output_dir / f"{base_filename}.mp4"
        
        if final_path.exists():
            logger.info(f"Video already exists, skipping: {final_path.name}")
            return True

        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # yt-dlp options for forced MP4 merging
        ydl_opts = {
            'format': 'bv*+ba/b',
            'merge_output_format': 'mp4',
            'outtmpl': str(self._output_dir / f"{base_filename}.%(ext)s"),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }

        try:
            logger.info(f"Downloading and merging {video_id} into single MP4...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if final_path.exists():
                logger.info(f"Download and merge successful: {final_path.name}")
                return True
            else:
                logger.error(f"Merge error: Expected file {final_path.name} not found.")
                return False

        except Exception as e:
            logger.error(f"yt-dlp error for {video_id}: {e}")
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """
        Removes special characters and keeps filename safe for Windows/Unix.
        """
        s = re.sub(r'[^\w\s-]', '', filename).strip()
        s = re.sub(r'[-\s]+', '_', s)
        return s[:150]
