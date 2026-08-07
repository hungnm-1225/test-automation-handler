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
        """Gửi thông báo CÓ NÚT BẤM cho Feedback có Google Doc hợp lệ"""
        fb_id = task_data['fb_id']
        self.pending_tasks[fb_id] = task_data

        msg = (
            f"📥 **FEEDBACK MỚI CẦN XỬ LÝ [{fb_id}]**\n\n"
            f"👤 **Người gửi:** {task_data['submitter']} ({task_data['country']})\n"
            f"✉️ **Email:** `{task_data.get('email', 'N/A')}`\n"
            f"📌 **Tiêu đề:** {task_data['subject']}\n"
            f"📝 **Ghi chú:** {task_data['remarks']}\n\n"
            f"🤖 **AI ĐỀ XUẤT:**\n"
            f"• **Category:** `{task_data['ai_res']['category']}`\n"
            f"• **Status (Cột P):** `To Implement` (Sẽ tự gán khi duyệt)\n"
            f"• **Người phụ trách:** {task_data['ai_res']['assigned_name']} ({task_data['ai_res']['assigned_email']})\n"
            f"💡 **Tóm tắt vấn đề:** {task_data['ai_res']['summary_vi']}\n\n"
            f"📄 **Doc Link:** {task_data['doc_url']}"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Đồng ý & Thực thi", callback_data=f"approve_{fb_id}"),
                InlineKeyboardButton("❌ Bỏ qua", callback_data=f"reject_{fb_id}")
            ]
        ]
        await self.app.bot.send_message(
            chat_id=self.admin_chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def send_info_notification(self, task_data: dict):
        """Gửi thông báo KHÔNG CÓ NÚT BẤM cho Feedback KHÔNG CÓ Google Doc"""
        msg = (
            f"ℹ️ **FEEDBACK KHÔNG CÓ GOOGLE DOC [{task_data['fb_id']}]**\n\n"
            f"👤 **Người gửi:** {task_data['submitter']} ({task_data['country']})\n"
            f"📌 **Tiêu đề:** {task_data['subject']}\n"
            f"📝 **Ghi chú:** {task_data['remarks']}\n\n"
            f"🤖 **ĐÃ TỰ ĐỘNG CẬP NHẬT SHEET:**\n"
            f"• **Category:** `{task_data['ai_res']['category']}`\n"
            f"• **Assigned (Cột M):** `TRUE` (Đã tick)\n"
            f"• **Status (Cột P):** `Non-Critical` (Đã gán)\n"
            f"• **Người phụ trách:** {task_data['ai_res']['assigned_name']}\n"
            f"💡 **Tóm tắt:** {task_data['ai_res']['summary_vi']}"
        )
        await self.app.bot.send_message(chat_id=self.admin_chat_id, text=msg, parse_mode="Markdown")

    async def send_restricted_doc_alert(self, task_data: dict):
        """Cảnh báo file Doc bị khóa quyền Commenter - Hướng dẫn Admin bấm Request Access 2 giây"""
        submitter_str = f"{task_data['submitter']}"
        if task_data.get('email'):
            submitter_str += f" ({task_data['email']})"

        msg = (
            f"⚠️ **CẢNH BÁO: GOOGLE DOC CHƯA MỞ QUYỀN COMMENT [{task_data['fb_id']}]**\n\n"
            f"👤 **Submitter:** {submitter_str}\n"
            f"📌 **Tiêu đề:** {task_data['subject']}\n"
            f"📄 **Link Doc:** {task_data['doc_url']}\n\n"
            f"👉 **HÀNH ĐỘNG CỦA ANH (MẤT 2 GIÂY):**\n"
            f"1. Nhấn vào link Doc ở trên.\n"
            f"2. Chọn **Commenter** -> Bấm **Request access**.\n"
            f"3. Google sẽ gửi Email yêu cầu chính thức tới submitter (100% Không vào Spam).\n\n"
            f"⏸️ **Trạng thái:** Tạm thời giữ nguyên dòng này trên Sheet. Lần quét tới khi người dùng mở quyền, Bot sẽ tự động xử lý tiếp!"
        )
        await self.app.bot.send_message(chat_id=self.admin_chat_id, text=msg, parse_mode="Markdown")

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
                target_sheet = task.get('sheet_name', 'Feedbacks')

                # 1. Cập nhật Sheet: Category (L), Assigned Checkbox = TRUE (M), Status = "To Implement" (P)
                self.sheet_mgr.update_feedback_row(
                    sheet_name=target_sheet,
                    row_index=row_idx,
                    category=ai_res['category'],
                    status="To Implement"
                )

                # 2. Tag người dùng vào Google Doc BẰNG TIẾNG ANH
                doc_msg = "Không có URL Doc."
                if doc_url:
                    comment_text_en = (
                        f"Hi {ai_res['assigned_name']},\n\n"
                        f"This feedback ticket [{fb_id}] has been assigned to you.\n"
                        f"Summary: {ai_res['summary_en']}\n\n"
                        f"Please review and process accordingly."
                    )
                    success, msg = self.doc_mgr.add_comment_and_tag(
                        doc_url=doc_url,
                        comment_text_en=comment_text_en,
                        tag_email=ai_res['assigned_email']
                    )
                    doc_msg = msg

                await query.edit_message_text(
                    f"✅ **ĐÃ XỬ LÝ THÀNH CÔNG [{fb_id}]**\n\n"
                    f"• Cập nhật Sheet: Category={ai_res['category']}, Assigned=TRUE, Status=To Implement (Cột P)\n"
                    f"• Comment Google Doc (English): {doc_msg}"
                )
            except Exception as e:
                logger.error(f"Lỗi thực thi approve: {e}")
                await query.edit_message_text(f"❌ **XỬ LÝ THẤT BẠI [{fb_id}]**: {str(e)}")

            del self.pending_tasks[fb_id]

        elif action == "reject":
            await query.edit_message_text(f"🚫 Đã bỏ qua feedback [{fb_id}].")
            del self.pending_tasks[fb_id]
