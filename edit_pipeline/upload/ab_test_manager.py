"""
A/B Test Manager - Phase 10
Handles experimental vs control group logic for video variants.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ABTestManager:
    """
    Determines if a variant should be part of an A/B test.
    """

    def __init__(self, ab_test_enabled: bool = True):
        self._enabled = ab_test_enabled

    def get_experiment_metadata(self, video_id: str, variant_name: str) -> Dict[str, str]:
        """
        Assings a group (control/experiment) to the upload.
        """
        if not self._enabled:
            return {"group": "standard"}
            
        # Deterministic assignment based on variant name for simplicity
        if "hook" in variant_name.lower():
            return {"group": "experiment_group", "test_id": f"test_{video_id}_hook"}
        
        return {"group": "control_group"}

    def should_test(self, score_diff: float, threshold: float = 5.0) -> bool:
        """Decides if A/B testing is valuable based on score proximity."""
        return score_diff < threshold
