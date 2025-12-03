# HW6 Toolkit

## Features
- `csv2json`: Convert a CSV file to JSON
- `fetch`: Download CWB JSON (provide API URL)
- `store`: Parse JSON and store into SQLite `data.db`
- `serve-info`: Print Streamlit usage hints
- Streamlit app `streamlit_app.py` to view SQLite data

## Quick Start (PowerShell)
```powershell
# 1) (Optional) CSV to JSON
python app.py csv2json --input .\data.csv --output .\data.json --pretty

# 2) Fetch weather JSON (replace with the actual API URL)
python app.py fetch --url "https://example.com/path/to/cwb_api.json" --out weather.json

# 3) Parse and store into SQLite
python app.py store --json weather.json --db data.db

# 4) Install and run Streamlit viewer
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Notes
- The CWB JSON schema may differ; adjust `parse_weather` in `app.py` if needed.
- Database schema:
  ```sql
  CREATE TABLE weather (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT,
    min_temp REAL,
    max_temp REAL,
    description TEXT
  );
  ```
