## ADDED Requirements
### Requirement: CSV to JSON CLI
The system SHALL provide a command-line tool to convert a CSV file into a JSON array of objects with the following behavior:

#### Scenario: Convert basic CSV with default delimiter
- **WHEN** the user runs `python app.py --input data.csv`
- **THEN** the tool reads `data.csv` (comma-delimited with header row)
- **AND** writes `data.json` next to the input file
- **AND** exits with code 0

#### Scenario: Specify output path and pretty printing
- **WHEN** the user runs `python app.py --input data.csv --output out.json --pretty`
- **THEN** the tool writes the JSON to `out.json` using 2-space indentation

#### Scenario: Use custom delimiter
- **WHEN** the user runs `python app.py --input data.csv --delimiter ';'`
- **THEN** the tool parses the CSV using `;` as the delimiter

#### Scenario: Missing input file
- **WHEN** the specified input file does not exist
- **THEN** the tool prints a clear error to stderr
- **AND** exits with non-zero status

#### Scenario: Invalid CSV content
- **WHEN** the CSV cannot be parsed (e.g., malformed rows)
- **THEN** the tool prints an error including the failing line number when possible
- **AND** exits with non-zero status
