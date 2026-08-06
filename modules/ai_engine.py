import json
import os
import google.generativeai as genai

class AIEngine:
    def __init__(self, api_key: str, knowledge_base_path: str = 'brain/knowledge_base.json'):
        genai.configure(api_key=api_key)
        
        # Danh sách ưu tiên dàn Model Gemini 3.x (Tự động Fallback khi bị 429)
        self.models_cascade = [
            os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-3-flash-preview"
        ]
        # Loại bỏ trùng lặp nếu GEMINI_MODEL đã trùng
        self.models_cascade = list(dict.fromkeys(self.models_cascade))
        
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

        last_error = None
        # VÒNG LẶP THỬ LẦN LƯỢT DÀN MODEL GEMINI 3.X
        for model_name in self.models_cascade:
            try:
                print(f"🧠 Đang gọi AI với Model: {model_name}...")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                
                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                result = json.loads(clean_text)
                result["used_model"] = model_name # Ghi nhận tên Model đã xử lý thành công
                print(f"✅ AI xử lý thành công bằng Model: {model_name}")
                return result

            except Exception as e:
                last_error = str(e)
                print(f"⚠️ Model {model_name} bị nghẽn/hết Quota (Lỗi: {e}). Đang tự động chuyển sang Model 3.x tiếp theo...")
                continue

        return {
            "summary": f"Chưa thể tóm tắt do tất cả Dàn Model Gemini 3.x đều hết Quota ({last_error})",
            "category": "other",
            "suggested_assignee_name": "Anh Hùng Nguyễn Mạnh",
            "suggested_assignee_email": "hung.nguyenmanh@dtt.vn",
            "priority": "Normal",
            "doc_warning": doc_data.get('warning', 'None'),
            "used_model": "None (Quota Full)"
        }
