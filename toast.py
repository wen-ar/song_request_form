import markdown2
import tkinter as tk
from tkinter import scrolledtext

def show_notification(message: str, duration: int = 3000):
    """
    顯示通知視窗，支援 Markdown 語法。
    message: 傳入的 Markdown 字串，例如 "**粗體**\n*斜體*"
    duration: 顯示時間（毫秒），預設 3000ms
    """

    # 將 Markdown 轉成 HTML（這裡只是轉換，tkinter 不支援 HTML 渲染）
    html_message = markdown2.markdown(message)

    # 建立視窗
    root = tk.Tk()
    root.title("通知")
    root.geometry("400x200")
    root.attributes("-topmost", True)  # 置頂顯示

    # 使用 ScrolledText 顯示轉換後的文字（HTML tag 會顯示為字串）
    text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Microsoft JhengHei", 12))
    text_area.insert(tk.INSERT, html_message)
    text_area.configure(state="disabled")
    text_area.pack(expand=True, fill="both")

    # 自動關閉
    root.after(duration, root.destroy)
    root.mainloop()
