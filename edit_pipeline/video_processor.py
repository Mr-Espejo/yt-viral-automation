"""
Video Processor Service
Phase 7: Video Processing & Normalization
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from mining_pipeline.core.config.app_config import AppConfig
from shared.storage.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class VideoProcessor:
    """
    Standardizes video assets for downstream analysis and editing.
    
    Responsibilities:
    - Format normalization (H.264/AAC, 1080p, 30fps).
    - Technical metadata extraction (ffprobe).
    - Asset generation (audio extraction, keyframes).
    - Structural segmentation (intro/body/outro timestamps).
    """

    def __init__(self, config: AppConfig, storage_manager: StorageManager):
        """
        Initialize VideoProcessor.
        
        Args:
            config: Application configuration.
            storage_manager: Storage manager for path resolution and persistence.
        """
        self._config = config
        self._storage = storage_manager
        
        # Ensure output directories exist
        self._normalized_dir = self._storage._root / "videos" / "normalized"
        self._frames_dir = self._storage._root / "videos" / "frames"
        self._audio_dir = self._storage._root / "videos" / "audio"
        
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Ensures that all processing subdirectories exist."""
        for d in [self._normalized_dir, self._frames_dir, self._audio_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def process_all(self) -> int:
        """
        Processes all discovered raw viral videos.
        
        Returns:
            int: Number of videos successfully processed.
        """
        raw_videos_dir = self._storage.videos_path
        if not raw_videos_dir.exists():
            logger.warning(f"Raw videos directory not found: {raw_videos_dir}")
            return 0

        # Discover videos (mp4)
        video_files = list(raw_videos_dir.glob("*.mp4"))
        logger.info(f"Discovered {len(video_files)} raw videos for processing")

        processed_count = 0
        technical_metadata = {}
        segments_metadata = {}

        for video_path in video_files:
            video_id = self._extract_id_from_filename(video_path.name)
            logger.info(f"--- Processing Video: {video_id} ---")
            
            try:
                # 1. Normalize
                normalized_path = self._normalize_video(video_path, video_id)
                
                # 2. Extract Technical Metadata
                metadata = self._extract_metadata(normalized_path)
                technical_metadata[video_id] = metadata
                
                # 3. Extract Audio
                self._extract_audio(normalized_path, video_id)
                
                # 4. Generate Keyframes
                self._generate_keyframes(normalized_path, video_id)
                
                # 5. Define Segments
                segments = self._define_segments(metadata['duration'])
                segments_metadata[video_id] = segments
                
                processed_count += 1
                logger.info(f"Successfully processed video: {video_id}")
                
            except Exception as e:
                logger.error(f"Failed to process video {video_id}: {e}")

        # Persist collective metadata
        self._save_json(technical_metadata, self._storage.metadata_path / "video_technical.json")
        self._save_json(segments_metadata, self._storage.metadata_path / "segments.json")

        return processed_count

    def _normalize_video(self, input_path: Path, video_id: str) -> Path:
        """
        Normalizes video to H.264/AAC, 1080p, 30fps.
        """
        output_path = self._normalized_dir / f"{video_id}.mp4"
        
        if output_path.exists():
            logger.info(f"Normalized video already exists: {video_id}.mp4")
            return output_path

        # ffmpeg command
        # scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2
        # This ensures 1080p with black bars if aspect ratio differs.
        command = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-r", "30",
            "-c:a", "aac", "-b:a", "192k", "-ac", "2",
            str(output_path)
        ]
        
        logger.info(f"Normalizing {video_id} to 1080p@30fps...")
        subprocess.run(command, check=True, capture_output=True)
        return output_path

    def _extract_metadata(self, video_path: Path) -> Dict[str, Any]:
        """
        Extracts technical metadata using ffprobe.
        """
        command = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,size,bit_rate",
            "-show_entries", "stream=avg_frame_rate,width,height,sample_rate",
            "-of", "json",
            str(video_path)
        ]
        
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        format_info = data.get('format', {})
        # Find video stream
        video_stream = next((s for s in data.get('streams', []) if s.get('width')), {})
        # Find audio stream
        audio_stream = next((s for s in data.get('streams', []) if s.get('sample_rate')), {})
        
        # Calculate FPS from avg_frame_rate (e.g. "30/1")
        fps_str = video_stream.get('avg_frame_rate', '0/0')
        fps = 0
        if '/' in fps_str:
            num, den = map(int, fps_str.split('/'))
            if den != 0: fps = num / den

        return {
            "duration": float(format_info.get('duration', 0)),
            "size_bytes": int(format_info.get('size', 0)),
            "bitrate": int(format_info.get('bit_rate', 0)),
            "width": int(video_stream.get('width', 0)),
            "height": int(video_stream.get('height', 0)),
            "fps": round(float(fps), 2),
            "audio_sample_rate": int(audio_stream.get('sample_rate', 0))
        }

    def _extract_audio(self, video_path: Path, video_id: str):
        """
        Extracts audio track to WAV.
        """
        output_path = self._audio_dir / f"{video_id}.wav"
        if output_path.exists(): return

        command = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
            str(output_path)
        ]
        subprocess.run(command, check=True, capture_output=True)

    def _generate_keyframes(self, video_path: Path, video_id: str):
        """
        Generates JPG keyframes at fixed intervals.
        """
        video_frames_dir = self._frames_dir / video_id
        video_frames_dir.mkdir(exist_ok=True)
        
        # Check if already has frames
        if any(video_frames_dir.iterdir()): return

        interval = self._config.edit_params.get("keyframe_interval", 5)
        
        command = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", f"fps=1/{interval}",
            str(video_frames_dir / "frame_%04d.jpg")
        ]
        subprocess.run(command, check=True, capture_output=True)

    def _define_segments(self, duration: float) -> Dict[str, Any]:
        """
        Calculates intro, body, and outro timestamps.
        """
        intro_dur = self._config.edit_params.get("intro_duration", 5)
        outro_dur = self._config.edit_params.get("outro_duration", 5)
        
        # Safety check for very short videos
        if duration < (intro_dur + outro_dur):
            intro_dur = duration * 0.1
            outro_dur = duration * 0.1

        return {
            "intro": {"start": 0, "end": intro_dur},
            "body": {"start": intro_dur, "end": max(intro_dur, duration - outro_dur)},
            "outro": {"start": max(intro_dur, duration - outro_dur), "end": duration}
        }

    def _extract_id_from_filename(self, filename: str) -> str:
        """
        Extracts video_id from filename pattern: <views>_<video_id>_<title>.mp4
        """
        parts = filename.split('_')
        if len(parts) >= 2:
            return parts[1]
        return filename.replace('.mp4', '')

    def _save_json(self, data: Dict[str, Any], path: Path):
        """Helper to save JSON data."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
