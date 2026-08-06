import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from modules.google_sheet import GoogleSheetModule
from modules.google_doc import GoogleDocModule
from modules.ai_engine import AIEngine
from modules.telegram_handler import TelegramHandler

load_dotenv()

# Tạo file credentials.json từ biến môi trường trên Render nếu chưa có
if not os.path.exists("credentials.json") and os.getenv("GOOGLE_CREDENTIALS_JSON"):
    with open("credentials.json", "w", encoding="utf-8") as f:
        f.write(os.getenv("GOOGLE_CREDENTIALS_JSON"))

app = Flask(__name__)

# Khởi tạo các module
sheet_mod = GoogleSheetModule(spreadsheet_id=os.getenv("SPREADSHEET_ID"))
doc_mod = GoogleDocModule()
ai_mod = AIEngine(api_key=os.getenv("GEMINI_API_KEY"))
telegram_mod = TelegramHandler(bot_token=os.getenv("TELEGRAM_BOT_TOKEN"), chat_id=os.getenv("TELEGRAM_CHAT_ID"))

# --- 1. ROUTE HEALTCHECK DÀNH CHO UPTIMEROBOT ---
@app.route('/', methods=['GET'])
def health_check():
    """UptimeRobot sẽ ping vào route này 5 phút/lần để giữ Render 24/7"""
    return jsonify({
        "status": "online",
        "system": "PTV Support Agent 24/7",
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 200

# --- 2. ROUTE WEBHOOK NHẬN NÚT BẤM TELEGRAM DUYỆT BẤT CỨ LÚC NÀO ---
@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if "callback_query" in data:
        callback = data["callback_query"]
        callback_id = callback["id"]
        callback_data = callback["data"] # Định dạng: approve|row_num|category|email|doc_url
        
        parts = callback_data.split("|")
        if parts[0] == "approve":
            row_num = int(parts[1])
            category = parts[2]
            email = parts[3]
            doc_url = parts[4] if len(parts) > 4 else ""

            # 1. Cập nhật Google Sheet
            sheet_mod.update_feedback_row(row_number=row_num, category=category, assigned_person=email, status="To Implement")
            
            # 2. Thử Comment & Tag vào Google Doc
            comment_msg = f"Lỗi đã được xác nhận. Anh/chị xem và hỗ trợ xử lý nhé!"
            if doc_url:
                doc_mod.add_comment_and_tag(url=doc_url, tag_email=email, comment_text=comment_msg)

            # 3. Phản hồi nút bấm Telegram
            import requests
            requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/answerCallbackQuery", json={
                "callback_query_id": callback_id,
                "text": f"✅ Đã duyệt dòng #{row_num} và gán cho {email}!"
            })

    return jsonify({"status": "ok"}), 200

# --- 3. BACKGROUND SCHEDULER (QUÉT SHEET 30M/LẦN & REPORT 22H ĐÊM) ---
def job_scan_feedback():
    print("⏰ [APScheduler 30m] Đang kiểm tra Sheet...")
    unprocessed = sheet_mod.get_unprocessed_rows()
    if unprocessed:
        print(f"🔥 Phát hiện {len(unprocessed)} feedback mới!")
        for row in unprocessed:
            doc_info = doc_mod.read_doc_content(row['doc_link']) if row['doc_link'] else {"status": "null", "content": "Không có link"}
            ai_res = ai_mod.analyze_and_summarize(feedback_data=row, doc_data=doc_info)
            telegram_mod.send_approval_card(row_data=row, ai_analysis=ai_res)

def job_daily_report():
    print("🌙 [APScheduler 22:00] Gửi báo cáo đêm...")
    stats = sheet_mod.get_dashboard_stats()
    now_str = datetime.now().strftime("%d/%m/%Y - 22:00")
    report_msg = f"🌙 **[BÁO CÁO TỔNG KẾT ĐÊM - {now_str}]**\n\n• Tổng Ticket: `{stats['total']}`\n• Chờ xử lý: `{stats['new_requests']}`\n• Đang xử lý: `{stats['in_progress']}`\n• Đã xong: `{stats['completed']}`"
    import requests
    requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage", json={
        "chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "text": report_msg,
        "parse_mode": "Markdown"
    })

scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")
scheduler.add_job(job_scan_feedback, 'interval', minutes=30)
scheduler.add_job(job_daily_report, 'cron', hour=22, minute=0)
scheduler.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
