from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class VideoAsset:
    """Represents a video file and its metadata."""
    path: str
    width: int = 0
    height: int = 0
    duration: float = 0.0
    fps: float = 30.0
    has_audio: bool = True

@dataclass
class Region:
    """A specific area on the canvas."""
    id: str
    x: int
    y: int
    width: int
    height: int

@dataclass
class ReframeStrategy:
    """Strategy for fitting a video into a region."""
    type: str  # crop_fill, scale_zoom, blur_background
    zoom: float = 1.0

@dataclass
class VideoSource:
    """Mapping of a video asset to a region with specific settings."""
    region_id: str
    asset: VideoAsset
    audio_enabled: bool = True
    strategy: ReframeStrategy = field(default_factory=lambda: ReframeStrategy(type="crop_fill"))

@dataclass
class Canvas:
    """The final video specifications."""
    width: int = 1080
    height: int = 1920
    fps: int = 30

@dataclass
class Layout:
    """The arrangement of regions on the canvas."""
    type: str
    regions: List[Region]

@dataclass
class CompositionConfig:
    """Top-level configuration for a composition."""
    layout_type: str
    sources: List[VideoSource]
    canvas: Canvas = field(default_factory=Canvas)
    duration_mode: str = "min"  # min, max, or specific float
