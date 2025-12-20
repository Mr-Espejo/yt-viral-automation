"""
Channel Information Domain Model
Phase 2: Channel Resolution
"""

from typing import Optional


class ChannelInfo:
    """
    Domain model representing a resolved YouTube channel.
    Represents a VALID channel state only.
    """
    
    def __init__(
        self,
        channel_id: str,
        title: str,
        uploads_playlist_id: str,
        description: str = "",
        custom_url: str = "",
        subscriber_count: Optional[int] = None,
        video_count: Optional[int] = None
    ):
        self.channel_id = channel_id
        self.title = title
        self.uploads_playlist_id = uploads_playlist_id
        self.description = description
        self.custom_url = custom_url
        self.subscriber_count = subscriber_count
        self.video_count = video_count

    def __repr__(self) -> str:
        return f"ChannelInfo(title={self.title!r}, handle={self.custom_url!r}, id={self.channel_id!r})"
