"""
Video Optimizer Service
Phase 8: AI Video Optimization Agent for YouTube Shorts
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from mining_pipeline.core.config.app_config import AppConfig
from shared.storage.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class VideoOptimizer:
    """
    Service responsible for technical optimization of YouTube Shorts.
    
    Functions:
    - Aspect Ratio Detection
    - Intelligent Reframing (Blur Background, Crop Fill, Scale Zoom)
    - Temporal Variant Generation (Hook, Mid-cut, Full)
    - Audio Normalization (-14 LUFS)
    - Speed Optimization (1.05x)
    - Output Organization & Metadata Generation
    """

    def __init__(self, config: AppConfig, storage_manager: StorageManager):
        self._config = config
        self._storage = storage_manager
        self._optimized_root = self._storage._root / "videos" / "optimized"
        self._optimized_root.mkdir(parents=True, exist_ok=True)

    def optimize_all(self) -> int:
        """Processes all normalized videos for Shorts optimization."""
        normalized_dir = self._storage._root / "videos" / "normalized"
        if not normalized_dir.exists():
            logger.warning("Normalized videos directory not found.")
            return 0

        video_files = list(normalized_dir.glob("*.mp4"))
        logger.info(f"Discovered {len(video_files)} videos for Phase 8 optimization.")

        processed_count = 0
        for video_path in video_files:
            video_id = video_path.stem
            logger.info(f"--- Optimizing Video: {video_id} ---")
            
            try:
                self._optimize_single_video(video_path, video_id)
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to optimize {video_id}: {e}")

        return processed_count

    def _optimize_single_video(self, video_path: Path, video_id: str):
        """Generates all optimized variants for a single video."""
        video_output_dir = self._optimized_root / video_id
        video_output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Detect Aspect Ratio
        width, height, duration = self._get_video_info(video_path)
        aspect_ratio_str = self._detect_aspect_ratio(width, height)
        
        # 2. Select strategy
        strategy, zoom_factor = self._select_strategy(aspect_ratio_str)
        speed_factor = 1.05  # Standard recommendation

        # 3. Define Variants
        variants_config = [
            ("hook_short", 0, min(20, duration)),
            ("mid_cut", min(5, duration * 0.1), min(30, duration)),
            ("full_optimized", 0, duration)
        ]

        # 4. Process Variants
        for name, start, length in variants_config:
            self._process_variant(
                video_path, 
                video_output_dir / f"{name}.mp4",
                start, 
                length, 
                strategy, 
                zoom_factor, 
                speed_factor
            )

        # 5. Metadata
        metadata = {
            "video_id": video_id,
            "original_aspect_ratio": aspect_ratio_str,
            "reframe_strategy": strategy,
            "zoom_factor": zoom_factor,
            "speed_factor": speed_factor,
            "audio_lufs": -14,
            "variants": [v[0] for v in variants_config]
        }
        
        with open(video_output_dir / "metadata.json", "w", encoding='utf-8') as f:
            json.dump(metadata, f, indent=4)

    def _get_video_info(self, video_path: Path) -> Tuple[int, int, float]:
        """Gets width, height, and duration using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error", 
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height:format=duration",
            "-of", "json", str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        width = int(data['streams'][0]['width'])
        height = int(data['streams'][0]['height'])
        duration = float(data['format']['duration'])
        return width, height, duration

    def _detect_aspect_ratio(self, width: int, height: int) -> str:
        ratio = width / height
        if 0.5 <= ratio <= 0.6: return "9:16"
        if 0.9 <= ratio <= 1.1: return "1:1"
        return "landscape"

    def _select_strategy(self, ratio_str: str) -> Tuple[str, float]:
        if ratio_str == "1:1":
            return "crop_fill", 1.0
        if ratio_str == "9:16":
            return "scale_zoom", 1.08
        return "blur_background", 1.0

    def _process_variant(self, 
                       input_path: Path, 
                       output_path: Path, 
                       start: float, 
                       length: float, 
                       strategy: str, 
                       zoom: float, 
                       speed: float):
        """Constructs and executes the ffmpeg command for a specific variant."""
        
        if output_path.exists():
            return

        # Filters
        video_filters = []
        
        # Speed & Zoom (Part of video filter)
        # Note: atempo is for audio speed
        
        if strategy == "crop_fill":
            # 1:1 to 9:16
            video_filters.append("crop=ih*9/16:ih")
            video_filters.append("scale=1080:1920")
        elif strategy == "blur_background":
            # Blur background strategy
            bg = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg];"
            fg = "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            video_filters.append(bg + fg + "[bg][fg]overlay=(W-w)/2:(H-h)/2")
        elif strategy == "scale_zoom":
            # 9:16 already, apply zoom
            video_filters.append(f"scale=iw*{zoom}:-1,crop=iw/{zoom}:ih/{zoom}")
            video_filters.append("scale=1080:1920")
        else:
            # Universal fallback: Blur Background to ensure "Nunca dejar bordes negros"
            bg = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg];"
            fg = "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            video_filters.append(bg + fg + "[bg][fg]overlay=(W-w)/2:(H-h)/2")

        # Add speed filter
        video_filters.append(f"setpts=PTS/{speed}")
        
        # Audio filters: speed + normalization
        audio_filters = [f"atempo={speed}", "loudnorm=I=-14:LRA=7:tp=-2"]

        # Command
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start:.3f}",
            "-t", f"{length:.3f}",
            "-i", str(input_path),
            "-vf", ",".join(video_filters) if strategy != "blur_background" else video_filters[0],
            "-af", ",".join(audio_filters),
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-c:a", "aac", "-b:a", "192k",
            str(output_path)
        ]
        
        # Special case for blur_background because filter_complex is used implicitly here or can be explicit
        if strategy == "blur_background":
            cmd[8] = "-filter_complex"

        logger.info(f"Generating optimized variant: {output_path.name}")
        subprocess.run(cmd, capture_output=True, text=True, check=True)
