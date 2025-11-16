"""
GSTR-2A Bulk Puller for OCTA GST
Main execution script with operation menu
Author: Your GST Automation System
"""

import os
import sys
import io
from datetime import datetime
from pathlib import Path

# Fix Unicode issues on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from excel_handler import ExcelHandler
from api_client import OctaGSTClient
from utils import (
    generate_month_range,
    setup_logging,
    get_user_date_input,
    select_input_file,
    create_output_filename,
    validate_config,
    ask_export_now,
    get_export_strategy,
    prepare_export_batches,
    get_report_type,
    process_export_batch,
    smart_retry_with_backoff,
    select_report_types,
    get_export_location,
    create_export_structure
)
from config import (
    API_CREDENTIALS, 
    OUTPUT_DIR, 
    INPUT_DIR, 
    SKIP_NOT_CONNECTED_COMPANIES,
    EXPORT_OUTPUT_DIR,
    EXPORT_RETRY_FAILED,
    EXPORT_JOB_TIMEOUT,
    EXPORT_CHECK_INTERVAL,
    EXPORT_MAX_WAIT,
    EXPORT_RETRY_TIMEOUT,
    PULL_DELAY_BETWEEN_CALLS
)
import logging
import time
import pandas as pd


def show_main_menu():
    """Display main menu and get user choice"""
    from config import GST_REPORTS
    
    enabled_count = sum(1 for r in GST_REPORTS.values() if r['enabled'])
    
    print("\n" + "="*50)
    print("GST BULK PULLER - MAIN MENU")
    print("="*50)
    print(f"Enabled Reports: {enabled_count} types available")
    print("Select an operation:")
    print("-"*50)
    print("  [1] Pull GST data only")
    print("  [2] Export previously pulled data")
    print("  [3] Pull and then Export")
    print("  [4] Direct Export (no pull required)")
    print("  [Q] Quit")
    print("-"*50)
    
    while True:
        choice = input("Enter your choice (1-4 or Q): ").strip().upper()
        if choice in ['1', '2', '3', '4', 'Q']:
            return choice
        else:
            print("[X] Invalid choice. Please enter 1, 2, 3, 4, or Q")

