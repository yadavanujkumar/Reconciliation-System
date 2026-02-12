"""
NeuroRecon - AI-Enhanced Reconciliation System
Main Package Initialization
"""

__version__ = "1.0.0"
__author__ = "NeuroRecon Team"

from neurorecon.reconciliation.engine import ReconciliationEngine
from neurorecon.data_ingestion.ingestion import DataIngestionModule
from neurorecon.reporting.report_generator import ReportingModule

__all__ = [
    'ReconciliationEngine',
    'DataIngestionModule',
    'ReportingModule'
]
