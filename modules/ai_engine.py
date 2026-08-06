import json
import os
import google.generativeai as genai

class AIEngine:
    def __init__(self, api_key: str, knowledge_base_path: str = 'brain/knowledge_base.json'):
        genai.configure(api_key=api_key)
        # Sử dụng model Gemini 3.6 Flash hoặc Gemini 3.1 Flash theo cấu hình .env
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        self.model = genai.GenerativeModel(self.model_name)
        with open(knowledge_base_path, 'r', encoding='utf-8') as f:
            self.kb = json.load(f)

    def analyze_and_summarize(self, feedback_data: dict, doc_data: dict) -> dict:
        prompt = f"""
        Bạn là Chuyên gia AI Triage quản lý hệ thống PTV Taskforce Support.
        Hãy đọc thông tin Feedback và nội dung chi tiết trong Google Doc để phân loại & tóm tắt.

        KNOWLEDGE BASE:
        {json.dumps(self.kb, ensure_ascii=False)}

        ĐẦU VÀO FORM:
        - Submitter: {feedback_data.get('submitter')} ({feedback_data.get('country')})
        - Subject: {feedback_data.get('subject')}
        - Remarks: {feedback_data.get('remarks')}

        NỘI DUNG ĐỌC TỪ GOOGLE DOC:
        - Trạng thái Doc: {doc_data.get('status')}
        - Tiêu đề Doc: {doc_data.get('doc_title', 'N/A')}
        - Nội dung Doc: {doc_data.get('content', 'Không thể đọc nội dung')}

        YÊU CẦU ĐẦU RA (Trả về định dạng JSON thuần túy, không chứa mã ```json):
        {{
            "summary": "Tóm tắt bản chất lỗi/yêu cầu trong 2-3 câu ngắn gọn",
            "category": "Chọn 1 trong các nhóm: Account, Software, Content, other",
            "suggested_assignee_name": "Tên nhân sự được đề xuất từ Knowledge Base",
            "suggested_assignee_email": "Email của nhân sự được đề xuất",
            "priority": "Normal hoặc Urgent",
            "doc_warning": "{doc_data.get('warning', 'None')}"
        }}
        """
        try:
            response = self.model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"Lỗi AI Engine ({self.model_name}): {e}")
            return {
                "summary": f"Chưa thể tóm tắt do lỗi AI ({self.model_name}): {str(e)}",
                "category": "other",
                "suggested_assignee_name": "Anh Hùng Nguyễn Mạnh",
                "suggested_assignee_email": "hung.nguyenmanh@dtt.vn",
                "priority": "Normal",
                "doc_warning": doc_data.get('warning', 'None')
            }
