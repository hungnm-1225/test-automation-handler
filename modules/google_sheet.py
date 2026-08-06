import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class GoogleSheetModule:
    def __init__(self, spreadsheet_id: str, creds_path: str = 'credentials.json'):
        self.spreadsheet_id = spreadsheet_id
        credentials = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        self.service = build('sheets', 'v4', credentials=credentials)
        self._cached_sheet_name = None

    def get_first_sheet_name(self) -> str:
        """Tự động lấy tên tab đầu tiên trong file Google Sheet để tránh lỗi sai tên trang"""
        if self._cached_sheet_name:
            return self._cached_sheet_name

        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            if sheets:
                self._cached_sheet_name = sheets[0]['properties']['title']
                print(f"📌 Tự động nhận diện Tab Google Sheet là: '{self._cached_sheet_name}'")
                return self._cached_sheet_name
        except Exception as e:
            print(f"⚠️ Không thể lấy metadata tab, dùng tên mặc định 'Form_Responses'. Lỗi: {e}")
            
        return 'Form_Responses'

    def get_unprocessed_rows(self, sheet_name: str = None):
        """Đọc danh sách các dòng chưa có CATEGORY (Cột K trống)"""
        sheet_name = sheet_name or self.get_first_sheet_name()
        sheet = self.service.spreadsheets()
        
        result = sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{sheet_name}'!A2:Q100"
        ).execute()
        rows = result.get('values', [])
        
        unprocessed = []
        for index, row in enumerate(rows, start=2): # Bắt đầu từ dòng 2
            category = row[10] if len(row) > 10 else ""
            if not category.strip():
                unprocessed.append({
                    "row_number": index,
                    "timestamp": row[0] if len(row) > 0 else "",
                    "country": row[1] if len(row) > 1 else "",
                    "submitter": row[2] if len(row) > 2 else "",
                    "subject": row[5] if len(row) > 5 else "",      # Cột F: SUBJECT
                    "doc_link": row[6] if len(row) > 6 else "",     # Cột G: REPORT GoogleDoc
                    "remarks": row[7] if len(row) > 7 else "",      # Cột H: REMARKS
                    "fb_id": row[8] if len(row) > 8 else f"FB-{index:03d}" # Cột I: FB ID
                })
        return unprocessed

    def update_feedback_row(self, row_number: int, category: str, assigned_person: str, status: str = "To Implement", sheet_name: str = None):
        """Cập nhật kết quả sau khi anh bấm Duyệt trên Telegram"""
        sheet_name = sheet_name or self.get_first_sheet_name()
        
        range_category = f"'{sheet_name}'!K{row_number}"
        range_assigned = f"'{sheet_name}'!L{row_number}"
        range_status = f"'{sheet_name}'!P{row_number}"

        body_cat = {'values': [[category]]}
        body_assign = {'values': [[assigned_person]]}
        body_status = {'values': [[status]]}

        sheet = self.service.spreadsheets().values()
        sheet.update(spreadsheetId=self.spreadsheet_id, range=range_category, valueInputOption="USER_ENTERED", body=body_cat).execute()
        sheet.update(spreadsheetId=self.spreadsheet_id, range=range_assigned, valueInputOption="USER_ENTERED", body=body_assign).execute()
        sheet.update(spreadsheetId=self.spreadsheet_id, range=range_status, valueInputOption="USER_ENTERED", body=body_status).execute()
        print(f"✅ Đã cập nhật dòng {row_number} trên Google Sheet thành công!")

    def get_dashboard_stats(self, sheet_name: str = None) -> dict:
        """Đọc và thống kê nhanh chỉ số của toàn bộ danh sách Feedback"""
        sheet_name = sheet_name or self.get_first_sheet_name()
        sheet = self.service.spreadsheets()
        
        result = sheet.values().get(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!A2:P200").execute()
        rows = result.get('values', [])

        stats = {
            "total": len(rows),
            "new_requests": 0,
            "in_progress": 0,
            "completed": 0
        }

        for row in rows:
            category = row[10] if len(row) > 10 else ""
            assigned = row[11] if len(row) > 11 else ""
            status = row[15] if len(row) > 15 else ""

            if not category.strip() or not status.strip():
                stats["new_requests"] += 1
            elif status in ["Closed", "Resolved"]:
                stats["completed"] += 1
            else:
                stats["in_progress"] += 1

        return stats
