import os
import sys
import json
import sqlite3
from typing import List, Dict, Any
import requests

DB_PATH = "data.db"
TABLE = "forecasts"
# Default URL; can be overridden by env `CWA_API_URL`
DEFAULT_URL = (
    "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"
    "?Authorization=CWA-9609908F-AEA0-4D0A-A1D5-92D03625C552&downloadType=WEB&format=JSON"
)

def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            date TEXT,
            weather TEXT,
            max_temp REAL
        )
        """
    )
    conn.commit()

def parse_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    # The exact JSON structure may vary; try to map common fields.
    # We'll be defensive and look for plausible paths.
    items: List[Dict[str, Any]] = []
    data = payload
    try:
        # Some CWA datasets use 'cwaopendata' → 'datasetDescription' / 'resources' / 'resource'
        # Others directly provide 'records' or similar. We'll probe a few options.
        if "cwaopendata" in data:
            data = data["cwaopendata"]
        # If records present
        if "records" in data:
            records = data["records"]
            # Try common nesting: locations -> location
            locs = None
            for key in ("locations", "Location", "location", "data"):
                if key in records:
                    locs = records[key]
                    break
            if locs is None:
                # If records is a list already
                if isinstance(records, list):
                    locs = records
                else:
                    locs = []
            # Normalize to list of locations
            if isinstance(locs, dict) and "location" in locs:
                loc_list = locs["location"]
            else:
                loc_list = locs if isinstance(locs, list) else []

            for loc in loc_list:
                name = (
                    loc.get("locationName")
                    or loc.get("name")
                    or loc.get("location")
                    or ""
                )
                # Weather elements
                weather_desc = None
                max_temp = None
                date_val = None

                # Explore weather elements
                we_list = loc.get("weatherElement") or loc.get("elements") or []
                if isinstance(we_list, list):
                    for el in we_list:
                        el_name = el.get("elementName") or el.get("name")
                        times = el.get("time") or el.get("values") or []
                        if el_name and isinstance(times, list) and times:
                            # Prefer first time block
                            t0 = times[0]
                            if isinstance(t0, dict):
                                # time dicts often have 'startTime'/'endTime' or 'dataTime'
                                date_val = (
                                    t0.get("startTime")
                                    or t0.get("dataTime")
                                    or t0.get("time")
                                    or date_val
                                )
                                # Values may be nested
                                val = None
                                if "elementValue" in t0:
                                    ev = t0["elementValue"]
                                    if isinstance(ev, list) and ev:
                                        val = ev[0].get("value")
                                    elif isinstance(ev, dict):
                                        val = ev.get("value")
                                elif "value" in t0:
                                    val = t0.get("value")

                                if el_name in ("Wx", "weather", "Weather"):  # weather description
                                    weather_desc = str(val) if val is not None else weather_desc
                                if el_name in ("T", "MaxT", "max_temp", "MaxTemperature"):
                                    try:
                                        max_temp = float(val) if val is not None else max_temp
                                    except (TypeError, ValueError):
                                        pass
                # Fallbacks
                weather_desc = weather_desc or loc.get("weather")
                if max_temp is None and isinstance(loc.get("max_temp"), (int, float)):
                    max_temp = float(loc["max_temp"])

                if name or weather_desc or date_val:
                    items.append(
                        {
                            "location": name or "",
                            "date": date_val or "",
                            "weather": weather_desc or "",
                            "max_temp": max_temp if max_temp is not None else None,
                        }
                    )
    except Exception:
        # If structure is unknown, try a very simple heuristic over top-level arrays
        if isinstance(payload, list):
            for row in payload:
                items.append(
                    {
                        "location": str(row.get("location", "")),
                        "date": str(row.get("date", "")),
                        "weather": str(row.get("weather", "")),
                        "max_temp": row.get("max_temp"),
                    }
                )
    return items

def upsert_forecasts(conn: sqlite3.Connection, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    ensure_schema(conn)
    cur = conn.cursor()
    inserted = 0
    for r in rows:
        cur.execute(
            f"""
            INSERT INTO {TABLE} (location, date, weather, max_temp)
            VALUES (?, ?, ?, ?)
            """,
            (
                r.get("location"),
                r.get("date"),
                r.get("weather"),
                r.get("max_temp"),
            ),
        )
        inserted += 1
    conn.commit()
    return inserted

def main() -> int:
    url = os.getenv("CWA_API_URL", DEFAULT_URL)
    print(f"Fetching: {url}")
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return 1
    try:
        payload = resp.json()
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        return 1

    rows = parse_payload(payload)
    print(f"Parsed rows: {len(rows)}")

    conn = sqlite3.connect(DB_PATH)
    try:
        n = upsert_forecasts(conn, rows)
        print(f"Inserted {n} rows into {TABLE} in {DB_PATH}")
    finally:
        conn.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
