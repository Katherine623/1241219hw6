import os
import json
import sqlite3
from typing import List, Dict, Any

import requests
import pandas as pd
import streamlit as st

DB_PATH = "data.db"
DEFAULT_URL = (
    "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"
    "?Authorization=CWA-9609908F-AEA0-4D0A-A1D5-92D03625C552&downloadType=WEB&format=JSON"
)

st.set_page_config(page_title="Weather (One File)", layout="wide")
st.title("天氣預報查詢（單檔版）")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS weather (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT NOT NULL,
    min_temp REAL,
    max_temp REAL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT NOT NULL,
    date TEXT,
    min_temp REAL,
    max_temp REAL,
    weather TEXT
);
"""

def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def parse_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not isinstance(payload, dict):
        return items
    co = payload.get("cwaopendata", {})
    res = co.get("resources", {}).get("resource", {})
    data = res.get("data", {})
    if not isinstance(data, dict):
        return items

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
                    all_dates = set(wx_map.keys()) | set(max_map.keys()) | set(min_map.keys())
                    for d in sorted(all_dates):
                        weather_desc = wx_map.get(d) or ""
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
                                "weather": weather_desc,
                                "min_temp": min_t,
                                "max_temp": max_t,
                                "description": weather_desc,
                            }
                        )
    return items


def upsert(conn: sqlite3.Connection, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    ensure_schema(conn)
    cur = conn.cursor()
    inserted = 0
    for r in rows:
        cur.execute(
            """
            INSERT INTO forecasts (location, date, min_temp, max_temp, weather)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                r.get("location"),
                r.get("date"),
                r.get("min_temp"),
                r.get("max_temp"),
                r.get("weather"),
            ),
        )
        cur.execute(
            """
            INSERT INTO weather (location, min_temp, max_temp, description)
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

@st.cache_data(show_spinner=False)
def load_df(db_path: str, table: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    finally:
        conn.close()
    return df

@st.cache_data(show_spinner=False)
def load_with_date(db_path: str) -> pd.DataFrame:
    """Prefer weather table, enrich with latest date from forecasts if available."""
    conn = sqlite3.connect(db_path)
    try:
        tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
        names = tables["name"].tolist()
        has_weather = "weather" in names
        has_forecasts = "forecasts" in names
        if has_weather and has_forecasts:
            q = (
                """
                WITH latest AS (
                    SELECT location, MAX(date) AS date
                    FROM forecasts
                    WHERE date IS NOT NULL AND date <> ''
                    GROUP BY location
                )
                SELECT w.id, w.location, latest.date AS date,
                       w.min_temp, w.max_temp, w.description
                FROM weather w
                LEFT JOIN latest ON latest.location = w.location
                ORDER BY w.id
                """
            )
            df = pd.read_sql_query(q, conn)
        elif has_weather:
            df = pd.read_sql_query("SELECT id, location, NULL as date, min_temp, max_temp, description FROM weather ORDER BY id", conn)
        elif has_forecasts:
            df = pd.read_sql_query("SELECT id, location, date, COALESCE(min_temp, NULL) as min_temp, max_temp, weather as description FROM forecasts ORDER BY id", conn)
        else:
            df = pd.DataFrame()
    finally:
        conn.close()
    return df

# UI
st.sidebar.header("篩選條件")
if st.sidebar.button("更新資料", use_container_width=True):
    url = os.getenv("CWA_API_URL", DEFAULT_URL)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        st.error(f"更新失敗: {e}")
    else:
        rows = parse_payload(payload)
        conn = sqlite3.connect(DB_PATH)
        try:
            n = upsert(conn, rows)
        finally:
            conn.close()
        load_df.clear()
        st.success(f"更新完成，寫入 {n} 筆資料。")

# 決定顯示哪張表（若有 weather 就優先）
conn = sqlite3.connect(DB_PATH)
try:
    tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
finally:
    conn.close()
use_table = "weather" if "weather" in tables["name"].tolist() else "forecasts"

# Enriched view with date
df = load_with_date(DB_PATH)

# 動態期望欄位
expected = ["id", "location", "date", "min_temp", "max_temp", "description"]
missing = [c for c in expected if c not in df.columns]
if missing:
    st.warning(f"資料表缺少欄位: {missing}")

# 篩選
locations = sorted(df["location"].dropna().unique()) if "location" in df.columns else []
selected_locations = st.sidebar.multiselect("地區", locations, default=locations[:1] if locations else [])
filtered = df.copy()
if selected_locations and "location" in filtered.columns:
    filtered = filtered[filtered["location"].isin(selected_locations)]

st.subheader("查詢結果")
# 美化表格：溫度欄位漸層背景
styled = filtered.copy()
for col in ("min_temp", "max_temp"):
    if col in styled.columns:
        styled[col] = pd.to_numeric(styled[col], errors="coerce")
try:
    st.dataframe(
        styled.style.background_gradient(cmap="RdYlGn_r", subset=[c for c in ["min_temp", "max_temp"] if c in styled.columns]),
        use_container_width=True,
    )
except Exception:
    st.dataframe(styled, use_container_width=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("筆數", len(filtered))
with col2:
    if "max_temp" in filtered.columns:
        try:
            st.metric("最高溫(平均)", f"{pd.to_numeric(filtered['max_temp']).mean():.1f}")
        except Exception:
            pass
with col3:
    if "date" in filtered.columns and filtered["date"].notna().any():
        try:
            st.metric("日期範圍", f"{pd.to_datetime(filtered['date']).min().date()} 至 {pd.to_datetime(filtered['date']).max().date()}")
        except Exception:
            pass

if "date" in filtered.columns and filtered["date"].notna().any():
    temp_plot = filtered.dropna(subset=["date"]).sort_values("date")
    if {"date", "min_temp", "max_temp"}.issubset(temp_plot.columns):
        chart_df = temp_plot[["date", "min_temp", "max_temp"]].copy().set_index("date")
        st.line_chart(chart_df, use_container_width=True)

st.caption(f"資料來源：SQLite `{DB_PATH}` → 優先顯示 `weather`（並補齊 `date`）")
