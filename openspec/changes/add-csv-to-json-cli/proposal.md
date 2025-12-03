# Change: Add CSV→JSON CLI tool

## Why
Provide a simple, demonstrable data-processing function for the homework repo, enabling conversion of CSV files to JSON with basic error handling.

## What Changes
- Add a command-line interface in `app.py` to convert CSV to JSON
- Support custom delimiter, output path, and pretty printing
- Handle common errors (missing file, unreadable CSV)

## Impact
- Affected specs: `tools/csv-json`
- Affected code: `app.py`
