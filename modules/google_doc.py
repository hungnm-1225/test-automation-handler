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
        """Kiểm tra và đọc nội dung Doc theo 3 Cấp độ phân quyền"""
        doc_id = self.extract_doc_id(url)
        if not doc_id:
            return {"status": "invalid_url", "content": "", "warning": "URL Google Doc không đúng định dạng"}

        try:
            # Thu thập thông tin tài liệu
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            doc_text = ""
            for element in document.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    for p_elem in element['paragraph'].get('elements', []):
                        if 'textRun' in p_elem:
                            doc_text += p_elem['textRun'].get('content', '')

            # Kiểm tra xem có quyền Comment hay không
            file_metadata = self.drive_service.files().get(fileId=doc_id, fields="capabilities").execute()
            can_comment = file_metadata.get('capabilities', {}).get('canComment', False)

            if can_comment:
                # LEVEL 1: Đầy đủ quyền Read + Comment
                return {
                    "status": "full_access",
                    "doc_title": document.get('title', 'Untitled'),
                    "content": doc_text.strip(),
                    "warning": "None"
                }
            else:
                # LEVEL 2: Chỉ có quyền Read (View Only), không Comment được
                return {
                    "status": "view_only",
                    "doc_title": document.get('title', 'Untitled'),
                    "content": doc_text.strip(),
                    "warning": "⚠️ Doc ở chế độ View Only (Cần mở quyền Commenter để Tag nhân sự)"
                }

        except Exception as e:
            # LEVEL 3: Restricted / Khóa kín hoàn toàn (Lỗi 403)
            return {
                "status": "restricted",
                "doc_title": "Khóa truy cập",
                "content": "",
                "warning": f"🔒 Tài liệu bị KHÓA QUYỀN TRUY CẬP (Restricted). Anh cần nhấp vào link để Bấm 'Request Access'!"
            }

    def add_comment_and_tag(self, url: str, tag_email: str, comment_text: str):
        """Thử chèn comment, nếu lỗi thiếu quyền sẽ trả về thông báo"""
        doc_id = self.extract_doc_id(url)
        if not doc_id: return False, "URL không hợp lệ"

        try:
            body = {'content': f"@{tag_email} {comment_text}"}
            self.drive_service.comments().create(fileId=doc_id, body=body, fields='id').execute()
            return True, "Thành công"
        except Exception as e:
            return False, f"Không thể Comment do thiếu quyền (Chi tiết: {e})"