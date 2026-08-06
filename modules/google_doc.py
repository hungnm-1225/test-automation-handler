import re
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']

class GoogleDocModule:
    def __init__(self, creds_path: str = 'credentials.json'):
        self.creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)

    def extract_doc_id(self, url: str) -> str:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        return match.group(1) if match else None

    def read_doc_content(self, url: str) -> dict:
        doc_id = self.extract_doc_id(url)
        if not doc_id:
            return {"status": "invalid_url", "content": "", "warning": "URL Google Doc không hợp lệ"}

        try:
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            doc_text = ""
            for element in document.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    for p_elem in element['paragraph'].get('elements', []):
                        if 'textRun' in p_elem:
                            doc_text += p_elem['textRun'].get('content', '')

            return {
                "status": "full_access",
                "doc_title": document.get('title', 'Untitled'),
                "content": doc_text.strip(),
                "warning": "None"
            }
        except Exception as e:
            return {
                "status": "restricted",
                "doc_title": "Khóa truy cập",
                "content": "",
                "warning": f"🔒 Doc bị khóa quyền. Cần bấm Request Access!"
            }

    def add_comment_and_assign(self, url: str, tag_email: str, comment_text: str):
        """TỰ ĐỘNG CHÈN COMMENT & CẤP QUYỀN ASSIGN ACTION ITEM CHO EMAIL"""
        doc_id = self.extract_doc_id(url)
        if not doc_id: return False, "URL không hợp lệ"

        try:
            body = {
                'content': f"@{tag_email} {comment_text}",
                'assignee': {
                    'emailAddress': tag_email  # KÍCH HOẠT TỰ ĐỘNG ASSIGN TO YOU TƯƠNG TỰ HÌNH 5
                }
            }
            self.drive_service.comments().create(fileId=doc_id, body=body, fields='id').execute()
            print(f"✅ Đã tự động Assign Action Item cho {tag_email} trên Doc!")
            return True, "Thành công"
        except Exception as e:
            return False, f"Lỗi Assign: {e}"
