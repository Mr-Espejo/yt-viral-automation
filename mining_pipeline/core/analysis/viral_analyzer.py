"""
Viral Analyzer Service
Phase 4: Viral Analysis & Filtering
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Optional

from ..config.app_config import AppConfig

logger = logging.getLogger(__name__)


class ViralAnalyzer:
    """
    Service responsible for analyzing video metadata and filtering viral candidates.
    
    Responsibilities:
    - Load raw video metadata from Phase 3.
    - Calculate engagement scores.
    - Apply configurable viral thresholds.
    - Persist the filtered "viral" dataset.
    """

    def __init__(self, config: AppConfig, metadata_dir: Path):
        """
        Initialize ViralAnalyzer with application configuration.
        
        Args:
            config: Validated application configuration.
            metadata_dir: Path to the storage metadata directory.
        """
        self._config = config
        self._data_dir = metadata_dir
        self._raw_file = self._data_dir / "raw_videos.csv"
        self._viral_file = self._data_dir / "viral_videos.csv"

    def analyze(self) -> pd.DataFrame:
        """
        Execute the full analysis pipeline: Load -> Score -> Filter -> Save.
        
        Returns:
            pd.DataFrame: DataFrame containing the filtered viral videos.
        """
        logger.info("Starting Phase 4: Viral Analysis & Filtering")
        
        # 1. Load data
        df = self._load_data()
        total_raw = len(df)
        logger.info(f"Loaded {total_raw} videos for analysis")

        if df.empty:
            logger.warning("No raw video data found to analyze.")
            return df

        # 2. Compute Engagement Score
        # engagement_score = (likes + comments) / views
        # If views == 0 -> engagement_score = 0
        df['engagement_score'] = (df['likes'] + df['comments']) / df['views']
        df['engagement_score'] = df['engagement_score'].fillna(0)

        # 3. Filter Viral Videos
        # Rule 1: views >= min_views
        # Rule 2: engagement_score >= min_engagement
        min_views = self._config.min_views
        min_engagement = self._config.min_engagement
        
        logger.info(f"Applying thresholds: min_views={min_views}, min_engagement={min_engagement:.2%}")
        
        viral_df = df[
            (df['views'] >= min_views) & 
            (df['engagement_score'] >= min_engagement)
        ].copy()

        total_viral = len(viral_df)
        
        if viral_df.empty:
            logger.warning("No videos met the viral criteria thresholds.")
            return viral_df

        # 4. Rank and Limit
        # Sort by views descending
        viral_df = viral_df.sort_values(by='views', ascending=False)
        
        # Limit if max_videos is defined
        if self._config.max_videos:
            viral_df = viral_df.head(self._config.max_videos)
            logger.info(f"Limited output to top {self._config.max_videos} viral videos")

        # 5. Persist Results
        self._save_results(viral_df)
        
        logger.info(f"Phase 4 complete: {len(viral_df)} viral videos selected")
        return viral_df

    def _load_data(self) -> pd.DataFrame:
        """Load raw metadata from CSV."""
        if not self._raw_file.exists():
            logger.error(f"Raw metadata file not found at {self._raw_file}")
            return pd.DataFrame()
        
        try:
            return pd.read_csv(self._raw_file)
        except Exception as e:
            logger.error(f"Failed to read raw metadata: {e}")
            return pd.DataFrame()

    def _save_results(self, df: pd.DataFrame):
        """Save filtered viral videos to CSV."""
        try:
            df.to_csv(self._viral_file, index=False, encoding='utf-8')
            logger.info(f"Viral videos saved to {self._viral_file}")
        except Exception as e:
            logger.error(f"Failed to save viral analysis results: {e}")
