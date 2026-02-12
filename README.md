# NeuroRecon - AI-Enhanced Reconciliation System

**NeuroRecon** is an advanced, AI-powered automated reconciliation system designed for ATM and POS networks. It combines traditional rule-based matching with modern machine learning capabilities to efficiently reconcile Switch Logs against CBS (Core Banking System) Ledgers.

## 🚀 Features

### Core Capabilities

- **Hybrid Reconciliation Engine**: Two-layer approach combining deterministic and probabilistic matching
  - **Layer 1 (Rule-Based)**: Exact matching on Transaction ID and Amount
  - **Layer 2 (AI/ML-Based)**: Smart fuzzy matching with timestamp tolerance and anomaly detection

- **AI/ML-Powered Anomaly Detection**:
  - Isolation Forest algorithm for identifying unusual transactions
  - Distinguishes between potential fraud and technical glitches
  - Feature engineering for time-based, location-based, and transaction patterns

- **Smart Fuzzy Matching**:
  - Handles slight timestamp variances (configurable tolerance)
  - Uses similarity scoring to match transactions with minor discrepancies
  - Configurable similarity thresholds

- **Predictive Reporting**:
  - Settlement file generation for banking operations
  - Predictive dashboard with ATM cash shortage forecasting
  - Historical trend analysis for proactive cash management

## 📁 Project Structure

```
Reconciliation-System/
├── neurorecon/                     # Main application package
│   ├── __init__.py
│   ├── data_ingestion/            # Data ingestion and cleaning
│   │   ├── __init__.py
│   │   └── ingestion.py
│   ├── reconciliation/            # Core reconciliation engine
│   │   ├── __init__.py
│   │   └── engine.py
│   ├── ml_models/                 # Machine learning models
│   │   ├── __init__.py
│   │   └── anomaly_detection.py
│   ├── reporting/                 # Report generation
│   │   ├── __init__.py
│   │   └── report_generator.py
│   └── utils/                     # Utility functions
│       ├── __init__.py
│       └── helpers.py
├── data/                          # Data directories
│   ├── input/                     # Input data files (CSV/JSON)
│   └── output/                    # Output reports and results
├── tests/                         # Test suite
├── main.py                        # Main application entry point
├── config.yaml                    # Configuration file
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Docker configuration
├── .gitignore
└── README.md
```

## 🛠️ Technology Stack

- **Language**: Python 3.10+
- **Data Processing**: Pandas, NumPy
- **Machine Learning**: Scikit-Learn (Isolation Forest for anomaly detection)
- **Fuzzy Matching**: FuzzyWuzzy, python-Levenshtein
- **Containerization**: Docker
- **Configuration**: YAML
- **Logging**: Python logging module

## 📦 Installation

### Local Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yadavanujkumar/Reconciliation-System.git
   cd Reconciliation-System
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Docker Installation

1. **Build the Docker image**:
   ```bash
   docker build -t neurorecon:latest .
   ```

2. **Run the container**:
   ```bash
   docker run -v $(pwd)/data:/app/data neurorecon:latest
   ```

## 🚀 Usage

### Quick Start

1. **Prepare your data**: Place your Switch logs and CBS ledger files in the `data/input/` directory:
   - `data/input/switch_logs.csv`
   - `data/input/cbs_ledgers.csv`

