"""
Video Metadata Miner Service
Phase 3: Video Metadata Mining
"""

import logging
import pandas as pd
from pathlib import Path
from typing import List, Optional

from .channel_info import ChannelInfo
from .video_info import VideoInfo
from .youtube_client import YouTubeClient
from ..config.app_config import AppConfig

logger = logging.getLogger(__name__)


class VideoMetadataMiner:
    """
    Service responsible for mining all video metadata from a channel.
    
    Responsibilities:
    - Iterate through the uploads playlist with pagination.
    - Efficiently batch requests to the YouTube API.
    - Persist results to a CSV file.
    """

    def __init__(
        self,
        youtube_client: YouTubeClient,
        channel_info: ChannelInfo,
        config: AppConfig,
        metadata_dir: Path
    ):
        self._client = youtube_client
        self._channel = channel_info
        self._config = config
        self._data_dir = metadata_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def mine_all_videos(self) -> List[VideoInfo]:
        """
        Retrieves metadata for all videos in the channel's uploads playlist.
        
        Returns:
            List[VideoInfo]: List of all mined videos.
        """
        logger.info(f"Starting metadata mining for channel: {self._channel.title}")
        
        # 1. Collect all video IDs from the uploads playlist (handles pagination)
        video_ids = self._discover_video_ids()
        total_discovered = len(video_ids)
        logger.info(f"Discovered {total_discovered} videos in uploads playlist")

        if total_discovered == 0:
            logger.warning("No videos found to mine.")
            return []

        # 2. Fetch detailed metadata in batches of 50
        all_videos: List[VideoInfo] = []
        batch_size = 50
        
        for i in range(0, total_discovered, batch_size):
            batch_ids = video_ids[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}: Videos {i} to {min(i + batch_size, total_discovered)}")
            
            batch_details = self._client.fetch_videos_details(batch_ids)
            all_videos.extend(batch_details)

        # 3. Persist to CSV
        self._save_to_csv(all_videos)
        
        return all_videos

    def _discover_video_ids(self) -> List[str]:
        """Iterates through playlist items to collect video IDs."""
        video_ids = []
        next_page_token = None
        max_videos_limit = self._config.max_videos
        
        while True:
            # Calculate how many more videos we can fetch
            max_results = 50
            if max_videos_limit is not None:
                remaining = max_videos_limit - len(video_ids)
                if remaining <= 0:
                    break
                max_results = min(50, remaining)

            response = self._client.fetch_playlist_items(
                playlist_id=self._channel.uploads_playlist_id,
                max_results=max_results,
                page_token=next_page_token
            )
            
            items = response.get("items", [])
            for item in items:
                v_id = item.get("contentDetails", {}).get("videoId")
                if v_id:
                    video_ids.append(v_id)
            
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
            
            if max_videos_limit is not None and len(video_ids) >= max_videos_limit:
                break
                
        return video_ids

    def _save_to_csv(self, videos: List[VideoInfo]):
        """Saves the collected metadata to data/raw_videos.csv."""
        if not videos:
            logger.warning("No videos collected. CSV will not be created.")
            return

        output_path = self._data_dir / "raw_videos.csv"
        df = pd.DataFrame([v.to_dict() for v in videos])
        
        # Reorder columns to match requirement explicitly
        cols = ["video_id", "title", "published_at", "views", "likes", "comments"]
        df = df[cols]
        
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Successfully saved {len(videos)} videos to {output_path}")
