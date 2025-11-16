"""
Excel Handler for GSTR-2A Puller
Manages reading input files and writing output files
"""

import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from config import REQUIRED_COLUMNS, OPTIONAL_COLUMNS, EXCEL_SHEET_NAME, OUTPUT_SHEET_NAME


class ExcelHandler:
    """Handles Excel file operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def read_companies(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Read companies from Excel file
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            List of company dictionaries
        """
        try:
            # Read Excel file
            self.logger.info(f"Reading Excel file: {file_path}")
            
            # Try to read with specific sheet name first
            try:
                df = pd.read_excel(file_path, sheet_name=EXCEL_SHEET_NAME)
                self.logger.info(f"Using sheet: {EXCEL_SHEET_NAME}")
            except:
                # If sheet doesn't exist, read first sheet
                df = pd.read_excel(file_path, sheet_name=0)
                self.logger.info("Using first sheet")
            
            # Convert column names to string and strip whitespace
            df.columns = df.columns.astype(str).str.strip()
            
            # Check for required columns
            missing_columns = []
            for col in REQUIRED_COLUMNS:
                if col not in df.columns:
                    # Try case-insensitive match
                    matched = False
                    for df_col in df.columns:
                        if col.lower() == df_col.lower():
                            df.rename(columns={df_col: col}, inplace=True)
                            matched = True
                            break
                    if not matched:
                        missing_columns.append(col)
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Clean and prepare data
            df = df.dropna(subset=['GSTIN'])  # Remove rows without GSTIN
            df = df.fillna('')  # Fill NaN with empty strings
            
            # Convert Company ID to string and clean
            if 'Company ID' in df.columns:
                df['Company ID'] = df['Company ID'].astype(str).str.strip()
                # Remove any .0 from numeric conversion
                df['Company ID'] = df['Company ID'].str.replace('.0', '', regex=False)
            
            # Clean GSTIN
            if 'GSTIN' in df.columns:
                df['GSTIN'] = df['GSTIN'].astype(str).str.strip().str.upper()
            
            # Convert to list of dictionaries
            companies = df.to_dict('records')
            
            self.logger.info(f"Successfully read {len(companies)} companies")
            
            # Log sample data for verification
            if companies:
                sample = companies[0]
                self.logger.debug(f"Sample company data: {sample}")
            
            return companies
            
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error reading Excel file: {e}")
            raise
    
    def save_results(self, results: List[Dict[str, Any]], file_path: str):
        """
        Save results to Excel file
        
        Args:
            results: List of result dictionaries
            file_path: Path to save the Excel file
        """
        try:
            # Create DataFrame from results
            df = pd.DataFrame(results)
            
            # Ensure Timestamp column is datetime
            if 'Timestamp' in df.columns:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                df['Timestamp'] = df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Sort by Company ID and Return Period
            if 'Company ID' in df.columns and 'Return Period' in df.columns:
                df = df.sort_values(['Company ID', 'Return Period'])
            
            # Create Excel writer with formatting
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Write main results
                df.to_excel(writer, sheet_name=OUTPUT_SHEET_NAME, index=False)
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets[OUTPUT_SHEET_NAME]
                
                # Adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
                
                # Add summary sheet
                self._add_summary_sheet(writer, df)
            
            self.logger.info(f"Results saved to: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving results to Excel: {e}")
            raise
    
    def _add_summary_sheet(self, writer: pd.ExcelWriter, df: pd.DataFrame):
        """
        Add a summary sheet to the Excel file
        
        Args:
            writer: Excel writer object
            df: Results DataFrame
        """
        try:
            # Create summary statistics
            summary_data = []
            
            # Overall statistics
            total_operations = len(df)
            success_count = len(df[df['Status'] == 'Success'])
            failed_count = len(df[df['Status'] == 'Failed'])
            skipped_count = len(df[df['Status'] == 'Skipped'])
            
            summary_data.append({
                'Metric': 'Total Operations',
                'Value': total_operations
            })
            summary_data.append({
                'Metric': 'Successful',
                'Value': success_count
            })
            summary_data.append({
                'Metric': 'Failed',
                'Value': failed_count
            })
            summary_data.append({
                'Metric': 'Skipped',
                'Value': skipped_count
            })
            summary_data.append({
                'Metric': 'Success Rate',
                'Value': f"{(success_count/total_operations*100):.1f}%" if total_operations > 0 else "0%"
            })
            
            # Per company statistics
            summary_data.append({
                'Metric': '',
                'Value': ''
            })
            summary_data.append({
                'Metric': 'PER COMPANY SUMMARY',
                'Value': ''
            })
            
            if 'Company Name' in df.columns:
                company_stats = df.groupby('Company Name').agg({
                    'Status': lambda x: (x == 'Success').sum(),
                    'Return Period': 'count'
                }).reset_index()
                company_stats.columns = ['Company', 'Successful', 'Total']
                
                for _, row in company_stats.iterrows():
                    summary_data.append({
                        'Metric': row['Company'],
                        'Value': f"{row['Successful']}/{row['Total']} periods"
                    })
            
            # Create summary DataFrame
            summary_df = pd.DataFrame(summary_data)
            
            # Write to Excel
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Format summary sheet
            worksheet = writer.sheets['Summary']
            worksheet.column_dimensions['A'].width = 30
            worksheet.column_dimensions['B'].width = 20
            
        except Exception as e:
            self.logger.warning(f"Could not create summary sheet: {e}")
    
    def validate_excel_structure(self, file_path: str) -> tuple[bool, str]:
        """
        Validate the structure of an Excel file
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Read first few rows
            df = pd.read_excel(file_path, nrows=5)
            df.columns = df.columns.astype(str).str.strip()
            
            # Check for required columns
            missing = []
            for col in REQUIRED_COLUMNS:
                found = False
                for df_col in df.columns:
                    if col.lower() == df_col.lower():
                        found = True
                        break
                if not found:
                    missing.append(col)
            
            if missing:
                return False, f"Missing columns: {', '.join(missing)}"
            
            # Check if there's at least one row of data
            if len(df) == 0:
                return False, "No data rows found"
            
            return True, "Excel structure is valid"
            
        except Exception as e:
            return False, f"Error reading file: {str(e)}"