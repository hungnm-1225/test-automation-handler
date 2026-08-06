import os
import json
import requests

class TelegramHandler:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def send_approval_card(self, row_data: dict, ai_analysis: dict):
        model_name = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash')
        warning_text = f"\n⚠️ **CẢNH BÁO:** {ai_analysis.get('doc_warning')}" if ai_analysis.get('doc_warning') != "None" else ""
        
        message_text = f"""
📥 **[FEEDBACK MỚI - #{row_data.get('fb_id')}]**

👤 **Người gửi:** {row_data.get('submitter')} ({row_data.get('country')})
📌 **Tiêu đề:** {row_data.get('subject')}
📝 **Ghi chú:** {row_data.get('remarks') or 'Không có'}
📄 **Google Doc:** [Mở Document]({row_data.get('doc_link')}){warning_text}

---
🧠 **AI TÓM TẮT DỮ LIỆU ({model_name}):**
• {ai_analysis.get('summary')}

🎯 **AI ĐỀ XUẤT:**
• **Category:** `{ai_analysis.get('category')}`
• **Phân công:** {ai_analysis.get('suggested_assignee_name')} (`{ai_analysis.get('suggested_assignee_email')}`)

👇 **ANH HÙNG NGUYỄN MẠNH BẤM DUYỆT BÊN DƯỚI:**
        """

        row_num = row_data.get('row_number')
        cat = ai_analysis.get('category')
        email = ai_analysis.get('suggested_assignee_email')
        doc_url = row_data.get('doc_link', '')

        keyboard = {
            "inline_keyboard": [
                [{"text": f"✅ Duyệt & Tag {ai_analysis.get('suggested_assignee_name')}", "callback_data": f"approve|{row_num}|{cat}|{email}|{doc_url}"}],
                [
                    {"text": "👤 Tag Quang Định", "callback_data": f"approve|{row_num}|Software|quang.dinh@dtt.vn|{doc_url}"},
                    {"text": "👤 Tag Linh Đặng", "callback_data": f"approve|{row_num}|Content|linh.dang.edu@dtt.vn|{doc_url}"}
                ]
            ]
        }

        payload = {
            "chat_id": self.chat_id,
            "text": message_text,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(keyboard)
        }
        res = requests.post(f"{self.api_url}/sendMessage", json=payload)
        return res.json()
