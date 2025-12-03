import argparse
import csv
import json
from pathlib import Path
import sys
import sqlite3
import os


# =====================
# CSV -> JSON CLI (from previous step)
# =====================
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


# =====================
# Weather JSON -> SQLite pipeline
# =====================
try:
	import requests  # type: ignore
except Exception:
	requests = None


def fetch_weather_json(api_url: str, out_file: Path) -> int:
	if requests is None:
		print("Error: requests not installed. Please run 'pip install requests'", file=sys.stderr)
		return 5
	try:
		r = requests.get(api_url, timeout=30)
		r.raise_for_status()
		data = r.json()
		out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
		return 0
	except Exception as e:
		print(f"Failed to fetch JSON: {e}", file=sys.stderr)
		return 6


def parse_weather(json_path: Path) -> list[dict]:
	if not json_path.exists():
		raise FileNotFoundError(f"JSON file not found: {json_path}")
	data = json.loads(json_path.read_text(encoding="utf-8"))
	# NOTE: The exact CWB API schema may vary. We extract a reasonable subset.
	# Expected fields: location name + min/max temperature. Adjust parsing as needed.
	rows: list[dict] = []
	# Try common CWB format paths
	# If schema differs, user can modify here.
	try:
		records = data.get("records") or {}
		locations = records.get("location") or []
		for loc in locations:
			name = loc.get("locationName")
			min_temp = None
			max_temp = None
			desc = None

			weather_elements = loc.get("weatherElement") or []
			for elem in weather_elements:
				if elem.get("elementName") in ("MinT", "min_temp"):
					v = elem.get("time") or elem.get("value")
					min_temp = extract_first_value(v)
				if elem.get("elementName") in ("MaxT", "max_temp"):
					v = elem.get("time") or elem.get("value")
					max_temp = extract_first_value(v)

			rows.append(
				{
					"location": name or "",
					"min_temp": try_float(min_temp),
					"max_temp": try_float(max_temp),
					"description": desc or "",
				}
			)
	except Exception:
		# Fallback: attempt generic parsing if structure is different
		if isinstance(data, list):
			for item in data:
				rows.append(
					{
						"location": item.get("location") or item.get("name") or "",
						"min_temp": try_float(item.get("min_temp")),
						"max_temp": try_float(item.get("max_temp")),
						"description": item.get("description") or "",
					}
				)
		else:
			# As a last resort, make a single row summary
			rows.append(
				{
					"location": data.get("location") or data.get("name") or "",
					"min_temp": try_float(data.get("min_temp")),
					"max_temp": try_float(data.get("max_temp")),
					"description": data.get("description") or "",
				}
			)

	return rows


def extract_first_value(v) -> str | None:
	# Helper to navigate CWB element/time arrays
	try:
		if isinstance(v, list) and v:
			first = v[0]
			val = first.get("elementValue") or first.get("value")
			if isinstance(val, list) and val:
				return val[0].get("value")
			if isinstance(val, dict):
				return val.get("value")
			return val
		if isinstance(v, dict):
			val = v.get("value") or v.get("elementValue")
			if isinstance(val, dict):
				return val.get("value")
			return val
		if isinstance(v, (str, int, float)):
			return str(v)
	except Exception:
		return None
	return None


def try_float(x) -> float | None:
	try:
		if x is None:
			return None
		return float(x)
	except Exception:
		return None


def init_db(db_path: Path) -> None:
	conn = sqlite3.connect(db_path)
	try:
		conn.execute(
			"""
			CREATE TABLE IF NOT EXISTS weather (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				location TEXT,
				min_temp REAL,
				max_temp REAL,
				description TEXT
			);
			"""
		)
		conn.commit()
	finally:
		conn.close()


def store_rows(db_path: Path, rows: list[dict]) -> int:
	try:
		conn = sqlite3.connect(db_path)
		with conn:
			conn.executemany(
				"INSERT INTO weather (location, min_temp, max_temp, description) VALUES (?, ?, ?, ?)",
				[
					(
						r.get("location"),
						r.get("min_temp"),
						r.get("max_temp"),
						r.get("description"),
					)
					for r in rows
				],
			)
		return 0
	except Exception as e:
		print(f"Failed to store rows: {e}", file=sys.stderr)
		return 7


# =====================
# Streamlit launcher helper
# =====================
def print_streamlit_instructions(db_path: Path) -> None:
	print("\nTo launch the Streamlit app:")
	print("  1) Install streamlit: pip install streamlit")
	print("  2) Run: streamlit run streamlit_app.py")
	print(f"  (It will read from: {db_path})\n")


