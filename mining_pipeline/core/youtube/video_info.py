"""
Video Information Domain Model
Phase 3: Video Metadata Mining
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass(frozen=True)
class VideoInfo:
    """
    Domain model representing a single YouTube video's metadata.
    Immutable dataclass for thread-safety and clarity.
    """
    video_id: str
    title: str
    published_at: str
    views: int
    likes: int
    comments: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary for serialization (e.g., CSV)."""
        return asdict(self)
