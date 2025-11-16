# GSTR-2A Bulk Puller for OCTA GST

A professional Python tool for bulk pulling GSTR-2A data from multiple companies using OCTA GST API.

## Features

✅ **Bulk Processing**: Pull GSTR-2A for multiple companies and multiple months in one run  
✅ **Error Resilience**: Skip failed companies and continue processing  
✅ **Detailed Logging**: Track every operation with comprehensive logs  
✅ **Excel Integration**: Read companies from Excel, save results to Excel  
✅ **Progress Tracking**: Real-time progress updates and time estimates  
✅ **Job ID Tracking**: Store job IDs for later status checking  
✅ **Smart Validation**: Validate GSTINs and data before processing  
✅ **Flexible Input**: Browse files or select from input folder  

## Quick Start

### 1. Install Python (if not already installed)
- Download Python 3.8+ from [python.org](https://www.python.org/downloads/)
- During installation, check "Add Python to PATH"

### 2. Download and Setup
1. Create a folder called `gstr2a_puller` on your computer
2. Save all the Python files in this folder
3. Open Command Prompt or Terminal in this folder
4. Install required libraries:
```bash
pip install -r requirements.txt
```

### 3. Configure API Credentials
1. Open `config.py` in any text editor
2. Replace the placeholder credentials:
```python
API_CREDENTIALS = {
    'API_KEY': 'your_actual_api_key_here',
    'API_SECRET': 'your_actual_api_secret_here'
}
```

### 4. Prepare Your Input Excel
Create an Excel file with these columns (minimum required):
- **Company ID** (e.g., `3372` or `oc-3372`)
- **Company Name** (e.g., `ABC Corp`)
- **GSTIN** (e.g., `19AADCG0737G1ZQ`)

Optional columns (will be preserved if present):
- Environment
- Description
- Registration

Save this file in the `input` folder.

### 5. Run the Script
```bash
python main.py
```

## Folder Structure

```
gstr2a_puller/
│
├── config.py          # ⚙️ Configuration (UPDATE THIS FIRST!)
├── main.py            # 🚀 Main script (RUN THIS)
├── api_client.py      # 🔌 API handling
├── excel_handler.py   # 📊 Excel operations
├── utils.py           # 🛠️ Helper functions
├── requirements.txt   # 📦 Dependencies
├── README.md          # 📖 This file
│
├── input/            # 📥 Place your Excel files here
│   └── companies.xlsx
│
├── output/           # 📤 Results will be saved here
│   └── gstr2a_pulls_[timestamp].xlsx
│
└── logs/             # 📝 Detailed logs for debugging
    └── gstr2a_puller_[timestamp].log
```

## Usage Guide

### Step-by-Step Process

1. **Start the script**
   ```bash
   python main.py
   ```

2. **Enter date range**
   - Start period: `2024-04` (April 2024)
   - End period: `2025-03` (March 2025)
   - Confirm the months to process

3. **Select input file**
   - Choose from files in input folder
   - Or browse to select from elsewhere

4. **Watch progress**
   - See real-time updates for each company/month
   - Monitor success/failure status
   - Track job IDs

5. **Check results**
   - Open the output Excel file
   - Review Summary sheet for statistics
   - Check detailed results in main sheet

### Input Excel Format

| Company ID | Company Name | GSTIN | Environment | Description |
|------------|--------------|--------|------------|-------------|
| 3372 | ABC Corporation | 19AADCG0737G1ZQ | Production | Main Office |
| 3373 | XYZ Limited | 27AABCX1234M1ZP | Production | Branch Office |

**Note**: The script will automatically add 'oc-' prefix to Company IDs if missing.

### Output Excel Format

**Main Sheet**: GSTR2A_Pull_Results
| Company ID | Company Name | GSTIN | Return Period | Job ID | Status | Error Message | Timestamp |
|------------|--------------|--------|---------------|---------|---------|---------------|-----------|
| oc-3372 | ABC Corp | 19AADCG0737G1ZQ | 2024-04 | 6492341 | Success | - | 2025-01-15 10:30:00 |

**Summary Sheet**: Statistics
- Total operations
- Success count
- Failed count
- Success rate
- Per-company breakdown

## Common Issues and Solutions

### Issue: "API credentials not configured!"
**Solution**: Update `config.py` with your actual API credentials

### Issue: "Not connected to GST System"
**Solution**: Login to OCTA GST web interface and complete OTP verification for the GSTIN

### Issue: "Missing required columns"
**Solution**: Ensure your Excel has columns: Company ID, Company Name, GSTIN

### Issue: "Rate limit exceeded"
**Solution**: The script has automatic retry logic. If persistent, wait and try again later.

### Issue: Can't find input file
**Solution**: Place your Excel file in the `input` folder or use the browse option

## Advanced Configuration

Edit `config.py` to customize:

- **API_TIMEOUT**: Increase if you have slow internet (default: 30 seconds)
- **API_RETRY_COUNT**: Number of retries for failed requests (default: 3)
- **DELAY_BETWEEN_CALLS**: Seconds between API calls (default: 1)
- **LOG_LEVEL**: Set to 'DEBUG' for more detailed logs
- **EXCEL_SHEET_NAME**: Specify which sheet to read from input Excel

## Tips for Best Results

1. **Start Small**: Test with 1-2 companies first
2. **Check Connectivity**: Ensure all GSTINs are OTP-verified in OCTA GST
3. **Monitor First Run**: Watch the detailed logs to understand the process
4. **Keep Records**: Save output files for audit trail
5. **Regular Runs**: Run monthly to avoid large backlogs
6. **Validate Data**: Check your input Excel for correct GSTINs
7. **Backup Results**: Output files have timestamps - keep them for reference

## Security Notes

⚠️ **Never share your config.py file** - it contains sensitive API credentials  
⚠️ **Keep your API credentials secure** - regenerate if exposed  
⚠️ **Don't commit credentials to git** - use .gitignore  

## Next Steps (Future Enhancements)

Once comfortable with pulling, you can extend the script to:
1. **Export to Excel**: Add export functionality after pulling
2. **Email Reports**: Send results via email
3. **Schedule Runs**: Use Windows Task Scheduler or cron
4. **Database Storage**: Store results in a database
5. **Status Checking**: Add job status monitoring
6. **Parallel Processing**: Speed up with concurrent requests

## Support

For issues with:
- **OCTA GST API**: Contact OCTA GST support
- **Script bugs**: Check the logs in `logs` folder
- **Excel issues**: Ensure correct format and data types

## Version History

- **v1.0.0** (Current): Initial version with pull functionality
- Future: Add export, status checking, and automation features

---

**Remember**: Always test with a small dataset first before running on all companies!