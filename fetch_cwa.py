import os
import sys
import json
import sqlite3
from typing import List, Dict, Any
import requests

DB_PATH = "data.db"
TABLE = "forecasts"
WEATHER_TABLE = "weather"
# Default URL; can be overridden by env `CWA_API_URL`
DEFAULT_URL = (
    "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"
    "?Authorization=CWA-9609908F-AEA0-4D0A-A1D5-92D03625C552&downloadType=WEB&format=JSON"
)

def ensure_schema(conn: sqlite3.Connection) -> None:
    # Existing forecasts table (for backward compatibility)
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
    # New weather table per assignment requirements
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {WEATHER_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT,
            min_temp REAL,
            max_temp REAL,
            description TEXT
        )
        """
    )
    conn.commit()

def parse_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse CWA F-A0010-001 via cwaopendata.resources.resource.data.

    This dataset often nests arrays under `data`, e.g., `agrWeatherForecasts`,
    `weatherForecasts`, or provides temperature profiles.
    We'll search for lists of dicts containing a location name plus fields for
    weather/temperature and extract MinT/MaxT/Wx when present.
    """
    items: List[Dict[str, Any]] = []
    if not isinstance(payload, dict):
        return items
    co = payload.get("cwaopendata", {})
    res = co.get("resources", {}).get("resource", {})
    data = res.get("data", {})

    def extract_from_list(lst: List[Dict[str, Any]]):
        for loc in lst:
            if not isinstance(loc, dict):
                continue
            name = loc.get("locationName") or loc.get("location") or loc.get("name") or ""
            weather_desc = None
            min_temp = None
            max_temp = None
            date_val = loc.get("date") or None

            # Direct fields
            for k in ("Wx", "weather", "description"):
                if k in loc and isinstance(loc[k], (str, int, float)):
                    weather_desc = str(loc[k])
                    break
            for k in ("MinT", "min_temp"):
                v = loc.get(k)
                try:
                    if v is not None:
                        min_temp = float(v)
                except (TypeError, ValueError):
                    pass
            for k in ("MaxT", "max_temp"):
                v = loc.get(k)
                try:
                    if v is not None:
                        max_temp = float(v)
                except (TypeError, ValueError):
                    pass

            # Nested weatherElement/time format
            we_list = loc.get("weatherElement") or []
            if isinstance(we_list, list):
                for el in we_list:
                    el_name = el.get("elementName")
                    times = el.get("time") or []
                    if not el_name or not isinstance(times, list) or not times:
                        continue
                    t0 = times[0]
                    if isinstance(t0, dict):
                        date_val = t0.get("startTime") or t0.get("dataTime") or date_val
                        val = None
                        ev = t0.get("elementValue")
                        if isinstance(ev, list) and ev:
                            val = ev[0].get("value")
                        elif isinstance(ev, dict):
                            val = ev.get("value")
                        elif "value" in t0:
                            val = t0.get("value")
                        if el_name == "Wx" and val is not None:
                            weather_desc = str(val)
                        elif el_name == "MinT" and val is not None:
                            try:
                                min_temp = float(val)
                            except (TypeError, ValueError):
                                pass
                        elif el_name == "MaxT" and val is not None:
                            try:
                                max_temp = float(val)
                            except (TypeError, ValueError):
                                pass

            items.append(
                {
                    "location": name,
                    "date": date_val or "",
                    "weather": weather_desc or "",
                    "min_temp": min_temp,
                    "max_temp": max_temp,
                    "description": weather_desc or "",
                }
            )

    # Try common arrays under data
    if isinstance(data, dict):
        # Precise mapping: agrWeatherForecasts -> weatherForecasts -> location[]
        agr = data.get("agrWeatherForecasts")
        if isinstance(agr, dict):
            wf = agr.get("weatherForecasts")
            if isinstance(wf, dict):
                locs = wf.get("location")
                if isinstance(locs, list):
                    for loc in locs:
                        name = loc.get("locationName") or ""
                        we = loc.get("weatherElements", {})
                        wx_daily = (we.get("Wx", {}).get("daily") or []) if isinstance(we, dict) else []
                        max_daily = (we.get("MaxT", {}).get("daily") or []) if isinstance(we, dict) else []
                        min_daily = (we.get("MinT", {}).get("daily") or []) if isinstance(we, dict) else []

                        # Index by date
                        def by_date(lst, key):
                            m = {}
                            for item in lst:
                                d = item.get("dataDate")
                                if d is None:
                                    continue
                                m[d] = item.get(key)
                            return m

                        wx_map = by_date(wx_daily, "weather")
                        max_map = by_date(max_daily, "temperature")
                        min_map = by_date(min_daily, "temperature")
                        # Union of dates
                        all_dates = set(wx_map.keys()) | set(max_map.keys()) | set(min_map.keys())
                        for d in sorted(all_dates):
                            weather_desc = wx_map.get(d)
                            min_t = min_map.get(d)
                            max_t = max_map.get(d)
                            try:
                                min_t = float(min_t) if min_t is not None else None
                            except (TypeError, ValueError):
                                min_t = None
                            try:
                                max_t = float(max_t) if max_t is not None else None
                            except (TypeError, ValueError):
                                max_t = None
                            items.append(
                                {
                                    "location": name,
                                    "date": d,
                                    "weather": weather_desc or "",
                                    "min_temp": min_t,
                                    "max_temp": max_t,
                                    "description": weather_desc or "",
                                }
                            )
        # Fallbacks: generic array scanning
        if not items:
            for key in ("weatherForecasts", "weather", "locations", "location"):
                arr = data.get(key)
                if isinstance(arr, list) and arr:
                    extract_from_list(arr)
                    break
            if not items:
                for v in data.values():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        extract_from_list(v)
                        break
    return items

def upsert_forecasts(conn: sqlite3.Connection, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    ensure_schema(conn)
    cur = conn.cursor()
    inserted = 0
    for r in rows:
        # Insert into legacy forecasts
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
        # Insert into new weather table
        cur.execute(
            f"""
            INSERT INTO {WEATHER_TABLE} (location, min_temp, max_temp, description)
            VALUES (?, ?, ?, ?)
            """,
            (
                r.get("location"),
                r.get("min_temp"),
                r.get("max_temp"),
                r.get("description"),
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
