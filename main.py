"""
NeuroRecon - Main Application Entry Point
AI-Enhanced Automated Reconciliation System for ATM and POS Networks
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neurorecon.utils.helpers import load_config, setup_logging, ensure_directories
from neurorecon.data_ingestion.ingestion import DataIngestionModule
from neurorecon.reconciliation.engine import ReconciliationEngine
from neurorecon.reporting.report_generator import ReportingModule


def main():
    """Main application execution"""
    print("=" * 80)
    print("NeuroRecon - AI-Enhanced Reconciliation System")
    print("=" * 80)
    print()
    
    # Load configuration
    print("Loading configuration...")
    config = load_config('config.yaml')
    
    # Setup logging
    logger = setup_logging(config)
    logger.info("NeuroRecon started")
    
    # Ensure directories exist
    ensure_directories(config)
    
    try:
        # Step 1: Data Ingestion
        print("\n[1/4] Data Ingestion Phase")
        print("-" * 80)
        ingestion = DataIngestionModule(config)
        
        # Check if input files exist
        switch_path = config['data_ingestion']['switch_log_path']
        cbs_path = config['data_ingestion']['cbs_ledger_path']
        
        if not os.path.exists(switch_path) or not os.path.exists(cbs_path):
            logger.warning("Input files not found. Generating sample data...")
            generate_sample_data(switch_path, cbs_path)
        
        switch_df, cbs_df = ingestion.ingest_both_sources()
        print(f"✓ Ingested {len(switch_df)} Switch records and {len(cbs_df)} CBS records")
        
        # Step 2: Reconciliation
        print("\n[2/4] Reconciliation Phase")
        print("-" * 80)
        engine = ReconciliationEngine(config)
        summary = engine.reconcile(switch_df, cbs_df)
        
        print(f"✓ Reconciliation completed:")
        print(f"  - Exact matches: {summary['exact_matches']}")
        print(f"  - Fuzzy matches: {summary['fuzzy_matches']}")
        print(f"  - Unmatched Switch: {summary['unmatched_switch']}")
        print(f"  - Unmatched CBS: {summary['unmatched_cbs']}")
        print(f"  - Reconciliation rate: {summary['reconciliation_rate']}%")
        if 'anomalies_detected' in summary:
            print(f"  - Anomalies detected: {summary['anomalies_detected']}")
        
        # Step 3: Export Results
        print("\n[3/4] Exporting Results")
        print("-" * 80)
        output_path = config['data_ingestion']['output_path']
        engine.export_results(output_path)
        print(f"✓ Results exported to {output_path}")
        
        # Step 4: Generate Reports
        print("\n[4/4] Generating Reports")
        print("-" * 80)
        reporting = ReportingModule(config)
        
        results = engine.get_results()
        
        # Generate settlement file
        settlement_file = reporting.generate_settlement_file(
            results['matched'],
            results['fuzzy_matched'],
            results['unmatched_switch'],
            results['unmatched_cbs'],
            output_path
        )
        print(f"✓ Settlement file: {settlement_file}")
        
        # Generate predictive dashboard
        all_transactions = switch_df  # Use switch data for forecasting
        dashboard_file = reporting.generate_predictive_dashboard(
            all_transactions,
            output_path
        )
        print(f"✓ Predictive dashboard: {dashboard_file}")
        
        print("\n" + "=" * 80)
        print("NeuroRecon completed successfully!")
        print("=" * 80)
        logger.info("NeuroRecon completed successfully")
        
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


def generate_sample_data(switch_path: str, cbs_path: str):
    """Generate sample data for demonstration"""
    # Create directories
    os.makedirs(os.path.dirname(switch_path), exist_ok=True)
    
    # Generate sample switch logs
    np.random.seed(42)
    n_records = 100
    
    base_time = datetime.now() - timedelta(days=7)
    
    switch_data = {
        'transaction_id': [f"TXN{str(i).zfill(6)}" for i in range(1, n_records + 1)],
        'timestamp': [base_time + timedelta(hours=i * 2) for i in range(n_records)],
        'amount': np.random.uniform(20, 5000, n_records).round(2),
        'atm_id': [f"ATM{np.random.randint(1, 11):03d}" for _ in range(n_records)],
        'location': np.random.choice(['Downtown', 'Mall', 'Airport', 'Station'], n_records),
        'transaction_type': np.random.choice(['Withdrawal', 'Deposit', 'Balance'], n_records)
    }
    
    switch_df = pd.DataFrame(switch_data)
    switch_df.to_csv(switch_path, index=False)
    
    # Generate CBS ledgers (with 90% match rate)
    cbs_records = int(n_records * 0.9)
    
    # Convert switch data to lists and take first 90%
    cbs_data = {}
    for key in switch_data:
        if isinstance(switch_data[key], np.ndarray):
            cbs_data[key] = switch_data[key][:cbs_records].tolist()
        else:
            cbs_data[key] = list(switch_data[key][:cbs_records])
    
    # Add some slight timestamp variations for fuzzy matching
    for i in range(10, 20):
        if i < len(cbs_data['timestamp']):
            cbs_data['timestamp'][i] = cbs_data['timestamp'][i] + timedelta(minutes=np.random.randint(1, 10))
    
    # Add some unique CBS records
    for i in range(5):
        cbs_data['transaction_id'].append(f"CBS{str(i).zfill(6)}")
        cbs_data['timestamp'].append(base_time + timedelta(hours=np.random.randint(1, 100)))
        cbs_data['amount'].append(round(np.random.uniform(50, 3000), 2))
        cbs_data['atm_id'].append(f"ATM{np.random.randint(1, 11):03d}")
        cbs_data['location'].append(np.random.choice(['Downtown', 'Mall', 'Airport', 'Station']))
        cbs_data['transaction_type'].append(np.random.choice(['Withdrawal', 'Deposit', 'Balance']))
    
    cbs_df = pd.DataFrame(cbs_data)
    cbs_df.to_csv(cbs_path, index=False)
    
    print(f"✓ Generated sample data:")
    print(f"  - Switch logs: {switch_path} ({n_records} records)")
    print(f"  - CBS ledgers: {cbs_path} ({len(cbs_df)} records)")


if __name__ == "__main__":
    main()
