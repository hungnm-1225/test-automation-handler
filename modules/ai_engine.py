import json
import time
from google import genai
from google.genai import types

class AIEngine:
    def __init__(self, api_key: str, knowledge_base: dict):
        self.client = genai.Client(api_key=api_key)
        self.kb = knowledge_base
        # Danh sách các Model Gemini ưu tiên từ cao xuống thấp (dùng bản 3 trở lên)
        self.models_priority = [
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

    def analyze_feedback(self, subject: str, remarks: str, doc_content: str) -> dict:
        """Sử dụng Gemini phân tích dữ liệu, tự động switch model khi dính lỗi 429 Quota Exceed"""
        
        system_instruction = f"""
        Bạn là Chuyên gia AI phân loại Feedback. 
        Bộ não tri thức (Knowledge Base): {json.dumps(self.kb, ensure_ascii=False)}
        
        Nhiệm vụ:
        1. Tóm tắt ngắn gọn sự cố/góp ý của người dùng.
        2. Chọn CATEGORY phù hợp nhất từ danh sách: {self.kb.get('categories')}.
        3. Chọn STATUS ban đầu từ danh sách: {self.kb.get('statuses')}.
        4. Chọn Nhân sự phụ trách (Assigned) từ danh sách 'team_members' dựa vào kinh nghiệm/lĩnh vực.
        
        Trả về kết quả ĐÚNG ĐỊNH DẠNG JSON duy nhất như sau (không kèm markdown dư thừa):
        {{
            "summary": "Tóm tắt vấn đề ngắn gọn...",
            "category": "Software",
            "assigned_name": "Bryan",
            "assigned_email": "bryan@pythaverse.space",
            "status": "To Implement",
            "reasoning": "Lý do lựa chọn ngắn gọn"
        }}
        """

        user_prompt = f"""
        - Tiêu đề (Subject): {subject}
        - Remarks: {remarks}
        - Nội dung chi tiết trong Google Doc: {doc_content}
        """

        for model_name in self.models_priority:
            for attempt in range(2):  # Thử lại 2 lần mỗi model
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            response_mime_type="application/json",
                            temperature=0.2
                        )
                    )
                    
                    data = json.loads(response.text)
                    data["model_used"] = model_name
                    return data

                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        print(f"[AI Warning] Model {model_name} bị dính 429 Quota Exceed. Đang thử lại hoặc switch model...")
                        time.sleep(2)  # Nghỉ 2s rồi thử tiếp
                    else:
                        print(f"[AI Error] Lỗi khi gọi model {model_name}: {e}")
                        break # Chuyển sang model tiếp theo
                        
        # Trường hợp tất cả model đều thất bại (Fallback an toàn)
        return {
            "summary": "Không thể phân tích bằng AI do nghẽn API Quota.",
            "category": "other",
            "assigned_name": "Linh Đặng Thủy",
            "assigned_email": "linh.dt@pythaverse.space",
            "status": "Backlog",
            "reasoning": "Fallback do lỗi Quota API Gemini"
        }
