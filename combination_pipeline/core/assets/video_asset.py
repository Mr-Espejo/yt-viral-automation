from dataclasses import dataclass
from typing import Optional

@dataclass
class VideoAsset:
    """Represents a video file and its metadata."""
    id: str
    filename: str
    path: str
    duration: Optional[float] = None
    aspect_ratio: str = "9:16"

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        if not isinstance(other, VideoAsset):
            return False
        return self.path == other.path
