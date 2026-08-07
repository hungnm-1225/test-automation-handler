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
            f"📌 **Tiêu
