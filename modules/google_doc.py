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
        # ĐẶT BÊN TRONG HÀM __init__
        self.docs_service = build('docs', 'v1', credentials=self.creds, cache_discovery=False)
        self.drive_service = build('drive', 'v3', credentials=self.creds, cache_discovery=False)

    @staticmethod
    def extract_doc_id(url: str) -> str:
        if not url:
            return None
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        return match.group(1) if match else None

    def check_comment_permission(self, doc_url: str) -> tuple[bool, str]:
        doc_id = self.extract_doc_id(doc_url)
        if not doc_id:
            return False, "INVALID_URL"
        try:
            file_meta = self.drive_service.files().get(
                fileId=doc_id,
                fields="capabilities"
            ).execute()
            capabilities = file_meta.get("capabilities", {})
            can_comment = capabilities.get("canComment", False)
            return can_comment, "OK" if can_comment else "RESTRICTED"
        except HttpError as e:
            logger.warning(f"Không thể kiểm tra quyền Doc {doc_id}: {e}")
            return False, "RESTRICTED"
        except Exception as e:
            return False, str(e)

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
            return "", "PERMISSION_DENIED"
        except Exception as e:
            return "", str(e)

    def add_comment_and_tag(self, doc_url: str, comment_text_en: str, tag_email: str) -> tuple[bool, str]:
        doc_id = self.extract_doc_id(doc_url)
        if not doc_id:
            return False, "Invalid Google Doc URL."

        full_comment = f"{comment_text_en}\n\nCc: +{tag_email}"

        try:
            body = {'content': full_comment}
            self.drive_service.comments().create(
                fileId=doc_id,
                body=body,
                fields='id'
            ).execute()
            return True, "Success"
        except HttpError as e:
            if e.resp.status == 403:
                return False, "Permission Denied: Document needs Commenter access for Everyone."
            return False, f"Google API Error: {e.reason}"
        except Exception as e:
            return False, str(e)