def run_pull_operation(logger, report_types=None):
    """Run the pull operation and return the output file path"""
    
    # Get report types if not provided
    if not report_types:
        report_types = select_report_types()
        if not report_types:
            logger.error("No report types selected!")
            return None
    
    logger.info(f"Selected report types: {', '.join(report_types)}")
    
    # Get date range from user
    start_period, end_period = get_user_date_input()
    months = generate_month_range(start_period, end_period)
    logger.info(f"Will process {len(months)} months: {months[0]} to {months[-1]}")
    
    # Select input file
    input_file = select_input_file(INPUT_DIR)
    if not input_file:
        logger.error("No input file selected!")
        return None
    
    logger.info(f"Using input file: {input_file}")
    
    # Initialize components
    excel_handler = ExcelHandler()
    api_client = OctaGSTClient(
        api_key=API_CREDENTIALS['API_KEY'],
        api_secret=API_CREDENTIALS['API_SECRET']
    )
    
    # Read companies from Excel
    try:
        companies = excel_handler.read_companies(input_file)
        logger.info(f"Found {len(companies)} companies to process")
    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        return None
    
    # Prepare results storage
    results = []
    failed_operations = []  # Move this outside the company loop
    total_operations = len(companies) * len(months) * len(report_types)
    current_operation = 0
    
    # Process each company and month combination
    logger.info("\n" + "="*50)
    logger.info("Starting GST Pull Operations")
    logger.info("="*50)
    
    for company in companies:
        company_id = company.get('Company ID', '')
        company_name = company.get('Company Name', 'Unknown')
        gstin = company.get('GSTIN', '')
        
        # Ensure company_id has 'oc-' prefix
        if company_id and not company_id.startswith('oc-'):
            company_id = f'oc-{company_id}'
        
        # Validate basic requirements
        if not company_id or not gstin:
            logger.warning(f"Skipping company {company_name}: Missing Company ID or GSTIN")
            for month in months:
                for report_type in report_types:
                    results.append({
                        'Report Type': report_type,
                        'Company ID': company_id or 'Missing',
                        'Company Name': company_name,
                        'GSTIN': gstin or 'Missing',
                        'Return Period': month,
                        'Job ID': '',
                        'Status': 'Skipped',
                        'Error Message': 'Missing Company ID or GSTIN',
                        'Timestamp': datetime.now()
                    })
            continue
        
        logger.info(f"\nProcessing Company: {company_name} ({company_id})")
        logger.info(f"GSTIN: {gstin}")
        
        # Track if company is not connected
        company_not_connected = False
        not_connected_error = None
        
        # Process each month for this company
        for month_index, month in enumerate(months):
            
            # If company is not connected, skip remaining months
            if company_not_connected:
                for report_type in report_types:
                    current_operation += 1
                    progress = f"[{current_operation}/{total_operations}]"
                    logger.info(f"{progress} Skipping {report_type} - {month} for {company_name} (Not connected to GST)")
                    
                    result = {
                        'Report Type': report_type,
                        'Company ID': company_id,
                        'Company Name': company_name,
                        'GSTIN': gstin,
                        'Return Period': month,
                        'Job ID': '',
                        'Status': 'Skipped',
                        'Error Message': not_connected_error,
                        'Timestamp': datetime.now()
                    }
                    results.append(result)
                continue
            
            # Process each report type for this month
            for report_type in report_types:
                current_operation += 1
                progress = f"[{current_operation}/{total_operations}]"
                
                logger.info(f"{progress} Pulling {report_type} - {month} for {company_name}...")
                
                # Make API call with new method
                success, job_id, error_msg = api_client.pull_gst_report(
                    report_type=report_type,
                    company_id=company_id,
                    gstin=gstin,
                    return_period=month
                )
                
                # Check if company is not connected to GST system
                if not success and error_msg and 'Not connected to GST System' in error_msg:
                    if SKIP_NOT_CONNECTED_COMPANIES:
                        company_not_connected = True
                        not_connected_error = error_msg
                        logger.warning(f"! Company not connected to GST system. Skipping remaining months.")
                    else:
                        logger.warning(f"! Company not connected, but continuing as per configuration.")
                
                # If failed, add to retry list
                if not success and not company_not_connected:
                    failed_operations.append({
                        'operation_type': 'pull',
                        'report_type': report_type,
                        'company_id': company_id,
                        'company_name': company_name,
                        'gstin': gstin,
                        'return_period': month,
                        'error': error_msg
                    })
                
                # Store result
                result = {
                    'Report Type': report_type,
                    'Company ID': company_id,
                    'Company Name': company_name,
                    'GSTIN': gstin,
                    'Return Period': month,
                    'Job ID': job_id if job_id else '',
                    'Status': 'Success' if success else ('Skipped' if company_not_connected else 'Failed'),
                    'Error Message': error_msg if error_msg else '-',
                    'Timestamp': datetime.now()
                }
                results.append(result)
                
                # Log result
                if success:
                    logger.info(f"  ✓ Success! Job ID: {job_id}")
                else:
                    logger.error(f"  ✗ Failed: {error_msg}")
                
                # Small delay between API calls
                if current_operation < total_operations and not company_not_connected:
                    time.sleep(PULL_DELAY_BETWEEN_CALLS)
    
    # After all operations, do smart retry
    if failed_operations:
        retry_results = smart_retry_with_backoff(failed_operations, api_client, logger)
        # Update results with retry outcomes
        for retry in retry_results:
            if retry['retry_status'] == 'Success':
                # Update the original failed result to success
                for r in results:
                    if (r.get('Report Type') == retry['report_type'] and
                        r['Company Name'] == retry['company_name'] and
                        r['Return Period'] == retry['return_period'] and
                        r['Status'] == 'Failed'):
                        r['Status'] = 'Success (After Retry)'
                        r['Job ID'] = retry['job_id']
                        break
    
    # Save results to Excel
    logger.info("\n" + "="*50)
    logger.info("Saving Results")
    logger.info("="*50)
    
    output_file = create_output_filename(OUTPUT_DIR)
    
    try:
        excel_handler.save_results(results, output_file)
        logger.info(f"/ Results saved to: {output_file}")
        
        # Summary statistics
        df = pd.DataFrame(results)
        success_count = len(df[df['Status'] == 'Success'])
        failed_count = len(df[df['Status'] == 'Failed'])
        skipped_count = len(df[df['Status'] == 'Skipped'])
        
        logger.info("\n" + "="*50)
        logger.info("PULL SUMMARY")
        logger.info("="*50)
        logger.info(f"Total Operations: {total_operations}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Skipped: {skipped_count}")
        logger.info(f"Success Rate: {(success_count/total_operations*100):.1f}%")
        
        return output_file
        
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        return None
def run_export_phase(pull_results_file, api_client, logger, export_paths=None):
    """Run the export phase with proper job status checking"""
    
    logger.info("\n" + "="*50)
    logger.info("Starting Export Phase")
    logger.info("="*50)
    
    # Get report type from user
    report_type = get_report_type()
    
    # Get export strategy
    strategy = get_export_strategy()
    
    # Read pull results
    pull_df = pd.read_excel(pull_results_file)
    
    # Detect which report type from the pull results
    report_type_name = 'GSTR-2A'  # Default
    if 'Report Type' in pull_df.columns:
        report_type_name = pull_df['Report Type'].iloc[0] if not pull_df.empty else 'GSTR-2A'
    
    # Prepare export batches
    export_batches = prepare_export_batches(pull_df, strategy)
    logger.info(f"Prepared {len(export_batches)} export batches")
    
    if len(export_batches) == 0:
        logger.warning("No export batches to process. Check if pull was successful.")
        return
    
    # Determine export directory
    if export_paths and report_type_name in export_paths:
        export_dir = export_paths[report_type_name]
    else:
        export_dir = EXPORT_OUTPUT_DIR
    
    # Track export results
    export_results = []
    failed_exports = []
    
    # Process each batch
    for i, batch in enumerate(export_batches, 1):
        logger.info(f"\n[{i}/{len(export_batches)}] Exporting {batch['company_name']}")
        logger.info(f"  Period: {batch['start_period']} to {batch['end_period']}")
        logger.info(f"  GSTIN: {batch['gstin']}")
        logger.info(f"  Report Type: {report_type}")
        
        # Use the common function (update process_export_batch to use export_dir)
        result, success = process_export_batch(batch, api_client, report_type, logger)
        export_results.append(result)
        
        if not success:
            failed_exports.append(batch)
        else:
            logger.info(f"  [SUCCESS] Downloaded: {result['Filename']}")
        
        # Small delay between exports
        if i < len(export_batches):
            time.sleep(2)
    
    # Retry failed exports once if configured
    if EXPORT_RETRY_FAILED and failed_exports:
        logger.info(f"\n" + "="*50)
        logger.info(f"Retrying {len(failed_exports)} failed exports...")
        logger.info("="*50)
        
        for i, batch in enumerate(failed_exports, 1):
            logger.info(f"\n[RETRY {i}/{len(failed_exports)}] {batch['company_name']}")
            
            try:
                # Retry creating export job with report type
                success, job_id, error = api_client.export_gst_report(
                    report_type_name,  # Add report type as first parameter
                    batch['company_id'],
                    batch['gstin'],
                    batch['start_period'],
                    batch['end_period'],
                    report_type
                )
                
                if success and job_id:
                    logger.info(f"  [SUCCESS] Retry job created. Job ID: {job_id}")
                    
                    # Shorter timeout for retry
                    max_wait = EXPORT_RETRY_TIMEOUT
                    check_interval = 10
                    waited = 0
                    
                    while waited < max_wait:
                        time.sleep(check_interval)
                        waited += check_interval
                        
                        job_status = api_client.check_job_status(batch['company_id'], job_id)
                        status = job_status.get('status', '').lower()
                        
                        if status in ['completed', 'complete', 'success', 'successful']:
                            # Try to download
                            dl_success, filepath, filename = api_client.download_export(
                                batch['company_id'],
                                job_id,
                                export_dir  # Use the determined export directory
                            )
                            
                            if dl_success:
                                logger.info(f"  [SUCCESS] Retry successful! Downloaded: {filename}")
                                # Update the original result
                                for r in export_results:
                                    if (r['Company'] == batch['company_name'] and 
                                        r['Period'] == f"{batch['start_period']} to {batch['end_period']}"):
                                        r['Status'] = 'Success (Retry)'
                                        r['Filename'] = filename
                                        r['Filepath'] = filepath
                                        r['Job ID'] = job_id
                                        break
                            break
                        
                        elif status in ['failed', 'error']:
                            logger.error(f"  [ERROR] Retry job failed")
                            break
                else:
                    logger.error(f"  [ERROR] Retry failed to create job: {error}")
                    
            except Exception as e:
                logger.error(f"  [ERROR] Retry error: {e}")
    
    # Save export tracking results
    if export_paths and '_session_dir' in export_paths:
        tracking_dir = export_paths['_session_dir']
    else:
        tracking_dir = EXPORT_OUTPUT_DIR
    
    export_tracking_file = tracking_dir / f"export_tracking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    # Create DataFrame and save
    tracking_df = pd.DataFrame(export_results)
    tracking_df.to_excel(export_tracking_file, index=False)
    logger.info(f"\n[SUCCESS] Export tracking saved to: {export_tracking_file}")
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("EXPORT SUMMARY")
    logger.info("="*50)
    successful = len([r for r in export_results if 'Success' in r.get('Status', '')])
    failed = len([r for r in export_results if 'Success' not in r.get('Status', '')])
    logger.info(f"Total Batches: {len(export_results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Report Type Used: {report_type}")
    
    if successful > 0:
        logger.info("\nSuccessfully exported files:")
        for r in export_results:
            if 'Success' in r.get('Status', ''):
                logger.info(f"  - {r.get('Filename', 'N/A')}")
    
    if failed > 0:
        logger.info("\nFailed exports:")
        for r in export_results:
            if 'Success' not in r.get('Status', ''):
                logger.info(f"  - {r['Company']}: {r['Status']} - {r.get('Error', '')}")
    
    # If export_paths provided, save operation summary
    if export_paths and '_session_dir' in export_paths:
        from utils import save_operation_summary
        save_operation_summary(export_paths['_session_dir'], export_results, report_type_name)
        
