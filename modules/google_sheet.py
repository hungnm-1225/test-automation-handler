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
        """
        Tự động lấy tên Tab thực tế trên Google Sheet để tránh lỗi 400 range
        """
        try:
            spreadsheet_info = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            sheets = spreadsheet_info.get('sheets', [])
            sheet_names = [s['properties']['title'] for s in sheets]
            
            if requested_name in sheet_names:
                return requested_name
            if len(sheet_names) > 0:
                logger.info(f"Chuyển tên Tab từ '{requested_name}' sang Tab thực tế '{sheet_names[0]}'")
                return sheet_names[0]
        except Exception as e:
            logger.error(f"Lỗi đọc tên Sheet: {e}")
        return requested_name

    def get_unprocessed_rows(self, sheet_name: str = "Feedbacks", *args, **kwargs):
        target_sheet_name = self._get_valid_sheet_name(sheet_name)
        range_name = f"'{target_sheet_name}'!A2:N"
        
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name
        ).execute()
        
        rows = result.get('values', [])
        unprocessed = []

        for index, row in enumerate(rows, start=2):
            def get_col(idx):
                return row[idx].strip() if idx < len(row) else ""

            fb_id = get_col(8)        # Cột I (Index 8)
            category = get_col(10)    # Cột K (Index 10)
            assigned_cb = get_col(11) # Cột L (Index 11)
            status = get_col(13)      # Cột N (Index 13)

            if assigned_cb.upper() != "TRUE" or not category or not status:
                unprocessed.append({
                    "row_index": index,
                    "sheet_name": target_sheet_name,
                    "timestamp": get_col(0),
                    "country": get_col(2),
                    "submitter": get_col(3),
                    "subject": get_col(4),
                    "doc_url": get_col(6),
                    "remarks": get_col(7),
                    "fb_id": fb_id if fb_id else f"FB-AUTO-{index}",
                    "category": category,
                    "status": status
                })
        return unprocessed

    def update_feedback_row(self, sheet_name: str, row_index: int, category: str, status: str, *args, **kwargs):
        # Tự động chuyển về đúng tên Tab thực tế trên Sheet
        target_sheet_name = self._get_valid_sheet_name(sheet_name)

        range_kl = f"'{target_sheet_name}'!K{row_index}:L{row_index}"
        body_kl = {"values": [[category, True]]}
        
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_kl,
            valueInputOption="USER_ENTERED",
            body=body_kl
        ).execute()

        range_n = f"'{target_sheet_name}'!N{row_index}"
        body_n = {"values": [[status]]}
        
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_n,
            valueInputOption="USER_ENTERED",
            body=body_n
        ).execute()
        
        logger.info(f"✅ Sheet row {row_index} in '{target_sheet_name}' updated successfully.")
