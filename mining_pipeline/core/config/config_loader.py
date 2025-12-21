"""
Configuration Loader
Loads and validates YAML configuration files
"""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from .app_config import AppConfig


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigLoader:
    """
    Loads and validates configuration from YAML files.
    
    Responsibilities:
    - Read YAML configuration file
    - Validate all required fields
    - Validate types and value ranges
    - Return validated AppConfig instance
    """
    
    def __init__(self, config_path: Path):
        """
        Initialize ConfigLoader with path to config file.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self._config_path = config_path
    
    def load(self) -> AppConfig:
        """
        Load and validate configuration from YAML file.
        
        Returns:
            AppConfig: Validated configuration object
            
        Raises:
            ConfigValidationError: If configuration is invalid
            FileNotFoundError: If config file doesn't exist
        """
        # Load YAML file
        config_data = self._load_yaml()
        
        # Validate and extract fields
        api_key = self._validate_api_key(config_data)
        channel = self._validate_channel(config_data)
        min_views = self._validate_min_views(config_data)
        min_engagement = self._validate_min_engagement(config_data)
        max_videos = self._validate_max_videos(config_data)
        
        # New Phase 6 storage structure
        storage_meta = self._validate_storage_config(config_data)
        
        # New Phase 7 edit parameters
        edit_params = self._validate_edit_config(config_data)
        
        # Create and return AppConfig
        return AppConfig(
            api_key=api_key,
            channel=channel,
            min_views=min_views,
            min_engagement=min_engagement,
            max_videos=max_videos,
            storage_mode=storage_meta["mode"],
            storage_root=storage_meta["root"],
            keep_local_copy=storage_meta["keep_local_copy"],
            edit_params=edit_params
        )
    
    def _load_yaml(self) -> Dict[str, Any]:
        """Load YAML file and return parsed data."""
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self._config_path}"
            )
        
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            if data is None:
                raise ConfigValidationError("Configuration file is empty")
                
            if not isinstance(data, dict):
                raise ConfigValidationError(
                    "Configuration must be a YAML mapping/dictionary"
                )
                
            return data
            
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML syntax: {e}")
    
    def _validate_api_key(self, config: Dict[str, Any]) -> str:
        """Validate api_key field."""
        if "api_key" not in config:
            raise ConfigValidationError("Missing required field: 'api_key'")
        
        api_key = config["api_key"]
        
        if not isinstance(api_key, str):
            raise ConfigValidationError(
                f"Field 'api_key' must be a string, got {type(api_key).__name__}"
            )
        
        if not api_key.strip():
            raise ConfigValidationError("Field 'api_key' cannot be empty")
        
        return api_key.strip()
    
    def _validate_channel(self, config: Dict[str, Any]) -> str:
        """Validate channel field."""
        if "channel" not in config:
            raise ConfigValidationError("Missing required field: 'channel'")
        
        channel = config["channel"]
        
        if not isinstance(channel, str):
            raise ConfigValidationError(
                f"Field 'channel' must be a string, got {type(channel).__name__}"
            )
        
        if not channel.strip():
            raise ConfigValidationError("Field 'channel' cannot be empty")
        
        return channel.strip()
    
    def _validate_min_views(self, config: Dict[str, Any]) -> int:
        """Validate min_views field."""
        if "min_views" not in config:
            raise ConfigValidationError("Missing required field: 'min_views'")
        
        min_views = config["min_views"]
        
        if not isinstance(min_views, int):
            raise ConfigValidationError(
                f"Field 'min_views' must be an integer, got {type(min_views).__name__}"
            )
        
        if min_views <= 0:
            raise ConfigValidationError(
                f"Field 'min_views' must be greater than 0, got {min_views}"
            )
        
        return min_views
    
    def _validate_min_engagement(self, config: Dict[str, Any]) -> float:
        """Validate min_engagement field."""
        if "min_engagement" not in config:
            raise ConfigValidationError("Missing required field: 'min_engagement'")
        
        min_engagement = config["min_engagement"]
        
        # Accept both int and float
        if not isinstance(min_engagement, (int, float)):
            raise ConfigValidationError(
                f"Field 'min_engagement' must be a number, got {type(min_engagement).__name__}"
            )
        
        min_engagement = float(min_engagement)
        
        if not (0.0 <= min_engagement <= 1.0):
            raise ConfigValidationError(
                f"Field 'min_engagement' must be between 0.0 and 1.0, got {min_engagement}"
            )
        
        return min_engagement
    
    def _validate_max_videos(self, config: Dict[str, Any]) -> Optional[int]:
        """Validate max_videos field (optional)."""
        if "max_videos" not in config:
            return None
        
        max_videos = config["max_videos"]
        
        # None/null is valid
        if max_videos is None:
            return None
        
        if not isinstance(max_videos, int):
            raise ConfigValidationError(
                f"Field 'max_videos' must be an integer or null, got {type(max_videos).__name__}"
            )
        
        if max_videos <= 0:
            raise ConfigValidationError(
                f"Field 'max_videos' must be greater than 0 or null, got {max_videos}"
            )
        
        return max_videos
    
    def _validate_storage_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate storage section including new Phase 6 fields."""
        defaults = {
            "mode": "local",
            "root": "./storage",
            "keep_local_copy": True
        }
        
        if "storage" not in config:
            return defaults
        
        storage = config["storage"]
        if not isinstance(storage, dict):
            return defaults
            
        # Extract and validate individual fields
        mode = storage.get("mode", storage.get("type", defaults["mode"]))
        root = storage.get("root", defaults["root"])
        keep_local_copy = storage.get("keep_local_copy", defaults["keep_local_copy"])
        
        if not isinstance(mode, str):
            raise ConfigValidationError(f"storage.mode must be string, got {type(mode).__name__}")
        if not isinstance(root, str):
            raise ConfigValidationError(f"storage.root must be string, got {type(root).__name__}")
        if not isinstance(keep_local_copy, bool):
            raise ConfigValidationError(f"storage.keep_local_copy must be boolean, got {type(keep_local_copy).__name__}")
            
        return {
            "mode": mode.strip(),
            "root": root.strip(),
            "keep_local_copy": keep_local_copy
        }

    def _validate_edit_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate edit section for Phase 7."""
        defaults = {
            "keyframe_interval": 5,
            "intro_duration": 5,
            "outro_duration": 5
        }
        
        if "edit" not in config:
            return defaults
            
        edit = config["edit"]
        if not isinstance(edit, dict):
            return defaults
            
        keyframe_interval = edit.get("keyframe_interval", defaults["keyframe_interval"])
        intro_duration = edit.get("intro_duration", defaults["intro_duration"])
        outro_duration = edit.get("outro_duration", defaults["outro_duration"])
        
        if not isinstance(keyframe_interval, (int, float)) or keyframe_interval <= 0:
            raise ConfigValidationError("edit.keyframe_interval must be a positive number")
        if not isinstance(intro_duration, (int, float)) or intro_duration < 0:
            raise ConfigValidationError("edit.intro_duration must be a non-negative number")
        if not isinstance(outro_duration, (int, float)) or outro_duration < 0:
            raise ConfigValidationError("edit.outro_duration must be a non-negative number")
            
        return {
            "keyframe_interval": float(keyframe_interval),
            "intro_duration": float(intro_duration),
            "outro_duration": float(outro_duration)
        }
