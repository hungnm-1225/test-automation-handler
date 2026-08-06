import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
from modules.google_sheet import GoogleSheetModule
from modules.google_doc import GoogleDocModule
from modules.ai_engine import AIEngine
from modules.telegram_handler import TelegramHandler

load_dotenv()

def mode_scan_new_feedback():
    """TÁC VỤ 1: Quét 30 phút/lần - Chỉ bắn Telegram khi CÓ FEEDBACK MỚI"""
    sheet_mod = GoogleSheetModule(spreadsheet_id=os.getenv("SPREADSHEET_ID"))
    unprocessed_rows = sheet_mod.get_unprocessed_rows()

    if not unprocessed_rows:
        print("🟢 [30m Scan] KHÔNG có feedback mới. Hệ thống giữ im lặng.")
        return

    print(f"🔥 [30m Scan] Phát hiện {len(unprocessed_rows)} feedback MỚI! Đang xử lý...")
    doc_mod = GoogleDocModule()
    ai_mod = AIEngine(api_key=os.getenv("GEMINI_API_KEY"))
    telegram_mod = TelegramHandler(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        chat_id=os.getenv("TELEGRAM_CHAT_ID")
    )

    for row in unprocessed_rows:
        doc_info = doc_mod.read_doc_content(row['doc_link']) if row['doc_link'] else {"status": "null", "content": "Không có link Doc"}
        ai_result = ai_mod.analyze_and_summarize(feedback_data=row, doc_data=doc_info)
        telegram_mod.send_approval_card(row_data=row, ai_analysis=ai_result)
        print(f"✅ Đã gửi thẻ phê duyệt cho dòng #{row['row_number']}")

def mode_daily_report():
    """TÁC VỤ 2: Báo cáo tổng hợp 22h Đêm (Daily Digest)"""
    sheet_mod = GoogleSheetModule(spreadsheet_id=os.getenv("SPREADSHEET_ID"))
    telegram_mod = TelegramHandler(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        chat_id=os.getenv("TELEGRAM_CHAT_ID")
    )

    stats = sheet_mod.get_dashboard_stats()
    now_str = datetime.now().strftime("%d/%m/%Y - 22:00")

    report_msg = f"""
🌙 **[BÁO CÁO TỔNG KẾT ĐÊM - {now_str}]**

📊 **THỐNG KÊ TỔNG THỂ (LŨY KẾ):**
• 📝 **Tổng số Ticket nhận được:** `{stats['total']}`
• 🆕 **Chờ xử lý (Request Mới):** `{stats['new_requests']}`
• ⏳ **Đang xử lý (Đã gán người):** `{stats['in_progress']}`
• ✅ **Đã hoàn thành (Closed/Resolved):** `{stats['completed']}`

🎯 **CHỈ SỐ HOÀN THÀNH:** `{(stats['completed']/stats['total']*100) if stats['total'] > 0 else 0:.1f}%`

Chúc anh Hùng Nguyễn Mạnh ngủ ngon! 😴💖
    """
    
    # Gửi báo cáo đêm qua Telegram API
    import requests
    requests.post(
        f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
        json={"chat_id": os.getenv("TELEGRAM_CHAT_ID"), "text": report_msg, "parse_mode": "Markdown"}
    )
    print("🌙 Đã gửi Báo Cáo Tổng Kết 22h Đêm thành công!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["scan", "daily_report"], default="scan")
    args = parser.parse_args()

    if args.mode == "scan":
        mode_scan_new_feedback()
    elif args.mode == "daily_report":
        mode_daily_report()
