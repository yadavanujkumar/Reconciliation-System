"""
Reporting Module for NeuroRecon
Generates settlement files and predictive dashboards with forecasting
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import json


class ReportingModule:
    """
    Handles generation of settlement reports and predictive dashboards
    Includes ATM cash shortage forecasting using historical trends
    """
    
    def __init__(self, config: dict):
        """
        Initialize the Reporting Module
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Get reporting configuration
        report_config = config.get('reporting', {})
        self.settlement_file_name = report_config.get('settlement_file_name', 'settlement_report.csv')
        self.dashboard_file_name = report_config.get('dashboard_file_name', 'predictive_dashboard.html')
        
        forecast_config = report_config.get('forecasting', {})
        self.forecasting_enabled = forecast_config.get('enabled', True)
        self.forecast_days = forecast_config.get('forecast_days', 7)
        self.cash_threshold = forecast_config.get('atm_cash_threshold', 10000)
    
    def generate_settlement_file(
        self,
        matched_df: pd.DataFrame,
        fuzzy_matched_df: pd.DataFrame,
        unmatched_switch: pd.DataFrame,
        unmatched_cbs: pd.DataFrame,
        output_path: str
    ) -> str:
        """
        Generate a settlement file for the bank
        
        Args:
            matched_df: Matched transactions
            fuzzy_matched_df: Fuzzy matched transactions
            unmatched_switch: Unmatched switch records
            unmatched_cbs: Unmatched CBS records
            output_path: Output directory path
            
        Returns:
            Path to the generated settlement file
        """
        self.logger.info("Generating settlement file...")
        
        # Combine all matches
        all_matches = pd.concat([matched_df, fuzzy_matched_df], ignore_index=True)
        
        # Create settlement report
        settlement_records = []
        
        # Add matched transactions
        for _, row in all_matches.iterrows():
            record = {
                'transaction_id': self._get_value(row, 'transaction_id'),
                'timestamp': self._get_value(row, 'timestamp'),
                'amount': self._get_value(row, 'amount'),
                'status': 'MATCHED',
                'match_type': row.get('match_type', 'exact'),
                'notes': f"Matched with confidence: {row.get('similarity_score', 100):.2f}%"
            }
            settlement_records.append(record)
        
        # Add unmatched switch transactions
        for _, row in unmatched_switch.iterrows():
            record = {
                'transaction_id': row.get('transaction_id', 'N/A'),
                'timestamp': row.get('timestamp', 'N/A'),
                'amount': row.get('amount', 0),
                'status': 'UNMATCHED_SWITCH',
                'match_type': 'none',
                'notes': self._get_anomaly_notes(row)
            }
            settlement_records.append(record)
        
        # Add unmatched CBS transactions
        for _, row in unmatched_cbs.iterrows():
            record = {
                'transaction_id': row.get('transaction_id', 'N/A'),
                'timestamp': row.get('timestamp', 'N/A'),
                'amount': row.get('amount', 0),
                'status': 'UNMATCHED_CBS',
                'match_type': 'none',
                'notes': self._get_anomaly_notes(row)
            }
            settlement_records.append(record)
        
        # Create DataFrame and save
        settlement_df = pd.DataFrame(settlement_records)
        output_file = f"{output_path}/{self.settlement_file_name}"
        settlement_df.to_csv(output_file, index=False)
        
        self.logger.info(f"Settlement file generated: {output_file}")
        return output_file
    
    def generate_predictive_dashboard(
        self,
        transaction_data: pd.DataFrame,
        output_path: str
    ) -> str:
        """
        Generate a predictive dashboard with ATM cash shortage forecasts
        
        Args:
            transaction_data: Historical transaction data
            output_path: Output directory path
            
        Returns:
            Path to the generated dashboard file
        """
        self.logger.info("Generating predictive dashboard...")
        
        # Prepare data for forecasting
        if 'atm_id' not in transaction_data.columns:
            self.logger.warning("No ATM data available for forecasting")
            return self._generate_basic_dashboard(transaction_data, output_path)
        
        # Forecast ATM cash needs
        forecasts = self._forecast_atm_cash_needs(transaction_data)
        
        # Generate HTML dashboard
        html_content = self._generate_html_dashboard(transaction_data, forecasts)
        
        output_file = f"{output_path}/{self.dashboard_file_name}"
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Predictive dashboard generated: {output_file}")
        return output_file
    
    def _forecast_atm_cash_needs(self, transaction_data: pd.DataFrame) -> Dict:
        """
        Forecast ATM cash needs for the next week
        
        Args:
            transaction_data: Historical transaction data
            
        Returns:
            Dictionary with forecasts per ATM
        """
        if not self.forecasting_enabled:
            return {}
        
        forecasts = {}
        
        # Group by ATM
        if 'atm_id' in transaction_data.columns:
            atm_groups = transaction_data.groupby('atm_id')
            
            for atm_id, atm_data in atm_groups:
                # Simple forecasting using moving average
                forecast = self._simple_forecast(atm_data)
                forecasts[atm_id] = forecast
        
        return forecasts
    
    def _simple_forecast(self, atm_data: pd.DataFrame) -> Dict:
        """
        Simple forecasting using historical averages
        
        Args:
            atm_data: Historical data for a single ATM
            
        Returns:
            Forecast dictionary
        """
        if 'amount' not in atm_data.columns or len(atm_data) < 7:
            return {
                'predicted_daily_usage': 0,
                'predicted_weekly_usage': 0,
                'shortage_risk': 'low',
                'recommendation': self._get_recommendation('low')
            }
        
        # Calculate daily average
        atm_data['date'] = pd.to_datetime(atm_data['timestamp']).dt.date
        daily_totals = atm_data.groupby('date')['amount'].sum()
        
        # Simple moving average for next 7 days
        avg_daily_usage = daily_totals.mean()
        predicted_weekly_usage = avg_daily_usage * self.forecast_days
        
        # Determine shortage risk
        if predicted_weekly_usage > self.cash_threshold * 0.8:
            risk = 'high'
        elif predicted_weekly_usage > self.cash_threshold * 0.5:
            risk = 'medium'
        else:
            risk = 'low'
        
        return {
            'predicted_daily_usage': round(avg_daily_usage, 2),
            'predicted_weekly_usage': round(predicted_weekly_usage, 2),
            'shortage_risk': risk,
            'recommendation': self._get_recommendation(risk)
        }
    
    def _get_recommendation(self, risk: str) -> str:
        """Get recommendation based on risk level"""
        recommendations = {
            'high': 'Immediate cash replenishment recommended',
            'medium': 'Monitor closely, replenish within 2-3 days',
            'low': 'Normal operations, standard refill schedule'
        }
        return recommendations.get(risk, 'Monitor as needed')
    
    def _generate_html_dashboard(
        self,
        transaction_data: pd.DataFrame,
        forecasts: Dict
    ) -> str:
        """
        Generate HTML dashboard with visualizations
        
        Args:
            transaction_data: Historical transaction data
            forecasts: ATM forecasts
            
        Returns:
            HTML content string
        """
        # Calculate summary statistics
        total_transactions = len(transaction_data)
        total_amount = transaction_data['amount'].sum() if 'amount' in transaction_data.columns else 0
        avg_amount = transaction_data['amount'].mean() if 'amount' in transaction_data.columns else 0
        
        # Generate HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NeuroRecon Predictive Dashboard</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
        }}
        .summary-card {{
            background-color: white;
            padding: 20px;
            margin: 10px 0;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }}
        .metric-label {{
            font-size: 14px;
            color: #7f8c8d;
        }}
        .forecast-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .forecast-table th, .forecast-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .forecast-table th {{
            background-color: #34495e;
            color: white;
        }}
        .risk-high {{ color: #e74c3c; font-weight: bold; }}
        .risk-medium {{ color: #f39c12; font-weight: bold; }}
        .risk-low {{ color: #27ae60; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>NeuroRecon Predictive Dashboard</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary-card">
        <h2>Transaction Summary</h2>
        <div class="metric">
            <div class="metric-value">{total_transactions:,}</div>
            <div class="metric-label">Total Transactions</div>
        </div>
        <div class="metric">
            <div class="metric-value">${total_amount:,.2f}</div>
            <div class="metric-label">Total Amount</div>
        </div>
        <div class="metric">
            <div class="metric-value">${avg_amount:,.2f}</div>
            <div class="metric-label">Average Transaction</div>
        </div>
    </div>
    
    <div class="summary-card">
        <h2>ATM Cash Shortage Forecast (Next {self.forecast_days} Days)</h2>
        <table class="forecast-table">
            <thead>
                <tr>
                    <th>ATM ID</th>
                    <th>Predicted Daily Usage</th>
                    <th>Predicted Weekly Usage</th>
                    <th>Shortage Risk</th>
                    <th>Recommendation</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Add forecast rows
        if forecasts:
            for atm_id, forecast in forecasts.items():
                risk_class = f"risk-{forecast['shortage_risk']}"
                html += f"""
                <tr>
                    <td>{atm_id}</td>
                    <td>${forecast['predicted_daily_usage']:,.2f}</td>
                    <td>${forecast['predicted_weekly_usage']:,.2f}</td>
                    <td class="{risk_class}">{forecast['shortage_risk'].upper()}</td>
                    <td>{forecast['recommendation']}</td>
                </tr>
"""
        else:
            html += """
                <tr>
                    <td colspan="5" style="text-align: center;">No forecast data available</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        
        return html
    
    def _generate_basic_dashboard(self, transaction_data: pd.DataFrame, output_path: str) -> str:
        """Generate basic dashboard when ATM data is not available"""
        html = self._generate_html_dashboard(transaction_data, {})
        output_file = f"{output_path}/{self.dashboard_file_name}"
        with open(output_file, 'w') as f:
            f.write(html)
        return output_file
    
    def _get_value(self, row: pd.Series, key: str):
        """Get value from row, checking both switch and cbs suffixes"""
        if key in row:
            return row[key]
        if f"{key}_switch" in row:
            return row[f"{key}_switch"]
        if f"{key}_cbs" in row:
            return row[f"{key}_cbs"]
        return 'N/A'
    
    def _get_anomaly_notes(self, row: pd.Series) -> str:
        """Get anomaly notes for a transaction"""
        if 'is_anomaly' not in row or not row['is_anomaly']:
            return 'Standard unmatched transaction'
        
        anomaly_type = row.get('anomaly_type', 'unknown')
        return f"ALERT: Anomaly detected - {anomaly_type}"
