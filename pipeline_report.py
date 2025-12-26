"""
YouTube Viral Automation - Pipeline Status Report
Utility to visualize the overall progress of the automation.
"""

import json
import pandas as pd
from pathlib import Path

def generate_report():
    print("="*60)
    print("      YOUTUBE VIRAL AUTOMATION - STATUS REPORT")
    print("="*60)
    
    storage_root = Path("storage")
    metadata_path = storage_root / "metadata"
    videos_path = storage_root / "videos"
    performance_path = Path("data/performance")
    
    # 1. Mining Stats
    viral_csv = metadata_path / "viral_videos.csv"
    if viral_csv.exists():
        df = pd.read_csv(viral_csv)
        print(f"🔍 Mining Status:    {len(df)} viral videos identified.")
    else:
        print("🔍 Mining Status:    Not started.")

    # 2. Download Stats
    viral_videos_dir = videos_path / "viral"
    downloaded = list(viral_videos_dir.glob("*.mp4")) if viral_videos_dir.exists() else []
    print(f"📥 Download Status:  {len(downloaded)} raw videos downloaded.")

    # 3. Processing Stats
    norm_dir = videos_path / "normalized"
    normalized = list(norm_dir.glob("*.mp4")) if norm_dir.exists() else []
    print(f"⚙️  Processing:      {len(normalized)} videos normalized.")

    # 4. Optimization Stats
    opt_dir = videos_path / "optimized"
    optimized_dirs = [d for d in opt_dir.iterdir() if d.is_dir()] if opt_dir.exists() else []
    
    total_variants = 0
    if opt_dir.exists():
        for d in opt_dir.glob("*/*.mp4"):
            total_variants += 1
            
    print(f"🚀 Optimization:    {len(optimized_dirs)} videos fully optimized.")
    print(f"📦 Final Assets:    {total_variants} ready-to-upload variants.")

    # 5. Scoring & Upload Stats (Fase 9 & 10)
    scores_csv = Path("data/scoring/video_scores.csv")
    if scores_csv.exists():
        df_scores = pd.read_csv(scores_csv)
        print(f"📊 Scoring:         {len(df_scores)} variants scored and ranked.")
    
    log_csv = performance_path / "uploads_log.csv"
    if log_csv.exists():
        df_log = pd.read_csv(log_csv)
        print(f"📤 Upload Status:    {len(df_log)} videos published/scheduled.")
    else:
        print(f"📤 Upload Status:    No videos published yet.")

    print("="*60)
    print(f"Storage:            {storage_root.absolute()}")
    print(f"Performance Data:   {performance_path.absolute()}")
    print("="*60)

if __name__ == "__main__":
    generate_report()
