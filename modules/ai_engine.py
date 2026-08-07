import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-pro-latest",
    "gemini-flash-latest",
    "gemini-flash-lite-latest"
]

class AIEngine:
    def __init__(self, api_key: str, knowledge_base_path: str = "brain/knowledge_base.json"):
        genai.configure(api_key=api_key)
        with open(knowledge_base_path, 'r', encoding='utf-8') as f:
            self.kb = json.load(f)

    def analyze_feedback(self, subject: str, remarks: str, doc_content: str, country: str) -> dict:
        prompt = f"""
Bạn là trợ lý AI chuyên phân loại ticket hỗ trợ. Hãy phân tích thông tin sau:

[THÔNG TIN FEEDBACK]
- Quốc gia: {country}
- Tiêu đề (Subject): {subject}
- Ghi chú (Remarks): {remarks}
- Nội dung file Doc đính kèm: {doc_content if doc_content else "Không có file Doc."}

[KNOWLEDGE BASE]
Danh mục hợp lệ (Category): {json.dumps(self.kb['categories'])}
Danh sách nhân sự (Team): {json.dumps(self.kb['team_members'], ensure_ascii=False)}
Mặc định Assignee: {json.dumps(self.kb['default_assignee'], ensure_ascii=False)}

[QUY TẮC GÁN NGƯỜI PHỤ TRÁCH]
1. Nếu vấn đề khớp rõ ràng với từ khóa/vaitro của từng nhân sự, hãy gán cho nhân sự đó.
2. Nếu vấn đề thuộc dạng chung chung, không rõ ràng, thuộc category 'other' hoặc không khớp cụ thể với nhân sự nào, MẶC ĐỊNH gán cho Administrator: Hung Nguyen (email: hung.nguyenmanh@dtt.vn).

Hãy phân loại và trả về duy nhất JSON object theo cấu trúc:
{{
    "category": "Chọn 1 Category phù hợp nhất",
    "assigned_name": "Tên người phụ trách",
    "assigned_email": "Email người phụ trách",
    "summary_vi": "Tóm tắt ngắn 2 câu bằng tiếng Việt cho Telegram.",
    "summary_en": "Short 2-sentence summary in English for Google Doc comment."
}}
"""
        for model_name in GEMINI_MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                return json.loads(response.text)
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    continue
                continue

        default_person = self.kb.get("default_assignee", {"name": "Hung Nguyen", "email": "hung.nguyenmanh@dtt.vn"})
        return {
            "category": "other",
            "assigned_name": default_person["name"],
            "assigned_email": default_person["email"],
            "summary_vi": f"Tiêu đề: {subject}",
            "summary_en": f"Subject: {subject}"
        }
