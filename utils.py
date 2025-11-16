"""
Utility functions for GSTR-2A Puller
Helper functions for date handling, file operations, and user interaction
"""

import os
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import tkinter as tk
from tkinter import filedialog
from config import (
    LOG_DIR, LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT,
    OUTPUT_FILE_PREFIX, OUTPUT_TIMESTAMP_FORMAT,
    GSTIN_PATTERN, API_CREDENTIALS
)


def setup_logging() -> logging.Logger:
    """
    Setup logging configuration
    
    Returns:
        Logger instance
    """
    # Create log filename with timestamp
    log_filename = LOG_DIR / f"gstr2a_puller_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure logging with UTF-8 encoding
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),  # Add encoding='utf-8'
            logging.StreamHandler()  # Console output
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_filename}")
    
    return logger


def generate_month_range(start_period: str, end_period: str) -> List[str]:
    """
    Generate a list of months between start and end periods
    
    Args:
        start_period: Start month in YYYY-MM format
        end_period: End month in YYYY-MM format
        
    Returns:
        List of months in YYYY-MM format
    """
    try:
        start_date = datetime.strptime(start_period, '%Y-%m')
        end_date = datetime.strptime(end_period, '%Y-%m')
        
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        
        months = []
        current_date = start_date
        
        while current_date <= end_date:
            months.append(current_date.strftime('%Y-%m'))
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return months
        
    except ValueError as e:
        raise ValueError(f"Invalid date format. Use YYYY-MM format: {e}")


