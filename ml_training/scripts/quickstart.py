"""
Quick start script for ML training pipeline.

Runs the complete pipeline: data loading → EDA → preprocessing → model training
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import CSIDataLoader
from eda import CSIExplorer
from preprocessing import preprocess_dataset
from models.baseline_models import train_all_baseline_models
from config import print_config


def main():
    """Run complete ML pipeline."""
    print("\n" + "=" * 80)
    print(" " * 20 + "CSI LOCALIZATION - ML PIPELINE")
    print("=" * 80)
    
    # Show configuration
    print_config()
    
    # Ask user what to run
    print("\n" + "=" * 80)
    print("SELECT PIPELINE STAGES TO RUN:")
    print("=" * 80)
    print("\n1. Data Inspection")
    print("2. Exploratory Data Analysis (EDA)")
    print("3. Data Preprocessing")
    print("4. Train Baseline Models")
    print("5. Run All (1-4)")
    print("\n0. Exit")
    
    choice = input("\nEnter your choice (e.g., '1' or '1,2,3' or '5'): ").strip()
    
    if choice == '0':
        print("Exiting...")
        return
    
    # Parse choices
    if choice == '5':
        stages = [1, 2, 3, 4]
    else:
        try:
            stages = [int(x.strip()) for x in choice.split(',')]
        except:
            print("Invalid input!")
            return
    
    # Stage 1: Data Inspection
    if 1 in stages:
        print("\n" + "=" * 80)
        print("STAGE 1: DATA INSPECTION")
        print("=" * 80)
        loader = CSIDataLoader()
        loader.inspect_dataset()
        input("\nPress Enter to continue...")
    
    # Stage 2: EDA
    if 2 in stages:
        print("\n" + "=" * 80)
        print("STAGE 2: EXPLORATORY DATA ANALYSIS")
        print("=" * 80)
        explorer = CSIExplorer()
        explorer.run_full_eda()
        input("\nPress Enter to continue...")
    
    # Stage 3: Preprocessing
    X_train, y_train, X_val, y_val = None, None, None, None
    if 3 in stages:
        print("\n" + "=" * 80)
        print("STAGE 3: DATA PREPROCESSING")
        print("=" * 80)
        X_train, y_train, X_val, y_val, preprocessor = preprocess_dataset()
        input("\nPress Enter to continue...")
    
    # Stage 4: Model Training
    if 4 in stages:
        print("\n" + "=" * 80)
        print("STAGE 4: BASELINE MODEL TRAINING")
        print("=" * 80)
        
        # Load data if not already loaded
        if X_train is None:
            print("\nLoading pre-processed data...")
            from config import OUTPUT_DIR
            processed_dir = OUTPUT_DIR / "processed_data"
            
            if (processed_dir / "processed_train.npz").exists():
                train_data = np.load(processed_dir / "processed_train.npz")
                X_train, y_train = train_data['X'], train_data['y']
                
                if (processed_dir / "processed_val.npz").exists():
                    val_data = np.load(processed_dir / "processed_val.npz")
                    X_val, y_val = val_data['X'], val_data['y']
            else:
                print("Pre-processed data not found! Running preprocessing first...")
                X_train, y_train, X_val, y_val, _ = preprocess_dataset()
        
        # Train models
        results = train_all_baseline_models(X_train, y_train, X_val, y_val)
        
        # Show best model
        if results:
            best_model_name = min(results.items(), 
                                 key=lambda x: x[1]['val_metrics']['position_mae'] 
                                 if x[1]['val_metrics'] else float('inf'))[0]
            best_mae = results[best_model_name]['val_metrics']['position_mae']
            
            print("\n" + "=" * 80)
            print(f"🏆 BEST MODEL: {best_model_name.upper()}")
            print(f"   Validation MAE: {best_mae:.2f} meters")
            print("=" * 80)
    
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE! ✓")
    print("=" * 80)
    print("\nCheck the following directories for outputs:")
    print(f"  - Plots: ml_training/output/plots/")
    print(f"  - Models: ml_training/output/saved_models/")
    print(f"  - Results: ml_training/output/results/")
    print("\n")


if __name__ == "__main__":
    import numpy as np  # Import here for Stage 4
    main()
