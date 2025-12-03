# HW6 Toolkit (Single-file)

## Features
- `csv2json`: Convert a CSV file to JSON
- `fetch`: Download CWB JSON (provide API URL)
- `store`: Parse JSON and store into SQLite `data.db`
- `serve-info`: Print Streamlit usage hints
- Streamlit UI now integrated in `app.py` (run with `streamlit run app.py`)

## Quick Start (PowerShell)
```powershell
# 1) (Optional) CSV to JSON
python app.py csv2json --input .\data.csv --output .\data.json --pretty

# 2) Fetch weather JSON (replace with the actual API URL)
python app.py fetch --url "https://example.com/path/to/cwb_api.json" --out weather.json

# 3) Parse and store into SQLite
python app.py store --json weather.json --db data.db

# 4) Install and run Streamlit UI (single-file)
pip install -r requirements.txt
streamlit run app.py
```

## Unified Streamlit Flow (single-file)
- Launch the integrated UI (fetch → store → view) from `app.py`:
```powershell
pip install -r requirements.txt
streamlit run app.py
```
- In the app:
  - Enter the CWB API JSON URL (e.g., F-A0010-001) and click "下載 JSON"
  - Use defaults `weather.json` and `data.db`, click "解析並存入"
  - View the `weather` table below

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