def select_previous_pull_results():
    """Select a previous pull results file for export"""
    print("\n" + "="*50)
    print("SELECT PULL RESULTS FILE")
    print("="*50)
    
    # Look for pull results files
    results_files = list(OUTPUT_DIR.glob("gstr2a_pulls_*.xlsx"))
    
    if not results_files:
        print("X No previous pull results found in output directory")
        return None
    
    # Sort by modification time (newest first)
    results_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    print(f"Found {len(results_files)} pull result file(s):")
    print("-"*50)
    
    for i, file in enumerate(results_files[:10], 1):  # Show only last 10
        file_size = file.stat().st_size / 1024  # Size in KB
        modified_time = datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
        print(f"  [{i}] {file.name}")
        print(f"      Size: {file_size:.1f} KB | Created: {modified_time}")
    
    print("-"*50)
    
    while True:
        choice = input("Select file number: ").strip()
        try:
            index = int(choice) - 1
            if 0 <= index < len(results_files):
                return str(results_files[index])
            else:
                print("X Invalid selection. Try again.")
        except ValueError:
            print("X Please enter a number.")

def run_direct_export(api_client, logger):
    """
    Run export directly without needing previous pull results
    User inputs company details manually
    """
    from config import EXPORT_CHECK_INTERVAL, EXPORT_MAX_WAIT, EXPORT_OUTPUT_DIR, EXPORT_BATCH_DELAY
    
    logger.info("\n" + "="*50)
    logger.info("DIRECT EXPORT (No Pull Required)")
    logger.info("="*50)
    
    # Get report type selection from user FIRST
    selected_report_types = select_report_types()
    if not selected_report_types:
        logger.error("No report types selected!")
        return
    
    # Use the first selected report type for export
    selected_report = selected_report_types[0]
    logger.info(f"Using report type: {selected_report}")
    
    # Get report format (100 or 101)
    report_format = get_report_type()
    
    # Get export details from user
    print("\nEnter export details:")
    print("-"*50)
    
    # Option to export single or multiple companies
    print("\nExport options:")
    print("  [1] Single company")
    print("  [2] Multiple companies from Excel")
    print("  [3] Manual entry (multiple companies)")
    
    choice = input("\nChoice (1-3): ").strip()
    
    export_batches = []
    
    if choice == '1':
        # Single company export
        company_id = input("Company ID (e.g., 3372): ").strip()
        company_name = input("Company Name: ").strip()
        gstin = input("GSTIN: ").strip()
        
        # Get period range
        print("\nPeriod range:")
        start_period = input("Start period (YYYY-MM): ").strip()
        end_period = input("End period (YYYY-MM): ").strip()
        
        # Ensure company_id has 'oc-' prefix
        if company_id and not company_id.startswith('oc-'):
            company_id = f'oc-{company_id}'
        
        export_batches.append({
            'company_id': company_id,
            'company_name': company_name,
            'gstin': gstin,
            'start_period': start_period,
            'end_period': end_period
        })
    
    elif choice == '2':
        # Multiple from Excel
        from excel_handler import ExcelHandler
        excel_handler = ExcelHandler()
        
        input_file = select_input_file(INPUT_DIR)
        if not input_file:
            logger.error("No input file selected!")
            return
        
        try:
            companies = excel_handler.read_companies(input_file)
            
            # Get period range for all
            print("\nPeriod range for all companies:")
            start_period = input("Start period (YYYY-MM): ").strip()
            end_period = input("End period (YYYY-MM): ").strip()
            
            for company in companies:
                company_id = company.get('Company ID', '')
                if company_id and not company_id.startswith('oc-'):
                    company_id = f'oc-{company_id}'
                
                export_batches.append({
                    'company_id': company_id,
                    'company_name': company.get('Company Name', 'Unknown'),
                    'gstin': company.get('GSTIN', ''),
                    'start_period': start_period,
                    'end_period': end_period
                })
        except Exception as e:
            logger.error(f"Failed to read input file: {e}")
            return
    
    elif choice == '3':
        # Manual entry of multiple companies
        print("\nEnter companies (type 'done' when finished):")
        
        # Get period range first
        print("\nPeriod range for all companies:")
        start_period = input("Start period (YYYY-MM): ").strip()
        end_period = input("End period (YYYY-MM): ").strip()
        
        count = 1
        while True:
            print(f"\nCompany {count}:")
            company_id = input("  Company ID (or 'done'): ").strip()
            
            if company_id.lower() == 'done':
                break
            
            company_name = input("  Company Name: ").strip()
            gstin = input("  GSTIN: ").strip()
            
            if company_id and not company_id.startswith('oc-'):
                company_id = f'oc-{company_id}'
            
            export_batches.append({
                'company_id': company_id,
                'company_name': company_name,
                'gstin': gstin,
                'start_period': start_period,
                'end_period': end_period
            })
            count += 1
    
    else:
        logger.error("Invalid choice")
        return
    
    if not export_batches:
        logger.warning("No companies to export")
        return
    
    # Get export strategy
    print("\n" + "="*50)
    print("EXPORT STRATEGY")
    print("="*50)
    print("How to group exports?")
    print("  [1] One file per company (entire range)")
    print("  [2] Separate files per month")
    print("  [3] Quarterly files")
    
    strategy = input("\nChoice (1-3): ").strip()
    
    # Adjust batches based on strategy
    if strategy == '2':
        # Split by month
        new_batches = []
        for batch in export_batches:
            months = generate_month_range(batch['start_period'], batch['end_period'])
            for month in months:
                new_batch = batch.copy()
                new_batch['start_period'] = month
                new_batch['end_period'] = month
                new_batches.append(new_batch)
        export_batches = new_batches
    
    elif strategy == '3':
        # Split by quarter - implement if needed
        pass
    
    logger.info(f"\nPrepared {len(export_batches)} export batches")
    logger.info(f"Using Report Type: {selected_report}")
    logger.info(f"Using Report Format: {report_format}")
    
    # Now process exports
    export_results = []
    failed_exports = []
    
    for i, batch in enumerate(export_batches, 1):
        logger.info(f"\n[{i}/{len(export_batches)}] Exporting {batch['company_name']}")
        logger.info(f"  Period: {batch['start_period']} to {batch['end_period']}")
        logger.info(f"  GSTIN: {batch['gstin']}")
        logger.info(f"  Report Type: {selected_report}")
        logger.info(f"  Report Format: {report_format}")
        
        try:
            # Create export job with selected report type
            success, job_id, error = api_client.export_gst_report(
                selected_report,  # USE THE SELECTED REPORT TYPE
                batch['company_id'],
                batch['gstin'],
                batch['start_period'],
                batch['end_period'],
                report_format
            )
                    
            if success and job_id:
                logger.info(f"  [SUCCESS] Export job created. Job ID: {job_id}")
                
                # Wait for job to complete
                max_wait = EXPORT_MAX_WAIT
                check_interval = EXPORT_CHECK_INTERVAL
                waited = 0
                job_completed = False
                
                logger.info(f"  Waiting for export job to complete (checking every {check_interval}s, max {max_wait}s)...")
                
                while waited < max_wait:
                    time.sleep(check_interval)
                    waited += check_interval
                    
                    # Check job status
                    job_status = api_client.check_job_status(batch['company_id'], job_id)
                    
                    status_code = job_status.get('jobStatus')
                    status = job_status.get('status', 'unknown')
                    
                    if waited % 30 == 0 or status == 'completed':  # Log every 30s or when done
                        logger.info(f"    Job status after {waited}s: {status} (code: {status_code})")
                    
                    # Check if completed
                    if status == 'completed' or status_code == 100:
                        logger.info(f"  [SUCCESS] Export job completed!")
                        job_completed = True
                        
                        # Download the file
                        logger.info(f"  Downloading export file...")
                        dl_success, filepath, filename = api_client.download_export(
                            batch['company_id'],
                            job_id,
                            EXPORT_OUTPUT_DIR
                        )
                        
                        if dl_success:
                            logger.info(f"  [SUCCESS] Downloaded: {filename}")
                            export_results.append({
                                'Company': batch['company_name'],
                                'GSTIN': batch['gstin'],
                                'Period': f"{batch['start_period']} to {batch['end_period']}",
                                'Job ID': job_id,
                                'Filename': filename,
                                'Filepath': filepath,
                                'Status': 'Success',
                                'Report Type': selected_report,
                                'Report Format': report_format,
                                'Timestamp': datetime.now()
                            })
                        else:
                            logger.error(f"  [ERROR] Download failed: {filename}")
                            failed_exports.append(batch)
                            export_results.append({
                                'Company': batch['company_name'],
                                'GSTIN': batch['gstin'],
                                'Period': f"{batch['start_period']} to {batch['end_period']}",
                                'Job ID': job_id,
                                'Filename': '',
                                'Status': 'Download Failed',
                                'Error': filename,
                                'Report Type': selected_report,
                                'Report Format': report_format,
                                'Timestamp': datetime.now()
                            })
                        break
                    
                    elif status in ['failed', 'error']:
                        logger.error(f"  [ERROR] Export job failed")
                        failed_exports.append(batch)
                        export_results.append({
                            'Company': batch['company_name'],
                            'GSTIN': batch['gstin'],
                            'Period': f"{batch['start_period']} to {batch['end_period']}",
                            'Job ID': job_id,
                            'Filename': '',
                            'Status': 'Job Failed',
                            'Error': job_status.get('message', 'Job failed'),
                            'Report Type': selected_report,
                            'Report Format': report_format,
                            'Timestamp': datetime.now()
                        })
                        break
                
                # Check if timed out
                if not job_completed and waited >= max_wait:
                    logger.error(f"  [ERROR] Export timeout after {max_wait} seconds")
                    failed_exports.append(batch)
                    export_results.append({
                        'Company': batch['company_name'],
                        'GSTIN': batch['gstin'],
                        'Period': f"{batch['start_period']} to {batch['end_period']}",
                        'Job ID': job_id,
                        'Filename': '',
                        'Status': 'Timeout',
                        'Error': f'Job did not complete within {max_wait} seconds',
                        'Report Type': selected_report,
                        'Report Format': report_format,
                        'Timestamp': datetime.now()
                    })
            
            else:
                logger.error(f"  [ERROR] Failed to create export job: {error}")
                failed_exports.append(batch)
                export_results.append({
                    'Company': batch['company_name'],
                    'GSTIN': batch['gstin'],
                    'Period': f"{batch['start_period']} to {batch['end_period']}",
                    'Job ID': '',
                    'Filename': '',
                    'Status': 'Failed to Create Job',
                    'Error': error,
                    'Report Type': selected_report,
                    'Report Format': report_format,
                    'Timestamp': datetime.now()
                })
        
        except Exception as e:
            logger.error(f"  [ERROR] Unexpected error: {e}")
            failed_exports.append(batch)
        
        # Delay between batches
        if i < len(export_batches):
            time.sleep(EXPORT_BATCH_DELAY)
    
    # Save export tracking
    if export_results:
        tracking_file = EXPORT_OUTPUT_DIR / f"direct_export_tracking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        tracking_df = pd.DataFrame(export_results)
        tracking_df.to_excel(tracking_file, index=False)
        logger.info(f"\n[SUCCESS] Export tracking saved to: {tracking_file}")
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("EXPORT SUMMARY")
    logger.info("="*50)
    successful = len([r for r in export_results if 'Success' in r.get('Status', '')])
    failed = len([r for r in export_results if 'Success' not in r.get('Status', '')])
    logger.info(f"Total Batches: {len(export_results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Report Type Used: {selected_report}")
    logger.info(f"Report Format Used: {report_format}")
    
    if successful > 0:
        logger.info("\nSuccessfully exported files:")
        for r in export_results:
            if 'Success' in r.get('Status', ''):
                logger.info(f"  - {r.get('Filename', 'N/A')}")
                
