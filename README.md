# 天氣資料查詢 (Streamlit)

以 Streamlit 顯示 SQLite `data.db` 中 `forecasts` 表的資料，提供地區、日期、與天氣關鍵字篩選。

## 安裝與執行 (Windows PowerShell)

```powershell
# 1) 建立並啟用虛擬環境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) 安裝相依套件（已釘選避免相依衝突）
pip install -r requirements.txt

# 3) 初始化資料庫（建立 weather/forecasts 表）
python .\init_db.py

# 4) 下載中央氣象署資料並寫入 SQLite
#    （可直接使用預設 URL，或自訂環境變數 `CWA_API_URL`）
python .\fetch_cwa.py

# 5) 啟動應用程式
python -m streamlit run .\streamlit_app.py
```

## 目錄
- `streamlit_app.py`：主程式，載入並顯示資料。
- `requirements.txt`：相依套件與相容版本。
- `data.db`：SQLite 資料庫（需包含 `forecasts` 表）。
- `fetch_cwa.py`：從中央氣象署 OpenData 下載 JSON，解析後寫入 `forecasts` 表。
  - 亦會建立並寫入 `weather` 表（欄位：`id`, `location`, `min_temp`, `max_temp`, `description`）。
 - `init_db.py`：初始化 `data.db`，建立 `weather` 與 `forecasts` 表。
## 資料庫結構（SQL）
```sql
CREATE TABLE IF NOT EXISTS weather (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  location TEXT,
  min_temp REAL,
  max_temp REAL,
  description TEXT
);

CREATE TABLE IF NOT EXISTS forecasts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  location TEXT,
  date TEXT,
  weather TEXT,
  max_temp REAL
);
```

## 常見問題
- 看到 `google-api-core` / `google-auth` 相依衝突：
  - 請先確認已啟用虛擬環境（提示前綴有 `.venv`）。
  - 使用 `requirements.txt` 進行安裝，已釘選相容版本。
  - 若仍衝突，可嘗試：
    ```powershell
    pip install --upgrade google-auth==2.31.0 google-api-core==2.19.1
    ```
- 找不到 `data.db` 或 `forecasts` 表：
  - 請確保 `data.db` 在專案根目錄，且表名為 `forecasts`。
  - 可用 DB 檢視工具或 `sqlite3` 驗證。
  - 若資料表不存在，執行 `fetch_cwa.py` 會自動建立表結構。

## 自訂 API URL
- 可透過環境變數 `CWA_API_URL` 指定下載連結，例如：
  ```powershell
  $env:CWA_API_URL = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001?Authorization=<YOUR_TOKEN>&downloadType=WEB&format=JSON"
  python .\fetch_cwa.py
  ```

## 自訂
- 若欄位名稱不同，請在 `streamlit_app.py` 中調整 `expected_cols` 與篩選邏輯。
 - 若存在 `weather` 表，應用會優先讀取 `weather`；否則回退使用 `forecasts`。
