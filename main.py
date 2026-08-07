import os
import logging
import threading
import asyncio
from flask import Flask
from dotenv import load_dotenv
from telegram.ext import ContextTypes

from modules.google_sheet import GoogleSheetManager
from modules.google_doc import GoogleDocManager
from modules.ai_engine import AIEngine
from modules.telegram_handler import TelegramBotHandler

# System Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Web Server Flask giữ ấm Render 24/7
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "PTV Support Automation Agent is Running Alive!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# Nạp biến môi trường
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 5))

# Khởi tạo Quản lý Sheet, Doc, AI
sheet_mgr = GoogleSheetManager(spreadsheet_id=SPREADSHEET_ID)
doc_mgr = GoogleDocManager()
ai_engine = AIEngine(api_key=GEMINI_API_KEY)

async def scan_job_callback(context: ContextTypes.DEFAULT_TYPE):
    """
    Hàm quét Sheet định kỳ chạy trong JobQueue của Telegram
    """
    logger.info("🔍 Đang quét file Google Sheet tìm feedback mới...")
    try:
        # Chạy tác vụ đọc Sheet bất đồng bộ để không nghẽn loop
        rows = await asyncio.to_thread(sheet_mgr.get_unprocessed_rows, "Feedbacks")
        if not rows:
            logger.info("✅ Không có feedback mới nào cần xử lý.")
            return

        for row in rows:
            doc_content = ""
            if row['doc_url']:
                content, err = await asyncio.to_thread(doc_mgr.read_doc_content, row['doc_url'])
                doc_content = content

            ai_res = await asyncio.to_thread(
                ai_engine.analyze_feedback,
                row['subject'], row['remarks'], doc_content, row['country']
            )

            row['ai_res'] = ai_res

            # Lấy Bot Handler từ context và gửi thông báo
            bot_handler: TelegramBotHandler = context.job.data
            await bot_handler.send_approval_request(row)

    except Exception as e:
        logger.error(f"Lỗi trong quá trình quét tự động: {e}")

if __name__ == "__main__":
    # 1. Chạy Web Server Flask ở Thread riêng cho Render Ping
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 2. Khởi tạo Telegram Bot Handler
    bot_handler = TelegramBotHandler(
        token=TELEGRAM_BOT_TOKEN,
        admin_chat_id=TELEGRAM_CHAT_ID,
        sheet_mgr=sheet_mgr,
        doc_mgr=doc_mgr
    )

    # 3. Đặt lịch quét định kỳ qua Telegram JobQueue (không đụng độ Async Loop)
    if bot_handler.app.job_queue:
        bot_handler.app.job_queue.run_repeating(
            callback=scan_job_callback,
            interval=CHECK_INTERVAL_MINUTES * 60, # Đổi phút sang giây
            first=10,                             # Chạy lần đầu sau 10 giây
            data=bot_handler
        )

    logger.info(f"🚀 PTV Agent đã khởi chạy thành công! Quét định kỳ mỗi {CHECK_INTERVAL_MINUTES} phút.")
    
    # Khởi chạy Polling Telegram Bot
    bot_handler.app.run_polling()
