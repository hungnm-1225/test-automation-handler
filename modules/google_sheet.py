import os
import json
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
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

class GoogleSheetManager:
    def __init__(self, spreadsheet_id: str = None, *args, **kwargs):
        self.spreadsheet_id = spreadsheet_id or os.getenv("SPREADSHEET_ID")
        self.creds = get_google_credentials()
        self.service = build('sheets', 'v4', credentials=self.creds)

    def _get_valid_sheet_name(self, requested_name: str) -> str:
        try:
            spreadsheet_info = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            sheets = spreadsheet_info.get('sheets', [])
            sheet_names = [s['properties']['title'] for s in sheets]
            
            if requested_name in sheet_names:
                return requested_name
            if len(sheet_names) > 0:
                return sheet_names[0]
        except Exception as e:
            logger.error(f"Lỗi đọc tên Sheet: {e}")
        return requested_name

    def get_unprocessed_rows(self, sheet_name: str = "Feedbacks", *args, **kwargs):
        target_sheet_name = self._get_valid_sheet_name(sheet_name)
        range_name = f"'{target_sheet_name}'!A2:P"
        
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name
        ).execute()
        
        rows = result.get('values', [])
        unprocessed = []

        for index, row in enumerate(rows, start=2):
            def get_col(idx):
                return row[idx].strip() if idx < len(row) else ""

            submitter = get_col(3)     # Cột D (Submitter Name)
            subject = get_col(4)       # Cột E (Subject)
            email = get_col(5)         # Cột F (Email)
            doc_url = get_col(6)       # Cột G (Report GoogleDoc)
            fb_id = get_col(8)         # Cột I (FB ID)
            category = get_col(11)     # Cột L (CATEGORY)
            assigned_cb = get_col(12)  # Cột M (Assigned Checkbox)
            status = get_col(15)       # Cột P (STATUS)

            # Lọc: Chỉ xử lý nếu Cột M (Assigned) CHƯA được tick [x]
            if assigned_cb.upper() != "TRUE" and (submitter or subject or fb_id):
                unprocessed.append({
                    "row_index": index,
                    "sheet_name": target_sheet_name,
                    "timestamp": get_col(0),
                    "country": get_col(2),
                    "submitter": submitter,
                    "subject": subject,
                    "email": email,
                    "doc_url": doc_url,
                    "remarks": get_col(7),
                    "fb_id": fb_id if fb_id else f"FB-AUTO-{index}",
                    "category": category,
                    "status": status
                })
        return unprocessed

    def update_feedback_row(self, sheet_name: str, row_index: int, category: str, status: str = "To Implement", *args, **kwargs):
        target_sheet_name = self._get_valid_sheet_name(sheet_name)

        # 1. Cập nhật Cột L (CATEGORY) và Cột M (Assigned Checkbox = TRUE)
        range_lm = f"'{target_sheet_name}'!L{row_index}:M{row_index}"
        body_lm = {"values": [[category, True]]}
        
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_lm,
            valueInputOption="USER_ENTERED",
            body=body_lm
        ).execute()

        # 2. Cập nhật Cột P (STATUS)
        range_p = f"'{target_sheet_name}'!P{row_index}"
        body_p = {"values": [[status]]}
        
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_p,
            valueInputOption="USER_ENTERED",
            body=body_p
        ).execute()
        
        logger.info(f"✅ Updated Row {row_index} [{target_sheet_name}]: Category={category}, Assigned=TRUE, Status={status} (Cột P)")
