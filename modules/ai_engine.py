import json
import google.generativeai as genai

class AIEngine:
    def __init__(self, api_key: str, knowledge_base_path: str = 'brain/knowledge_base.json'):
        genai.configure(api_key=api_key)
        
        # Tự động dò tìm các Model Gemini Flash mới nhất có sẵn trong API Key
        chosen_model_name = 'gemini-2.0-flash'
        try:
            available_models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            flash_models = [m for m in available_models if 'flash' in m.lower()]
            if flash_models:
                chosen_model_name = flash_models[0] # Lấy model flash mới nhất
            elif available_models:
                chosen_model_name = available_models[0]
            print(f"🤖 AI Engine tự động chọn Model: '{chosen_model_name}'")
        except Exception as e:
            print(f"⚠️ Dùng mặc định gemini-2.0-flash. Lỗi list model: {e}")

        self.model = genai.GenerativeModel(chosen_model_name)

        with open(knowledge_base_path, 'r', encoding='utf-8') as f:
            self.kb = json.load(f)

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

        YÊU CẦU ĐẦU RA (Trả về định dạng JSON thuần túy, không có mã markdown ```json):
        {{
            "summary": "Tóm tắt ngắn gọn 2-3 câu bản chất lỗi/yêu cầu",
            "category": "Chọn 1 trong các nhóm: Account, Software, Content, other",
            "suggested_assignee_name": "Tên nhân sự được đề xuất từ Knowledge Base",
            "suggested_assignee_email": "Email của nhân sự được đề xuất",
            "priority": "Normal hoặc Urgent",
            "doc_warning": "Warning nếu doc bị khóa quyền hoặc null, ngược lại ghi None"
        }}
        """
        response = self.model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
