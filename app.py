from flask import Flask, request, jsonify, render_template
from toast import show_notification
from flask import Flask, session, redirect, url_for
from datetime import timedelta
from authlib.integrations.flask_client import OAuth
import requests
import sqlite3
import pandas as pd
import base64
import json
from datetime import datetime
from flask import send_file
import requests
import time
import certifi

app = Flask(__name__)

CLIENT_ID = "c96951bf51d74a4b87ceb1f7dc6a0fea"
CLIENT_SECRET = "1ebde6feea114d2ca5512c5af5eae6b0"

spotify_token = None
spotify_token_expiry = 0

app = Flask(__name__)
app.secret_key = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # 用於 session
app.permanentsessionlifetime = timedelta(days=7)

# 設定 OAuth
oauth = OAuth(app)
microsoft = oauth.register(
    name="microsoft",
    client_id="d952e562-dd22-4a94-9dff-36593a201f31",   # Application (client) ID
    client_secret="AiK8Q~1zOKx3Dq5fm.pjhjCK6cQsPvgW1pWCcab0",                   # 需要在 Azure 建立
    server_metadata_url="https://login.microsoftonline.com/00057328-0b9c-443f-ae16-0b2d1761430d/v2.0/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile User.Read"
    }
)

@app.route("/login/microsoft")
def login_microsoft():
    redirecturi = urlfor("authorizemicrosoft", _external=True)
    return microsoft.authorizeredirect(redirecturi)

@app.route("/login/callback/microsoft")
def authorize_microsoft():
    try:
        token = microsoft.authorizeaccesstoken()
        user_info = microsoft.get("https://graph.microsoft.com/v1.0/me").json()
     session.permanent = True
     session["user"] = user_info

     return redirect(url_for("index"))
    except Exception as e:
        return f"登入失敗：{str(e)}"

@app.route("/logout")
def logout():
 session.pop("user", None)
 return redirect(url_for("index"))
def get_spotify_token():
    global spotify_token, spotify_token_expiry
    if spotify_token and time.time() < spotify_token_expiry:
        return spotify_token

    res = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET),
        verify=certifi.where()
    )
    token_data = res.json()
    spotify_token = token_data["access_token"]
    spotify_token_expiry = time.time() + token_data["expires_in"] - 60  # 提前 1 分鐘更新
    return spotify_token

def safe_spotify_request(url, headers, params=None):
    for attempt in range(3):  # 最多重試 3 次
        try:
            res = requests.get(url, headers=headers, params=params, timeout=5)
            if res.status_code == 200:
                return res.json()
        except requests.exceptions.SSLError:
            continue
        except requests.exceptions.RequestException:
            continue
    return {"error": "Spotify API 請求失敗"}

# ======================
# SQLite 初始化
# ======================
def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            song TEXT NOT NULL,
            link TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ======================
# 載入設定檔 (config.json)
# ======================
def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}

    # 預設值補齊
    config.setdefault("accept_responses", True)
    config.setdefault("deadline", "")
    config.setdefault("notification_content", "")
    config.setdefault("version", "1.0.0")

    return config

# ======================
# Spotify 搜尋 API
# ======================
@app.route("/search")
def search():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "缺少搜尋關鍵字 q"}), 400

    token = get_spotify_token()
    headers = {"Authorization": f"Bearer {token}"}

    data = safe_spotify_request(
        "https://api.spotify.com/v1/search",
        headers,
        params={"q": query, "type": "track", "limit": 5}
    )

    # 如果 API 請求失敗，直接回傳錯誤
    if "error" in data:
        return jsonify(data), 500

    results = []
    for item in data.get("tracks", {}).get("items", []):
        results.append({
            "name": item["name"],
            "artist": item["artists"][0]["name"],
            "url": item["external_urls"]["spotify"]
        })

    return jsonify(results)

