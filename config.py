"""
Configuration file for GSTR-2A Puller
IMPORTANT: Keep this file secure and never commit to version control with actual credentials!
"""

import os
from pathlib import Path
from datetime import datetime

# Import credentials from separate file
try:
    from credentials import API_KEY, API_SECRET
except ImportError:
    print("ERROR: credentials.py not found!")
    print("Please copy credentials_template.py to credentials.py and add your API keys")
    API_KEY = 'NOT_CONFIGURED'
    API_SECRET = 'NOT_CONFIGURED'

API_CREDENTIALS = {
    'API_KEY': os.environ.get('OCTA_API_KEY', API_KEY),
    'API_SECRET': os.environ.get('OCTA_API_SECRET', API_SECRET)
}

# API Endpoints
API_BASE_URL = 'https://app.octagst.com/api'
API_ENDPOINTS = {
    'PULL_GSTR2A': f'{API_BASE_URL}/gstr2a/pull',
    'EXPORT_GSTR2A': f'{API_BASE_URL}/gstr2a/export',
    'JOB_STATUS': f'{API_BASE_URL}/robot/jobstatus'
}

# GST Report Types Configuration
GST_REPORTS = {
    'GSTR-2A': {
        'enabled': True,
        'pull_endpoint': f'{API_BASE_URL}/gstr2a/pull',
        'export_endpoint': f'{API_BASE_URL}/gstr2a/export',
        'supports_monthly': True,
        'supports_quarterly': True,
        'supports_yearly': True,
        'description': 'Auto-drafted supplies from registered suppliers'
    },
    'GSTR-2B': {
        'enabled': False,  # Set to True when API is released
        'pull_endpoint': f'{API_BASE_URL}/gstr2b/pull',
        'export_endpoint': f'{API_BASE_URL}/gstr2b/export',
        'supports_monthly': True,
        'supports_quarterly': True,
        'supports_yearly': True,
        'description': 'Auto-generated statement of input tax credit'
    },
    'IMS': {
        'enabled': False,  # Set to True when API is released
        'pull_endpoint': f'{API_BASE_URL}/ims/pull',
        'export_endpoint': f'{API_BASE_URL}/ims/export',
        'supports_monthly': True,
        'supports_quarterly': True,
        'supports_yearly': True,
        'description': 'Invoice Management System data'
    },
    'IMS-RECO': {
        'enabled': False,  # Set to True when API is released
        'pull_endpoint': f'{API_BASE_URL}/ims-reco/pull',
        'export_endpoint': f'{API_BASE_URL}/ims-reco/export',
        'supports_monthly': True,
        'supports_quarterly': True,
        'supports_yearly': True,
        'description': 'IMS Reconciliation reports'
    },
    'ANNUAL-REPORT': {
        'enabled': False,  # Set to True when API is released
        'pull_endpoint': f'{API_BASE_URL}/annual-report/pull',
        'export_endpoint': f'{API_BASE_URL}/annual-report/export',
        'supports_monthly': False,  # Annual report doesn't support monthly
        'supports_quarterly': False,  # Annual report doesn't support quarterly
        'supports_yearly': True,
        'description': 'Annual GST report'
    },
    'GSTR-2B-RECO': {
        'enabled': False,  # Set to True when API is released
        'pull_endpoint': f'{API_BASE_URL}/gstr2b-reco/pull',
        'export_endpoint': f'{API_BASE_URL}/gstr2b-reco/export',
        'supports_monthly': True,
        'supports_quarterly': True,
        'supports_yearly': True,
        'description': 'GSTR-2B Reconciliation reports'
    },
    'ITC-CLAIMS': {
        'enabled': False,  # Set to True when API is released
        'pull_endpoint': f'{API_BASE_URL}/itc-claims/pull',
        'export_endpoint': f'{API_BASE_URL}/itc-claims/export',
        'supports_monthly': True,
        'supports_quarterly': True,
        'supports_yearly': True,
        'description': 'Input Tax Credit claims data'
    },
    'GSTR-1': {
        'enabled': False,  # Set to True when API is released
        'pull_endpoint': f'{API_BASE_URL}/gstr1/pull',
        'export_endpoint': f'{API_BASE_URL}/gstr1/export',
        'supports_monthly': True,
        'supports_quarterly': True,
        'supports_yearly': True,
        'description': 'Outward supplies details'
    },
    'GSTR-3B': {
        'enabled': False,  # Set to True when API is released
        'pull_endpoint': f'{API_BASE_URL}/gstr3b/pull',
        'export_endpoint': f'{API_BASE_URL}/gstr3b/export',
        'supports_monthly': True,
        'supports_quarterly': False,  # Assuming 3B is monthly only
        'supports_yearly': True,
        'description': 'Summary return for outward and inward supplies'
    }
}

