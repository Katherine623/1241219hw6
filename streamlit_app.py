import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path

DB_PATH = Path("data.db")

st.set_page_config(page_title="Weather (SQLite)", layout="centered")
st.title("Weather Data Viewer")

if not DB_PATH.exists():
    st.error(f"Database not found: {DB_PATH}")
else:
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT id, location, min_temp, max_temp, description FROM weather ORDER BY id DESC", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Failed to read from DB: {e}")

st.caption("Use 'python app.py serve-info --db data.db' for setup hints.")
