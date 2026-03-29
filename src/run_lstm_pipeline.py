"""
Main orchestration script for the unified mental health LSTM pipeline.

Pipeline phases:
1. Data Preparation
   - Aggregate HRV sensor data to nightly level
   - Align sleep diary to survey assessment dates
   - Create unified nightly feature matrix
   - Prepare training labels

2. Model Training
   - Build and train LSTM model
   - Evaluate on test set
   - Save model and metrics

3. Analysis & Interpretation (optional in later phase)
   - Feature importance
   - Trajectory clustering
   - Clinical insights
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import aggregate_hrv, align_survey_dates, create_unified_features, prepare_labels
from src.models import mh_lstm_model

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_phase1_data_preparation():
    """Phase 1: Data preparation and feature engineering."""
    logger.info("\n" + "="*60)
    logger.info("PHASE 1: DATA PREPARATION")
    logger.info("="*60)
    
    try:
        # Step 1.1: Aggregate HRV
        logger.info("\n[1.1] Aggregating HRV to nightly level...")
        aggregated_hrv = aggregate_hrv.main()
        
        # Step 1.2: Align sleep to survey dates
        logger.info("\n[1.2] Aligning sleep to survey assessment dates...")
        aligned_sleep = align_survey_dates.main()
        
        # Step 1.3: Create unified features
        logger.info("\n[1.3] Creating unified nightly features...")
        unified_features = create_unified_features.main()
        
        # Step 1.4: Prepare labels
        logger.info("\n[1.4] Preparing training labels...")
        labels = prepare_labels.main()
        
        logger.info("\n✅ Phase 1 complete: All data prepared")
        return True
    
    except Exception as e:
        logger.error(f"❌ Phase 1 failed: {e}", exc_info=True)
        return False


def run_phase2_model_training():
    """Phase 2: Model training and evaluation."""
    logger.info("\n" + "="*60)
    logger.info("PHASE 2: MODEL TRAINING")
    logger.info("="*60)
    
    try:
        # Step 2.1: Train LSTM model
        logger.info("\n[2.1] Building and training LSTM model...")
        mh_lstm_model.main()
        
        logger.info("\n✅ Phase 2 complete: Model trained and evaluated")
        return True
    
    except Exception as e:
        logger.error(f"❌ Phase 2 failed: {e}", exc_info=True)
        return False


def main():
    """Run full pipeline."""
    logger.info("\n" + "="*60)
    logger.info("MENTAL HEALTH LSTM REGRESSION PIPELINE")
    logger.info("="*60)
    
    # Phase 1: Data Preparation
    phase1_success = run_phase1_data_preparation()
    if not phase1_success:
        logger.error("Pipeline aborted at Phase 1")
        return False
    
    # Phase 2: Model Training
    phase2_success = run_phase2_model_training()
    if not phase2_success:
        logger.error("Pipeline aborted at Phase 2")
        return False
    
    logger.info("\n" + "="*60)
    logger.info("✅ PIPELINE COMPLETE")
    logger.info("="*60)
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
