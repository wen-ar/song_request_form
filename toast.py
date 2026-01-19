import datetime
import markdown2

def show_notification(message: str, level: str = "info"):
    """
    後端通知函式（Render 可用）
    - message: 通知內容（支援 Markdown）
    - level: 通知等級，可選 "info", "success", "warning", "error"
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_message = markdown2.markdown(message)

    # 在後端 log 顯示
    print(f"[{level.upper()}] {timestamp} - {message}")

    # 回傳 JSON 給前端使用
    return {
        "level": level,
        "timestamp": timestamp,
        "message": message,
        "html": html_message
    }
