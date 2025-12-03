import sqlite3
import pandas as pd
import streamlit as st
import os
import fetch_cwa

DB_PATH = "data.db"
TABLE = "forecasts"
ALT_TABLE = "weather"

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

@st.cache_data(show_spinner=False)
def load_with_date(db_path: str) -> pd.DataFrame:
    """Prefer `weather` but enrich with `date` from `forecasts` if available."""
    conn = sqlite3.connect(db_path)
    try:
        tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
        names = tables["name"].tolist()
        has_weather = ALT_TABLE in names
        has_forecasts = TABLE in names
        if has_weather and has_forecasts:
            # Join on location; choose most recent date per location
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

# Load data
try:
    # Prefer new `weather` table if available; fallback to `forecasts`.
    conn = sqlite3.connect(DB_PATH)
    tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
    conn.close()
    use_table = ALT_TABLE if ALT_TABLE in tables["name"].tolist() else TABLE
    # Load enriched data including date when possible
    df = load_with_date(DB_PATH)
except Exception as e:
    st.error(f"載入資料庫失敗: {e}")
    st.stop()

# 基本欄位期望：依實際載入表決定期望欄位
expected_cols = ["id", "location", "date", "min_temp", "max_temp", "description"]
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

if st.sidebar.button("更新資料", use_container_width=True):
    url = os.getenv("CWA_API_URL", None)
    code = fetch_cwa.main() if url is None else fetch_cwa.main()
    if code == 0:
        st.success("資料已更新，重新載入中…")
        load_data.clear(); load_with_date.clear()
        try:
            df = load_with_date(DB_PATH)
        except Exception as e:
            st.error(f"載入資料庫失敗: {e}")
            st.stop()
    else:
        st.error("資料更新失敗，請稍後重試或檢查網路/API 設定。")

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
# 美化表格：溫度欄位漸層背景，提高可讀性
styled = filtered.copy()
for col in ("min_temp", "max_temp"):
    if col in styled.columns:
        # 確保為數值
        styled[col] = pd.to_numeric(styled[col], errors="coerce")
try:
    st.dataframe(
        styled.style.background_gradient(cmap="RdYlGn_r", subset=[c for c in ["min_temp", "max_temp"] if c in styled.columns]),
        use_container_width=True,
    )
except Exception:
    st.dataframe(styled, use_container_width=True)

# Simple stats
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("筆數", len(filtered))
with col2:
    if "max_temp" in filtered.columns:
        st.metric("最高溫(平均)", f"{pd.to_numeric(filtered['max_temp'], errors='coerce').mean():.1f}")
with col3:
    if "date" in filtered.columns and filtered["date"].notna().any():
        st.metric("日期範圍", f"{filtered['date'].min().date()} 至 {filtered['date'].max().date()}")

# 視覺化：若有日期，畫出溫度隨時間的變化
if "date" in filtered.columns and filtered["date"].notna().any():
    temp_plot = filtered.dropna(subset=["date"]).sort_values("date")
    if {"date", "min_temp", "max_temp"}.issubset(temp_plot.columns):
        chart_df = temp_plot[["date", "min_temp", "max_temp"]].copy()
        chart_df = chart_df.set_index("date")
        st.line_chart(chart_df, use_container_width=True)

st.caption(f"資料來源：SQLite `{DB_PATH}` → 優先顯示 `weather`（並補齊 `date`）")
