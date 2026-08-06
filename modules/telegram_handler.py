import json
import requests

class TelegramHandler:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def send_approval_card(self, row_data: dict, ai_analysis: dict):
        warning_text = f"\n⚠️ <b>CẢNH BÁO:</b> {ai_analysis.get('doc_warning')}" if ai_analysis.get('doc_warning') != "None" else ""
        
        # Chuyển sang định dạng HTML chuẩn
        message_text = f"""📥 <b>[FEEDBACK MỚI CẦN XỬ LÝ - #{row_data.get('fb_id')}]</b>

👤 <b>Người gửi:</b> {row_data.get('submitter')} ({row_data.get('country')})
📌 <b>Tiêu đề:</b> {row_data.get('subject')}
📝 <b>Ghi chú:</b> {row_data.get('remarks') or 'Không có'}
📄 <b>Google Doc:</b> <a href="{row_data.get('doc_link')}">Mở File Doc</a>{warning_text}

---
🧠 <b>AI TÓM TẮT NỘI DUNG DOC & BÀI TOÁN:</b>
• {ai_analysis.get('summary')}

🎯 <b>AI ĐỀ XUẤT:</b>
• <b>Category:</b> <code>{ai_analysis.get('category')}</code>
• <b>Phân công:</b> {ai_analysis.get('suggested_assignee_name')} (<code>{ai_analysis.get('suggested_assignee_email')}</code>)
• <b>Mức độ:</b> {ai_analysis.get('priority')}

👇 <b>ANH HÙNG NGUYỄN MẠNH BẤM DUYỆT BÊN DƯỚI:</b>"""

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
            "parse_mode": "HTML", # Đổi sang HTML chống lỗi ký tự đặc biệt
            "reply_markup": json.dumps(keyboard)
        }
        
        res = requests.post(f"{self.api_url}/sendMessage", json=payload)
        res_data = res.json()
        
        if not res_data.get("ok"):
            print(f"⚠️ LỖI GỬI TELEGRAM: {res_data}")
        else:
            print(f"📲 Đã bắn tin nhắn Telegram thành công tới Chat ID {self.chat_id}!")
            
        return res_data
