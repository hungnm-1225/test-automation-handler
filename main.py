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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "PTV Support Automation Agent is Running Alive!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 5))

sheet_mgr = GoogleSheetManager(spreadsheet_id=SPREADSHEET_ID)
doc_mgr = GoogleDocManager()
ai_engine = AIEngine(api_key=GEMINI_API_KEY)

async def scan_job_callback(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔍 Đang quét file Google Sheet tìm feedback mới...")
    try:
        rows = await asyncio.to_thread(sheet_mgr.get_unprocessed_rows, "Feedbacks")
        if not rows:
            logger.info("✅ Không có feedback mới nào cần xử lý.")
            return

        bot_handler: TelegramBotHandler = context.job.data

        for row in rows:
            doc_url = row['doc_url']

            # KỊCH BẢN 1: KHÔNG CÓ GOOGLE DOC
            if not doc_url:
                ai_res = await asyncio.to_thread(
                    ai_engine.analyze_feedback, row['subject'], row['remarks'], "", row['country']
                )
                row['ai_res'] = ai_res
                
                # Cập nhật Sheet: Status Cột P = "Non-Critical", Tick Assigned = True
                await asyncio.to_thread(
                    sheet_mgr.update_feedback_row,
                    row['sheet_name'], row['row_index'], ai_res['category'], "Non-Critical"
                )
                # Bắn thông báo thuần túy (không nút)
                await bot_handler.send_no_doc_info(row)
                continue

            # KỊCH BẢN 2 & 3: CÓ GOOGLE DOC -> KIỂM TRA QUYỀN COMMENT
            can_comment, perm_status = await asyncio.to_thread(doc_mgr.check_comment_permission, doc_url)

            if not can_comment:
                # KỊCH BẢN 2: CHƯA MỞ QUYỀN COMMENTER -> BẢO BỎ QUA & CẢNH BÁO TELEGRAM
                await bot_handler.send_permission_warning(row)
                continue

            # KỊCH BẢN 3: ĐÃ MỞ QUYỀN COMMENTER -> ĐỌC DOC + GỌI AI + GỬI NÚT BẤM DUYỆT
            doc_content, _ = await asyncio.to_thread(doc_mgr.read_doc_content, doc_url)
            ai_res = await asyncio.to_thread(
                ai_engine.analyze_feedback, row['subject'], row['remarks'], doc_content, row['country']
            )
            row['ai_res'] = ai_res
            await bot_handler.send_approval_request(row)

    except Exception as e:
        logger.error(f"Lỗi trong quá trình quét tự động: {e}")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    bot_handler = TelegramBotHandler(
        token=TELEGRAM_BOT_TOKEN,
        admin_chat_id=TELEGRAM_CHAT_ID,
        sheet_mgr=sheet_mgr,
        doc_mgr=doc_mgr
    )

    if bot_handler.app.job_queue:
        bot_handler.app.job_queue.run_repeating(
            callback=scan_job_callback,
            interval=CHECK_INTERVAL_MINUTES * 60,
            first=10,
            data=bot_handler
        )

    logger.info(f"🚀 Agent đã sẵn sàng! Quét định kỳ mỗi {CHECK_INTERVAL_MINUTES} phút.")
    bot_handler.app.run_polling()
