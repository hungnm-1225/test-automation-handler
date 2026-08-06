import os
import json
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from modules.google_sheet import GoogleSheetModule
from modules.google_doc import GoogleDocModule

load_dotenv()

# Cấu hình log
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer(text="⏳ Đang thực thi cập nhật Sheet & Google Doc...") # Hiện toast thông báo trên Telegram

    data = query.data.split("|")
    if len(data) < 4:
        return

    action, row_num, category, email = data[0], int(data[1]), data[2], data[3]

    if action == "approve":
        sheet_mod = GoogleSheetModule(spreadsheet_id=os.getenv("SPREADSHEET_ID"))
        doc_mod = GoogleDocModule()

        # 1. Lấy thông tin dòng trên Sheet để lấy link Doc
        rows = sheet_mod.get_unprocessed_rows()
        target_row = next((r for r in rows if r['row_number'] == row_num), None)
        
        # Lấy tên người từ Email
        assignee_name = email.split("@")[0].replace(".", " ").title()

        # 2. Cập nhật Google Sheet
        sheet_mod.update_feedback_row(
            row_number=row_num,
            category=category,
            assigned_person=assignee_name,
            status="To Implement"
        )

        # 3. Chèn Comment & Assign Action Item vào Google Doc
        doc_status_msg = ""
        if target_row and target_row.get('doc_link'):
            success, msg = doc_mod.add_comment_and_assign(
                url=target_row['doc_link'],
                tag_email=email,
                comment_text=f"Anh/Chị vui lòng kiểm tra và xử lý Feedback #{target_row.get('fb_id')} này giúp em nhé ạ!"
            )
            doc_status_msg = " và đã Assign trên Google Doc!" if success else f" (Lỗi Doc: {msg})"

        # 4. Sửa lại tin nhắn Telegram xác nhận thành công
        edited_text = query.message.text + f"\n\n🎉 **[ĐÃ PHÊ DUYỆT & THỰC THI THÀNH CÔNG]**\n• **Gán cho:** {assignee_name} (`{email}`)\n• **Danh mục:** `{category}`{doc_status_msg}"
        await query.edit_message_text(text=edited_text, parse_mode="Markdown")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Thiếu TELEGRAM_BOT_TOKEN!")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CallbackQueryHandler(handle_button_click))
    
    print("🤖 Bot Telegram Listener đang chạy lắng nghe nút bấm (Nhấn Ctrl+C để dừng)...")
    app.run_polling()

if __name__ == "__main__":
    main()
