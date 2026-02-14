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

# 管理員清單
ADMIN_EMAILS = ["huiyingl936@gmail.com", "S0702265@o365.kh.edu.tw", "lynnn0215@gmail.com"]

# ======================
# 設定 OAuth
# ======================
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

google = oauth.register(
    name="google",
    client_id="628573695360-r3kaekifha3u164l09parhvjvlkerbjl.apps.googleusercontent.com",
    client_secret="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",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# ======================
# 登入
# ======================
@app.route("/login/microsoft")
def login_microsoft():
    redirect_uri = url_for("authorize_microsoft", _external=True)
    return microsoft.authorize_redirect(redirect_uri)

@app.route("/login/google")
def login_google():
    redirect_uri = url_for("authorize_google", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/login/callback/microsoft")
def authorize_microsoft():
    try:
        token = microsoft.authorize_access_token()
        user_info = microsoft.get("https://graph.microsoft.com/v1.0/me").json()
        session.permanent = True
        if "userPrincipalName" in user_info:
            user_info["email"] = user_info["userPrincipalName"]
        session["user"] = user_info
        return redirect(url_for("index"))
    except Exception as e:
        return f"登入失敗：{str(e)}"

@app.route("/authorize/google")
def authorize_google():
    token = google.authorize_access_token()
    user_info = google.get("https://www.googleapis.com/oauth2/v1/userinfo").json()
    session["user"] = user_info
    return redirect(url_for("index"))

# ======================
# 登出
# ======================
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))