def validate_period_format(period: str) -> bool:
    """
    Validate if period is in YYYY-MM format
    
    Args:
        period: Period string to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^\d{4}-(0[1-9]|1[0-2])$'
    return bool(re.match(pattern, period))


def validate_gstin(gstin: str) -> bool:
    """
    Validate GSTIN format
    
    Args:
        gstin: GSTIN to validate
        
    Returns:
        True if valid, False otherwise
    """
    return bool(re.match(GSTIN_PATTERN, gstin.upper()))

def get_user_date_input() -> Tuple[str, str]:
    """
    Get date range input from user
    Defaults to previous month if no input provided
    
    Returns:
        Tuple of (start_period, end_period) in YYYY-MM format
    """
    logger = logging.getLogger(__name__)
    
    # Calculate default (previous month)
    today = datetime.now()
    if today.month == 1:
        # If current month is January, previous month is December of last year
        default_month = today.replace(year=today.year - 1, month=12, day=1)
    else:
        # Otherwise, just subtract one month
        default_month = today.replace(month=today.month - 1, day=1)
    
    default_period = default_month.strftime('%Y-%m')
    
    print("\n" + "="*50)
    print("DATE RANGE SELECTION")
    print("="*50)
    print("Enter the period range for GST data pull")
    print("Format: YYYY-MM (e.g., 2024-04)")
    print(f"Default: {default_period} (press Enter to use default)")
    print("-"*50)
    
    while True:
        try:
            # Get start period
            start_input = input(f"Enter START period (YYYY-MM) [Default: {default_period}]: ").strip()
            
            # Use default if no input
            if not start_input:
                start_period = default_period
                print(f"  Using default: {start_period}")
            else:
                if not validate_period_format(start_input):
                    print("X Invalid format! Please use YYYY-MM format (e.g., 2024-04)")
                    continue
                start_period = start_input
            
            # Get end period
            end_input = input(f"Enter END period (YYYY-MM) [Default: {start_period}]: ").strip()
            
            # Use start period as default for end period
            if not end_input:
                end_period = start_period
                print(f"  Using default: {end_period}")
            else:
                if not validate_period_format(end_input):
                    print("X Invalid format! Please use YYYY-MM format (e.g., 2024-12)")
                    continue
                end_period = end_input
            
            # Generate and show month list
            months = generate_month_range(start_period, end_period)
            print(f"\n✓ Will process {len(months)} months:")
            print(f"  From: {months[0]}")
            print(f"  To:   {months[-1]}")
            print(f"  Total months: {len(months)}")
            
            # Confirm
            confirm = input("\nProceed with these dates? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y', '']:  # Empty input also means yes
                logger.info(f"User selected period range: {start_period} to {end_period}")
                return start_period, end_period
            elif confirm in ['no', 'n']:
                print("Let's try again...\n")
                continue  # This will restart the loop
            else:
                print("Please enter 'yes' or 'no'")
                # Ask again for confirmation
                confirm = input("Proceed with these dates? (yes/no): ").strip().lower()
                if confirm in ['yes', 'y', '']:
                    logger.info(f"User selected period range: {start_period} to {end_period}")
                    return start_period, end_period
                else:
                    print("Let's try again...\n")
                    continue
            
        except KeyboardInterrupt:
            print("\n\nOperation cancelled.")
            raise
        except Exception as e:
            print(f"X Error: {e}")
            
def select_input_file(input_dir: Path) -> Optional[str]:
    """
    Let user select input Excel file
    
    Args:
        input_dir: Default directory to look for files
        
    Returns:
        Selected file path or None
    """
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*50)
    print("INPUT FILE SELECTION")
    print("="*50)
    
    # Check for Excel files in input directory
    excel_files = list(input_dir.glob("*.xlsx")) + list(input_dir.glob("*.xls"))
    
    if excel_files:
        print(f"Found {len(excel_files)} Excel file(s) in input folder:")
        print("-"*50)
        for i, file in enumerate(excel_files, 1):
            file_size = file.stat().st_size / 1024  # Size in KB
            modified_time = datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            print(f"  [{i}] {file.name}")
            print(f"      Size: {file_size:.1f} KB | Modified: {modified_time}")
        
        print(f"  [B] Browse for file in different location")
        print(f"  [Q] Quit")
        print("-"*50)
        
        while True:
            choice = input("Select file (enter number, B, or Q): ").strip().upper()
            
            if choice == 'Q':
                return None
            elif choice == 'B':
                break
            else:
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(excel_files):
                        selected_file = str(excel_files[index])
                        logger.info(f"User selected file from list: {selected_file}")
                        return selected_file
                    else:
                        print("❌ Invalid selection. Try again.")
                except ValueError:
                    print("❌ Please enter a number, B, or Q.")
    else:
        print("No Excel files found in input folder.")
        print("Please browse to select your file.")
    
    # Browse for file
    print("\n" + "🔍 OPENING FILE BROWSER...")
    print("=" * 50)
    print("⚠️  IMPORTANT: A file browser window is opening!")
    print("⚠️  It may appear BEHIND this window.")
    print("⚠️  Check your taskbar or ALT+TAB if you don't see it.")
    print("=" * 50)
    print("Waiting for file selection...\n")
    
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Force the dialog to appear on top
    root.lift()
    root.attributes('-topmost', True)
    
    file_path = filedialog.askopenfilename(
        title="Select Company Excel File",
        initialdir=input_dir,
        filetypes=[
            ("Excel files", "*.xlsx *.xls"),
            ("All files", "*.*")
        ]
    )
    
    # After dialog closes, restore normal window behavior
    root.attributes('-topmost', False)
    root.destroy()
    
    if file_path:
        print(f"✅ File selected: {Path(file_path).name}")
        logger.info(f"User selected file via browser: {file_path}")
        return file_path
    else:
        print("❌ No file selected.")
        logger.info("User cancelled file selection")
        return None


def create_output_filename(output_dir: Path) -> str:
    """
    Create output filename with timestamp
    
    Args:
        output_dir: Directory to save the file
        
    Returns:
        Full path to output file
    """
    timestamp = datetime.now().strftime(OUTPUT_TIMESTAMP_FORMAT)
    filename = f"{OUTPUT_FILE_PREFIX}_{timestamp}.xlsx"
    return str(output_dir / filename)


def validate_config() -> bool:
    """
    Validate configuration settings
    
    Returns:
        True if config is valid, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    # Check API credentials
    if not API_CREDENTIALS['API_KEY'] or API_CREDENTIALS['API_KEY'] == 'YOUR_API_KEY_HERE' or len(API_CREDENTIALS['API_KEY']) < 10:
        logger.error("API credentials not configured! Please update config.py")
        print("\n" + "="*50)
        print("❌ ERROR: API CREDENTIALS NOT CONFIGURED")
        print("="*50)
        print("Please update config.py with your OCTA GST API credentials:")
        print("  1. Open config.py")
        print("  2. Replace 'YOUR_API_KEY_HERE' with your actual API key")
        print("  3. Replace 'YOUR_API_SECRET_HERE' with your actual API secret")
        print("="*50)
        return False
    
    # Check directories exist
    from config import INPUT_DIR, OUTPUT_DIR, LOG_DIR
    for dir_path, dir_name in [(INPUT_DIR, 'input'), (OUTPUT_DIR, 'output'), (LOG_DIR, 'logs')]:
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created {dir_name} directory: {dir_path}")
            except Exception as e:
                logger.error(f"Could not create {dir_name} directory: {e}")
                return False
    
    return True


