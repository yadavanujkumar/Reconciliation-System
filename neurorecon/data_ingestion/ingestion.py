"""
Data Ingestion Module for NeuroRecon
Handles ingestion, cleaning, and standardization of transaction data from Switch and CBS sources
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Tuple, Optional
import re


class DataIngestionModule:
    """
    Handles data ingestion from multiple sources (Switch Logs and CBS Ledgers)
    Cleans and standardizes the data for reconciliation
    """
    
    def __init__(self, config: dict):
        """
        Initialize the Data Ingestion Module
        
        Args:
            config: Configuration dictionary with data paths and settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def ingest_switch_logs(self, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        Ingest and process Switch Log data
        
        Args:
            file_path: Path to the switch log file (CSV or JSON)
            
        Returns:
            Cleaned and standardized DataFrame
        """
        if file_path is None:
            file_path = self.config.get('data_ingestion', {}).get('switch_log_path')
        
        self.logger.info(f"Ingesting Switch Logs from: {file_path}")
        
        try:
            # Read file based on extension
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            # Clean and standardize
            df = self._clean_data(df, source='switch')
            df = self._standardize_timestamps(df)
            
            self.logger.info(f"Successfully ingested {len(df)} records from Switch Logs")
            return df
            
        except Exception as e:
            self.logger.error(f"Error ingesting Switch Logs: {str(e)}")
            raise
    
    def ingest_cbs_ledgers(self, file_path: Optional[str] = None) -> pd.DataFrame:
        """
        Ingest and process CBS Ledger data
        
        Args:
            file_path: Path to the CBS ledger file (CSV or JSON)
            
        Returns:
            Cleaned and standardized DataFrame
        """
        if file_path is None:
            file_path = self.config.get('data_ingestion', {}).get('cbs_ledger_path')
        
        self.logger.info(f"Ingesting CBS Ledgers from: {file_path}")
        
        try:
            # Read file based on extension
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            # Clean and standardize
            df = self._clean_data(df, source='cbs')
            df = self._standardize_timestamps(df)
            
            self.logger.info(f"Successfully ingested {len(df)} records from CBS Ledgers")
            return df
            
        except Exception as e:
            self.logger.error(f"Error ingesting CBS Ledgers: {str(e)}")
            raise
    
    def _clean_data(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """
        Clean raw data by handling missing values, duplicates, and invalid entries
        
        Args:
            df: Input DataFrame
            source: Data source ('switch' or 'cbs')
            
        Returns:
            Cleaned DataFrame
        """
        self.logger.info(f"Cleaning {source} data...")
        
        # Remove duplicates
        initial_count = len(df)
        df = df.drop_duplicates()
        dropped = initial_count - len(df)
        if dropped > 0:
            self.logger.warning(f"Dropped {dropped} duplicate records")
        
        # Standardize column names (lowercase, replace spaces with underscores)
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        
        # Ensure required columns exist
        required_cols = ['transaction_id', 'amount', 'timestamp']
        for col in required_cols:
            if col not in df.columns:
                self.logger.warning(f"Required column '{col}' not found in {source} data")
        
        # Handle missing values in critical columns
        if 'transaction_id' in df.columns:
            df = df.dropna(subset=['transaction_id'])
        
        if 'amount' in df.columns:
            # Convert amount to numeric, handling currency symbols
            df['amount'] = df['amount'].apply(self._parse_amount)
            df = df.dropna(subset=['amount'])
        
        # Add source identifier
        df['source'] = source
        
        return df
    
    def _parse_amount(self, value) -> Optional[float]:
        """
        Parse amount value, handling currency symbols and formats
        
        Args:
            value: Amount value (could be string or numeric)
            
        Returns:
            Parsed float value or None
        """
        if pd.isna(value):
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # Remove currency symbols and commas
        value_str = str(value).strip()
        value_str = re.sub(r'[^\d.-]', '', value_str)
        
        try:
            return float(value_str)
        except ValueError:
            return None
    
    def _standardize_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize timestamp formats across different sources
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with standardized timestamps
        """
        if 'timestamp' not in df.columns:
            return df
        
        self.logger.info("Standardizing timestamps...")
        
        # Convert to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Drop records with invalid timestamps
        invalid_count = df['timestamp'].isna().sum()
        if invalid_count > 0:
            self.logger.warning(f"Dropping {invalid_count} records with invalid timestamps")
            df = df.dropna(subset=['timestamp'])
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
    
    def ingest_both_sources(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Convenience method to ingest both Switch and CBS data
        
        Returns:
            Tuple of (switch_df, cbs_df)
        """
        switch_df = self.ingest_switch_logs()
        cbs_df = self.ingest_cbs_ledgers()
        
        return switch_df, cbs_df
