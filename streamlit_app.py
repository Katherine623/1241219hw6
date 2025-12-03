import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path

from app import (
    fetch_weather_json,
    parse_weather,
    init_db,
    store_rows,
)

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
