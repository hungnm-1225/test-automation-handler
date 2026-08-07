import os
import logging
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive'
]

def load_credentials():
    # 1. Ưu tiên đọc từ biến môi trường Render (dạng chuỗi JSON)
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json_str:
        try:
            info = json.loads(creds_json_str)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            print(f"Lỗi parse GOOGLE_CREDENTIALS_JSON: {e}")

    # 2. Dự phòng nếu chạy thử dưới Local có file credentials.json
    if os.path.exists("credentials.json"):
        return Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

    raise ValueError("❌ KHÔNG TÌM THẤY GOOGLE CREDENTIALS TRÊN RENDER HOẶC FILE LOCAL!")

class GoogleSheetManager:
    def __init__(self, spreadsheet_id: str, creds_path: str = "credentials.json"):
        self.spreadsheet_id = spreadsheet_id
        self.creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        self.service = build('sheets', 'v4', credentials=self.creds)

    def get_unprocessed_rows(self, sheet_name: str = "Feedbacks"):
        """
        Lấy các dòng chưa xử lý (Ô Assigned ở cột L là False/Trống hoặc Status/Category trống)
        """
        range_name = f"{sheet_name}!A2:N"
        result = self.service.spreadsheets().values().get(
            spreadsheet_id=self.spreadsheet_id,
            range=range_name
        ).execute()
        
        rows = result.get('values', [])
        unprocessed = []

        for index, row in enumerate(rows, start=2): # Hàng 1 là Header
            # Đảm bảo row có đủ phần tử để đọc
            def get_col(idx):
                return row[idx].strip() if idx < len(row) else ""

            fb_id = get_col(8)       # Cột I (Index 8)
            category = get_col(10)   # Cột K (Index 10)
            assigned_cb = get_col(11)# Cột L (Index 11) - Checkbox TRUE/FALSE
            status = get_col(13)     # Cột N (Index 13)

            # Nếu chưa tick checkbox Assigned (hoặc FALSE/trống)
            if assigned_cb.upper() != "TRUE" or not category or not status:
                unprocessed.append({
                    "row_index": index,
                    "timestamp": get_col(0),   # Col A
                    "country": get_col(2),     # Col C
                    "submitter": get_col(3),   # Col D
                    "subject": get_col(4),     # Col E
                    "doc_url": get_col(6),     # Col G
                    "remarks": get_col(7),     # Col H
                    "fb_id": fb_id if fb_id else f"FB-AUTO-{index}",
                    "category": category,
                    "status": status
                })
        return unprocessed

    def update_feedback_row(self, sheet_name: str, row_index: int, category: str, status: str):
        """
        Cập nhật Category (Col K), Mark Assigned = TRUE (Col L), Status (Col N)
        """
        # Cập nhật Category (K) & Assigned (L = TRUE)
        range_kl = f"{sheet_name}!K{row_index}:L{row_index}"
        body_kl = {
            "values": [[category, True]]
        }
        self.service.spreadsheets().values().update(
            spreadsheet_id=self.spreadsheet_id,
            range=range_kl,
            valueInputOption="USER_ENTERED",
            body=body_kl
        ).execute()

        # Cập nhật Status (N)
        range_n = f"{sheet_name}!N{row_index}"
        body_n = {
            "values": [[status]]
        }
        self.service.spreadsheets().values().update(
            spreadsheet_id=self.spreadsheet_id,
            range=range_n,
            valueInputOption="USER_ENTERED",
            body=body_n
        ).execute()
        
        logger.info(f"✅ Updated Sheet Row {row_index}: Category={category}, Assigned=TRUE, Status={status}")