def format_progress_bar(current: int, total: int, width: int = 50) -> str:
    """
    Create a text progress bar
    
    Args:
        current: Current progress
        total: Total items
        width: Width of progress bar
        
    Returns:
        Formatted progress bar string
    """
    if total == 0:
        return "[" + "=" * width + "]"
    
    progress = current / total
    filled = int(width * progress)
    bar = "=" * filled + "-" * (width - filled)
    percentage = progress * 100
    
    return f"[{bar}] {percentage:.1f}% ({current}/{total})"


def format_time_remaining(start_time: datetime, current: int, total: int) -> str:
    """
    Estimate time remaining
    
    Args:
        start_time: When processing started
        current: Current progress
        total: Total items
        
    Returns:
        Formatted time remaining string
    """
    if current == 0:
        return "Calculating..."
    
    elapsed = (datetime.now() - start_time).total_seconds()
    rate = current / elapsed
    remaining_items = total - current
    
    if rate > 0:
        remaining_seconds = remaining_items / rate
        
        if remaining_seconds < 60:
            return f"{int(remaining_seconds)}s"
        elif remaining_seconds < 3600:
            return f"{int(remaining_seconds / 60)}m {int(remaining_seconds % 60)}s"
        else:
            hours = int(remaining_seconds / 3600)
            minutes = int((remaining_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    return "Unknown"


def clean_company_id(company_id: str) -> str:
    """
    Clean and format company ID
    
    Args:
        company_id: Raw company ID
        
    Returns:
        Cleaned company ID with 'oc-' prefix
    """
    # Remove any whitespace
    company_id = str(company_id).strip()
    
    # Remove .0 if present (from Excel numeric conversion)
    company_id = company_id.replace('.0', '')
    
    # Add 'oc-' prefix if not present
    if not company_id.startswith('oc-'):
        company_id = f'oc-{company_id}'
    
    return company_id

def get_export_strategy() -> str:
    """Get export strategy from user"""
    from config import EXPORT_STRATEGIES
    
    print("\n" + "="*50)
    print("EXPORT STRATEGY SELECTION")
    print("="*50)
    print("How would you like to export the GSTR-2A data?")
    print("-"*50)
    
    for key, strategy in EXPORT_STRATEGIES.items():
        print(f"  [{key}] {strategy['description']}")
    
    print("-"*50)
    
    while True:
        choice = input("Select strategy (1-4): ").strip()
        if choice in EXPORT_STRATEGIES:
            selected = EXPORT_STRATEGIES[choice]['name']
            print(f"✓ Selected: {EXPORT_STRATEGIES[choice]['description']}")
            return selected
        else:
            print("❌ Invalid choice. Please enter 1, 2, 3, or 4")


def prepare_export_batches(pull_results_df, strategy='full_range'):
    """Prepare export batches based on strategy"""
    export_batches = []
    
    # Only process successful pulls
    successful_pulls = pull_results_df[pull_results_df['Status'] == 'Success'].copy()
    
    if strategy == 'full_range':
        # Group by company
        for (company_id, company_name, gstin), group in successful_pulls.groupby(['Company ID', 'Company Name', 'GSTIN']):
            periods = sorted(group['Return Period'].unique())
            if len(periods) > 0:
                export_batches.append({
                    'company_id': company_id,
                    'company_name': company_name,
                    'gstin': gstin,
                    'start_period': periods[0],
                    'end_period': periods[-1],
                    'periods': periods
                })
    
    elif strategy == 'monthly':
        # Each month separately
        for _, row in successful_pulls.iterrows():
            export_batches.append({
                'company_id': row['Company ID'],
                'company_name': row['Company Name'],
                'gstin': row['GSTIN'],
                'start_period': row['Return Period'],
                'end_period': row['Return Period'],
                'periods': [row['Return Period']]
            })
    
    # Add yearly and quarterly logic here when needed
    
    return export_batches


def ask_export_now() -> bool:
    """Ask user if they want to export now"""
    print("\n" + "="*50)
    print("EXPORT OPTION")
    print("="*50)
    
    while True:
        choice = input("Do you want to export GSTR-2A data now? (yes/no): ").strip().lower()
        if choice in ['yes', 'y']:
            return True
        elif choice in ['no', 'n']:
            print("✓ Pull results saved. You can run export later using the saved results.")
            return False
        else:
            print("Please enter 'yes' or 'no'")

def get_report_type() -> int:
    """
    Get report type choice from user
    
    Returns:
        Report type code (100 or 101)
    """
    print("\n" + "="*50)
    print("REPORT TYPE SELECTION")
    print("="*50)
    print("Select the type of GSTR-2A report to export:")
    print("-"*50)
    print("  [1] Full Report (Type 100)")
    print("      Complete detailed report with all data")
    print("  [2] Smart Report (Type 101)")  
    print("      Optimized report with essential information")
    print("-"*50)
    
    while True:
        choice = input("Select report type (1 or 2): ").strip()
        
        if choice == '1':
            print("✔ Selected: Full Report (Type 100)")
            return 100
        elif choice == '2':
            print("✔ Selected: Smart Report (Type 101)")
            return 101
        else:
            print("❌ Invalid choice. Please enter 1 or 2")
            
def process_export_batch(batch, api_client, report_format, logger, report_type_name='GSTR-2A', export_dir=None):
    """
    Common function to process a single export batch
    Returns: tuple of (result dict, success bool)
    """
    from config import EXPORT_MAX_WAIT, EXPORT_CHECK_INTERVAL, EXPORT_OUTPUT_DIR
    from datetime import datetime
    import time
    
    # Use provided export_dir or default
    if not export_dir:
        export_dir = EXPORT_OUTPUT_DIR
    
    result = {
        'Company': batch['company_name'],
        'GSTIN': batch['gstin'],
        'Period': f"{batch['start_period']} to {batch['end_period']}",
        'Report Type': report_format,
        'Timestamp': datetime.now()
    }
    
    try:
        # Create export job with report type name
        success, job_id, error = api_client.export_gst_report(
            report_type_name,  # Report type name (e.g., 'GSTR-2A')
            batch['company_id'],
            batch['gstin'],
            batch['start_period'],
            batch['end_period'],
            report_format  # Report format (100 or 101)
        )
        
        if not success:
            result.update({
                'Job ID': '',
                'Filename': '',
                'Status': 'Failed to Create Job',
                'Error': error
            })
            return result, False
        
        # Wait for job completion
        logger.info(f"  Export job created. Job ID: {job_id}")
        result['Job ID'] = job_id
        
        waited = 0
        while waited < EXPORT_MAX_WAIT:
            time.sleep(EXPORT_CHECK_INTERVAL)
            waited += EXPORT_CHECK_INTERVAL
            
            job_status = api_client.check_job_status(batch['company_id'], job_id)
            status = job_status.get('status', '').lower()
            
            if waited % 30 == 0 or status == 'completed':
                logger.info(f"    Job status after {waited}s: {status}")
            
            if status in ['completed', 'complete', 'success', 'successful']:
                # Download file - FIX: Use export_dir instead of EXPORT_OUTPUT_DIR
                dl_success, filepath, filename = api_client.download_export(
                    batch['company_id'], job_id, export_dir  # FIXED: Using export_dir parameter
                )
                
                if dl_success:
                    result.update({
                        'Filename': filename,
                        'Filepath': filepath,
                        'Status': 'Success'
                    })
                    return result, True
                else:
                    result.update({
                        'Filename': '',
                        'Status': 'Download Failed',
                        'Error': filename  # filename contains error message on failure
                    })
                    return result, False
                    
            elif status in ['failed', 'error', 'cancelled']:
                result.update({
                    'Filename': '',
                    'Status': 'Job Failed',
                    'Error': job_status.get('message', 'Job failed')
                })
                return result, False
        
        # Timeout
        result.update({
            'Filename': '',
            'Status': 'Timeout',
            'Error': f'Job did not complete within {EXPORT_MAX_WAIT} seconds'
        })
        return result, False
        
    except Exception as e:
        result.update({
            'Job ID': '',
            'Filename': '',
            'Status': 'Error',
            'Error': str(e)
        })
        return result, False
    
def get_enabled_reports() -> List[str]:
    """Get list of enabled GST reports"""
    from config import GST_REPORTS
    return [name for name, config in GST_REPORTS.items() if config['enabled']]

def select_report_types() -> List[str]:
    """
    Let user select which GST report types to process
    
    Returns:
        List of selected report types
    """
    from config import GST_REPORTS
    
    enabled_reports = get_enabled_reports()
    
    if not enabled_reports:
        print("No GST reports are currently enabled!")
        return []
    
    print("\n" + "="*50)
    print("GST REPORT TYPE SELECTION")
    print("="*50)
    print("Select GST report types to process:")
    print("-"*50)
    
    # Show enabled reports
    for i, report_name in enumerate(enabled_reports, 1):
        description = GST_REPORTS[report_name]['description']
        print(f"  [{i}] {report_name}")
        print(f"      {description}")
    
    print(f"  [A] All enabled reports")
    print("-"*50)
    
    while True:
        choice = input("Enter your choices (comma-separated numbers or 'A' for all): ").strip().upper()
        
        if choice == 'A':
            selected = enabled_reports
            print(f"✓ Selected all {len(selected)} report types")
            return selected
        
        try:
            # Parse comma-separated numbers
            indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected = []
            
            for idx in indices:
                if 0 <= idx < len(enabled_reports):
                    selected.append(enabled_reports[idx])
                else:
                    print(f"Invalid choice: {idx + 1}")
                    selected = []
                    break
            
            if selected:
                print(f"✓ Selected: {', '.join(selected)}")
                return selected
            else:
                print("Please try again with valid numbers")
                
        except ValueError:
            print("Invalid input. Use numbers separated by commas or 'A' for all")

def get_export_location() -> Path:
    """
    Get export location from user
    
    Returns:
        Path object for export directory
    """
    from config import EXPORT_OUTPUT_DIR
    import tkinter as tk
    from tkinter import filedialog
    
    print("\n" + "="*50)
    print("EXPORT LOCATION")
    print("="*50)
    print(f"Default location: {EXPORT_OUTPUT_DIR}")
    print("-"*50)
    print("  [1] Use default location")
    print("  [2] Select custom folder")
    print("  [3] Enter custom path")
    print("-"*50)
    
    while True:
        choice = input("Select option (1-3): ").strip()
        
        if choice == '1':
            return EXPORT_OUTPUT_DIR
        
        elif choice == '2':
            print("\n" + "📁 OPENING FOLDER BROWSER...")
            print("=" * 50)
            print("⚠️  IMPORTANT: A folder browser window is opening!")
            print("⚠️  It may appear BEHIND this window.")
            print("⚠️  Check your taskbar or ALT+TAB if you don't see it.")
            print("=" * 50)
            print("Waiting for folder selection...\n")
            
            root = tk.Tk()
            root.withdraw()
            
            # Force the dialog to appear on top
            root.lift()
            root.attributes('-topmost', True)
            
            folder_path = filedialog.askdirectory(
                title="Select Export Folder",
                initialdir=EXPORT_OUTPUT_DIR
            )
            
            # After dialog closes, restore normal window behavior
            root.attributes('-topmost', False)
            root.destroy()
            
            if folder_path:
                print(f"✅ Folder selected: {folder_path}")
                return Path(folder_path)
            else:
                print("❌ No folder selected. Using default.")
                return EXPORT_OUTPUT_DIR
        
        elif choice == '3':
            custom_path = input("Enter folder path: ").strip()
            
            if custom_path:
                path = Path(custom_path)
                
                # Create if doesn't exist
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    print(f"✓ Using custom path: {path}")
                    return path
                except Exception as e:
                    print(f"Error creating directory: {e}")
                    print("Using default location.")
                    return EXPORT_OUTPUT_DIR
            else:
                return EXPORT_OUTPUT_DIR
        
        else:
            print("Invalid choice. Please select 1, 2, or 3.")

def create_export_structure(base_dir: Path, report_types: List[str]) -> Dict[str, Path]:
    """
    Create timestamped export folder structure
    
    Args:
        base_dir: Base export directory
        report_types: List of report types to create folders for
        
    Returns:
        Dictionary mapping report types to their export paths
    """
    from datetime import datetime
    
    # Create timestamp folder
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_session_dir = base_dir / f"export_{timestamp}"
    export_session_dir.mkdir(parents=True, exist_ok=True)
    
    # Create report type folders
    report_paths = {}
    for report_type in report_types:
        report_dir = export_session_dir / report_type
        report_dir.mkdir(parents=True, exist_ok=True)
        report_paths[report_type] = report_dir
    
    # Store session directory for summary
    report_paths['_session_dir'] = export_session_dir
    
    return report_paths

def save_operation_summary(session_dir: Path, operations: List[Dict], report_type: str = "Multi-Report"):
    """
    Save operation summary in both JSON and Excel formats
    
    Args:
        session_dir: Session directory path
        operations: List of operation results
        report_type: Type of report being processed
    """
    import json
    import pandas as pd
    from datetime import datetime
    
    # Prepare summary data
    summary = {
        'session_timestamp': datetime.now().isoformat(),
        'report_type': report_type,
        'total_operations': len(operations),
        'successful': len([op for op in operations if op.get('Status') == 'Success']),
        'failed': len([op for op in operations if op.get('Status') == 'Failed']),
        'skipped': len([op for op in operations if op.get('Status') == 'Skipped']),
        'operations': operations
    }
    
    # Save JSON
    json_file = session_dir / 'operation_summary.json'
    with open(json_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    # Save Excel
    excel_file = session_dir / 'operation_summary.xlsx'
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = {
            'Metric': ['Session Timestamp', 'Report Type', 'Total Operations', 
                      'Successful', 'Failed', 'Skipped', 'Success Rate'],
            'Value': [
                summary['session_timestamp'],
                summary['report_type'],
                summary['total_operations'],
                summary['successful'],
                summary['failed'],
                summary['skipped'],
                f"{(summary['successful']/summary['total_operations']*100):.1f}%" if summary['total_operations'] > 0 else "0%"
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Detailed operations sheet
        if operations:
            ops_df = pd.DataFrame(operations)
            ops_df.to_excel(writer, sheet_name='Detailed_Operations', index=False)
    
    print(f"✓ Operation summaries saved to {session_dir}")

def smart_retry_with_backoff(failed_operations: List[Dict], api_client, logger) -> List[Dict]:
    """
    Retry failed operations with exponential backoff
    
    Args:
        failed_operations: List of failed operation details
        api_client: API client instance
        logger: Logger instance
        
    Returns:
        List of retry results
    """
    from config import SMART_RETRY_ENABLED, RETRY_EXPONENTIAL_BASE, RETRY_MAX_WAIT
    import time
    
    if not SMART_RETRY_ENABLED or not failed_operations:
        return []
    
    logger.info(f"\n" + "="*50)
    logger.info(f"SMART RETRY: Retrying {len(failed_operations)} failed operations")
    logger.info("="*50)
    
    retry_results = []
    
    for i, operation in enumerate(failed_operations, 1):
        attempt = 1
        max_attempts = 3
        wait_time = RETRY_EXPONENTIAL_BASE
        
        while attempt <= max_attempts:
            logger.info(f"[{i}/{len(failed_operations)}] Retry attempt {attempt} for {operation['company_name']}")
            
            # Retry the operation based on type
            if operation['operation_type'] == 'pull':
                success, job_id, error = api_client.pull_gst_report(
                    operation['report_type'],
                    operation['company_id'],
                    operation['gstin'],
                    operation['return_period']
                )
            else:  # export
                success, job_id, error = api_client.export_gst_report(
                    operation['report_type'],
                    operation['company_id'],
                    operation['gstin'],
                    operation['start_period'],
                    operation['end_period'],
                    operation.get('report_format', 101)
                )
            
            if success:
                logger.info(f"  ✓ Retry successful! Job ID: {job_id}")
                retry_results.append({
                    **operation,
                    'retry_status': 'Success',
                    'retry_attempts': attempt,
                    'job_id': job_id
                })
                break
            else:
                logger.warning(f"  ✗ Retry {attempt} failed: {error}")
                
                if attempt < max_attempts:
                    # Calculate wait time with exponential backoff
                    wait_time = min(RETRY_EXPONENTIAL_BASE ** attempt, RETRY_MAX_WAIT)
                    logger.info(f"  Waiting {wait_time} seconds before next retry...")
                    time.sleep(wait_time)
                else:
                    retry_results.append({
                        **operation,
                        'retry_status': 'Failed',
                        'retry_attempts': attempt,
                        'final_error': error
                    })
            
            attempt += 1
    
    return retry_results