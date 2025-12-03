# Project Context

## Purpose
Homework 6 repository for the 在職專班/資工/資訊處理 課程作業。以最小可行的 Python 專案為起點，透過 OpenSpec 與 GitHub Copilot 規劃與實作後續功能（例如資料處理、檔案轉換或簡易應用程式）。

## Tech Stack
- Python 3.12+（本機已安裝多個 Python 版本）
- Node.js 22 + npm（用於 `@fission-ai/openspec` CLI）
- VS Code（Windows 10/11，OneDrive 同步目錄）
- Git + GitHub（主分支 `main`）

## Project Conventions

### Code Style
- 遵循 PEP 8；縮排 4 空格；字元編碼 UTF-8。
- 建議行寬 88；檔名使用英文或可讀名稱，避免空白。
- 後續若需要，可加入 `black`/`ruff` 作為格式與靜態檢查工具。

### Architecture Patterns
- 目前為單檔/小型腳本結構（`app.py` 暫無內容）。
- 若出現多個功能，優先以模組化方式拆分到 `src/` 或以功能為單位的檔案。

### Testing Strategy
- 預計使用 `pytest` 撰寫單元測試（尚未建立測試目錄）。
- 變更時優先為新增功能補上最小可行測試。

### Git Workflow
- Trunk-based：以 `main` 為主分支，小變更可直接 commit/push。
- Commit 訊息以動詞開頭，必要時可採用 Conventional Commits（如 `feat: ...`, `fix: ...`, `chore: ...`）。
- PR 由個人倉庫維護，可視需要開分支進行較大變更再合併。

## Domain Context
- 課程背景：在職專班／資工／資訊處理（w3）。
- 目前倉庫包含 PDF 檔（`ChatGPT-整理成CSV檔.pdf`），可能與資料處理作業或說明相關。

## Important Constraints
- Windows + OneDrive 同步路徑，包含中文與非 ASCII 字元；請避免硬編碼路徑與注意編碼/路徑相容性。
- 行尾序可能為 CRLF（Windows）；跨平台腳本請顧及 eol 差異。
- 若後續納入大型二進位檔案，建議評估 Git LFS。

## External Dependencies
- 目前尚無必備第三方雲端服務或 API。若新增，請在此登錄用途、金鑰管理與速率限制。
