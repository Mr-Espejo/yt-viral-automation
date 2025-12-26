"""
Metadata Enrichment Service
Phase 9: AI-Driven Marketing & Upload Preparation
"""

import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List

from shared.storage.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class MetadataEnricher:
    """
    Service responsible for preparing platform-ready metadata (Titles, Tags, Descriptions).
    
    Responsibilities:
    - Link original viral data with optimized variants.
    - Generate optimized titles with hashtags.
    - Create upload bundles (JSON) for each variant.
    """

    def __init__(self, storage_manager: StorageManager):
        self._storage = storage_manager
        self._optimized_dir = self._storage._root / "videos" / "optimized"
        self._viral_csv = self._storage.metadata_path / "viral_videos.csv"
        self._output_file = self._storage.metadata_path / "upload_ready.json"

    def enrich_all(self) -> int:
        """Generates upload bundles for all optimized videos."""
        if not self._viral_csv.exists():
            logger.error(f"Viral metadata not found: {self._viral_csv}")
            return 0
            
        if not self._optimized_dir.exists():
            logger.error("Optimized videos directory not found.")
            return 0

        # Load original metadata
        df = pd.read_csv(self._viral_csv)
        viral_data = df.set_index('video_id').to_dict('index')

        enriched_count = 0
        bundles = {}

        # Scan optimized directory
        for video_folder in self._optimized_dir.iterdir():
            if not video_folder.is_dir():
                continue
            
            video_id = video_folder.name
            if video_id not in viral_data:
                logger.warning(f"Metadata for {video_id} not found in viral CSV. Skipping enrichment.")
                continue

            orig = viral_data[video_id]
            
            # Generate bundles for each variant found in the folder
            video_bundles = []
            for video_file in video_folder.glob("*.mp4"):
                variant_name = video_file.stem
                bundle = self._create_bundle(video_id, variant_name, orig, video_file)
                video_bundles.append(bundle)
                enriched_count += 1
            
            bundles[video_id] = video_bundles

        # Save global upload manifest
        with open(self._output_file, 'w', encoding='utf-8') as f:
            json.dump(bundles, f, indent=4, ensure_ascii=False)

        logger.info(f"Phase 9 complete: {enriched_count} upload bundles prepared.")
        return enriched_count

    def _create_bundle(self, video_id: str, variant: str, orig: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Creates a single metadata bundle for a variant."""
        base_title = orig.get('title', 'YouTube Short')
        
        # Clean title for tags
        clean_title = "".join(c for c in base_title if c.isalnum() or c.isspace())
        
        # Simple dynamic title generation
        # hook_short = Hook version, mid_cut = Highlight, full = Optimized
        prefix = ""
        if variant == "hook_short": prefix = "🔥 Must Watch: "
        elif variant == "mid_cut": prefix = "✂️ Best Part: "
        
        final_title = f"{prefix}{base_title}"
        if len(final_title) > 90:
            final_title = final_title[:87] + "..."
            
        # Add hashtags
        final_title += " #shorts #viral #trending"

        return {
            "video_id": video_id,
            "variant": variant,
            "file_path": str(file_path.absolute()),
            "platform_metadata": {
                "title": final_title,
                "description": f"Optimized version of {base_title}.\nOriginal views: {orig.get('views', 0)}\n\n#shorts #viral #edit",
                "tags": ["shorts", "viral", "trending", video_id],
                "privacy": "private"  # Always safe by default
            }
        }
