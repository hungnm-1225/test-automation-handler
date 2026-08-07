import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger(__name__)

class TelegramBotHandler:
    def __init__(self, token: str, admin_chat_id: str, executor_callback):
        self.token = token
        self.admin_chat_id = admin_chat_id
        self.executor_callback = executor_callback # Hàm xử lý khi người dùng ấn nút Đồng ý
        self.pending_tasks = {} # Lưu trữ các ticket đang chờ duyệt trong bộ nhớ
        self.app = Application.builder().token(token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self._start_command))
        self.app.add_handler(CallbackQueryHandler(self._button_click))

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🤖 Bot PTV Feedback Automation đã sẵn sàng hoạt động!")

    async def send_approval_request(self, task_data: dict):
        """
        Gửi thông báo đề xuất cho Admin kèm Inline Buttons
        """
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
            # Gọi callback thực thi chính
            success, detail = await self.executor_callback(task)
            if success:
                await query.edit_message_text(
                    f"✅ **ĐÃ XỬ LÝ THÀNH CÔNG [{fb_id}]**\n\n"
                    f"• Cập nhật Sheet: Thành công\n"
                    f"• Comment Google Doc: {detail}"
                )
            else:
                await query.edit_message_text(
                    f"⚠️ **XỬ LÝ THẤT BẠI MOT PHẦN [{fb_id}]**\n\nChi tiết: {detail}"
                )
            del self.pending_tasks[fb_id]

        elif action == "reject":
            await query.edit_message_text(f"🚫 Đã bỏ qua feedback [{fb_id}].")
            del self.pending_tasks[fb_id]
