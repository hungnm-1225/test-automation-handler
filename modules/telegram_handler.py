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
        await update.message.reply_text("🤖 Bot PTV Support Automation đã sẵn sàng!")

    async def send_permission_warning(self, task_data: dict):
        """
        Cảnh báo khi File Doc chưa mở quyền Commenter
        """
        msg = (
            f"⚠️ **CẢNH BÁO: GOOGLE DOC CHƯA MỞ QUYỀN COMMENT [{task_data['fb_id']}]**\n\n"
            f"👤 **Người gửi:** {task_data['submitter']} ({task_data['country']})\n"
            f"📌 **Tiêu đề:** {task_data['subject']}\n"
            f"📄 **Doc Link:** {task_data['doc_url']}\n\n"
            f"💡 **Ghi chú:** File Google Doc này ở chế độ Viewer/Restricted. Yêu cầu mở quyền Commenter/Editor cho Everyone with link. Feedback này tạm thời được BỎ QUA và chưa tick Assigned trên Sheet."
        )
        await self.app.bot.send_message(chat_id=self.admin_chat_id, text=msg, parse_mode="Markdown")

    async def send_no_doc_info(self, task_data: dict):
        """
        Thông báo thuần túy cho Feedback KHÔNG CÓ Google Doc (KHÔNG NÚT BẤM)
        """
        msg = (
            f"ℹ️ **FEEDBACK KHÔNG CÓ GOOGLE DOC [{task_data['fb_id']}]**\n\n"
            f"👤 **Người gửi:** {task_data['submitter']} ({task_data['country']})\n"
            f"📌 **Tiêu đề:** {task_data['subject']}\n"
            f"📝 **Ghi chú:** {task_data['remarks']}\n\n"
            f"✅ **TỰ ĐỘNG XỬ LÝ:**\n"
            f"• Cột M (Assigned): Đã tick [x]\n"
            f"• Cột P (Status): `Non-Critical`\n"
            f"• Cột L (Category): `{task_data['ai_res']['category']}`"
        )
        await self.app.bot.send_message(chat_id=self.admin_chat_id, text=msg, parse_mode="Markdown")

    async def send_approval_request(self, task_data: dict):
        """
        Gửi yêu cầu duyệt cho Feedback CÓ GOOGLE DOC hợp lệ
        """
        fb_id = task_data['fb_id']
        self.pending_tasks[fb_id] = task_data

        msg = (
            f"📥 **FEEDBACK CẦN XỬ LÝ [{fb_id}]**\n\n"
            f"👤 **Người gửi:** {task_data['submitter']} ({task_data['country']})\n"
            f"📌 **Tiêu đề:** {task_data['subject']}\n"
            f"🤖 **AI ĐỀ XUẤT:**\n"
            f"• **Category:** `{task_data['ai_res']['category']}`\n"
            f"• **Status sẽ gán (Cột P):** `To Implement`\n"
            f"• **Gán cho:** {task_data['ai_res']['assigned_name']} ({task_data['ai_res']['assigned_email']})\n"
            f"💡 **Tóm tắt:** {task_data['ai_res']['summary_vi']}\n\n"
            f"📄 **Doc:** {task_data['doc_url']}"
        )

        keyboard = [[
            InlineKeyboardButton("✅ Đồng ý & Thực thi", callback_data=f"approve_{fb_id}"),
            InlineKeyboardButton("❌ Bỏ qua", callback_data=f"reject_{fb_id}")
        ]]
        await self.app.bot.send_message(
            chat_id=self.admin_chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        action, fb_id = query.data.split("_", 1)
        if fb_id not in self.pending_tasks:
            await query.edit_message_text("⚠️ Yêu cầu này đã xử lý hoặc hết hạn.")
            return

        task = self.pending_tasks[fb_id]

        if action == "approve":
            await query.edit_message_text(f"⏳ Đang thực thi gán dữ liệu vào Sheet & Doc cho `{fb_id}`...")
            try:
                ai_res = task['ai_res']

                # 1. Cập nhật Sheet: Status Cột P = "To Implement"
                self.sheet_mgr.update_feedback_row(
                    sheet_name=task['sheet_name'],
                    row_index=task['row_index'],
                    category=ai_res['category'],
                    status="To Implement"
                )

                # 2. Comment TIẾNG ANH vào Google Doc
                comment_en = (
                    f"Hello @{ai_res['assigned_email']}, this support ticket has been assigned to you.\n"
                    f"Summary: {ai_res['summary_en']}\n"
                    f"Status: To Implement"
                )
                success, doc_msg = self.doc_mgr.add_comment_and_tag(
                    doc_url=task['doc_url'],
                    comment_text_en=comment_en,
                    tag_email=ai_res['assigned_email']
                )

                await query.edit_message_text(
                    f"✅ **ĐÃ XỬ LÝ THÀNH CÔNG [{fb_id}]**\n\n"
                    f"• Cập nhật Sheet (Cột P: To Implement): Thành công\n"
                    f"• Comment Google Doc (English): {doc_msg}"
                )
            except Exception as e:
                await query.edit_message_text(f"❌ **XỬ LÝ THẤT BẠI [{fb_id}]**: {str(e)}")

            del self.pending_tasks[fb_id]

        elif action == "reject":
            await query.edit_message_text(f"🚫 Đã bỏ qua feedback [{fb_id}].")
            del self.pending_tasks[fb_id]
