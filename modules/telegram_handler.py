import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger(__name__)

class TelegramBotHandler:
    def __init__(self, token: str, admin_chat_id: str, sheet_mgr, doc_mgr):
        self.token = token
        self.admin_chat_id = admin_chat_id
        self.sheet_mgr = sheet_mgr
        self.doc_mgr = doc_mgr
        self.pending_tasks = {}
        self.app = Application.builder().token(token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self._start_command))
        self.app.add_handler(CallbackQueryHandler(self._button_click))

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🤖 Bot PTV Feedback Automation đã sẵn sàng hoạt động!")

    async def send_approval_request(self, task_data: dict):
        fb_id = task_data['fb_id']
        self.pending_tasks[fb_id] = task_data

        msg = (
            f"📥 **FEEDBACK MỚI CẦN XỬ LÝ [{fb_id}]**\n\n"
            f"👤 **Người gửi:** {task_data['submitter']} ({task_data['country']})\n"
            f"📌 **Tiêu đề:** {task_data['subject']}\n"
            f"📝 **Ghi chú:** {task_data['remarks']}\n\n"
            f"🤖 **AI ĐỀ XUẤT:**\n"
            f"• **Category:** `{task_data['ai_res']['category']}`\n"
            f"• **Status:** `{task_data['ai_res']['status']}`\n"
            f"• **Người phụ trách:** {task_data['ai_res']['assigned_name']} ({task_data['ai_res']['assigned_email']})\n"
            f"💡 **Tóm tắt vấn đề:** {task_data['ai_res']['summary']}\n\n"
            f"📄 **Doc:** {task_data['doc_url'] if task_data['doc_url'] else 'Không có'}"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Đồng ý & Thực thi", callback_data=f"approve_{fb_id}"),
                InlineKeyboardButton("❌ Bỏ qua", callback_data=f"reject_{fb_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await self.app.bot.send_message(
            chat_id=self.admin_chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    async def _button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data
        action, fb_id = data.split("_", 1)

        if fb_id not in self.pending_tasks:
            await query.edit_message_text("⚠️ Yêu cầu này đã xử lý hoặc hết hạn trong bộ nhớ tạm.")
            return

        task = self.pending_tasks[fb_id]

        if action == "approve":
            await query.edit_message_text(f"⏳ Đang thực thi gán dữ liệu vào Sheet & Doc cho `{fb_id}`...")
            
            try:
                row_idx = task['row_index']
                ai_res = task['ai_res']
                doc_url = task['doc_url']

                # 1. Cập nhật Google Sheet
                self.sheet_mgr.update_feedback_row(
                    sheet_name="Feedbacks",
                    row_index=row_idx,
                    category=ai_res['category'],
                    status=ai_res['status']
                )

                # 2. Tag người dùng vào Google Doc
                doc_msg = "Không có URL Doc."
                if doc_url:
                    comment_text = f"Hi {ai_res['assigned_name']}, tác vụ feedback này đã được gán cho bạn. Nội dung: {ai_res['summary']}"
                    success, msg = self.doc_mgr.add_comment_and_tag(
                        doc_url=doc_url,
                        comment_text=comment_text,
                        tag_email=ai_res['assigned_email']
                    )
                    doc_msg = msg

                await query.edit_message_text(
                    f"✅ **ĐÃ XỬ LÝ THÀNH CÔNG [{fb_id}]**\n\n"
                    f"• Cập nhật Sheet: Thành công\n"
                    f"• Comment Google Doc: {doc_msg}"
                )
            except Exception as e:
                logger.error(f"Lỗi thực thi: {e}")
                await query.edit_message_text(f"❌ **XỬ LÝ THẤT BẠI [{fb_id}]**: {str(e)}")

            del self.pending_tasks[fb_id]

        elif action == "reject":
            await query.edit_message_text(f"🚫 Đã bỏ qua feedback [{fb_id}].")
            del self.pending_tasks[fb_id]
