"""
Hybrid Reconciliation Engine for NeuroRecon
Combines Rule-Based Matching with AI/ML-based Anomaly Detection
"""

import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz
import logging
from datetime import timedelta
from typing import Dict, List, Tuple, Optional
from neurorecon.ml_models.anomaly_detection import AnomalyDetector


class ReconciliationEngine:
    """
    Hybrid Reconciliation Engine with two layers:
    - Layer 1: Deterministic rule-based matching
    - Layer 2: AI/ML-based probabilistic matching and anomaly detection
    """
    
    def __init__(self, config: dict):
        """
        Initialize the Reconciliation Engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize anomaly detector
        self.anomaly_detector = AnomalyDetector(config)
        
        # Get configuration parameters
        recon_config = config.get('reconciliation', {})
        self.exact_match_fields = recon_config.get('exact_match_fields', ['transaction_id', 'amount'])
        
        fuzzy_config = recon_config.get('fuzzy_matching', {})
        self.fuzzy_enabled = fuzzy_config.get('enabled', True)
        self.timestamp_tolerance = fuzzy_config.get('timestamp_tolerance_seconds', 300)
        self.similarity_threshold = fuzzy_config.get('similarity_threshold', 85)
        
        # Results storage
        self.matched_transactions = pd.DataFrame()
        self.unmatched_switch = pd.DataFrame()
        self.unmatched_cbs = pd.DataFrame()
        self.fuzzy_matched = pd.DataFrame()
        self.reconciliation_summary = {}
    
    def reconcile(self, switch_df: pd.DataFrame, cbs_df: pd.DataFrame) -> Dict:
        """
        Main reconciliation method
        
        Args:
            switch_df: Switch logs DataFrame
            cbs_df: CBS ledgers DataFrame
            
        Returns:
            Dictionary with reconciliation results and statistics
        """
        self.logger.info("Starting reconciliation process...")
        self.logger.info(f"Switch records: {len(switch_df)}, CBS records: {len(cbs_df)}")
        
        # Layer 1: Exact matching (Rule-Based)
        self.logger.info("Layer 1: Performing exact rule-based matching...")
        matched, unmatched_switch, unmatched_cbs = self._exact_match(switch_df, cbs_df)
        
        self.matched_transactions = matched
        self.logger.info(f"Exact matches found: {len(matched)}")
        
        # Layer 2: Fuzzy matching for remaining records
        if self.fuzzy_enabled and len(unmatched_switch) > 0 and len(unmatched_cbs) > 0:
            self.logger.info("Layer 2: Performing fuzzy matching on unmatched records...")
            fuzzy_matched, unmatched_switch, unmatched_cbs = self._fuzzy_match(
                unmatched_switch, unmatched_cbs
            )
            self.fuzzy_matched = fuzzy_matched
            self.logger.info(f"Fuzzy matches found: {len(fuzzy_matched)}")
        
        # Store final unmatched records
        self.unmatched_switch = unmatched_switch
        self.unmatched_cbs = unmatched_cbs
        
        # Layer 3: AI/ML Anomaly Detection on unmatched records
        self.logger.info("Layer 3: Running anomaly detection on unmatched records...")
        self._detect_anomalies()
        
        # Generate summary
        self._generate_summary(len(switch_df), len(cbs_df))
        
        self.logger.info("Reconciliation completed successfully")
        return self.reconciliation_summary
    
    def _exact_match(
        self, 
        switch_df: pd.DataFrame, 
        cbs_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Perform exact matching based on configured fields
        
        Args:
            switch_df: Switch logs DataFrame
            cbs_df: CBS ledgers DataFrame
            
        Returns:
            Tuple of (matched, unmatched_switch, unmatched_cbs)
        """
        # Prepare dataframes with consistent columns
        switch_prep = switch_df.copy()
        cbs_prep = cbs_df.copy()
        
        # Create merge keys
        merge_keys = []
        for field in self.exact_match_fields:
            if field in switch_prep.columns and field in cbs_prep.columns:
                merge_keys.append(field)
        
        if not merge_keys:
            self.logger.warning("No common fields for exact matching")
            return pd.DataFrame(), switch_df, cbs_df
        
        # Perform inner join for matches
        matched = pd.merge(
            switch_prep,
            cbs_prep,
            on=merge_keys,
            how='inner',
            suffixes=('_switch', '_cbs')
        )
        
        # Find unmatched records
        matched_switch_ids = matched['transaction_id'] if 'transaction_id' in merge_keys else matched.index
        
        if 'transaction_id' in switch_prep.columns:
            unmatched_switch = switch_prep[~switch_prep['transaction_id'].isin(matched_switch_ids)]
            unmatched_cbs = cbs_prep[~cbs_prep['transaction_id'].isin(matched_switch_ids)]
        else:
            # Fallback to index-based filtering
            switch_matched_idx = matched.index if 'transaction_id' not in merge_keys else matched['transaction_id']
            unmatched_switch = switch_prep[~switch_prep.index.isin(switch_matched_idx)]
            unmatched_cbs = cbs_prep[~cbs_prep.index.isin(switch_matched_idx)]
        
        # Add match type
        matched['match_type'] = 'exact'
        
        return matched, unmatched_switch, unmatched_cbs
    
    def _fuzzy_match(
        self,
        switch_df: pd.DataFrame,
        cbs_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Perform fuzzy matching with timestamp tolerance and similarity scoring
        
        Args:
            switch_df: Unmatched switch records
            cbs_df: Unmatched CBS records
            
        Returns:
            Tuple of (fuzzy_matched, remaining_switch, remaining_cbs)
        """
        fuzzy_matches = []
        matched_switch_ids = set()
        matched_cbs_ids = set()
        
        for switch_idx, switch_row in switch_df.iterrows():
            best_match = None
            best_score = 0
            
            for cbs_idx, cbs_row in cbs_df.iterrows():
                # Skip already matched CBS records
                if cbs_idx in matched_cbs_ids:
                    continue
                
                # Calculate match score
                score = self._calculate_similarity_score(switch_row, cbs_row)
                
                if score >= self.similarity_threshold and score > best_score:
                    best_score = score
                    best_match = (cbs_idx, cbs_row, score)
            
            # If we found a good match, record it
            if best_match:
                cbs_idx, cbs_row, score = best_match
                
                # Create matched record
                match_record = {
                    **{f"{k}_switch": v for k, v in switch_row.items()},
                    **{f"{k}_cbs": v for k, v in cbs_row.items()},
                    'match_type': 'fuzzy',
                    'similarity_score': score
                }
                fuzzy_matches.append(match_record)
                
                matched_switch_ids.add(switch_idx)
                matched_cbs_ids.add(cbs_idx)
        
        # Create DataFrame from matches
        fuzzy_matched_df = pd.DataFrame(fuzzy_matches) if fuzzy_matches else pd.DataFrame()
        
        # Get remaining unmatched records
        remaining_switch = switch_df[~switch_df.index.isin(matched_switch_ids)]
        remaining_cbs = cbs_df[~cbs_df.index.isin(matched_cbs_ids)]
        
        return fuzzy_matched_df, remaining_switch, remaining_cbs
    
    def _calculate_similarity_score(self, switch_row: pd.Series, cbs_row: pd.Series) -> float:
        """
        Calculate similarity score between two transactions
        
        Args:
            switch_row: Switch transaction record
            cbs_row: CBS transaction record
            
        Returns:
            Similarity score (0-100)
        """
        score = 0
        components = 0
        
        # Amount similarity (exact match gets high score)
        if 'amount' in switch_row and 'amount' in cbs_row:
            amount_diff = abs(switch_row['amount'] - cbs_row['amount'])
            if amount_diff == 0:
                score += 40
            elif amount_diff < 1:  # Very close
                score += 30
            elif amount_diff < 10:  # Somewhat close
                score += 10
            components += 1
        
        # Timestamp proximity
        if 'timestamp' in switch_row and 'timestamp' in cbs_row:
            time_diff = abs((switch_row['timestamp'] - cbs_row['timestamp']).total_seconds())
            if time_diff <= self.timestamp_tolerance:
                # Score decreases as time difference increases
                time_score = 40 * (1 - time_diff / self.timestamp_tolerance)
                score += time_score
            components += 1
        
        # Transaction ID similarity (fuzzy string matching)
        if 'transaction_id' in switch_row and 'transaction_id' in cbs_row:
            id_similarity = fuzz.ratio(str(switch_row['transaction_id']), str(cbs_row['transaction_id']))
            score += (id_similarity * 0.2)  # Up to 20 points
            components += 1
        
        # Normalize score to 0-100 range
        if components > 0:
            return min(100, score)
        
        return 0
    
    def _detect_anomalies(self):
        """
        Run anomaly detection on unmatched records
        """
        # Combine all unmatched records for analysis
        all_unmatched = pd.concat([
            self.unmatched_switch.assign(unmatched_source='switch'),
            self.unmatched_cbs.assign(unmatched_source='cbs')
        ], ignore_index=True)
        
        if len(all_unmatched) == 0:
            self.logger.info("No unmatched records for anomaly detection")
            return
        
        # Train and predict anomalies
        all_unmatched_with_anomalies = self.anomaly_detector.predict(all_unmatched)
        
        # Split back into switch and CBS
        self.unmatched_switch = all_unmatched_with_anomalies[
            all_unmatched_with_anomalies['unmatched_source'] == 'switch'
        ].drop('unmatched_source', axis=1)
        
        self.unmatched_cbs = all_unmatched_with_anomalies[
            all_unmatched_with_anomalies['unmatched_source'] == 'cbs'
        ].drop('unmatched_source', axis=1)
        
        # Get anomaly summary
        anomaly_summary = self.anomaly_detector.get_anomaly_summary(all_unmatched_with_anomalies)
        self.logger.info(f"Anomaly detection summary: {anomaly_summary}")
    
    def _generate_summary(self, total_switch: int, total_cbs: int):
        """
        Generate reconciliation summary statistics
        
        Args:
            total_switch: Total switch records
            total_cbs: Total CBS records
        """
        exact_matches = len(self.matched_transactions)
        fuzzy_matches = len(self.fuzzy_matched)
        total_matches = exact_matches + fuzzy_matches
        
        unmatched_switch_count = len(self.unmatched_switch)
        unmatched_cbs_count = len(self.unmatched_cbs)
        
        # Calculate reconciliation rate
        recon_rate = (total_matches / max(total_switch, total_cbs)) * 100 if max(total_switch, total_cbs) > 0 else 0
        
        self.reconciliation_summary = {
            'total_switch_records': total_switch,
            'total_cbs_records': total_cbs,
            'exact_matches': exact_matches,
            'fuzzy_matches': fuzzy_matches,
            'total_matches': total_matches,
            'unmatched_switch': unmatched_switch_count,
            'unmatched_cbs': unmatched_cbs_count,
            'reconciliation_rate': round(recon_rate, 2),
        }
        
        # Add anomaly statistics if available
        if not self.unmatched_switch.empty and 'is_anomaly' in self.unmatched_switch.columns:
            anomalies_switch = self.unmatched_switch['is_anomaly'].sum()
            anomalies_cbs = self.unmatched_cbs['is_anomaly'].sum() if 'is_anomaly' in self.unmatched_cbs.columns else 0
            
            self.reconciliation_summary['anomalies_detected'] = int(anomalies_switch + anomalies_cbs)
    
    def get_results(self) -> Dict[str, pd.DataFrame]:
        """
        Get all reconciliation results
        
        Returns:
            Dictionary with all result DataFrames
        """
        return {
            'matched': self.matched_transactions,
            'fuzzy_matched': self.fuzzy_matched,
            'unmatched_switch': self.unmatched_switch,
            'unmatched_cbs': self.unmatched_cbs,
            'summary': self.reconciliation_summary
        }
    
    def export_results(self, output_path: str):
        """
        Export reconciliation results to CSV files
        
        Args:
            output_path: Directory path for output files
        """
        import os
        
        os.makedirs(output_path, exist_ok=True)
        
        # Export matched transactions
        if not self.matched_transactions.empty:
            self.matched_transactions.to_csv(
                f"{output_path}/matched_transactions.csv", index=False
            )
        
        # Export fuzzy matched
        if not self.fuzzy_matched.empty:
            self.fuzzy_matched.to_csv(
                f"{output_path}/fuzzy_matched_transactions.csv", index=False
            )
        
        # Export unmatched with anomaly flags
        if not self.unmatched_switch.empty:
            self.unmatched_switch.to_csv(
                f"{output_path}/unmatched_switch.csv", index=False
            )
        
        if not self.unmatched_cbs.empty:
            self.unmatched_cbs.to_csv(
                f"{output_path}/unmatched_cbs.csv", index=False
            )
        
        # Export summary
        import json
        with open(f"{output_path}/reconciliation_summary.json", 'w') as f:
            json.dump(self.reconciliation_summary, f, indent=2)
        
        self.logger.info(f"Results exported to {output_path}")
