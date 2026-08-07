import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Danh sách Model ưu tiên giảm dần theo yêu cầu
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
- Nội dung file Doc đính kèm: {doc_content if doc_content else "Không đọc được hoặc không có file Doc."}

[BỘ NÃO BẬC THẦY - KNOWLEDGE BASE]
Danh mục hợp lệ (Category): {json.dumps(self.kb['categories'])}
Trạng thái hợp lệ (Status): {json.dumps(self.kb['statuses'])}
Danh sách nhân sự (Team): {json.dumps(self.kb['team_members'], ensure_ascii=False)}

[YÊU CẦU LƯU Ý DỮ LIỆU CỘT]
1. Chọn 1 Category phù hợp nhất trong danh mục trên.
2. Chọn 1 Status đề xuất (Ví dụ: "To Implement", "Critical", "Non-Critical", "Backlog").
3. Gán người chịu trách nhiệm (Assigned) dựa trên từ khóa bài toán và kỹ năng nhân sự. Trả về đúng `name` và `email`.

Hãy trả về duy nhất một chuỗi JSON chuẩn (JSON object) không kèm markdown format khác, theo cấu trúc:
{{
    "category": "...",
    "status": "...",
    "assigned_name": "...",
    "assigned_email": "...",
    "summary": "Tóm tắt ngắn gọn 2-3 câu về cốt lõi vấn đề người dùng gặp phải."
}}
"""
        # Cơ chế Switch Model tự động khi gặp lỗi 429 (Quota Exceeded)
        for model_name in GEMINI_MODELS:
            try:
                logger.info(f"🤖 Đang gửi request tới Gemini Model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                res_json = json.loads(response.text)
                return res_json
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "quota" in err_msg.lower():
                    logger.warning(f"⚠️ Model {model_name} bị tràn Quota (429). Đang đổi sang model tiếp theo...")
                    continue
                else:
                    logger.error(f"❌ Lỗi với model {model_name}: {err_msg}")
                    continue

        # Fallback nếu tất cả model đều lỗi
        logger.error("❌ Tất cả Gemini Models đều quá tải hoặc lỗi!")
        default_person = self.kb.get("default_assignee", {"name": "Bryan", "email": "bryan@example.com"})
        return {
            "category": "other",
            "status": "To Implement",
            "assigned_name": default_person["name"],
            "assigned_email": default_person["email"],
            "summary": f"Tự động phân loại thất bại do AI Quota. Tiêu đề: {subject}"
        }
