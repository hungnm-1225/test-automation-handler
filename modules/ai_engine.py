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
Bạn là trợ lý AI phân loại ticket hỗ trợ. Hãy phân tích:

[THÔNG TIN FEEDBACK]
- Quốc gia: {country}
- Tiêu đề: {subject}
- Ghi chú: {remarks}
- Nội dung file Doc đính kèm: {doc_content if doc_content else "Không có file Doc."}

[KNOWLEDGE BASE]
Categories: {json.dumps(self.kb['categories'])}
Team Members: {json.dumps(self.kb['team_members'], ensure_ascii=False)}

YÊU CẦU TRẢ VỀ JSON:
1. "category": Chọn 1 Category phù hợp nhất từ danh sách trên.
2. "assigned_name": Tên nhân sự phù hợp.
3. "assigned_email": Email nhân sự phù hợp.
4. "summary_vi": Tóm tắt ngắn gọn 2 câu bằng TIẾNG VIỆT (Dùng gửi Telegram).
5. "summary_en": Brief 2-sentence summary strictly in ENGLISH (Used for Google Doc comment).

Trả về duy nhất 1 JSON Object:
{{
    "category": "...",
    "assigned_name": "...",
    "assigned_email": "...",
    "summary_vi": "...",
    "summary_en": "..."
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

        default_person = self.kb.get("default_assignee", {"name": "Bryan", "email": "bryan@example.com"})
        return {
            "category": "other",
            "assigned_name": default_person["name"],
            "assigned_email": default_person["email"],
            "summary_vi": f"Tóm tắt tự động: {subject}",
            "summary_en": f"Automated summary: {subject}"
        }
