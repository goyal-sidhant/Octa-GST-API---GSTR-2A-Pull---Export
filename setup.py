# !/usr/bin/env python3
"""
Initial setup script for GSTR-2A Puller
Run this first to set up everything
"""

import os
import sys
import subprocess
from pathlib import Path


def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)


def check_python_version():
    """Check if Python version is 3.7+"""
    print_header("Checking Python Version")
    
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Python 3.7+ is required")
        print("Please update Python from https://python.org")
        return False
    
    print("✅ Python version is compatible")
    return True


def install_requirements():
    """Install required packages"""
    print_header("Installing Required Packages")
    
    try:
        # Upgrade pip first
        print("Upgrading pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        
        # Install requirements
        print("\nInstalling packages from requirements.txt...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        print("✅ All packages installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False


def create_directories():
    """Create necessary directories"""
    print_header("Creating Directory Structure")
    
    directories = ['input', 'output', 'logs']
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created {dir_name}/ directory")
        else:
            print(f"ℹ️  {dir_name}/ directory already exists")
    
    # Create .gitkeep files to preserve empty directories
    for dir_name in directories:
        gitkeep = Path(dir_name) / '.gitkeep'
        if not gitkeep.exists():
            gitkeep.touch()
    
    return True


def check_config():
    """Check if config.py needs to be updated"""
    print_header("Checking Configuration")
    
    try:
        from config import API_CREDENTIALS
        
        if API_CREDENTIALS['API_KEY'] == 'YOUR_API_KEY_HERE':
            print("⚠️  API credentials not configured!")
            print("\nYou need to update config.py with your OCTA GST credentials:")
            print("  1. Open config.py in any text editor")
            print("  2. Replace 'YOUR_API_KEY_HERE' with your actual API key")
            print("  3. Replace 'YOUR_API_SECRET_HERE' with your actual API secret")
            print("\nGet your API credentials from OCTA GST:")
            print("  1. Login to OCTA GST")
            print("  2. Go to Settings → ERP Keys")
            print("  3. Generate new API key and secret")
            return False
        else:
            print("✅ API credentials are configured")
            # Don't show actual credentials for security
            print(f"   API Key: {API_CREDENTIALS['API_KEY'][:10]}...")
            return True
            
    except ImportError:
        print("❌ config.py not found!")
        return False


def create_sample_input():
    """Create sample input file"""
    print_header("Creating Sample Input File")
    
    try:
        import pandas as pd
        
        sample_data = {
            'Company ID': ['3372', '3373', '3374'],
            'Company Name': [
                'ABC Corporation Pvt Ltd',
                'XYZ Industries Limited',
                'Sample Company'
            ],
            'GSTIN': [
                '19AADCG0737G1ZQ',
                '27AABCX1234M1ZP',
                '06AAFCD5862K1Z5'
            ],
            'Environment': ['Production', 'Production', 'Testing'],
            'Description': [
                'Main Office',
                'Head Office',
                'Test Company'
            ]
        }
        
        df = pd.DataFrame(sample_data)
        
        input_file = Path('input') / 'sample_companies.xlsx'
        
        if not input_file.exists():
            df.to_excel(input_file, index=False, sheet_name='Companies')
            print(f"✅ Created sample input file: {input_file}")
            print("   Edit this file with your actual company data")
        else:
            print(f"ℹ️  Sample file already exists: {input_file}")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Could not create sample file: {e}")
        return False


def test_imports():
    """Test if all imports work"""
    print_header("Testing Imports")
    
    modules = [
        ('requests', 'API calls'),
        ('pandas', 'Excel handling'),
        ('openpyxl', 'Excel writing'),
        ('tkinter', 'File selection dialog')
    ]
    
    all_good = True
    
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name:12} - {description}")
        except ImportError:
            print(f"❌ {module_name:12} - {description} (MISSING)")
            all_good = False
    
    return all_good


def main():
    """Main setup function"""
    print("="*60)
    print("     GSTR-2A PULLER - INITIAL SETUP")
    print("="*60)
    
    # Track overall status
    all_steps_passed = True
    
    # Step 1: Check Python version
    if not check_python_version():
        all_steps_passed = False
    
    # Step 2: Install requirements
    if not install_requirements():
        all_steps_passed = False
    
    # Step 3: Test imports
    if not test_imports():
        all_steps_passed = False
    
    # Step 4: Create directories
    if not create_directories():
        all_steps_passed = False
    
    # Step 5: Create sample input
    create_sample_input()  # Optional, don't fail setup if this fails
    
    # Step 6: Check configuration
    config_ready = check_config()
    
    # Final summary
    print_header("SETUP SUMMARY")
    
    if all_steps_passed:
        print("✅ Setup completed successfully!")
        
        if config_ready:
            print("\n🚀 You're ready to run the GSTR-2A puller!")
            print("\nNext steps:")
            print("  1. Review/edit the sample input file in the input folder")
            print("  2. Run: python main.py")
        else:
            print("\n⚠️  Almost ready! Just need to:")
            print("  1. Update config.py with your API credentials")
            print("  2. Edit the sample input file with your company data")
            print("  3. Run: python main.py")
    else:
        print("❌ Setup encountered some issues")
        print("\nPlease fix the errors above and run setup.py again")
    
    print("\n" + "="*60)
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()