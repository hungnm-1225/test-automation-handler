import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials

class GoogleDocManager:
    def __init__(self, credentials_path: str):
        scopes = [
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    @staticmethod
    def extract_doc_id(url_or_id: str) -> str:
        """Trích xuất Document ID từ URL Google Doc"""
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', str(url_or_id))
        if match:
            return match.group(1)
        return url_or_id.strip()

    def read_doc_content(self, url_or_id: str) -> str:
        """Đọc nội dung văn bản từ Google Doc"""
        doc_id = self.extract_doc_id(url_or_id)
        if not doc_id:
            return ""
        try:
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            text_content = []
            for element in doc.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    for elem in element['paragraph'].get('elements', []):
                        if 'textRun' in elem:
                            text_content.append(elem['textRun'].get('content', ''))
            return "".join(text_content).strip()
        except Exception as e:
            print(f"[Doc Read Warning] Không thể đọc Doc {doc_id}: {e}")
            return "Không thể đọc nội dung file Doc (Có thể do giới hạn quyền truy cập)."

    def add_comment_and_tag(self, url_or_id: str, email: str, comment_text: str) -> tuple[bool, str]:
        """
        Tạo comment và tag email vào Google Doc.
        Trả về: (Thành công True/False, Thông báo chi tiết)
        """
        doc_id = self.extract_doc_id(url_or_id)
        if not doc_id:
            return False, "URL/ID Doc không hợp lệ"

        try:
            comment_body = {
                'content': f"@{email} {comment_text}"
            }
            self.drive_service.comments().create(
                fileId=doc_id,
                body=comment_body,
                fields='id'
            ).execute()
            return True, "Đã tag tên thành công vào Google Doc!"
            
        except HttpError as err:
            if err.resp.status in [403, 404]:
                return False, f"⚠️ Quyền truy cập bị từ chối (Chỉ có quyền Viewer hoặc Restricted). Cần quyền Commenter/Editor!"
            return False, f"Lỗi Google Drive API: {err}"
        except Exception as e:
            return False, f"Lỗi không xác định khi comment vào Doc: {str(e)}"
