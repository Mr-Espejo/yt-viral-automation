import os
import argparse
from .core.assets.video_asset import VideoAsset
from .core.combinations.combination_generator import CombinationGenerator

def scan_videos(video_dir: str) -> list[VideoAsset]:
    """Scans a directory for mp4 files and returns a list of VideoAssets."""
    assets = []
    # Supporting nested directories (like 'viral/')
    for root, _, files in os.walk(video_dir):
        for f in files:
            if f.lower().endswith('.mp4'):
                path = os.path.join(root, f)
                assets.append(VideoAsset(
                    id=f.split('.')[0], # Simple id from filename
                    filename=f,
                    path=path
                ))
    return assets

def run():
    parser = argparse.ArgumentParser(description="Video Combination Generator Phase")
    parser.add_argument("--input", type=str, default="storage/videos/normalized", help="Directory with source videos")
    parser.add_argument("--output", type=str, default="storage/metadata/video_combinations.json", help="Output JSON path")
    
    args = parser.parse_args()
    
    workspace_root = os.getcwd()
    
    # Use relative paths from CWD if not absolute
    input_dir = args.input if os.path.isabs(args.input) else os.path.join(workspace_root, args.input)
    output_path = args.output if os.path.isabs(args.output) else os.path.join(workspace_root, args.output)
    
    print(f"Scanning videos in: {input_dir}")
    video_assets = scan_videos(input_dir)
    
    if not video_assets:
        print(f"Error: No videos found in {input_dir}")
        return

    print(f"Found {len(video_assets)} videos. Generating combinations...")
    
    try:
        generator = CombinationGenerator(video_assets)
        combos = generator.generate()
        generator.save_to_json(combos, output_path)
        print("Done.")
    except Exception as e:
        print(f"Failed to generate combinations: {e}")

if __name__ == "__main__":
    run()