# =====================
# Argparse commands
# =====================
def build_parser() -> argparse.ArgumentParser:
	p = argparse.ArgumentParser(description="Homework 6 Toolkit")
	sub = p.add_subparsers(dest="cmd", required=True)

	# csv->json
	p_csv = sub.add_parser("csv2json", help="Convert CSV to JSON")
	p_csv.add_argument("--input", required=True, help="Path to input CSV")
	p_csv.add_argument("--output", help="Output JSON file path (default: input with .json)")
	p_csv.add_argument("--delimiter", default=",", help="CSV delimiter (default: ,)")
	p_csv.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

	# weather fetch
	p_fetch = sub.add_parser("fetch", help="Fetch weather JSON from CWB API")
	p_fetch.add_argument("--url", required=True, help="CWB API url (e.g., F-A0010-001)")
	p_fetch.add_argument("--out", default="weather.json", help="Output JSON file path")

	# weather parse+store
	p_store = sub.add_parser("store", help="Parse weather JSON and store into SQLite")
	p_store.add_argument("--json", default="weather.json", help="Input JSON file path")
	p_store.add_argument("--db", default="data.db", help="SQLite database path")

	# streamlit hint
	p_ui = sub.add_parser("serve-info", help="Print Streamlit run instructions")
	p_ui.add_argument("--db", default="data.db", help="SQLite database path")

	# streamlit UI from this file
	p_ui2 = sub.add_parser("ui", help="Run Streamlit UI from this file")
	p_ui2.add_argument("--db", default="data.db", help="SQLite database path")

	return p


def main(argv: list[str] | None = None) -> int:
	parser = build_parser()
	args = parser.parse_args(argv)

	if args.cmd == "csv2json":
		input_path = Path(args.input)
		output_path = Path(args.output) if args.output else None
		return csv_to_json(input_path, output_path, args.delimiter, args.pretty)

	if args.cmd == "fetch":
		out_file = Path(args.out)
		return fetch_weather_json(args.url, out_file)

	if args.cmd == "store":
		json_path = Path(args.json)
		db_path = Path(args.db)
		init_db(db_path)
		try:
			rows = parse_weather(json_path)
		except Exception as e:
			print(f"Failed to parse weather JSON: {e}", file=sys.stderr)
			return 8
		return store_rows(db_path, rows)

	if args.cmd == "serve-info":
		print_streamlit_instructions(Path(args.db))
		return 0

	if args.cmd == "ui":
		# Launch Streamlit against this file to use the integrated UI
		# Prefer 'streamlit run app.py' behavior. If streamlit not installed, instruct the user.
		try:
			import streamlit
		except Exception:
			print("Error: streamlit not installed. Run 'pip install -r requirements.txt'", file=sys.stderr)
			return 9
		# Re-exec via streamlit run for consistent experience
		# On Windows PowerShell, users typically run: streamlit run app.py
		# Here we print guidance instead of trying to spawn a nested process.
		print("Run: streamlit run app.py", file=sys.stderr)
		return 0

	parser.print_help()
	return 1


if __name__ == "__main__":
	# If executed by Streamlit (`streamlit run app.py`), render UI
	if os.environ.get("STREAMLIT_SERVER_ENABLED") or os.environ.get("STREAMLIT_RUNTIME"):
		try:
			import streamlit as st
			import pandas as pd

			DB_PATH = Path("data.db")
			JSON_PATH = Path("weather.json")

			st.set_page_config(page_title="Weather (SQLite)", layout="centered")
			st.title("Weather Pipeline (Fetch → Store → View)")

			with st.form("fetch_form"):
				st.subheader("1) 下載中央氣象局 JSON")
				api_url = st.text_input("API 連結 (F-A0010-001 JSON)", value="")
				out_file = st.text_input("輸出 JSON 路徑", value=str(JSON_PATH))
				fetch_submit = st.form_submit_button("下載 JSON")
				if fetch_submit:
					if not api_url:
						st.error("請輸入 API 連結")
					else:
						code = fetch_weather_json(api_url, Path(out_file))
						if code == 0:
							st.success(f"下載完成：{out_file}")
						else:
							st.error("下載失敗，請檢查連結或網路")

			with st.form("store_form"):
				st.subheader("2) 解析並存入 SQLite3")
				json_path = st.text_input("JSON 檔案路徑", value=str(JSON_PATH))
				db_path = st.text_input("SQLite 檔案路徑", value=str(DB_PATH))
				store_submit = st.form_submit_button("解析並存入")
				if store_submit:
					try:
						rows = parse_weather(Path(json_path))
						init_db(Path(db_path))
						code = store_rows(Path(db_path), rows)
						if code == 0:
							st.success(f"已存入 {len(rows)} 筆資料 → {db_path}")
						else:
							st.error("寫入資料庫失敗")
					except Exception as e:
						st.error(f"解析失敗：{e}")

			st.subheader("3) 檢視 SQLite 內容")
			if not Path(DB_PATH).exists():
				st.info("尚未建立資料庫，請先執行步驟 2")
			else:
				try:
					conn = sqlite3.connect(DB_PATH)
					df = pd.read_sql_query(
						"SELECT id, location, min_temp, max_temp, description FROM weather ORDER BY id DESC",
						conn,
					)
					conn.close()
					st.dataframe(df, use_container_width=True)
				except Exception as e:
					st.error(f"讀取資料庫失敗：{e}")

			st.caption("小提示：也可用 CLI 指令 python app.py fetch/store 來操作")
		except Exception:
			# Fallback to CLI main if not under streamlit
			sys.exit(main())
	else:
		sys.exit(main())

