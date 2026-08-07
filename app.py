import os
import asyncio
import logging
import threading
from flask import Flask
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

from modules.google_sheet import GoogleSheetManager
from modules.google_doc import GoogleDocManager
from modules.ai_engine import AIEngine
from modules.telegram_handler import TelegramBotHandler

# System Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Web Server Flask để Render Ping 24/7 (Tránh ngắt ứng dụng)
app = Flask(__name__)

@app.route('/')
def home():
    return "PTV Support Automation Agent is Running Alive!", 200

# Các biến môi trường
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 5))

# Khởi tạo các Modules
sheet_mgr = GoogleSheetManager(spreadsheet_id=SPREADSHEET_ID)
doc_mgr = GoogleDocManager()
ai_engine = AIEngine(api_key=GEMINI_API_KEY)
bot_handler = None
loop = None

async def execute_task_action(task_data: dict) -> tuple[bool, str]:
    """
    Callback thực thi sau khi anh ấn nút 'Đồng ý' trên Telegram
    """
    try:
        row_idx = task_data['row_index']
        ai_res = task_data['ai_res']
        doc_url = task_data['doc_url']

        # 1. Cập nhật Google Sheet
        sheet_mgr.update_feedback_row(
            sheet_name="Feedbacks",
            row_index=row_idx,
            category=ai_res['category'],
            status=ai_res['status']
        )

        # 2. Tag người liên quan vào Google Doc (Nếu có URL)
        doc_msg = "Không có URL Doc."
        if doc_url:
            comment_text = f"Hi {ai_res['assigned_name']}, tác vụ feedback này đã được gán cho bạn. Nội dung: {ai_res['summary']}"
            success, msg = doc_mgr.add_comment_and_tag(
                doc_url=doc_url,
                comment_text=comment_text,
                tag_email=ai_res['assigned_email']
            )
            doc_msg = msg

        return True, doc_msg
    except Exception as e:
        logger.error(f"Lỗi thực thi: {e}")
        return False, str(e)

def scan_and_process():
    """
    Hàm định kỳ quét Google Sheet tìm Ticket chưa xử lý
    """
    logger.info("🔍 Đang quét file Google Sheet tìm feedback mới...")
    try:
        rows = sheet_mgr.get_unprocessed_rows(sheet_name="Feedbacks")
        if not rows:
            logger.info("✅ Không có feedback mới nào cần xử lý.")
            return

        for row in rows:
            # 1. Đọc nội dung file Google Doc (nếu có)
            doc_content, doc_err = "", None
            if row['doc_url']:
                doc_content, doc_err = doc_mgr.read_doc_content(row['doc_url'])

            # 2. Phân tích qua Gemini AI
            ai_res = ai_engine.analyze_feedback(
                subject=row['subject'],
                remarks=row['remarks'],
                doc_content=doc_content,
                country=row['country']
            )

            row['ai_res'] = ai_res

            # 3. Gửi thông báo đến Telegram chờ duyệt
            asyncio.run_coroutine_threadsafe(
                bot_handler.send_approval_request(row),
                loop
            )
    except Exception as e:
        logger.error(f"Lỗi trong quá trình scan: {e}")

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Chạy Web Server ở Thread riêng
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Tạo Event Loop chính cho Telegram Bot Async
    loop = asyncio.get_event_loop()
    bot_handler = TelegramBotHandler(
        token=TELEGRAM_BOT_TOKEN,
        admin_chat_id=TELEGRAM_CHAT_ID,
        executor_callback=execute_task_action
    )

    # Đặt Lịch Quét Tự Động bằng APScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(scan_and_process, 'interval', minutes=CHECK_INTERVAL_MINUTES)
    scheduler.start()

    logger.info(f"🚀 Hệ thống đã khởi chạy thành công! Quét định kỳ mỗi {CHECK_INTERVAL_MINUTES} phút.")
    
    # Khởi chạy Telegram Bot
    bot_handler.app.run_polling()
