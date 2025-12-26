from dataclasses import dataclass, field
from typing import List, Dict
from ..assets.video_asset import VideoAsset

@dataclass
class VideoCombination:
    """Represents a unique combination of videos with specific roles."""
    combination_id: str
    videos: List[VideoAsset]
    layout: str = "vertical_split"
    roles: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Converts the combination to a serializable dictionary."""
        return {
            "combination_id": self.combination_id,
            "videos": [v.filename for v in self.videos],
            "layout": self.layout,
            "roles": self.roles
        }
