# GSTR-2A Puller Troubleshooting Guide

## Quick Diagnostics Checklist

Before troubleshooting, run through this checklist:

- [ ] Python 3.7+ installed and in PATH
- [ ] All required packages installed (`pip install -r requirements.txt`)
- [ ] API credentials updated in `config.py`
- [ ] Input Excel file has correct columns
- [ ] All GSTINs are OTP-verified in OCTA GST web interface
- [ ] Internet connection is stable

---

## Common Errors and Solutions

### 1. API Authentication Errors

#### Error: "Authentication failed - Check API credentials"
```
Status: Failed
Error Message: Authentication failed - Check API credentials
```

**Causes:**
- Incorrect API key or secret
- API credentials not properly formatted
- Credentials expired or revoked

**Solutions:**
1. Verify credentials in OCTA GST:
   - Login to OCTA GST
   - Go to Settings → ERP Keys
   - Generate new credentials if needed

2. Update `config.py`:
```python
API_CREDENTIALS = {
    'API_KEY': 'z638922957705273562',  # Your actual key
    'API_SECRET': 'sULCYNpuEKJMphBAbBg6'  # Your actual secret
}
```

3. Check for extra spaces or quotes in credentials

---

### 2. GSTIN Connection Errors

#### Error: "Not connected to GST System - Please complete OTP verification"
```
Status: Failed  
Error Message: Not connected to GST System - Please complete OTP verification for 19AADCG0737G1ZQ
```

**Cause:** GSTIN not linked to OCTA GST via OTP

**Solution:**
1. Login to OCTA GST web interface
2. Go to the company with this GSTIN
3. Click "Connect to GST Portal"
4. Enter OTP received on registered mobile
5. Wait for confirmation
6. Retry the API pull

---

### 3. Excel File Issues

#### Error: "Missing required columns"
```
Error reading Excel file: Missing required columns: ['GSTIN']
```

**Cause:** Input Excel doesn't have required columns

**Solution:**
1. Ensure these columns exist (case-sensitive):
   - Company ID
   - Company Name
   - GSTIN

2. Check for extra spaces in column names
3. Use the sample file as template:
```bash
python sample_input.py
```

#### Error: "No data rows found"
```
Error: No data rows found in Excel file
```

**Solution:**
- Check if data is in the correct sheet
- Ensure there are no empty rows at the top
- Verify GSTIN column has values

---

### 4. Network and Timeout Issues

#### Error: "Request timeout"
```
Status: Failed
Error Message: Request timeout
```

**Solutions:**
1. Check internet connection
2. Increase timeout in `config.py`:
```python
API_TIMEOUT = 60  # Increase from 30 to 60 seconds
```
3. Retry during off-peak hours
4. Check if OCTA GST is under maintenance

#### Error: "Connection error - Check internet"
```
Status: Failed
Error Message: Connection error - Check internet
```

**Solutions:**
1. Test internet connectivity
2. Check firewall settings
3. Verify proxy settings if applicable
4. Try using a different network

---

### 5. Rate Limiting

#### Error: "Rate limit exceeded"
```
Status: Failed
Error Message: Rate limit exceeded
```

**Solution:**
1. Increase delay between calls in `config.py`:
```python
DELAY_BETWEEN_CALLS = 3  # Increase from 1 to 3 seconds
```
2. Process fewer companies at once
3. Wait 15-30 minutes before retrying

---

### 6. Invalid Data Formats

#### Error: "Invalid period format"
```
Error 100: Invalid period format: 2024-13
```

**Solution:**
- Use YYYY-MM format (e.g., 2024-04)
- Month must be 01-12
- Year should be 4 digits

#### Error: Invalid GSTIN
```
Skipping company ABC Corp: Invalid GSTIN format
```

**Solution:**
- GSTIN must be exactly 15 characters
- Format: 2 digits + 5 letters + 4 digits + 1 letter + 1 alphanumeric + Z + 1 alphanumeric
- Example: 19AADCG0737G1ZQ

---

### 7. Python Environment Issues

