import os
import json
import subprocess
import yaml
from typing import List, Optional
from .models import (
    VideoAsset, Region, VideoSource, Canvas, Layout, 
    CompositionConfig, ReframeStrategy
)

class AudioManager:
    """Handles audio normalization and routing."""
    
    @staticmethod
    def get_normalization_filter() -> str:
        """Returns the FFmpeg loudnorm filter for -14 LUFS."""
        # Standard loudnorm filter parameters for -14 LUFS
        return "loudnorm=I=-14:LRA=11:tp=-1.5"

class ReframeEngine:
    """Calculates FFmpeg filter strings for reframing strategies."""
    
    @staticmethod
    def get_crop_fill_filter(source_w: int, source_h: int, target_w: int, target_h: int) -> str:
        """Calculates crop and scale to fill the target region without black bars."""
        aspect_source = source_w / source_h
        aspect_target = target_w / target_h
        
        if aspect_source > aspect_target:
            # Source is wider than target
            new_w = int(source_h * aspect_target)
            crop_x = (source_w - new_w) // 2
            return f"crop={new_w}:{source_h}:{crop_x}:0,scale={target_w}:{target_h}"
        else:
            # Source is taller than target
            new_h = int(source_w / aspect_target)
            crop_y = (source_h - new_h) // 2
            return f"crop={source_w}:{new_h}:0:{crop_y},scale={target_w}:{target_h}"

    @staticmethod
    def get_scale_zoom_filter(source_w: int, source_h: int, target_w: int, target_h: int, zoom: float = 1.0) -> str:
        """Scales the video and applies a zoom center crop."""
        # First scale to match one dimension while keeping aspect ratio
        aspect_source = source_w / source_h
        aspect_target = target_w / target_h
        
        if aspect_source > aspect_target:
            scale_h = target_h
            scale_w = int(target_h * aspect_source)
        else:
            scale_w = target_w
            scale_h = int(target_w / aspect_source)
            
        return f"scale={scale_w}:{scale_h},crop={target_w}:{target_h}:(iw-{target_w})/2:(ih-{target_h})/2,zoompan=z={zoom}:d=1:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s={target_w}x{target_h}"

    @staticmethod
    def get_blur_background_filter(source_w: int, source_h: int, target_w: int, target_h: int) -> str:
        """Overlays the scaled video onto a blurred and cropped version of itself to fill the area."""
        # Background: scale to target, crop, blur
        # Foreground: scale to fit target
        bg = f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},boxblur=20:10"
        fg = f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease"
        return f"split[bg_orig][fg_orig];[bg_orig]{bg}[bg_blur];[fg_orig]{fg}[fg_scaled];[bg_blur][fg_scaled]overlay=(W-w)/2:(H-h)/2"

