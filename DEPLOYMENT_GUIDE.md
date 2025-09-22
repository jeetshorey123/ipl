# Cricket Analytics Website - Deployment Guide

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
   venv\Scripts\activate
   
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