# Smart Retry Configuration
SMART_RETRY_ENABLED = True
RETRY_EXPONENTIAL_BASE = 2  # Exponential backoff base (2^attempt seconds)
RETRY_MAX_WAIT = 30  # Maximum wait time between retries in seconds

# Directory Configuration (MOVED UP - This must come BEFORE Export Configuration)
PROJECT_ROOT = Path(__file__).parent
INPUT_DIR = PROJECT_ROOT / 'input'
OUTPUT_DIR = PROJECT_ROOT / 'output'
LOG_DIR = PROJECT_ROOT / 'logs'

# Create directories if they don't exist
for dir_path in [INPUT_DIR, OUTPUT_DIR, LOG_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

# Export Configuration
EXPORT_STRATEGIES = {
    '1': {'name': 'full_range', 'description': 'One file per company for entire date range'},
    '2': {'name': 'financial_year', 'description': 'Separate files per financial year'},
    '3': {'name': 'quarterly', 'description': 'Separate files per quarter'},
    '4': {'name': 'monthly', 'description': 'Individual files per month'}
}

EXPORT_JOB_TIMEOUT = 300  # Maximum seconds to wait for export job (5 minutes)
EXPORT_CHECK_INTERVAL = 3  # Seconds between status checks
EXPORT_RETRY_TIMEOUT = 180  # Timeout for retry attempts (3 minutes)
EXPORT_BATCH_DELAY = 2  # Seconds between export batches
EXPORT_MAX_WAIT = 180  # Maximum seconds to wait for export completion

EXPORT_RETRY_FAILED = True
EXPORT_OUTPUT_DIR = OUTPUT_DIR / 'exports'
EXPORT_OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Logging Configuration
LOG_LEVEL = 'INFO'  # Options: DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# API Configuration
API_TIMEOUT = 30  # seconds

# Excel Configuration
EXCEL_SHEET_NAME = 'Companies'  # Sheet name to read from input Excel
OUTPUT_SHEET_NAME = 'GSTR2A_Pull_Results'

# Expected columns in input Excel
REQUIRED_COLUMNS = [
    'Company ID',
    'Company Name',
    'GSTIN'
]

# Optional columns that will be preserved if present
OPTIONAL_COLUMNS = [
    'Environment',
    'Description',
    'Registration'
]

# Rate Limiting
# API Timing Configuration (Different speeds for different operations)
PULL_DELAY_BETWEEN_CALLS = 1  # Wait 1 second between pull requests
PULL_RETRY_DELAY = 2  # If pull fails, wait 2 seconds before retry
API_RETRY_COUNT = 3  # Try 3 times if something fails
API_RETRY_DELAY = 2  # Generic retry delay (fallback)
DELAY_BETWEEN_CALLS = 1  # Keep for backward compatibility

# Validation Rules
GSTIN_PATTERN = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'

# Display Configuration
PROGRESS_BAR_WIDTH = 50
SHOW_DETAILED_LOGS = True

# Error Handling
CONTINUE_ON_ERROR = True  # If True, skip failed companies and continue
SKIP_NOT_CONNECTED_COMPANIES = True  # If True, skip all months for companies not connected via OTP
LOG_ERRORS_TO_FILE = True

# Date Configuration - Dynamic defaults based on previous month
def get_default_period():
    """Get previous month as default period"""
    today = datetime.now()
    if today.month == 1:
        # If current month is January, previous month is December of last year
        default_month = today.replace(year=today.year - 1, month=12, day=1)
    else:
        # Otherwise, just subtract one month
        default_month = today.replace(month=today.month - 1, day=1)
    return default_month.strftime('%Y-%m')

DEFAULT_START_PERIOD = get_default_period()  # Dynamic - previous month
DEFAULT_END_PERIOD = get_default_period()    # Same as start by default

# Output File Configuration
OUTPUT_FILE_PREFIX = 'gstr2a_pulls'
OUTPUT_TIMESTAMP_FORMAT = '%Y%m%d_%H%M%S'