class Composer:
    """Orchestrates the FFmpeg process to create the final video."""
    
    def __init__(self, config: CompositionConfig, workspace_root: str):
        self.config = config
        self.workspace_root = workspace_root
        self.output_dir = os.path.join(workspace_root, "storage/videos/composed")
        self.metadata_dir = os.path.join(workspace_root, "storage/metadata/compositions")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)

    def _get_abs_path(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        # Try relative to workspace root (storage/...)
        r_path = os.path.join(self.workspace_root, path)
        return r_path

    def _get_video_info(self, path: str) -> dict:
        """Uses ffprobe to get video metadata."""
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration,r_frame_rate",
            "-of", "json", path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise FileNotFoundError(f"Could not probe file: {path}")
        data = json.loads(result.stdout)
        stream = data["streams"][0]
        
        # Parse framerate (e.g. "30/1")
        fr_parts = stream["r_frame_rate"].split('/')
        fps = float(fr_parts[0]) / float(fr_parts[1]) if len(fr_parts) > 1 else float(fr_parts[0])
        
        duration = float(stream.get("duration", 0))
        if duration == 0:
            # Try to get duration from format if stream duration is missing
            cmd_fmt = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "json", path
            ]
            res_fmt = subprocess.run(cmd_fmt, capture_output=True, text=True)
            data_fmt = json.loads(res_fmt.stdout)
            duration = float(data_fmt["format"].get("duration", 0))

        return {
            "width": int(stream["width"]),
            "height": int(stream["height"]),
            "duration": duration,
            "fps": fps
        }

    def compose(self, output_filename: str):
        """Builds and executes the FFmpeg command."""
        # 1. Prepare assets and determine duration
        durations = []
        for src in self.config.sources:
            abs_path = self._get_abs_path(src.asset.path)
            info = self._get_video_info(abs_path)
            src.asset.path = abs_path # Use absolute path for FFmpeg
            src.asset.width = info["width"]
            src.asset.height = info["height"]
            src.asset.duration = info["duration"]
            src.asset.fps = info["fps"]
            durations.append(info["duration"])
        
        if self.config.duration_mode == "min":
            final_duration = min(durations)
        else:
            final_duration = durations[0]

        # 2. Build FFmpeg command
        cmd = ["ffmpeg", "-y"]
        for src in self.config.sources:
            cmd.extend(["-t", str(final_duration), "-i", src.asset.path])
        
        # Filter Complex
        filter_parts = []
        
        for i, src in enumerate(self.config.sources):
            region = next(r for r in self.layout.regions if r.id == src.region_id)
            
            if src.strategy.type == "crop_fill":
                reframe_filter = ReframeEngine.get_crop_fill_filter(
                    src.asset.width, src.asset.height, region.width, region.height
                )
            elif src.strategy.type == "scale_zoom":
                reframe_filter = ReframeEngine.get_scale_zoom_filter(
                    src.asset.width, src.asset.height, region.width, region.height, src.strategy.zoom
                )
            elif src.strategy.type == "blur_background":
                reframe_filter = ReframeEngine.get_blur_background_filter(
                    src.asset.width, src.asset.height, region.width, region.height
                )
            else:
                reframe_filter = f"scale={region.width}:{region.height}"
            
            filter_parts.append(f"[{i}:v]{reframe_filter}[v{i}]")
            
        # Canvas construction
        canvas_bg = f"color=c=black:s={self.config.canvas.width}x{self.config.canvas.height}:d={final_duration} [base]"
        filter_parts.insert(0, canvas_bg)
        
        curr_label = "[base]"
        for i, src in enumerate(self.config.sources):
            region = next(r for r in self.layout.regions if r.id == src.region_id)
            next_label = f"[tmp{i}]" if i < len(self.config.sources) - 1 else "[vfinal]"
            filter_parts.append(f"{curr_label}[v{i}]overlay=x={region.x}:y={region.y}{next_label}")
            curr_label = next_label

        # Audio routing
        top_src_idx = -1
        for i, src in enumerate(self.config.sources):
            if src.region_id == "top" and src.audio_enabled:
                top_src_idx = i
                break
        
        if top_src_idx != -1:
            audio_filter = f"[{top_src_idx}:a]{AudioManager.get_normalization_filter()}[afinal]"
            filter_parts.append(audio_filter)
            audio_map = ["[afinal]"]
        else:
            audio_map = []

        cmd.extend(["-filter_complex", ";".join(filter_parts)])
        cmd.extend(["-map", "[vfinal]"])
        if audio_map:
            cmd.extend(["-map", "[afinal]"])
        else:
            cmd.append("-an") # No audio
        
        cmd.extend([
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(self.config.canvas.fps),
            "-c:a", "aac", "-b:a", "192k",
            os.path.join(self.output_dir, output_filename)
        ])
        
        print(f"Creating composed video: {output_filename}")
        subprocess.run(cmd, check=True)
        
        self._save_metadata(output_filename, final_duration)

    def _save_metadata(self, filename: str, duration: float):
        meta = {
            "output_video": filename,
            "videos_used": [src.asset.path for src in self.config.sources],
            "layout": self.config.layout_type,
            "audio_control": {
                "master_source": next((src.region_id for src in self.config.sources if src.audio_enabled), "none")
            },
            "duration_final": duration,
            "pipeline_stage": "composition"
        }
        meta_path = os.path.join(self.metadata_dir, filename.replace(".mp4", ".json"))
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=4)

    @property
    def layout(self) -> Layout:
        return self._layout

    @layout.setter
    def layout(self, val: Layout):
        self._layout = val