2. **Configure the system**: Edit `config.yaml` to adjust settings:
   ```yaml
   data_ingestion:
     switch_log_path: "data/input/switch_logs.csv"
     cbs_ledger_path: "data/input/cbs_ledgers.csv"
   
   reconciliation:
     exact_match_fields:
       - "transaction_id"
       - "amount"
     fuzzy_matching:
       enabled: true
       timestamp_tolerance_seconds: 300
       similarity_threshold: 85
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

### Sample Data

If you don't have data files, NeuroRecon will automatically generate sample data for demonstration purposes.

### Output Files

After execution, you'll find the following files in `data/output/`:

- **matched_transactions.csv**: Successfully matched transactions
- **fuzzy_matched_transactions.csv**: Transactions matched via fuzzy logic
- **unmatched_switch.csv**: Unmatched Switch records with anomaly flags
- **unmatched_cbs.csv**: Unmatched CBS records with anomaly flags
- **reconciliation_summary.json**: Summary statistics
- **settlement_report.csv**: Settlement file for banking operations
- **predictive_dashboard.html**: Interactive dashboard with forecasts

## 🔧 Configuration

The `config.yaml` file allows you to customize:

### Data Ingestion
- Input file paths
- Output directory

### Reconciliation
- Exact match fields
- Fuzzy matching parameters (enabled/disabled, timestamp tolerance, similarity threshold)
- ML settings (Isolation Forest parameters, anomaly threshold)

### Reporting
- Settlement file naming
- Forecasting settings (enabled/disabled, forecast period, cash thresholds)

### Logging
- Log level (INFO, DEBUG, WARNING, ERROR)
- Log file location
- Log format

## 🧠 How It Works

### 1. Data Ingestion Module
- Reads CSV/JSON files from Switch and CBS sources
- Cleans data (removes duplicates, handles missing values)
- Standardizes timestamps and formats
- Normalizes column names and data types

### 2. Reconciliation Engine

**Layer 1 - Rule-Based Matching**:
- Performs exact matching on configured fields (transaction_id, amount)
- Fast and deterministic
- Identifies clear matches with 100% confidence

**Layer 2 - AI/ML-Based Matching**:
- **Fuzzy Matching**: Handles timestamp variations and minor discrepancies
  - Calculates similarity scores based on multiple factors
  - Considers timestamp proximity, amount similarity, and ID matching
  - Configurable thresholds for matching confidence

- **Anomaly Detection**: Uses Isolation Forest algorithm
  - Analyzes unmatched transactions for unusual patterns
  - Features: amount, time of day, day of week, location, transaction type
  - Classifies anomalies as potential fraud vs. technical glitches
  - Provides anomaly scores and classifications

### 3. Reporting Module
- **Settlement File**: Comprehensive report for banking operations
  - All matched transactions with confidence scores
  - Unmatched transactions with anomaly flags
  - Status and notes for each record

- **Predictive Dashboard**: HTML dashboard with forecasts
  - Transaction summaries and statistics
  - ATM cash shortage predictions (7-day forecast)
  - Risk assessment (high/medium/low)
  - Recommendations for cash replenishment

## 🧪 Testing

Run tests with pytest:
```bash
pytest tests/
```

With coverage:
```bash
pytest --cov=neurorecon tests/
```

## 🔒 Security

- No hardcoded credentials
- Environment-based configuration support
- Input validation and sanitization
- Anomaly detection for fraud prevention
- Docker isolation for secure deployment

## 📊 Example Output

```
================================================================================
NeuroRecon - AI-Enhanced Reconciliation System
================================================================================

Loading configuration...

[1/4] Data Ingestion Phase
--------------------------------------------------------------------------------
✓ Ingested 100 Switch records and 95 CBS records

[2/4] Reconciliation Phase
--------------------------------------------------------------------------------
✓ Reconciliation completed:
  - Exact matches: 85
  - Fuzzy matches: 8
  - Unmatched Switch: 7
  - Unmatched CBS: 2
  - Reconciliation rate: 93.00%
  - Anomalies detected: 3

[3/4] Exporting Results
--------------------------------------------------------------------------------
✓ Results exported to data/output/

[4/4] Generating Reports
--------------------------------------------------------------------------------
✓ Settlement file: data/output/settlement_report.csv
✓ Predictive dashboard: data/output/predictive_dashboard.html

================================================================================
NeuroRecon completed successfully!
================================================================================
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- NeuroRecon Team

## 🙏 Acknowledgments

- Inspired by Maximus TRACE
- Built for financial institutions requiring robust reconciliation solutions
- Leverages modern AI/ML capabilities for enhanced accuracy

## 📞 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**NeuroRecon** - Bringing AI to Financial Reconciliation 🧠💰