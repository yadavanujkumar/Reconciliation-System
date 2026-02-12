"""
Machine Learning Models for NeuroRecon
Includes Anomaly Detection using Isolation Forest
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler, LabelEncoder
import logging
from typing import Dict, List, Tuple
import joblib


class AnomalyDetector:
    """
    Anomaly Detection using Isolation Forest algorithm
    Identifies potential fraud vs. technical glitches in unmatched transactions
    """
    
    def __init__(self, config: dict):
        """
        Initialize the Anomaly Detector
        
        Args:
            config: Configuration dictionary with ML settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Get ML configuration
        ml_config = config.get('reconciliation', {}).get('ml_settings', {})
        if_config = ml_config.get('isolation_forest', {})
        
        # Initialize Isolation Forest
        self.model = IsolationForest(
            contamination=if_config.get('contamination', 0.1),
            n_estimators=if_config.get('n_estimators', 100),
            random_state=if_config.get('random_state', 42),
            n_jobs=-1
        )
        
        self.scaler = StandardScaler()
        self.anomaly_threshold = ml_config.get('anomaly_threshold', -0.5)
        self.is_fitted = False
        
        # Initialize label encoders for categorical features
        self.atm_encoder = LabelEncoder()
        self.location_encoder = LabelEncoder()
        self.encoders_fitted = False
        
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for anomaly detection
        
        Args:
            df: DataFrame with transaction data
            
        Returns:
            DataFrame with engineered features
        """
        features = pd.DataFrame()
        
        # Amount-based features
        if 'amount' in df.columns:
            features['amount'] = df['amount']
            features['amount_log'] = np.log1p(df['amount'].abs())
        
        # Time-based features
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            features['hour'] = df['timestamp'].dt.hour
            features['day_of_week'] = df['timestamp'].dt.dayofweek
            features['is_weekend'] = (df['timestamp'].dt.dayofweek >= 5).astype(int)
            features['is_night'] = ((df['timestamp'].dt.hour >= 22) | 
                                   (df['timestamp'].dt.hour <= 6)).astype(int)
        
        # Location-based features (if available)
        if 'atm_id' in df.columns:
            # Use deterministic label encoding instead of hash
            if not self.encoders_fitted:
                features['atm_encoded'] = self.atm_encoder.fit_transform(df['atm_id'].astype(str))
            else:
                # Handle unseen labels during prediction
                known_labels = set(self.atm_encoder.classes_)
                atm_values = df['atm_id'].astype(str).apply(
                    lambda x: x if x in known_labels else 'unknown'
                )
                features['atm_encoded'] = self.atm_encoder.transform(atm_values)
        
        if 'location' in df.columns:
            # Use deterministic label encoding instead of hash
            if not self.encoders_fitted:
                features['location_encoded'] = self.location_encoder.fit_transform(df['location'].astype(str))
            else:
                # Handle unseen labels during prediction
                known_labels = set(self.location_encoder.classes_)
                location_values = df['location'].astype(str).apply(
                    lambda x: x if x in known_labels else 'unknown'
                )
                features['location_encoded'] = self.location_encoder.transform(location_values)
        
        # Transaction type features (if available)
        if 'transaction_type' in df.columns:
            # One-hot encode transaction types
            type_dummies = pd.get_dummies(df['transaction_type'], prefix='type')
            features = pd.concat([features, type_dummies], axis=1)
        
        # Fill missing values
        features = features.fillna(0)
        
        return features
    
    def fit(self, df: pd.DataFrame) -> 'AnomalyDetector':
        """
        Fit the anomaly detection model on transaction data
        
        Args:
            df: DataFrame with transaction data
            
        Returns:
            Self
        """
        self.logger.info("Training Isolation Forest model...")
        
        # Prepare features
        features = self.prepare_features(df)
        
        if len(features) == 0:
            self.logger.warning("No features available for training")
            return self
        
        # Scale features
        features_scaled = self.scaler.fit_transform(features)
        
        # Fit model
        self.model.fit(features_scaled)
        self.is_fitted = True
        self.encoders_fitted = True
        
        self.logger.info(f"Model trained on {len(features)} samples with {features.shape[1]} features")
        
        return self
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Predict anomalies in transaction data
        
        Args:
            df: DataFrame with transaction data
            
        Returns:
            DataFrame with anomaly predictions and scores
        """
        if not self.is_fitted:
            self.logger.warning("Model not fitted. Fitting on provided data...")
            self.fit(df)
        
        # Prepare features
        features = self.prepare_features(df)
        
        if len(features) == 0:
            self.logger.warning("No features available for prediction")
            df['anomaly_score'] = 0
            df['is_anomaly'] = False
            df['anomaly_type'] = 'unknown'
            return df
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Predict anomaly scores (-1 for anomalies, 1 for normal)
        predictions = self.model.predict(features_scaled)
        scores = self.model.score_samples(features_scaled)
        
        # Add predictions to DataFrame
        result_df = df.copy()
        result_df['anomaly_score'] = scores
        result_df['is_anomaly'] = predictions == -1
        
        # Classify anomaly types
        result_df['anomaly_type'] = result_df.apply(
            lambda row: self._classify_anomaly_type(row), axis=1
        )
        
        # Log results
        anomaly_count = result_df['is_anomaly'].sum()
        self.logger.info(f"Detected {anomaly_count} anomalies out of {len(result_df)} transactions")
        
        return result_df
    
    def _classify_anomaly_type(self, row: pd.Series) -> str:
        """
        Classify the type of anomaly (fraud vs. technical glitch)
        
        Args:
            row: Transaction row
            
        Returns:
            Anomaly type classification
        """
        if not row.get('is_anomaly', False):
            return 'normal'
        
        # High amount anomalies are more likely fraud
        if 'amount' in row and row['amount'] > 10000:
            return 'potential_fraud'
        
        # Night-time transactions at unusual locations
        if 'is_night' in row and row.get('is_night', 0) == 1:
            return 'potential_fraud'
        
        # Otherwise, likely a technical glitch
        return 'technical_glitch'
    
    def get_anomaly_summary(self, df: pd.DataFrame) -> Dict:
        """
        Get summary statistics of anomaly detection results
        
        Args:
            df: DataFrame with anomaly predictions
            
        Returns:
            Dictionary with summary statistics
        """
        if 'is_anomaly' not in df.columns:
            return {}
        
        total = len(df)
        anomalies = df['is_anomaly'].sum()
        
        summary = {
            'total_transactions': total,
            'total_anomalies': int(anomalies),
            'anomaly_rate': float(anomalies / total) if total > 0 else 0.0,
        }
        
        # Count by anomaly type
        if 'anomaly_type' in df.columns:
            type_counts = df[df['is_anomaly']]['anomaly_type'].value_counts().to_dict()
            summary['anomalies_by_type'] = type_counts
        
        return summary
    
    def save_model(self, file_path: str):
        """
        Save the trained model to disk
        
        Args:
            file_path: Path to save the model
        """
        if not self.is_fitted:
            self.logger.warning("Cannot save unfitted model")
            return
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'config': self.config
        }
        
        joblib.dump(model_data, file_path)
        self.logger.info(f"Model saved to {file_path}")
    
    def load_model(self, file_path: str):
        """
        Load a trained model from disk
        
        Args:
            file_path: Path to load the model from
        """
        model_data = joblib.load(file_path)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.is_fitted = True
        
        self.logger.info(f"Model loaded from {file_path}")
