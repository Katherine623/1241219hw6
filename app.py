import argparse
import csv
import json
from pathlib import Path
import sys


def csv_to_json(input_path: Path, output_path: Path | None, delimiter: str, pretty: bool) -> int:
	if not input_path.exists() or not input_path.is_file():
		print(f"Error: input file not found: {input_path}", file=sys.stderr)
		return 2

	if output_path is None:
		output_path = input_path.with_suffix(".json")

	try:
		with input_path.open("r", encoding="utf-8", newline="") as f:
			reader = csv.DictReader(f, delimiter=delimiter)
			rows = list(reader)
	except csv.Error as e:
		print(f"CSV parse error: {e}", file=sys.stderr)
		return 3
	except Exception as e:
		print(f"Failed to read CSV: {e}", file=sys.stderr)
		return 3

	try:
		with output_path.open("w", encoding="utf-8", newline="") as out:
			if pretty:
				json.dump(rows, out, ensure_ascii=False, indent=2)
			else:
				json.dump(rows, out, ensure_ascii=False, separators=(",", ":"))
	except Exception as e:
		print(f"Failed to write JSON: {e}", file=sys.stderr)
		return 4

	return 0


def build_parser() -> argparse.ArgumentParser:
	p = argparse.ArgumentParser(description="Convert CSV to JSON")
	p.add_argument("--input", required=True, help="Path to input CSV")
	p.add_argument("--output", help="Output JSON file path (default: same as input with .json)")
	p.add_argument("--delimiter", default=",", help="CSV delimiter (default: ,)")
	p.add_argument("--pretty", action="store_true", help="Pretty-print JSON with indentation")
	return p


def main(argv: list[str] | None = None) -> int:
	parser = build_parser()
	args = parser.parse_args(argv)

	input_path = Path(args.input)
	output_path = Path(args.output) if args.output else None
	delimiter = args.delimiter
	pretty = args.pretty

	return csv_to_json(input_path, output_path, delimiter, pretty)


if __name__ == "__main__":
	sys.exit(main())

