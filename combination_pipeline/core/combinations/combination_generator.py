import os
import json
import logging
from itertools import combinations
from typing import List
from ..assets.video_asset import VideoAsset
from .video_combination import VideoCombination

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CombinationGenerator:
    """Generates unique, deterministic combinations of VideoAssets."""

    def __init__(self, video_assets: List[VideoAsset]):
        if len(video_assets) < 2:
            raise ValueError(f"At least 2 unique videos are required to generate combinations. Found: {len(video_assets)}")
        
        # Remove duplicates based on path (VideoAsset implements __eq__ and __hash__)
        self.video_assets = list(dict.fromkeys(video_assets))
        if len(self.video_assets) < 2:
            raise ValueError("After removing duplicates, less than 2 unique videos remain.")
            
        # Ensure deterministic order by filename
        self.video_assets.sort(key=lambda x: x.filename)

    def generate(self) -> List[VideoCombination]:
        """Creates combinations of size 2 following itertools.combinations logic."""
        combos = list(combinations(self.video_assets, 2))
        results = []
        
        for idx, pair in enumerate(combos, 1):
            v1, v2 = pair
            combo_id = f"combo_{idx:03d}"
            
            # Roles assignment: First video -> top, Second video -> bottom
            roles = {
                "top": v1.filename,
                "bottom": v2.filename
            }
            
            results.append(VideoCombination(
                combination_id=combo_id,
                videos=list(pair),
                roles=roles
            ))
            
        logger.info(f"Generated {len(results)} total combinations from {len(self.video_assets)} assets.")
        return results

    @staticmethod
    def save_to_json(combinations_list: List[VideoCombination], output_path: str):
        """Saves a list of VideoCombinations to a structured JSON file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        data = [c.to_dict() for c in combinations_list]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved combinations to {output_path}")
