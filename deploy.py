#!/usr/bin/env python3
"""
Cricket Analytics Website - Deployment and Testing Script
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required. Current version:", sys.version)
        return False
    print("✅ Python version check passed:", sys.version)
    return True

def check_data_files():
    """Check if data files exist"""
    data_dir = Path("data")
    if not data_dir.exists():
        print("❌ Data directory not found!")
        return False
    
    json_files = list(data_dir.glob("*.json"))
    if not json_files:
        print("❌ No JSON data files found in data directory!")
        return False
    
    print(f"✅ Found {len(json_files)} JSON data files")
    
    # Test loading a sample file
    try:
        sample_file = json_files[0]
        with open(sample_file, 'r') as f:
            data = json.load(f)
        print("✅ Sample JSON file loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Error loading sample JSON file: {e}")
        return False

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def test_imports():
    """Test if all required modules can be imported"""
    required_modules = [
        ('flask', 'flask'), 
        ('flask_cors', 'flask_cors'), 
        ('pandas', 'pandas'), 
        ('numpy', 'numpy'), 
        ('sklearn', 'scikit-learn'), 
        ('json', 'json'), 
        ('os', 'os')
    ]
    
    for import_name, display_name in required_modules:
        try:
            __import__(import_name)
            print(f"✅ {display_name} imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import {display_name}: {e}")
            return False
    
    return True

def test_data_processing():
    """Test basic data processing functionality"""
    try:
        from data_processor import CricketDataProcessor
        
        processor = CricketDataProcessor("data")
        matches = processor.matches_data
        
        if not matches:
            print("❌ No matches loaded from data files")
            return False
        
        print(f"✅ Loaded {len(matches)} matches successfully (development mode - limited dataset)")
        
        # Test basic filtering
        test_teams = processor.get_all_teams()
        test_venues = processor.get_all_venues()
        
        print(f"✅ Found {len(test_teams)} teams and {len(test_venues)} venues")
        return True
        
    except Exception as e:
        print(f"❌ Error testing data processing: {e}")
        return False

def test_api_endpoints():
    """Test that Flask app can start and API endpoints are accessible"""
    try:
        from app import app
        
        # Test app creation
        if not app:
            print("❌ Failed to create Flask app")
            return False
        
        print("✅ Flask app created successfully")
        
        # Test with app context
        with app.app_context():
            # Test basic routes exist
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            required_routes = ['/api/all-teams', '/api/all-players', '/api/all-venues']
            
            for route in required_routes:
                if route in rules:
                    print(f"✅ Route {route} found")
                else:
                    print(f"❌ Route {route} not found")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Flask app: {e}")
        return False

def create_startup_script():
    """Create a startup script for easy deployment"""
    startup_content = """@echo off
echo Starting Cricket Analytics Website...
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\\Scripts\\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Start the application
echo.
echo Starting Flask application...
echo Open your browser and go to: http://localhost:5000
echo.
python app.py

pause
"""
    
    with open("start_cricket_analytics.bat", "w") as f:
        f.write(startup_content)
    
    print("✅ Created startup script: start_cricket_analytics.bat")

def create_deployment_guide():
    """Create a deployment guide"""
    guide_content = """# Cricket Analytics Website - Deployment Guide

## Quick Start

1. **Windows Users**: Double-click `start_cricket_analytics.bat`
2. **Linux/Mac Users**: Run `python app.py`
3. Open your browser and go to: http://localhost:5000

## Manual Setup

### Prerequisites
- Python 3.8 or higher
- Cricket match data in JSON format (place in `data/` directory)

### Installation Steps

1. **Clone/Download the project**
   ```bash
   cd cricket-analytics
   ```

2. **Create virtual environment (recommended)**
   ```bash
   python -m venv venv
   
   # Windows
   venv\\Scripts\\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify data files**
   - Ensure JSON files are in the `data/` directory
   - Files should contain cricket match data with ball-by-ball information

5. **Start the application**
   ```bash
   python app.py
   ```

6. **Access the website**
   - Open http://localhost:5000 in your browser
   - Navigate through different sections using the menu

## Features

### Dashboard
- Overview of all statistics
- Quick access to different analysis sections

### Player Analysis
- Individual player statistics
- Batting and bowling performance
- Dismissal analysis with charts
- Player comparison functionality

### Team Analysis
- Team performance metrics
- Head-to-head comparisons
- Format-wise analysis
- Historical performance tracking

### Venue Analysis
- Ground-specific statistics
- Batting and bowling conditions
- Toss impact analysis
- Venue comparisons

### Win Prediction
- AI-powered match outcome predictions
- Factor analysis
- Historical performance consideration

## Troubleshooting

### Common Issues

1. **No data found**
   - Check that JSON files are in the `data/` directory
   - Verify JSON file format is correct

2. **Import errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version is 3.8+

3. **Port already in use**
   - Change port in `app.py`: `app.run(debug=True, port=5001)`

4. **Slow loading**
   - Large datasets may take time to process
   - Consider filtering data for specific date ranges

### Data Format
The application expects JSON files with cricket match data including:
- Match information (teams, venue, date)
- Ball-by-ball data
- Player information
- Match results

## Customization

### Adding New Features
- Modify Python files in the root directory
- Update templates in `templates/` directory
- Add styling in `static/css/style.css`
- Extend JavaScript in `static/js/` directory

### Styling
- The application uses Bootstrap 5 with custom CSS
- Modern glass morphism design
- Responsive layout for all devices

## Deployment to Production

### Using Gunicorn (Linux/Mac)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Waitress (Windows)
```bash
pip install waitress
waitress-serve --port=5000 app:app
```

### Environment Variables
Set these for production:
- `FLASK_ENV=production`
- `SECRET_KEY=your-secret-key`

## Support
For issues or questions, check the code comments or modify as needed for your specific use case.
"""
    
    with open("DEPLOYMENT_GUIDE.md", "w") as f:
        f.write(guide_content)
    
    print("✅ Created deployment guide: DEPLOYMENT_GUIDE.md")

def run_tests():
    """Run all deployment tests"""
    print("🚀 Cricket Analytics Website - Deployment Test")
    print("=" * 50)
    
    tests = [
        ("Python Version", check_python_version),
        ("Data Files", check_data_files),
        ("Dependencies", install_dependencies),
        ("Module Imports", test_imports),
        ("Data Processing", test_data_processing),
        ("API Endpoints", test_api_endpoints),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} test failed!")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your Cricket Analytics website is ready to deploy!")
        create_startup_script()
        create_deployment_guide()
        print("\n📝 Quick Start:")
        print("   Windows: Double-click 'start_cricket_analytics.bat'")
        print("   Others: Run 'python app.py'")
        print("   Then open: http://localhost:5000")
    else:
        print("⚠️  Some tests failed. Please check the errors above and fix them before deployment.")
    
    return passed == total

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)