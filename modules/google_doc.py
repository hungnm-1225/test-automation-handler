import re
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive'
]

class GoogleDocManager:
    def __init__(self, creds_path: str = "credentials.json"):
        self.creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    @staticmethod
    def extract_doc_id(url: str) -> str:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        return match.group(1) if match else None

    def read_doc_content(self, doc_url: str) -> tuple[str, str]:
        """
        Trả về (content, error_flag). Lấy chữ trong file Google Doc.
        """
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
        """
        Thêm Comment và Tag email vào Google Doc thông qua Google Drive API v3
        """
        doc_id = self.extract_doc_id(doc_url)
        if not doc_id:
            return False, "Đường dẫn Google Doc không hợp lệ."

        full_comment = f"{comment_text}\n\nCc: +{tag_email}"

        try:
            body = {
                'content': full_comment
            }
            # Sử dụng Drive API v3
            self.drive_service.comments().create(
                fileId=doc_id,
                body=body,
                fields='id'
            ).execute()
            return True, "Thành công"
        except HttpError as e:
            if e.resp.status == 403:
                return False, "⚠️ KHÔNG THỂ TAG: File Doc ở chế độ chỉ xem (Viewer/Restricted). Cần cấp quyền Commenter/Editor cho Service Account!"
            return False, f"Lỗi Google API: {e.reason}"
        except Exception as e:
            return False, str(e)
