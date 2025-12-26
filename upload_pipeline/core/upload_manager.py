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

    def execute_upload_pipeline(self, max_uploads: int = 9, mode: str = "auto") -> int:
        """
        Main entry point for uploads. 
        Modes: 
        - 'auto': Uploads 'composed' if they exist, otherwise 'priority'.
        - 'composed': Forced upload of composed videos.
        - 'priority': Forced upload of priority queue.
        """
        composed_dir = self._storage._root / "videos" / "composed"
        
        if mode == "composed" or (mode == "auto" and composed_dir.exists()):
            logger.info("🎬 Entering COMPOSED upload mode.")
            return self.execute_composed_upload_pipeline(max_uploads)
            
        if mode == "priority" or mode == "auto":
            logger.info("🚀 Entering PRIORITY QUEUE upload mode.")
            if not self._priority_file.exists():
                logger.error("Upload priority file not found.")
                return 0
            return self._execute_priority_upload_pipeline(max_uploads)
        
        return 0

    def _execute_priority_upload_pipeline(self, max_uploads: int) -> int:
        """Internal logic for priority queue uploads."""

        if not self._ready_file.exists():
            logger.error(f"Upload ready manifest not found: {self._ready_file}")
            return 0

        # Load queue
        with open(self._priority_file, 'r', encoding='utf-8') as f:
            queue = json.load(f).get("upload_order", [])

        # Load enrichment metadata
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
            return 0

        uploads_done = 0
        limit = min(self._scheduler.daily_limit, max_uploads)
        
        # Load existing log to skip already published
        published_ids = self._get_published_ids()

        for item in queue:
            if uploads_done >= limit:
                break
                
            video_id = item["video_id"]
            variant = item["variant"]
            
            if (video_id, variant) in published_ids:
                continue

            # Get Marketing Metadata
            variants_meta = enrichment_data.get(video_id, [])
            meta = next((v["platform_metadata"] for v in variants_meta if v["variant"] == variant), None)
            
            if not meta:
                continue

            # REAL Physical Upload
            file_path = self._storage._root / "videos" / "optimized" / video_id / f"{variant}.mp4"
            success = self._perform_real_upload(file_path, meta)
            
            if success:
                uploads_done += 1
                self._log_upload(video_id, variant, item.get("score", 0), {})
                logger.info(f"✅ PUBLISHED: {meta['title']}")
            
        return uploads_done

    def execute_composed_upload_pipeline(self, max_uploads: int = 9) -> int:
        """
        Processes the 'composed' directory and uploads pending videos.
        """
        composed_dir = self._storage._root / "videos" / "composed"
        if not composed_dir.exists():
            logger.warning("No composed videos directory found.")
            return 0

        # 1. Authenticate
        if not self._authenticate():
            return 0

        # 2. Get pending videos
        published_ids = self._get_published_ids()
        
        # Find all .mp4 files in composed/
        video_files = [f for f in composed_dir.glob("*.mp4")]
        video_files.sort() # Ensure deterministic order

        uploads_done = 0
        limit = min(self._scheduler.daily_limit, max_uploads)
        
        for file_path in video_files:
            if uploads_done >= limit:
                break
            
            video_id = file_path.stem # e.g. "combo_001"
            variant = "composed"
            
            if (video_id, variant) in published_ids:
                continue
            
            # For composed videos, we might not have 'enrichment_data' yet.
            # We'll use a generic title or look for a .json metadata file
            meta = self._get_composed_metadata(file_path)
            
            success = self._perform_real_upload(file_path, meta)
            if success:
                uploads_done += 1
                self._log_upload(video_id, variant, 0, {})
                logger.info(f"✅ PUBLISHED COMPOSED: {meta['title']}")
                
        return uploads_done

    def _get_published_ids(self) -> set:
        """Returns a set of (video_id, variant) already published."""
        published_ids = set()
        if self._log_file.exists():
            try:
                df_log = pd.read_csv(self._log_file)
                published_ids = set(zip(df_log['video_id'].astype(str), df_log['variant'].astype(str)))
            except Exception as e:
                logger.error(f"Error reading upload log: {e}")
        return published_ids

    def _get_composed_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Tries to find metadata for a composed video or returns defaults."""
        meta_path = self._storage._root / "metadata" / "compositions" / f"{file_path.stem}.json"
        
        default_meta = {
            "title": f"Viral Shorts - {file_path.stem}",
            "description": "Explora los mejores momentos virales combinados. #Shorts #Viral",
            "tags": ["Shorts", "Viral", "Trend"],
            "privacy": "public"
        }
        
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # You could enrich this further with real titles
                    return {**default_meta, **data.get('platform_metadata', {})}
            except:
                pass
        return default_meta

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

    def _perform_real_upload(self, file_path: Path, meta: Dict[str, Any]) -> bool:
        """
        Executes the videos().insert API call with sanitized metadata.
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        # 1. Sanitize Title (YouTube limit: 100 chars, cannot be empty)
        raw_title = meta.get("title", "").strip()
        final_title = raw_title if raw_title else f"Short Viral: {file_path.stem}"
        if len(final_title) > 100:
            final_title = final_title[:97] + "..."

        # 2. Sanitize Description
        final_desc = meta.get("description", "Contenido viral procesado automáticamente. #Shorts #Viral").strip()
        
        # 3. Build API Body
        body = {
            "snippet": {
                "title": final_title,
                "description": final_desc,
                "tags": meta.get("tags", ["Shorts", "Viral"]),
                "categoryId": "22"  # People & Blogs
            },
            "status": {
                "privacyStatus": meta.get("privacy", "private"), # Use 'public' if desired
                "selfDeclaredMadeForKids": False, # Strict requirement
                "embeddable": True
            }
        }

        try:
            logger.info(f"Uploading to YouTube: '{final_title}' (Path: {file_path.name})")
            media = MediaFileUpload(
                str(file_path), 
                chunksize=1024*1024, # 1MB chunks
                resumable=True, 
                mimetype='video/mp4'
            )
            
            request = self._youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            
            response = request.execute()
            logger.info(f"✅ SUCCESS! Video uploaded. YouTube ID: {response['id']}")
            return True
        except Exception as e:
            logger.error(f"❌ YouTube Upload Failed for {file_path.name}: {e}")
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