def main():
    """Main execution function with menu"""
    
    # Setup logging
    logger = setup_logging()
    logger.info("="*50)
    logger.info("GST Bulk Puller Started")
    logger.info("="*50)
    
    # Validate configuration
    if not validate_config():
        logger.error("Configuration validation failed! Check config.py")
        return
    
    # Show main menu
    choice = show_main_menu()
    
    if choice == 'Q':
        logger.info("User chose to quit")
        print("Goodbye!")
        return
    
    # Initialize API client (needed for all operations)
    api_client = OctaGSTClient(
        api_key=API_CREDENTIALS['API_KEY'],
        api_secret=API_CREDENTIALS['API_SECRET']
    )
    
    try:
        if choice == '1':
            # Pull only
            logger.info("User selected: Pull GST data only")
            output_file = run_pull_operation(logger)
            if output_file:
                print(f"\n✓ Pull completed! Results saved to: {output_file}")
        
        elif choice == '2':
            # Export only
            logger.info("User selected: Export only")
            
            # Get report types FIRST
            report_types = select_report_types()
            if not report_types:
                logger.error("No report types selected!")
                return
            
            # Then get export location
            export_location = get_export_location()
            export_paths = create_export_structure(export_location, report_types)
            
            pull_results_file = select_previous_pull_results()
            if pull_results_file:
                logger.info(f"Using pull results: {pull_results_file}")
                run_export_phase(pull_results_file, api_client, logger, export_paths)
            else:
                print("No file selected for export")
        
        elif choice == '3':
            # Pull and Export
            logger.info("User selected: Pull and Export")
            
            # Get report types FIRST (will be used by both pull and export)
            report_types = select_report_types()
            if not report_types:
                logger.error("No report types selected!")
                return
            
            output_file = run_pull_operation(logger, report_types)
            if output_file:
                print("\n" + "="*50)
                print("Pull completed! Starting export...")
                print("="*50)
                
                # Get export location
                export_location = get_export_location()
                export_paths = create_export_structure(export_location, report_types)
                
                run_export_phase(output_file, api_client, logger, export_paths)
        
        elif choice == '4':
            # Direct Export (no pull required)
            logger.info("User selected: Direct Export")
            run_direct_export(api_client, logger)
    
    finally:
        api_client.close()
    
    logger.info("\n" + "="*50)
    logger.info("GST Bulk Puller Completed!")
    logger.info("="*50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()