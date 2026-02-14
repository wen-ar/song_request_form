# 🎵 SongMate 點歌系統

## 📌 專案簡介
SongMate 是一個基於 **Flask** 的線上點歌系統，結合前端 HTML/JS 與後端 Python，支援：
- 使用者登入（Microsoft / Google OAuth）
- 男生與女生各自的點歌上限
- 即時顯示剩餘可點數量
- 管理員後台設定（上限、截止時間、公告）
- 前端通知與狀態提示

---

## 🏗️ 系統架構
- **後端 (`app.py`)**
  - Flask 主程式，處理 API 與資料庫存取。
  - 提供 `/submit` 與 `/status` API。
  - 管理員可透過 `admin.html` 設定限制與截止時間。
  - 使用 SQLite 作為資料庫。

- **前端 (`index.html`)**
  - 使用者表單（姓名、性別、歌曲名稱、Spotify 連結）。
  - 呼叫 `/config` 顯示公告與截止時間。
  - 呼叫 `/status` 顯示目前狀態（剩餘可點數量 / 是否達上限）。
  - 即時提示訊息（紅色警告 / 黃色警告 / 藍色提示）。

- **資料庫 (`database.db`)**
  - `songs` 表：紀錄使用者姓名、性別、歌曲、連結、email、時間戳記。
  - `config.json`：儲存系統設定（截止時間、男女上限、公告）。

---

## 🔧 功能流程
1. 使用者進入首頁 `index.html`。
2. 系統呼叫 `/config` → 顯示公告與截止時間。
3. 系統呼叫 `/status` → 顯示目前狀態：
   - 不接受回應 → 紅色警告。
   - 超過截止時間 → 黃色警告。
   - 已達上限 → 紅色警告。
   - 還有剩餘 → 藍色提示。
4. 使用者填寫表單並送出 → 呼叫 `/submit`。
   - 後端檢查限制 → 超過上限則拒絕，否則寫入資料庫。

---

## 🚀 安裝與執行
1. **安裝依賴**
   ```bash
   pip install flask flask-session requests

---

## License
本專案採用 MIT License，詳見 LICENSE 檔案。

---

## 作者與合作
1. wen-ar
2. Microsoft Copilot
3. Google Gemini
4. Chat GPT
