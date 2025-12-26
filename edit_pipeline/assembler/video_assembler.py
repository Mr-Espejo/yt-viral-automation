"""
Video Assembler Service
Phase 8: Creative Assembly & Variant Generation
"""

import json
import logging
import subprocess
import yaml
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from mining_pipeline.core.config.app_config import AppConfig
from shared.storage.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class VideoAssembler:
    """
    Assembles final video variants based on configuration-driven rules and templates.
    """

    def __init__(self, config: AppConfig, storage_manager: StorageManager):
        self._config = config
        self._storage = storage_manager
        
        # Paths to configs
        self._config_dir = Path(__file__).parent.parent / "configs"
        self._variants_cfg = self._load_yaml(self._config_dir / "variants.yaml")
        self._templates_cfg = self._load_yaml(self._config_dir / "templates.yaml")
        self._rules_cfg = self._load_yaml(self._config_dir / "assembly_rules.yaml")
        
        # Output directory
        self._assembled_dir = self._storage._root / "videos" / "assembled"
        self._assembled_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata files
        self._segments_file = self._storage.metadata_path / "segments.json"
        self._variants_metadata_file = self._storage.metadata_path / "variants.json"
        self._log_file = self._storage.metadata_path / "assembly_log.json"

    def assemble_all(self) -> int:
        """
        Processes all normalized videos and generates variants.
        """
        logger.info("Starting Phase 8: Creative Assembly & Variant Generation")
        
        if not self._segments_file.exists():
            logger.error(f"Segments metadata not found: {self._segments_file}")
            return 0
            
        with open(self._segments_file, 'r', encoding='utf-8') as f:
            segments_data = json.load(f)
            
        normalized_dir = self._storage._root / "videos" / "normalized"
        video_files = list(normalized_dir.glob("*.mp4"))
        
        if not video_files:
            logger.warning("No normalized videos found to assemble.")
            return 0
            
        total_variants_count = 0
        all_variants_metadata = {}
        assembly_logs = []

        for video_path in video_files:
            video_id = video_path.stem
            if video_id not in segments_data:
                logger.warning(f"No segment metadata for {video_id}. Skipping.")
                continue
                
            video_segments = segments_data[video_id]
            logger.info(f"--- Assembling Variants for: {video_id} ---")
            
            for variant in self._variants_cfg.get('variants', []):
                variant_name = variant['name']
                template_name = variant['template']
                rule_name = variant['rule']
                max_dur = variant.get('max_duration', 60)
                
                try:
                    output_path = self._generate_variant(
                        video_path, 
                        video_id, 
                        variant_name, 
                        template_name, 
                        rule_name, 
                        video_segments,
                        max_dur
                    )
                    
                    if output_path:
                        total_variants_count += 1
                        meta = {
                            "source_video_id": video_id,
                            "variant_name": variant_name,
                            "template": template_name,
                            "output_path": str(output_path),
                            "timestamp": time.time()
                        }
                        all_variants_metadata[f"{video_id}_{variant_name}"] = meta
                        assembly_logs.append(f"SUCCESS: {video_id} -> {variant_name}")
                except Exception as e:
                    logger.error(f"Failed to assemble variant {variant_name} for {video_id}: {e}")
                    assembly_logs.append(f"ERROR: {video_id} -> {variant_name}: {str(e)}")

        # Save results
        self._save_json(all_variants_metadata, self._variants_metadata_file)
        self._save_json(assembly_logs, self._log_file)
        
        logger.info(f"Phase 8 complete: {total_variants_count} variants generated.")
        return total_variants_count

    def _generate_variant(
        self, 
        video_path: Path, 
        video_id: str, 
        variant_name: str, 
        template_name: str, 
        rule_name: str, 
        segments: Dict[str, Any],
        max_duration: float
    ) -> Optional[Path]:
        """
        Uses ffmpeg to create a specific video variant.
        """
        template = self._templates_cfg.get('templates', {}).get(template_name)
        rule = self._rules_cfg.get('rules', {}).get(rule_name)
        
        if not template or not rule:
            logger.error(f"Config missing for variant {variant_name} (template: {template_name}, rule: {rule_name})")
            return None
            
        outcome_dir = self._assembled_dir / variant_name
        outcome_dir.mkdir(parents=True, exist_ok=True)
        
        output_filename = f"{video_id}_{variant_name}_{template_name}.mp4"
        output_path = outcome_dir / output_filename
        
        if output_path.exists():
            logger.info(f"Variant already exists: {output_filename}")
            return output_path

        # 1. Calculate timestamps based on rule
        segments_to_include = rule.get('segments', [])
        filter_complex = ""
        inputs = []
        
        # Simplest approach for MVP: One filter complex that trims and joins
        # Or even simpler: Use multiple -ss and -to but that's messy for concat
        # We'll use a single pass with trims
        
        trim_filters = []
        for i, seg_key in enumerate(segments_to_include):
            seg = segments.get(seg_key)
            if not seg: continue
            
            start = seg['start']
            end = seg['end']
            
            # Simple trim/concat logic for ffmpeg
            trim_filters.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];")
            trim_filters.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];")

        concat_v = "".join([f"[v{i}]" for i in range(len(trim_filters)//2)])
        concat_a = "".join([f"[a{i}]" for i in range(len(trim_filters)//2)])
        
        v_label = "[vcomp]"
        a_label = "[acomp]"
        
        filter_complex = "".join(trim_filters)
        filter_complex += f"{concat_v}concat=n={len(trim_filters)//2}:v=1:a=0[vtmp];"
        filter_complex += f"{concat_a}concat=n={len(trim_filters)//2}:v=0:a=1[atmp];"
        
        # Apply template resolution/aspect ratio
        res = template.get('resolution', '1920x1080').replace('x', ':')
        # Padding logic to maintain aspect ratio
        filter_complex += f"[vtmp]scale={res}:force_original_aspect_ratio=decrease,pad={res}:(ow-iw)/2:(oh-ih)/2[vfinal]"

        command = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-filter_complex", filter_complex,
            "-map", "[vfinal]", "-map", "[atmp]",
            "-t", str(max_duration),
            "-c:v", template.get('vcodec', 'libx264'),
            "-c:a", template.get('acodec', 'aac'),
            "-crf", str(template.get('crf', 23)),
            "-b:a", template.get('bitrate_audio', '192k'),
            str(output_path)
        ]

        logger.info(f"Generating variant: {output_filename}...")
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"ffmpeg failed for {output_filename}: {result.stderr}")
            return None
            
        return output_path

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _save_json(self, data: Any, path: Path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
