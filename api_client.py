"""
OCTA GST API Client - Complete Fixed Version
Handles all API interactions with OCTA GST including job status checking
"""

import requests
from requests.auth import HTTPBasicAuth
import json
import time
import logging
from typing import Tuple, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from config import API_ENDPOINTS, API_TIMEOUT, API_RETRY_COUNT, API_RETRY_DELAY, PULL_RETRY_DELAY


class OctaGSTClient:
    """Client for interacting with OCTA GST APIs"""
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize the API client
        
        Args:
            api_key: OCTA GST API Key
            api_secret: OCTA GST API Secret
        """
        self.auth = HTTPBasicAuth(api_key, api_secret)
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
    def pull_gst_report(self, report_type: str, company_id: str, gstin: str, return_period: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Pull GST report data from government portal
        
        Args:
            report_type: Type of GST report (e.g., 'GSTR-2A', 'GSTR-2B', etc.)
            company_id: OCTA Company ID (e.g., 'oc-3372')
            gstin: Company GSTIN
            return_period: Period in YYYY-MM format
            
        Returns:
            Tuple of (success, job_id, error_message)
        """
        from config import GST_REPORTS
        
        if report_type not in GST_REPORTS:
            return False, None, f"Unknown report type: {report_type}"
        
        if not GST_REPORTS[report_type]['enabled']:
            return False, None, f"{report_type} is not yet enabled. Waiting for API documentation."
        
        headers = {
            'Octa-Company': company_id,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'gstin': gstin,
            'returnPeriod': return_period
        }
        
        endpoint = GST_REPORTS[report_type]['pull_endpoint']
        
        self.logger.debug(f"API Request - Report: {report_type}, Company: {company_id}, GSTIN: {gstin}, Period: {return_period}")
        
        # Retry logic for resilience
        for attempt in range(API_RETRY_COUNT):
            try:
                response = self.session.post(
                    endpoint,
                    auth=self.auth,
                    headers=headers,
                    json=payload,
                    timeout=API_TIMEOUT
                )
                
                self.logger.debug(f"API Response Status: {response.status_code}")
                
                # Check for success
                if response.status_code == 200:
                    try:
                        data = response.json()
                        job_id = data.get('jobId')
                        if job_id:
                            self.logger.debug(f"Successfully initiated pull. Job ID: {job_id}")
                            return True, job_id, None
                        else:
                            return False, None, "No job ID in response"
                    except json.JSONDecodeError:
                        return False, None, "Invalid JSON response"
                        
                # Handle specific error codes
                elif response.status_code == 400:
                    error_code = response.headers.get('Octa-ErrorCode', 'Unknown')
                    error_msg = response.headers.get('Octa-ErrorMessage', 'Bad Request')
                    
                    # Common error scenarios
                    if error_code == '2000':
                        return False, None, f"Not connected to GST System - Please complete OTP verification for {gstin}"
                    elif error_code == '100':
                        return False, None, f"Invalid period format: {return_period}"
                    else:
                        return False, None, f"Error {error_code}: {error_msg}"
                        
                elif response.status_code == 401:
                    return False, None, "Authentication failed - Check API credentials"
                    
                elif response.status_code == 403:
                    return False, None, "Access denied - Check company permissions"
                    
                elif response.status_code == 429:
                    # Rate limiting
                    if attempt < API_RETRY_COUNT - 1:
                        wait_time = PULL_RETRY_DELAY * (attempt + 1)
                        self.logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    return False, None, "Rate limit exceeded"
                    
                elif response.status_code == 500:
                    if attempt < API_RETRY_COUNT - 1:
                        self.logger.warning(f"Server error. Retrying... (Attempt {attempt + 1})")
                        time.sleep(PULL_RETRY_DELAY)
                        continue
                    return False, None, "OCTA GST server error"
                    
                else:
                    return False, None, f"HTTP {response.status_code}: {response.text[:100]}"
                    
            except requests.exceptions.Timeout:
                if attempt < API_RETRY_COUNT - 1:
                    self.logger.warning(f"Request timeout. Retrying... (Attempt {attempt + 1})")
                    time.sleep(API_RETRY_DELAY)
                    continue
                return False, None, "Request timeout"
                
            except requests.exceptions.ConnectionError:
                if attempt < API_RETRY_COUNT - 1:
                    self.logger.warning(f"Connection error. Retrying... (Attempt {attempt + 1})")
                    time.sleep(API_RETRY_DELAY)
                    continue
                return False, None, "Connection error - Check internet"
                
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                return False, None, f"Unexpected error: {str(e)}"
        
        return False, None, "Max retries exceeded"
    
    def export_gst_report(self, report_type: str, company_id: str, gstin: str, 
                        start_period: str, end_period: str, report_format: int = 101) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Export GST report data to Excel - Returns job ID
        
        Args:
            report_type: Type of GST report (e.g., 'GSTR-2A', 'GSTR-2B', etc.)
            company_id: OCTA Company ID
            gstin: GSTIN to export (single string)
            start_period: Start period in YYYY-MM format
            end_period: End period in YYYY-MM format
            report_format: 100 (Full) or 101 (Smart)
            
        Returns:
            Tuple of (success, job_id, error_message)
        """
        from config import GST_REPORTS
        
        if report_type not in GST_REPORTS:
            return False, None, f"Unknown report type: {report_type}"
        
        if not GST_REPORTS[report_type]['enabled']:
            return False, None, f"{report_type} is not yet enabled. Waiting for API documentation."
        
        headers = {
            'Octa-Company': company_id,
            'Content-Type': 'application/json'
        }
        
        # Ensure gstin is in a list format for the API
        if isinstance(gstin, str):
            gstins = [gstin]
        else:
            gstins = gstin if isinstance(gstin, list) else [gstin]
        
        payload = {
            'gstins': gstins,
            'startReturnPeriod': start_period,
            'endReturnPeriod': end_period,
            'reportType': report_format
        }
        
        endpoint = GST_REPORTS[report_type]['export_endpoint']
        
        self.logger.debug(f"Export request - Company: {company_id}, GSTIN: {gstins[0]}, Period: {start_period} to {end_period}")
        
        try:
            response = self.session.post(
                endpoint,
                auth=self.auth,
                headers=headers,
                json=payload,
                timeout=API_TIMEOUT
            )
            
            self.logger.debug(f"Export response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    job_id = data.get('jobId')
                    
                    if job_id:
                        self.logger.info(f"Export job created successfully. Job ID: {job_id}")
                        return True, job_id, None
                    else:
                        self.logger.error(f"No job ID in response. Response: {data}")
                        return False, None, "No job ID in response"
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON response: {e}")
                    return False, None, f"Invalid JSON response: {e}"
            
            elif response.status_code == 400:
                error_msg = response.headers.get('Octa-ErrorMessage', 'Bad Request')
                error_code = response.headers.get('Octa-ErrorCode', '')
                self.logger.error(f"Export failed with error {error_code}: {error_msg}")
                return False, None, f"Error {error_code}: {error_msg}"
            
            elif response.status_code == 401:
                return False, None, "Authentication failed - Check API credentials"
            
            elif response.status_code == 403:
                return False, None, "Access denied - Check company permissions"
            
            else:
                error_msg = response.headers.get('Octa-ErrorMessage', f'HTTP {response.status_code}')
                self.logger.error(f"Export failed: {error_msg}")
                return False, None, error_msg
                
        except requests.exceptions.Timeout:
            return False, None, "Request timeout"
        except requests.exceptions.ConnectionError:
            return False, None, "Connection error"
        except Exception as e:
            self.logger.error(f"Export error: {e}")
            return False, None, str(e)
    
    def check_job_status(self, company_id: str, job_id: str) -> Dict[str, Any]:
        """
        Check the status of a job
        """
        # No need for manual Authorization header - self.auth handles it
        # Construct URL with job_id in path
        url = f"{API_ENDPOINTS['JOB_STATUS']}/{job_id}"
        
        # ADD THIS: Include the company header just in case
        headers = {
            'Octa-Company': company_id
        }
                
        try:
            response = self.session.get(
                url,
                auth=self.auth,  # This already handles Basic Auth
                headers=headers,
                timeout=API_TIMEOUT
            )
            
            self.logger.debug(f"Job status check - URL: {url}, Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.logger.debug(f"Job status response: {json.dumps(data, indent=2)}")
                
                # Map OCTA status codes to standard status
                job_status_code = data.get('jobStatus')
                status_mapping = {
                    100: 'completed',
                    0: 'pending',
                    1: 'processing',
                    2: 'processing',
                    -1: 'failed',
                    -2: 'cancelled',
                    99: 'expired'
                }
                data['status'] = status_mapping.get(job_status_code, 'unknown')

                # Add human-readable message
                if job_status_code not in status_mapping:
                    self.logger.warning(f"Unknown job status code: {job_status_code}")
                
                return data
            else:
                return {
                    'status': 'error',
                    'message': f'Failed to get status: HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def download_export(self, company_id: str, job_id: str, output_dir: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check job status and download export when ready
        """
        import re
        from urllib.parse import urlparse, parse_qs
        
        # Check job status
        job_status = self.check_job_status(company_id, job_id)
        
        self.logger.debug(f"Job status for download: {job_status}")
        
        # Check if job is completed (status code 100)
        if job_status.get('jobStatus') == 100 or job_status.get('status') == 'completed':
            # Get download URL
            download_url = job_status.get('url')
            
            if not download_url:
                self.logger.error(f"No download URL in completed job. Status: {job_status}")
                return False, None, "No download URL in completed job"
            
            try:
                self.logger.info(f"Downloading from: {download_url[:100]}...")  # Log first 100 chars
                
                # Download the file
                response = self.session.get(
                    download_url,
                    stream=True,
                    timeout=API_TIMEOUT
                )
                
                if response.status_code != 200:
                    return False, None, f"Download failed: HTTP {response.status_code}"
                
                # Extract filename from URL or headers
                filename = None
                
                # Try to get from response headers first
                content_disp = response.headers.get('content-disposition', '')
                if content_disp and 'filename=' in content_disp:
                    matches = re.findall('filename[^;=\n]*=(([\'"]).*?\\2|[^;\\n]*)', content_disp)
                    if matches:
                        filename = matches[0][0].strip('"\'')
                
                # If not in headers, try to extract from URL (S3 URLs often have filename in metadata)
                if not filename:
                    # Parse the S3 URL to extract filename from x-amz-meta headers
                    parsed = urlparse(download_url)
                    # The filename might be in the path or query parameters
                    path_parts = parsed.path.split('/')
                    if path_parts[-1] and '.xlsx' in path_parts[-1]:
                        filename = path_parts[-1]
                
                # Default filename if still not found
                if not filename:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"GSTR2A_Export_{job_id}_{timestamp}.xlsx"
                    self.logger.warning(f"Could not extract filename, using: {filename}")
                
                self.logger.info(f"Saving file as: {filename}")
                
                # Save file
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                filepath = output_path / filename
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Verify file
                if filepath.exists() and filepath.stat().st_size > 0:
                    file_size = filepath.stat().st_size
                    self.logger.info(f"File saved successfully: {filepath} ({file_size} bytes)")
                    return True, str(filepath), filename
                else:
                    return False, None, "File creation failed or file is empty"
                    
            except Exception as e:
                self.logger.error(f"Download error: {e}")
                return False, None, str(e)
        else:
            status = job_status.get('jobStatus', job_status.get('status', 'unknown'))
            return False, None, f"Job not ready. Status: {status}"

    def close(self):
        """Close the session"""
        self.session.close()