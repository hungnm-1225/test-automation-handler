import os
import re
import json
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive'
]

def get_google_credentials():
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json_str:
        raise ValueError("❌ THIẾU CẤU HÌNH: Không tìm thấy biến môi trường GOOGLE_CREDENTIALS_JSON trên Render!")
    
    try:
        info = json.loads(creds_json_str)
        return Credentials.from_service_account_info(info, scopes=SCOPES)
    except Exception as e:
        raise ValueError(f"❌ Lỗi định dạng JSON trong biến GOOGLE_CREDENTIALS_JSON: {e}")

class GoogleDocManager:
    def __init__(self):
        self.creds = get_google_credentials()
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    @staticmethod
    def extract_doc_id(url: str) -> str:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        return match.group(1) if match else None

    def read_doc_content(self, doc_url: str) -> tuple[str, str]:
        doc_id = self.extract_doc_id(doc_url)
        if not doc_id:
            return "", "URL_INVALID"

        try:
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            content = ""
            for item in doc.get('body', {}).get('content', []):
                if 'paragraph' in item:
                    elements = item.get('paragraph', {}).get('elements', [])
                    for elem in elements:
                        content += elem.get('textRun', {}).get('content', '')
            return content.strip(), None
        except HttpError as e:
            if e.resp.status in [403, 404]:
                logger.warning(f"Không thể đọc Doc {doc_id}: Quyền truy cập bị từ chối hoặc file không tồn tại.")
                return "", "PERMISSION_DENIED"
            return "", f"HTTP_ERROR_{e.resp.status}"
        except Exception as e:
            return "", str(e)

    def add_comment_and_tag(self, doc_url: str, comment_text: str, tag_email: str) -> tuple[bool, str]:
        doc_id = self.extract_doc_id(doc_url)
        if not doc_id:
            return False, "Đường dẫn Google Doc không hợp lệ."

        full_comment = f"{comment_text}\n\nCc: +{tag_email}"

        try:
            body = {'content': full_comment}
            self.drive_service.comments().create(
                fileId=doc_id,
                body=body,
                fields='id'
            ).execute()
            return True, "Thành công"
        except HttpError as e:
            if e.resp.status == 403:
                return False, "⚠️ File Doc ở chế độ Viewer/Restricted (Cần quyền Commenter)."
            return False, f"Lỗi Google API: {e.reason}"
        except Exception as e:
            return False, str(e)
