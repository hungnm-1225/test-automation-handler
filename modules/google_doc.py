import os
import json
import re
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']

class GoogleDocModule:
    def __init__(self, creds_path: str = 'credentials.json'):
        # Ưu tiên 1: Đọc từ Biến Môi Trường trên Render
        env_creds = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if env_creds:
            try:
                creds_info = json.loads(env_creds)
                self.creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            except Exception as e:
                raise ValueError(f"Lỗi đọc JSON từ GOOGLE_CREDENTIALS_JSON: {e}")
        # Ưu tiên 2: Đọc từ file credentials.json ở Local
        elif os.path.exists(creds_path):
            self.creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        else:
            raise FileNotFoundError(f"Không tìm thấy biến GOOGLE_CREDENTIALS_JSON hoặc file {creds_path}")

        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    def extract_doc_id(self, url: str) -> str:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        return match.group(1) if match else None

    def read_doc_content(self, url: str) -> dict:
        doc_id = self.extract_doc_id(url)
        if not doc_id:
            return {"status": "invalid_url", "content": "", "warning": "URL không đúng định dạng"}

        try:
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            doc_text = ""
            for element in document.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    for p_elem in element['paragraph'].get('elements', []):
                        if 'textRun' in p_elem:
                            doc_text += p_elem['textRun'].get('content', '')

            file_metadata = self.drive_service.files().get(fileId=doc_id, fields="capabilities").execute()
            can_comment = file_metadata.get('capabilities', {}).get('canComment', False)

            if can_comment:
                return {"status": "full_access", "doc_title": document.get('title', 'Untitled'), "content": doc_text.strip(), "warning": "None"}
            else:
                return {"status": "view_only", "doc_title": document.get('title', 'Untitled'), "content": doc_text.strip(), "warning": "⚠️ Doc ở chế độ View Only"}

        except Exception as e:
            return {"status": "restricted", "doc_title": "Khóa truy cập", "content": "", "warning": "🔒 Tài liệu bị KHÓA QUYỀN TRUY CẬP (Restricted)"}

    def add_comment_and_tag(self, url: str, tag_email: str, comment_text: str):
        doc_id = self.extract_doc_id(url)
        if not doc_id: return False, "URL không hợp lệ"

        try:
            body = {'content': f"@{tag_email} {comment_text}"}
            self.drive_service.comments().create(fileId=doc_id, body=body, fields='id').execute()
            return True, "Thành công"
        except Exception as e:
            return False, f"Không thể Comment: {e}"