class CompositionEngine:
    """Hub for coordination and parsing configuration."""
    
    def __init__(self, yaml_path: str, workspace_root: str):
        self.workspace_root = workspace_root
        with open(yaml_path, 'r') as f:
            self.raw_config = yaml.safe_load(f)
        
        self.canvas = Canvas(
            width=self.raw_config.get('canvas', {}).get('width', 1080),
            height=self.raw_config.get('canvas', {}).get('height', 1920),
            fps=self.raw_config.get('canvas', {}).get('fps', 30)
        )
        
        self.layout = self._parse_layout()
        self.config = self._parse_composition_config()

    def _parse_layout(self) -> Layout:
        l_cfg = self.raw_config['layout']
        regions = []
        for r in l_cfg['regions']:
            regions.append(Region(
                id=r['id'],
                x=r['x'],
                y=r['y'],
                width=r['width'],
                height=r['height']
            ))
        return Layout(type=l_cfg['type'], regions=regions)

    def _parse_composition_config(self) -> CompositionConfig:
        sources_cfg = self.raw_config['sources']
        sources = []
        for region_id, s in sources_cfg.items():
            asset = VideoAsset(path=s['video'])
            
            # Reframe strategy parsing
            s_cfg = s.get('reframe', {})
            strategy_type = s_cfg.get('type', 'crop_fill')
            zoom = s_cfg.get('zoom', 1.0)
            
            strategy = ReframeStrategy(type=strategy_type, zoom=zoom)
            sources.append(VideoSource(
                region_id=region_id,
                asset=asset,
                audio_enabled=s.get('audio', False),
                strategy=strategy
            ))
            
        return CompositionConfig(
            layout_type=self.layout.type,
            sources=sources,
            canvas=self.canvas,
            duration_mode=self.raw_config.get('duration', {}).get('mode', 'min')
        )

    def run(self, output_name: str = "composed_video.mp4"):
        composer = Composer(self.config, self.workspace_root)
        composer.layout = self.layout
        composer.compose(output_name)

    def process_combinations(self, combinations_path: str):
        """Processes all combinations from a JSON file."""
        if not os.path.isabs(combinations_path):
            combinations_path = os.path.join(self.workspace_root, combinations_path)
            
        with open(combinations_path, 'r') as f:
            combinations = json.load(f)
            
        print(f"Total combinations found: {len(combinations)}")
        
        for combo in combinations:
            combo_id = combo['combination_id']
            roles = combo['roles']
            
            # Map roles to sources
            # We assume the layout in self.raw_config matches the roles
            # Let's rebuild the CompositionConfig for each combo
            sources = []
            for region_id, filename in roles.items():
                # We need the relative path to the video (storage/videos/normalized/...)
                # The generator saves filenames only, we assume they are in 'storage/videos/normalized'
                video_path = f"storage/videos/normalized/{filename}"
                asset = VideoAsset(path=video_path)
                
                # Use default reframe from first source in raw_config or crop_fill
                strategy = ReframeStrategy(type="crop_fill")
                
                sources.append(VideoSource(
                    region_id=region_id,
                    asset=asset,
                    audio_enabled=(region_id == "top"),
                    strategy=strategy
                ))
            
            config = CompositionConfig(
                layout_type=self.layout.type,
                sources=sources,
                canvas=self.canvas,
                duration_mode=self.raw_config.get('duration', {}).get('mode', 'min')
            )
            
            print(f"Processing {combo_id}...")
            composer = Composer(config, self.workspace_root)
            composer.layout = self.layout
            composer.compose(f"{combo_id}.mp4")
