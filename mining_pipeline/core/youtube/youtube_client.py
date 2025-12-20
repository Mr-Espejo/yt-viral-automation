"""
YouTube API Client - Phase 2 (Strict MVP Mode)
Resolves channel identifiers (ID, Handle, URL) into canonical metadata.
"""

import re
import logging
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .channel_info import ChannelInfo
from .video_info import VideoInfo

logger = logging.getLogger(__name__)


class ChannelResolutionError(Exception):
    """Exception raised for errors in channel resolution."""
    pass


class YouTubeClient:
    """
    YouTube Data API client with strict resolution rules.
    
    Allowed formats:
    - Channel ID (starts with 'UC')
    - Handle (starts with '@')
    - Full YouTube URL (starts with 'http')
    """

    def __init__(self, api_key: str):
        """Initialize the YouTube API service."""
        # static_discovery=False prevents the 'file_cache' warning in logs
        self._service = build('youtube', 'v3', developerKey=api_key, static_discovery=False)

    def resolve_channel(self, channel_input: str) -> ChannelInfo:
        """
        Main entry point for channel resolution.
        Implements Strict MVP rules.
        """
        identifier = channel_input.strip()

        # --- REGLA ESTRICTA MVP ---
        if not identifier.startswith(("UC", "http", "@")):
            raise ChannelResolutionError(
                "Formato de canal no soportado en MVP. "
                "Debe ser Channel ID (UC...), Handle (@...) o URL completa (http...)."
            )

        channel_id = None

        # 1. Direct Channel ID
        if identifier.startswith("UC") and len(identifier) == 24:
            channel_id = identifier
            logger.info(f"Resolviendo por ID directo: {channel_id}")

        # 2. Handle (@username)
        elif identifier.startswith("@"):
            channel_id = self._resolve_by_handle(identifier)
            logger.info(f"Resolviendo por Handle oficial: {channel_id}")

        # 3. URL completa
        elif identifier.startswith("http"):
            channel_id = self._resolve_from_url(identifier)
            logger.info(f"Resolviendo por URL: {channel_id}")

        if not channel_id:
            raise ChannelResolutionError(f"No se pudo determinar un ID de canal válido para: {identifier}")

        return self._fetch_and_verify(channel_id, identifier)

    def _resolve_by_handle(self, handle: str) -> str:
        """Uses channels().list(forHandle=...) for deterministic handle resolution."""
        try:
            # Deterministic resolution: list(forHandle) is exact.
            response = self._service.channels().list(
                part="id",
                forHandle=handle
            ).execute()

            items = response.get("items", [])
            if not items:
                raise ChannelResolutionError(f"Handle no encontrado o no resoluble: {handle}")
            
            return items[0]["id"]
        except HttpError as e:
            raise ChannelResolutionError(f"Error de API al resolver handle {handle}: {e}")

    def _resolve_from_url(self, url: str) -> str:
        """Extracts channel ID or Handle from a YouTube URL."""
        # Handle /channel/UC...
        if "/channel/" in url:
            match = re.search(r"channel/(UC[\w-]{22})", url)
            if match:
                return match.group(1)
        
        # Handle /@handle
        if "/@" in url:
            match = re.search(r"/(@[\w.-]+)", url)
            if match:
                return self._resolve_by_handle(match.group(1))
            
        # Handle old /user/ or /c/ styles via search fallback is DISCOURAGED in Strict MVP,
        # but if we have the URL, we should try to get the ID.
        # For now, we only support the most common ones (/channel/ and /@/)
        raise ChannelResolutionError(
            f"La URL no contiene un formato de canal soportado (/channel/ o /@/): {url}"
        )

    def _fetch_and_verify(self, channel_id: str, original_input: str) -> ChannelInfo:
        """Fetches final metadata and performs cross-validation."""
        try:
            response = self._service.channels().list(
                part="snippet,contentDetails,statistics",
                id=channel_id
            ).execute()

            items = response.get("items", [])
            if not items:
                raise ChannelResolutionError(f"El ID de canal resuelto no existe: {channel_id}")

            data = items[0]
            snippet = data.get("snippet", {})
            content_details = data.get("contentDetails", {})
            statistics = data.get("statistics", {})

            # Related Playlists for uploads
            uploads_playlist_id = content_details.get("relatedPlaylists", {}).get("uploads")
            if not uploads_playlist_id:
                raise ChannelResolutionError(f"El canal no tiene una playlist de uploads pública: {channel_id}")

            # Cross-Validation: Check if customUrl matches handle input
            custom_url = snippet.get("customUrl", "")
            if original_input.startswith("@"):
                # Handle comparison (case insensitive)
                if custom_url.lower() != original_input.lower():
                    logger.warning(
                        f"Discrepancia detectada: Buscaba {original_input}, "
                        f"pero el canal tiene customUrl {custom_url}"
                    )
                    # En modo MUY ESTRICTO lanzaríamos error. Por ahora advertimos.

            return ChannelInfo(
                channel_id=channel_id,
                title=snippet.get("title", "Unknown"),
                uploads_playlist_id=uploads_playlist_id,
                description=snippet.get("description", ""),
                custom_url=custom_url,
                subscriber_count=int(statistics.get("subscriberCount", 0)) if "subscriberCount" in statistics else None,
                video_count=int(statistics.get("videoCount", 0)) if "videoCount" in statistics else None
            )

        except HttpError as e:
            raise ChannelResolutionError(f"Error de API al obtener metadatos: {e}")

    def fetch_playlist_items(self, playlist_id: str, max_results: int = 50, page_token: Optional[str] = None) -> dict:
        """Low-level API call to playlistItems.list."""
        try:
            return self._service.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=max_results,
                pageToken=page_token
            ).execute()
        except HttpError as e:
            raise ChannelResolutionError(f"Error fetching playlist items: {e}")

    def fetch_videos_details(self, video_ids: list[str]) -> list[VideoInfo]:
        """Low-level API call to videos.list for detailed statistics in batches."""
        try:
            response = self._service.videos().list(
                part="snippet,statistics",
                id=",".join(video_ids)
            ).execute()

            items = response.get("items", [])
            videos_info = []

            for item in items:
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                
                videos_info.append(VideoInfo(
                    video_id=item.get("id", ""),
                    title=snippet.get("title", "Untitled"),
                    published_at=snippet.get("publishedAt", ""),
                    views=int(stats.get("viewCount", 0)),
                    likes=int(stats.get("likeCount", 0)),
                    comments=int(stats.get("commentCount", 0))
                ))
            return videos_info
        except HttpError as e:
            logger.error(f"Error fetching video details: {e}")
            return []
