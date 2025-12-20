"""
Application Configuration Model
Represents a validated configuration state
"""

from typing import Optional


class AppConfig:
    """
    Immutable configuration object for YouTube Viral Automation.
    
    Represents a VALID configuration state only.
    All validation must be performed before instantiation.
    """
    
    def __init__(
        self,
        api_key: str,
        channel: str,
        min_views: int,
        min_engagement: float,
        max_videos: Optional[int] = None,
        storage_mode: str = "local",
        storage_root: str = "./storage",
        keep_local_copy: bool = True
    ):
        """
        Initialize AppConfig with validated values.
        
        Args:
            api_key: YouTube API key (non-empty)
            channel: Channel ID, @handle, or URL (non-empty)
            min_views: Minimum views threshold (> 0)
            min_engagement: Minimum engagement rate (0.0 - 1.0)
            max_videos: Maximum videos to analyze (optional, > 0 or None)
            storage_mode: Storage backend type (default: "local")
            storage_root: Root directory for storage (default: "./storage")
            keep_local_copy: Whether to keep local files after moving to storage (default: True)
        """
        self._api_key = api_key
        self._channel = channel
        self._min_views = min_views
        self._min_engagement = min_engagement
        self._max_videos = max_videos
        self._storage_mode = storage_mode
        self._storage_root = storage_root
        self._keep_local_copy = keep_local_copy
    
    @property
    def api_key(self) -> str:
        """YouTube API key."""
        return self._api_key
    
    @property
    def channel(self) -> str:
        """Channel identifier (ID, @handle, or URL)."""
        return self._channel
    
    @property
    def min_views(self) -> int:
        """Minimum views threshold."""
        return self._min_views
    
    @property
    def min_engagement(self) -> float:
        """Minimum engagement rate (0.0 - 1.0)."""
        return self._min_engagement
    
    @property
    def max_videos(self) -> Optional[int]:
        """Maximum number of videos to analyze (None = unlimited)."""
        return self._max_videos
    
    @property
    def storage_mode(self) -> str:
        """Storage backend mode."""
        return self._storage_mode

    @property
    def storage_root(self) -> str:
        """Root directory for storage."""
        return self._storage_root

    @property
    def keep_local_copy(self) -> bool:
        """Whether to keep local copies of files."""
        return self._keep_local_copy
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"AppConfig(channel={self.channel!r}, "
            f"min_views={self.min_views}, "
            f"min_engagement={self.min_engagement}, "
            f"storage_mode={self.storage_mode!r})"
        )
