"""
Video Scorer Service
Phase 9: AI Scoring & Decision Agent
"""

import json
import logging
import subprocess
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

from shared.storage.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class VideoScorer:
    """
    Evaluates and prioritizes video variants based on technical and structural data.
    """

    def __init__(self, storage_manager: StorageManager):
        self._storage = storage_manager
        self._optimized_dir = self._storage._root / "videos" / "optimized"
        self._scoring_dir = Path("data/scoring")
        self._scoring_dir.mkdir(parents=True, exist_ok=True)
        
        self._scores_csv = self._scoring_dir / "video_scores.csv"
        self._priority_json = self._scoring_dir / "upload_priority.json"

    def score_all_variants(self) -> int:
        """Evaluates all found variants in the optimized folder."""
        if not self._optimized_dir.exists():
            logger.error("Optimized videos directory not found.")
            return 0

        all_results = []
        
        # Iterate through each video folder in optimized/
        for video_folder in self._optimized_dir.iterdir():
            if not video_folder.is_dir():
                continue
            
            video_id = video_folder.name
            metadata_path = video_folder / "metadata.json"
            
            if not metadata_path.exists():
                logger.warning(f"Metadata missing for {video_id}. Skipping.")
                continue

            with open(metadata_path, 'r', encoding='utf-8') as f:
                v8_metadata = json.load(f)

            # Analyze each variant in the folder
            for variant_file in video_folder.glob("*.mp4"):
                variant_name = variant_file.stem
                logger.info(f"Scoring Variant: {video_id} - {variant_name}")
                
                score_data = self._evaluate_variant(variant_file, v8_metadata, variant_name)
                all_results.append(score_data)

        if not all_results:
            return 0

        # Save CSV
        df = pd.DataFrame(all_results)
        df.to_csv(self._scores_csv, index=False)
        
        # Generate Priority Ranking (JSON)
        self._generate_priority_json(df)
        
        logger.info(f"Phase 9 complete: {len(all_results)} variants scored and ranked.")
        return len(all_results)

    def _evaluate_variant(self, file_path: Path, meta: Dict[str, Any], variant: str) -> Dict[str, Any]:
        """Calculates the 5 dimensions of scoring."""
        
        # 1. Get Technical Data via ffprobe
        width, height, duration = self._get_basic_info(file_path)
        
        # 2. Score Dimensions
        # D1: Duration (25%)
        d_score = self._score_duration(duration)
        
        # D2: Hook (25%) - Analyze motion/scene changes in first 3s
        h_score = self._score_hook_visual(file_path)
        
        # D3: Framing (20%)
        f_score = self._score_framing(meta)
        
        # D4: Rhythm (15%)
        r_score = self._score_rhythm(meta.get("speed_factor", 1.0))
        
        # D5: Audio (15%)
        a_score = self._score_audio(meta.get("audio_lufs", -14))

        # Final Calculation
        final_score = (
            d_score * 0.25 +
            h_score * 0.25 +
            f_score * 0.20 +
            r_score * 0.15 +
            a_score * 0.15
        ) * 100
        
        priority = "🔴 BAJA"
        if final_score >= 80: priority = "🟢 ALTA"
        elif final_score >= 65: priority = "🟡 MEDIA"

        return {
            "video_id": meta["video_id"],
            "variant": variant,
            "duration": round(duration, 2),
            "reframe": meta["reframe_strategy"],
            "speed": meta["speed_factor"],
            "hook_level": h_score, # For internal verification
            "final_score": round(final_score, 1),
            "priority": priority
        }

    def _score_duration(self, duration: float) -> float:
        if 15 <= duration <= 25: return 1.0
        if 26 <= duration <= 35: return 0.7
        if duration < 15: return 0.5
        return 0.4 # > 35s

    def _score_hook_visual(self, file_path: Path) -> float:
        """Analyze scene changes in the first 3 seconds as a proxy for visual hook."""
        try:
            # Use ffmpeg scdetect filter on the first 3 seconds
            cmd = [
                "ffmpeg", "-i", str(file_path),
                "-t", "3",
                "-vf", "scdetect=0.1", 
                "-f", "null", "-"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Count occurrences of 'show_entries' or 'parsed_scdetect' in logs? 
            # Actually, we'll use metadata from ffprobe for scene changes if available,
            # but simpler: check I-frame distribution in first 3s.
            
            cmd_frames = [
                "ffprobe", "-v", "error", "-t", "3",
                "-show_entries", "frame=pict_type", 
                "-of", "json", str(file_path)
            ]
            res = subprocess.run(cmd_frames, capture_output=True, text=True, check=True)
            frames = json.loads(res.stdout).get('frames', [])
            i_frames = [f for f in frames if f.get('pict_type') == 'I']
            
            # More I-frames (cuts/scene changes) in first 3s = higher hook
            count = len(i_frames)
            if count >= 3: return 1.0  # High
            if count >= 2: return 0.7  # Medium
            return 0.4                 # Low
        except:
            return 0.5 # Default

    def _score_framing(self, meta: Dict[str, Any]) -> float:
        strategy = meta.get("reframe_strategy", "unknown")
        zoom = meta.get("zoom_factor", 1.0)
        
        score = 0.5
        if strategy == "crop_fill": score = 1.0
        elif strategy == "scale_zoom": score = 0.8
        elif strategy == "blur_background": score = 0.6
        
        # Penalize excessive zoom
        if zoom > 1.12: score *= 0.8
        
        return score

    def _score_rhythm(self, speed: float) -> float:
        if 1.03 <= speed <= 1.08: return 1.0
        if speed < 1.03: return 0.6
        return 0.8 # > 1.08

    def _score_audio(self, lufs: float) -> float:
        # Ideal is -14
        diff = abs(lufs - (-14))
        if diff <= 0.5: return 1.0
        if diff <= 2.0: return 0.8
        return 0.5

    def _get_basic_info(self, path: Path) -> Tuple[int, int, float]:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height:format=duration",
            "-of", "json", str(path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        w = int(data['streams'][0]['width'])
        h = int(data['streams'][0]['height'])
        d = float(data['format']['duration'])
        return w, h, d

    def _generate_priority_json(self, df: pd.DataFrame):
        # Sort by score descending
        df_sorted = df.sort_values(by="final_score", ascending=False)
        upload_order = []
        
        for idx, row in df_sorted.iterrows():
            upload_order.append({
                "video_id": row["video_id"],
                "variant": row["variant"],
                "score": row["final_score"],
                "priority_rank": len(upload_order) + 1
            })
            
        with open(self._priority_json, 'w', encoding='utf-8') as f:
            json.dump({"upload_order": upload_order}, f, indent=4)

    def _save_json(self, data: Any, path: Path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
