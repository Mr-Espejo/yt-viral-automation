import os
import argparse
from .engine import CompositionEngine

def main():
    parser = argparse.ArgumentParser(description="Multi-Source Vertical Video Builder")
    parser.add_argument("--config", type=str, default="composition_pipeline/composition.yaml", help="Path to composition.yaml")
    parser.add_argument("--combinations", type=str, help="Path to video_combinations.json to process all pairs")
    parser.add_argument("--output", type=str, default="composed_video.mp4", help="Output filename (ignored if --combinations is used)")
    
    args = parser.parse_args()
    
    workspace_root = os.getcwd()
    
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(workspace_root, config_path)
        
    print(f"Starting Composition Engine with config: {config_path}")
    
    engine = CompositionEngine(config_path, workspace_root)
    
    if args.combinations:
        engine.process_combinations(args.combinations)
    else:
        engine.run(args.output)
    
    print("Composition completed successfully.")

if __name__ == "__main__":
    main()
