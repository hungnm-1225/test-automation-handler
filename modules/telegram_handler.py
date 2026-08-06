import json
import requests

class TelegramHandler:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def send_approval_card(self, row_data: dict, ai_analysis: dict):
        warning_text = f"\n⚠️ **CẢNH BÁO:** {ai_analysis.get('doc_warning')}" if ai_analysis.get('doc_warning') != "None" else ""
        
        message_text = f"""
📥 **[FEEDBACK MỚI CẦN XỬ LÝ - #{row_data.get('fb_id')}]**

👤 **Người gửi:** {row_data.get('submitter')} ({row_data.get('country')})
📌 **Tiêu đề:** {row_data.get('subject')}
📝 **Ghi chú:** {row_data.get('remarks') or 'Không có'}
📄 **Google Doc:** [Mở File Doc]({row_data.get('doc_link')}){warning_text}

---
🧠 **AI TÓM TẮT NỘI DUNG DOC & BÀI TOÁN:**
• {ai_analysis.get('summary')}

🎯 **AI ĐỀ XUẤT:**
• **Category:** `{ai_analysis.get('category')}`
• **Phân công:** {ai_analysis.get('suggested_assignee_name')} (`{ai_analysis.get('suggested_assignee_email')}`)
• **Mức độ:** {ai_analysis.get('priority')}

👇 **ANH HÙNG NGUYỄN MẠNH BẤM DUYỆT BÊN DƯỚI:**
        """

        row_num = row_data.get('row_number')
        cat = ai_analysis.get('category')
        email = ai_analysis.get('suggested_assignee_email')
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": f"✅ Duyệt & Tag {ai_analysis.get('suggested_assignee_name')}", 
                        "callback_data": f"approve|{row_num}|{cat}|{email}"
                    }
                ],
                [
                    {"text": "👤 Tag Quang Định", "callback_data": f"approve|{row_num}|Software|quang.dinh@dtt.vn"},
                    {"text": "👤 Tag Linh Đặng", "callback_data": f"approve|{row_num}|Content|linh.dang.edu@dtt.vn"}
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
        res_data = res.json()
        
        if not res_data.get("ok"):
            print(f"⚠️ LỖI GỬI TELEGRAM (Có thể sai Chat ID): {res_data}")
        else:
            print(f"📲 Đã bắn tin nhắn Telegram thành công tới Chat ID {self.chat_id}!")
            
        return res_data