#### Error: "ModuleNotFoundError: No module named 'pandas'"
```python
Traceback (most recent call last):
  File "main.py", line 15, in <module>
    import pandas as pd
ModuleNotFoundError: No module named 'pandas'
```

**Solution:**
```bash
pip install -r requirements.txt
```

If pip isn't working:
```bash
python -m pip install pandas openpyxl requests
```

#### Error: "No module named 'tkinter'"
**Solution for different OS:**
- **Windows**: Reinstall Python with tcl/tk option
- **Ubuntu/Debian**: `sudo apt-get install python3-tk`
- **Mac**: `brew install python-tk`
- **Alternative**: Comment out file browser in `utils.py` and specify file directly

---

### 8. File Permission Errors

#### Error: "Permission denied: output/gstr2a_pulls_20250115.xlsx"
```
PermissionError: [Errno 13] Permission denied: 'output/gstr2a_pulls_20250115.xlsx'
```

**Solution:**
1. Close the Excel file if it's open
2. Check folder permissions
3. Run as administrator (Windows)
4. Change output directory in `config.py`

---

### 9. Company ID Issues

#### Error: Company ID format
```
HTTP 403: Access denied - Check company permissions
```

**Solution:**
1. Ensure Company ID has 'oc-' prefix
2. Verify you have access to this company in OCTA GST
3. Check if company ID matches exactly (case-sensitive)

---

## Debug Mode

To get more detailed error information:

1. Edit `config.py`:
```python
LOG_LEVEL = 'DEBUG'  # Change from 'INFO' to 'DEBUG'
```

2. Check log files in `logs` folder for detailed traces

---

## Performance Optimization

### Processing is too slow

1. **Reduce API retry attempts** in `config.py`:
```python
API_RETRY_COUNT = 1  # Reduce from 3 to 1
```

2. **Process specific companies** by filtering input Excel

3. **Split large batches**:
   - Process 10-20 companies at a time
   - Use multiple input files

---

## Testing Your Setup

Run this test script to verify everything works:

```python
# test_setup.py
from config import API_CREDENTIALS, API_ENDPOINTS
from api_client import OctaGSTClient

# Test with one company
client = OctaGSTClient(
    API_CREDENTIALS['API_KEY'],
    API_CREDENTIALS['API_SECRET']
)

# Replace with your test company details
success, job_id, error = client.pull_gstr2a(
    company_id='oc-3372',
    gstin='19AADCG0737G1ZQ',
    return_period='2024-12'
)

if success:
    print(f"✅ Success! Job ID: {job_id}")
else:
    print(f"❌ Failed: {error}")
```

---

## Still Having Issues?

### Collect this information:

1. **Error message** from console
2. **Log file** from `logs` folder
3. **Python version**: `python --version`
4. **Package versions**: `pip list`
5. **Sample of input Excel** (remove sensitive data)
6. **config.py settings** (hide credentials)

### Contact:

- **OCTA GST Support**: For API-specific issues
- **Script Issues**: Check logs first, then review this guide
- **Python Help**: Stack Overflow or Python forums

---

## Emergency Workarounds

### Can't use the script at all?

1. **Use OCTA GST web interface** manually
2. **Use OCTA GST Assistant** browser extension for bulk downloads
3. **Try during off-peak hours** (early morning/late night)
4. **Process one company at a time** using curl:

```bash
curl -X POST "https://app.octagst.com/api/gstr2a/pull" \
  -u "API_KEY:API_SECRET" \
  -H "Octa-Company: oc-3372" \
  -H "Content-Type: application/json" \
  -d '{"gstin":"19AADCG0737G1ZQ","returnPeriod":"2024-12"}'
```

---

## Prevention Tips

1. **Test with one company first** before bulk processing
2. **Keep credentials secure** and rotate regularly
3. **Monitor OCTA GST announcements** for API changes
4. **Backup output files** regularly
5. **Document any custom changes** you make to scripts
6. **Run during off-peak hours** for better performance
7. **Keep logs** for audit trail and debugging

---

**Remember**: Most issues are related to credentials, data format, or connectivity. Start with the basics before diving deep into troubleshooting!