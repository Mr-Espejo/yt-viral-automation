"""
Upload Manager - Phase 10
Main orchestrator for video publication and experimentation.
Handles REAL YouTube uploads via OAuth2.
"""

import logging
import json
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from .scheduler import Scheduler
from .ab_test_manager import ABTestManager

logger = logging.getLogger(__name__)

# Scopes required for YouTube Uploads
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

class UploadManager:
    """
    Coordinates scheduling, A/B testing, and REAL publication to YouTube.
    """

    def __init__(self, storage_manager, config_dir: Path):
        self._storage = storage_manager
        self._priority_file = Path("data/scoring/upload_priority.json")
        self._ready_file = self._storage.metadata_path / "upload_ready.json"
        self._log_file = Path("data/performance/uploads_log.csv")
        self._config_dir = config_dir
        
        # Credentials paths
        self._secrets_file = self._config_dir / "client_secrets.json"
        self._token_file = self._config_dir / "token.json"
        
        # Components
        self._scheduler = Scheduler(self._config_dir / "schedule.yaml")
        self._ab_manager = ABTestManager(ab_test_enabled=True)
        
        # Authenticated Service
        self._youtube = None

    def execute_upload_pipeline(self, max_uploads: int = 5) -> int:
        """
        Processes the priority queue and executes real uploads.
        """
        if not self._priority_file.exists():
            logger.error("Upload priority file not found.")
            return 0

        if not self._ready_file.exists():
            logger.error(f"Upload ready manifest not found: {self._ready_file}")
            return 0

        # Load queue
        with open(self._priority_file, 'r', encoding='utf-8') as f:
            queue = json.load(f).get("upload_order", [])

        # Load enrichment metadata (titles, tags, etc.)
        with open(self._ready_file, 'r', encoding='utf-8') as f:
            enrichment_data = json.load(f)

        if not queue:
            logger.warning("Upload queue is empty.")
            return 0

        # Check Window
        if not self._scheduler.is_in_window():
            logger.info("Current time is outside allowed upload windows. Skipping...")
            return 0

        # Authenticate with YouTube
        if not self._authenticate():
            logger.error("Authentication failed. Ensure client_secrets.json is in upload_pipeline/config/")
            return 0

        uploads_done = 0
        limit = min(self._scheduler.daily_limit, max_uploads)
        
        # Load existing log to skip already published
        published_ids = set()
        if self._log_file.exists():
            df_log = pd.read_csv(self._log_file)
            published_ids = set(zip(df_log['video_id'], df_log['variant']))

        for item in queue:
            if uploads_done >= limit:
                logger.info(f"Upload limit reached for this session ({limit}).")
                break
                
            video_id = item["video_id"]
            variant = item["variant"]
            score = item["score"]
            priority = item["priority_rank"]

            if (video_id, variant) in published_ids:
                logger.debug(f"Skipping already published: {video_id} ({variant})")
                continue

            # Get Marketing Metadata
            variants_meta = enrichment_data.get(video_id, [])
            meta = next((v["platform_metadata"] for v in variants_meta if v["variant"] == variant), None)
            
            if not meta:
                logger.warning(f"No platform metadata for {video_id} ({variant}). Skipping.")
                continue

            # Determine A/B Test Group
            exp_meta = self._ab_manager.get_experiment_metadata(video_id, variant)
            
            # REAL Physical Upload
            success = self._perform_real_upload(video_id, variant, meta)
            
            if success:
                uploads_done += 1
                self._log_upload(video_id, variant, score, exp_meta)
                logger.info(f"✅ PUBLISHED TO YOUTUBE: {meta['title']} [Rank {priority}]")
            
        return uploads_done

    def _authenticate(self) -> bool:
        """
        Handles OAuth2 flow and returns True if service is ready.
        """
        creds = None
        if self._token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self._token_file), SCOPES)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self._secrets_file.exists():
                    logger.error(f"Missing {self._secrets_file}. Please download it from Google Cloud Console.")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(str(self._secrets_file), SCOPES)
                creds = flow.run_local_server(port=8080)
            
            # Save token
            with open(self._token_file, 'w') as token:
                token.write(creds.to_json())

        self._youtube = build('youtube', 'v3', credentials=creds, static_discovery=False)
        return True

    def _perform_real_upload(self, video_id: str, variant: str, meta: Dict[str, Any]) -> bool:
        """
        Executes the videos().insert API call.
        """
        file_path = self._storage._root / "videos" / "optimized" / video_id / f"{variant}.mp4"
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        body = {
            "snippet": {
                "title": meta["title"],
                "description": meta["description"],
                "tags": meta.get("tags", []),
                "categoryId": "22"  # People & Blogs
            },
            "status": {
                "privacyStatus": meta.get("privacy", "private"),
                "selfDeclaredMadeForKids": False
            }
        }

        try:
            logger.info(f"Uploading {file_path.name}...")
            media = MediaFileUpload(str(file_path), chunksize=-1, resumable=True, mimetype='video/mp4')
            request = self._youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            
            response = request.execute()
            logger.info(f"Upload Successful! Video ID: {response['id']}")
            return True
        except Exception as e:
            logger.error(f"YouTube Upload Failed for {video_id}: {e}")
            return False

    def _log_upload(self, video_id: str, variant: str, score: float, experiment: Dict[str, Any]):
        """Records upload event in CSV."""
        log_entry = {
            "video_id": video_id,
            "variant": variant,
            "score": score,
            "group": experiment.get("group"),
            "test_id": experiment.get("test_id", ""),
            "timestamp": datetime.now().isoformat(),
            "status": "published"
        }
        
        df = pd.DataFrame([log_entry])
        if self._log_file.exists():
            df.to_csv(self._log_file, mode='a', header=False, index=False)
        else:
            df.to_csv(self._log_file, index=False)
