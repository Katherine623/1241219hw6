import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "data.db"
TABLE = "forecasts"

st.set_page_config(page_title="Weather Forecasts", layout="wide")
st.title("天氣預報查詢")

@st.cache_data(show_spinner=False)
def load_data(db_path: str, table: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    finally:
        conn.close()
    return df

# Load data
try:
    df = load_data(DB_PATH, TABLE)
except Exception as e:
    st.error(f"載入資料庫失敗: {e}")
    st.stop()

# Basic columns expected based on screenshot: id, location, date, weather, max_temp
expected_cols = ["id", "location", "date", "weather", "max_temp"]
missing = [c for c in expected_cols if c not in df.columns]
if missing:
    st.warning(f"資料表缺少欄位: {missing}")

# Convert date to datetime if present
if "date" in df.columns:
    try:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    except Exception:
        pass

# Sidebar filters
st.sidebar.header("篩選條件")
locations = sorted(df["location"].dropna().unique()) if "location" in df.columns else []
selected_locations = st.sidebar.multiselect("地區", locations, default=locations[:1] if locations else [])

date_range = None
if "date" in df.columns and df["date"].notna().any():
    min_date = pd.to_datetime(df["date"].min())
    max_date = pd.to_datetime(df["date"].max())
    date_range = st.sidebar.date_input("日期範圍", value=(min_date.date(), max_date.date()))

weather_keywords = st.sidebar.text_input("天氣關鍵字", value="")

# Apply filters
filtered = df.copy()
if selected_locations and "location" in filtered.columns:
    filtered = filtered[filtered["location"].isin(selected_locations)]

if date_range and "date" in filtered.columns:
    start, end = date_range
    if start and end:
        filtered = filtered[(filtered["date"] >= pd.to_datetime(start)) & (filtered["date"] <= pd.to_datetime(end))]

if weather_keywords and "weather" in filtered.columns:
    kw = weather_keywords.strip()
    if kw:
        filtered = filtered[filtered["weather"].astype(str).str.contains(kw, case=False, na=False)]

# Display
st.subheader("查詢結果")
st.dataframe(filtered, use_container_width=True)

# Simple stats
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("筆數", len(filtered))
with col2:
    if "max_temp" in filtered.columns:
        st.metric("最高溫(平均)", f"{filtered['max_temp'].astype(float).mean():.1f}")
with col3:
    if "date" in filtered.columns and filtered["date"].notna().any():
        st.metric("日期範圍", f"{filtered['date'].min().date()} 至 {filtered['date'].max().date()}")

st.caption("資料來源：SQLite `data.db` → 表格 `forecasts`")
