import json
import requests

class AIEngine:
    def __init__(self, api_key: str, knowledge_base_path: str = 'brain/knowledge_base.json'):
        self.api_key = api_key
        with open(knowledge_base_path, 'r', encoding='utf-8') as f:
            self.kb = json.load(f)

    def _call_gemini_api(self, prompt: str) -> str:
        # Danh sách mô hình chuẩn chính thức từ Google Gemini API
        models_to_try = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash-exp"
        ]

        last_error = None
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [{"text": prompt}]
                    }
                ]
            }
            try:
                res = requests.post(url, json=payload, timeout=30)
                if res.status_code == 200:
                    data = res.json()
                    text_out = data['candidates'][0]['content']['parts'][0]['text']
                    print(f"🤖 AI phản hồi thành công sử dụng Model: [{model}]")
                    return text_out
                else:
                    last_error = f"HTTP {res.status_code}: {res.text}"
            except Exception as e:
                last_error = str(e)

        raise RuntimeError(f"Không thể kết nối Gemini API. Chi tiết: {last_error}")

    def analyze_and_summarize(self, feedback_data: dict, doc_data: dict) -> dict:
        prompt = f"""
        Bạn là Chuyên gia AI Triage quản lý hệ thống PTV Taskforce Support.
        Hãy đọc thông tin Feedback và nội dung chi tiết trong Google Doc đính kèm để phân loại & tóm tắt.

        THÔNG TIN HỆ THỐNG & NHÂN SỰ (KNOWLEDGE BASE):
        {json.dumps(self.kb, ensure_ascii=False)}

        ĐẦU VÀO FORM FEEDBACK:
        - Submitter: {feedback_data.get('submitter')} ({feedback_data.get('country')})
        - Subject: {feedback_data.get('subject')}
        - Remarks: {feedback_data.get('remarks')}

        NỘI DUNG ĐỌC TỪ GOOGLE DOC:
        - Trang thai Doc: {doc_data.get('status')}
        - Tieu de Doc: {doc_data.get('doc_title', 'N/A')}
        - Noi dung Doc: {doc_data.get('content', 'Không thể đọc nội dung file Doc này')}

        YÊU CẦU ĐẦU RA (Bắt buộc trả về định dạng JSON thuần túy, KHÔNG chứa các ký tự mã ```json hay markdown):
        {{
            "summary": "Tóm tắt ngắn gọn 2-3 câu bản chất lỗi/yêu cầu",
            "category": "Chọn 1 trong các nhóm: Account, Software, Content, other",
            "suggested_assignee_name": "Tên nhân sự được đề xuất từ Knowledge Base",
            "suggested_assignee_email": "Email của nhân sự được đề xuất",
            "priority": "Normal hoặc Urgent",
            "doc_warning": "Warning nếu doc bị khóa quyền hoặc null, ngược lại ghi None"
        }}
        """
        raw_text = self._call_gemini_api(prompt)
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