# ======================
# Spotify 請求
# ======================
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
            email TEXT,
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
    # 新增男女限制設定的預設值
    config.setdefault("male_limit_enabled", False)
    config.setdefault("male_limit_count", 0)
    config.setdefault("female_limit_enabled", False)
    config.setdefault("female_limit_count", 0)

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

    # 檢查是否接受回應
    if not config.get("accept_responses", True):
        return jsonify({"error": "目前已停止收集回應"}), 403

    # 檢查截止時間
    if config.get("deadline"):
        try:
            deadline_dt = datetime.strptime(config["deadline"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > deadline_dt:
                return jsonify({"error": "已超過截止日期"}), 403
        except Exception:
            pass

    # 取得前端送來的資料
    data = request.json
    name = data.get("name")
    gender = data.get("gender")
    song = data.get("songName")
    link = data.get("songLink")

    if not all([name, gender, song, link]):
        return jsonify({"error": "欄位不可為空"}), 400

    # 判斷使用者身份：登入優先，否則用姓名
    if session.get("user"):
        email = session["user"].get("email")
        cur_query = ("SELECT COUNT(*) FROM songs WHERE email = ? AND gender = ?", (email, gender))
    else:
        cur_query = ("SELECT COUNT(*) FROM songs WHERE name = ? AND gender = ?", (name, gender))

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute(*cur_query)
    count = cur.fetchone()[0]
    conn.close()

    # 性別限制判斷
    if gender == "男" and config.get("male_limit_enabled") and count >= config.get("male_limit_count", 0):
        return jsonify({"error": "你已達男生點歌上限"}), 403
    if gender == "女" and config.get("female_limit_enabled") and count >= config.get("female_limit_count", 0):
        return jsonify({"error": "你已達女生點歌上限"}), 403

    # --- 寫入資料庫 ---
    email = session["user"]["email"] if session.get("user") else None
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO songs (name, gender, song, link, email, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (name, gender, song, link, email, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True})
    
# ======================
# 狀態檢查 API
# ======================
@app.route("/status")
def status():

    config = load_config()
    now = datetime.now()

    name = request.args.get("name")
    gender = request.args.get("gender")

    status = {
        "accept_responses": config.get("accept_responses", True),
        "deadline": config.get("deadline"),
        "male_limit_enabled": config.get("male_limit_enabled", False),
        "male_limit_count": config.get("male_limit_count", 0),
        "female_limit_enabled": config.get("female_limit_enabled", False),
        "female_limit_count": config.get("female_limit_count", 0),
        "current_count": 0,
        "remaining": None,
        "message": ""
    }

    # 不接受回應
    if not status["accept_responses"]:
        status["message"] = "目前不接受回應"
        return jsonify(status)

    # 截止時間
    if status["deadline"]:
        try:
            deadline_dt = datetime.strptime(status["deadline"], "%Y-%m-%d %H:%M:%S")
            if now > deadline_dt:
                status["message"] = "已超過截止時間"
                return jsonify(status)
        except:
            pass

    if not gender:
        return jsonify(status)

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # 🔥 優先用帳號判斷
    if session.get("user"):
        email = session["user"].get("email")
        cur.execute(
            "SELECT COUNT(*) FROM songs WHERE email = ? AND gender = ?",
            (email, gender)
        )
    # 🔥 未登入才用姓名
    elif name:
        cur.execute(
            "SELECT COUNT(*) FROM songs WHERE name = ? AND gender = ?",
            (name, gender)
        )
    else:
        conn.close()
        return jsonify(status)

    count = cur.fetchone()[0]
    conn.close()

    status["current_count"] = count

    # 性別限制
    if gender == "男" and status["male_limit_enabled"]:
        status["remaining"] = max(0, status["male_limit_count"] - count)
    elif gender == "女" and status["female_limit_enabled"]:
        status["remaining"] = max(0, status["female_limit_count"] - count)

    if status["remaining"] is not None:
        if status["remaining"] <= 0:
            status["message"] = "已達點歌上限"
        else:
            status["message"] = f"你還可以再點 {status['remaining']} 首歌"

    return jsonify(status)
    
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
        "SELECT id AS ID, name AS 姓名, gender AS 性別, email AS Email, song AS 歌名, link AS 歌曲連結, timestamp AS 填寫時間 FROM songs",
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

        # ✅ 更新限制設定
        if "male_limit_enabled" in data:
            config["male_limit_enabled"] = data["male_limit_enabled"]
        if "male_limit_count" in data:
            config["male_limit_count"] = int(data["male_limit_count"])
        if "female_limit_enabled" in data:
            config["female_limit_enabled"] = data["female_limit_enabled"]
        if "female_limit_count" in data:
            config["female_limit_count"] = int(data["female_limit_count"])

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

# ======================
# 刪除所有結果
# ======================
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
        cursor.execute("SELECT id, name, gender, song, link, timestamp, email FROM songs WHERE gender = ? ORDER BY id", (gender,))
    else:
        cursor.execute("SELECT id, name, gender, song, link, timestamp, email FROM songs ORDER BY id")

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
            "timestamp": row[5],
            "email": row[6] if row[6] else "無"
        })
    return jsonify(results)

# ======================
# 搜尋 ID
# ======================
@app.route("/result/<int:song_id>")
def get_result(song_id):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT id, name, gender, song, link, timestamp, email FROM songs WHERE id = ?", (song_id,))
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
        "timestamp": row[5],
        "email": row[6] if row[6] else "無"
    })

@app.route("/notify")
def notify():
    result = show_notification("**操作成功！**\n請查看結果", level="success")
    return jsonify(result)

@app.route("/result/<int:result_id>")
def result_detail(result_id):
    result = get_result_by_id(result_id)  # 假設這是你抓資料的函式
    email = result.get("email", "無")     # 如果沒有 email 就顯示「無」
    return render_template("result_detail.html", result=result, email=email)

# ======================
# 管理頁面路由
# ======================
@app.route("/admin")
def admin_page():
    if not session.get("user") or session["user"].get("email") not in ADMIN_EMAILS:
        return render_template("not_admin.html", ADMIN_EMAILS=ADMIN_EMAILS)
    return render_template("admin.html", ADMIN_EMAILS=ADMIN_EMAILS)

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