# ======================
# 表單提交 API
# ======================
@app.route("/submit", methods=["POST"])
def submit():
    config = load_config()

    if not config["accept_responses"]:
        return jsonify({"error": "目前已停止收集回應"}), 403

    now = datetime.now()
    deadline_dt = datetime.strptime(config["deadline"], "%Y-%m-%d %H:%M:%S")
    if now > deadline_dt:
        return jsonify({"error": "已超過截止日期"}), 403

    data = request.json
    name = data.get("name")
    gender = data.get("gender")
    song = data.get("songName")
    link = data.get("songLink")

    if not all([name, gender, song, link]):
        return jsonify({"error": "欄位不可為空"}), 400

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO songs (name, gender, song, link) VALUES (?, ?, ?, ?)",
                (name, gender, song, link))
    conn.commit()
    conn.close()

    return jsonify({"success": True})

# ======================
# 重置 ID API
# ======================

@app.route("/reset_ids", methods=["POST"])
def reset_ids():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 讀取所有資料
    cursor.execute("SELECT * FROM songs ORDER BY id")
    rows = cursor.fetchall()

    # 清空資料表
    cursor.execute("DELETE FROM songs")

    # 重新插入並重編 ID
    for i, row in enumerate(rows, start=1):
        cursor.execute(
            "INSERT INTO songs (id, name, gender, song, link, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (i, row[1], row[2], row[3], row[4], row[5])
        )

    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ======================
# 匯出 Excel API
# ======================

@app.route("/export")
def export():
    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query(
        "SELECT id AS ID, name AS 姓名, gender AS 性別, song AS 歌名, link AS 歌曲連結, timestamp AS 填寫時間 FROM songs",
        conn
    )
    conn.close()

    filename = "線上點歌.xlsx"
    df.to_excel(filename, index=False)

    return send_file(filename, as_attachment=True)

# ======================
# 管理設定 API
# ======================
@app.route("/config", methods=["GET", "POST"])
def config_route():
    if request.method == "GET":
        return jsonify(load_config())
    else:
        data = request.json
        config = load_config()

        # 更新基本設定
        if "accept_responses" in data:
            config["accept_responses"] = data["accept_responses"]
        if "deadline" in data:
            config["deadline"] = data["deadline"]

        # 更新通知設定
        if "notification_content" in data:
            config["notification_content"] = data["notification_content"]
        if "version" in data:
            config["version"] = data["version"]

        # 寫回檔案
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return jsonify({"success": True})

# ======================
# 刪除 API
# ======================
@app.route("/delete/<int:song_id>", methods=["DELETE"])
def delete_song(song_id):
    try:
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        conn.commit()
        deleted_count = cur.rowcount
        conn.close()

        if deleted_count == 0:
            return jsonify({"error": f"找不到 id={song_id} 的紀錄"}), 404
        return jsonify({"success": True, "deleted_id": song_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete_all", methods=["DELETE"])
def delete_all_songs():
    try:
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("DELETE FROM songs")
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "所有結果已刪除"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ======================
# 結果清單 & 單一結果 API
# ======================

@app.route("/results")
def get_results():
    gender = request.args.get("gender")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if gender:
        cursor.execute("SELECT * FROM songs WHERE gender = ? ORDER BY id", (gender,))
    else:
        cursor.execute("SELECT * FROM songs ORDER BY id")

    rows = cursor.fetchall()
    conn.close()

    results = []
    for i, row in enumerate(rows, start=1):
        results.append({
            "index": i,
            "id": row[0],
            "name": row[1],
            "gender": row[2],
            "song": row[3],
            "link": row[4],
            "timestamp": row[5]
        })
    return jsonify(results)

@app.route("/result/<int:song_id>")
def get_result(song_id):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT id, name, gender, song, link, timestamp FROM songs WHERE id = ?", (song_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "找不到此結果"}), 404

    return jsonify({
        "id": row[0],
        "name": row[1],
        "gender": row[2],
        "song": row[3],
        "link": row[4],
        "timestamp": row[5]
    })

@app.route("/notify")
def notify():
    result = show_notification("**操作成功！**\n請查看結果", level="success")
    return jsonify(result)

# ======================
# 管理頁面路由
# ======================
@app.route("/admin")
def admin_page():
    return render_template("admin.html")

# ======================
# 前端入口頁面
# ======================
@app.route("/")
def index():
    return render_template("index.html")

# ======================
# 啟動 Flask
# ======================
if __name__ == "__main__":
    app.run(debug=True)
