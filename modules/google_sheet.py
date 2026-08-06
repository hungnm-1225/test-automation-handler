import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class GoogleSheetModule:
    def __init__(self, spreadsheet_id: str, creds_path: str = 'credentials.json'):
        self.spreadsheet_id = spreadsheet_id
        
        env_creds = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if env_creds:
            try:
                creds_info = json.loads(env_creds)
                credentials = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            except Exception as e:
                raise ValueError(f"Lỗi đọc JSON từ GOOGLE_CREDENTIALS_JSON: {e}")
        elif os.path.exists(creds_path):
            credentials = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        else:
            raise FileNotFoundError(f"Không tìm thấy biến GOOGLE_CREDENTIALS_JSON hoặc file {creds_path}")

        self.service = build('sheets', 'v4', credentials=credentials)

    def get_first_sheet_name(self) -> str:
        """Tự động hỏi Google Sheet lấy tên Tab đầu tiên để tránh lỗi sai tên Tab"""
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            if sheets:
                title = sheets[0]['properties']['title']
                print(f"📊 Tìm thấy tên Tab thực tế trên Sheet: '{title}'")
                return title
        except Exception as e:
            print(f"⚠️ Lỗi tự động lấy tên sheet: {e}")
        return 'Form Responses 1'

    def get_unprocessed_rows(self, sheet_name: str = None):
        if not sheet_name:
            sheet_name = self.get_first_sheet_name()

        sheet = self.service.spreadsheets()
        result = sheet.values().get(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!A2:N100").execute()
        rows = result.get('values', [])
        
        unprocessed = []
        for index, row in enumerate(rows, start=2):
            category = row[9] if len(row) > 9 else ""
            if not category.strip():
                unprocessed.append({
                    "row_number": index,
                    "timestamp": row[0] if len(row) > 0 else "",
                    "country": row[1] if len(row) > 1 else "",
                    "submitter": row[2] if len(row) > 2 else "",
                    "email": row[3] if len(row) > 3 else "",
                    "subject": row[4] if len(row) > 4 else "",
                    "doc_link": row[5] if len(row) > 5 else "",
                    "remarks": row[6] if len(row) > 6 else "",
                    "fb_id": row[7] if len(row) > 7 else f"FB-{index:03d}"
                })
        return unprocessed

    def update_feedback_row(self, row_number: int, category: str, assigned_person: str, targetted_date: str = "", status: str = "To Implement", sheet_name: str = None):
        if not sheet_name:
            sheet_name = self.get_first_sheet_name()

        sheet = self.service.spreadsheets().values()
        sheet.update(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!J{row_number}", valueInputOption="USER_ENTERED", body={'values': [[category]]}).execute()
        sheet.update(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!K{row_number}", valueInputOption="USER_ENTERED", body={'values': [[assigned_person]]}).execute()
        if targetted_date:
            sheet.update(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!L{row_number}", valueInputOption="USER_ENTERED", body={'values': [[targetted_date]]}).execute()
        sheet.update(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!M{row_number}", valueInputOption="USER_ENTERED", body={'values': [[status]]}).execute()
        print(f"✅ Đã điền tự động Cột J->M cho dòng #{row_number} trên Sheet '{sheet_name}'!")

    def get_dashboard_stats(self, sheet_name: str = None) -> dict:
        if not sheet_name:
            sheet_name = self.get_first_sheet_name()

        sheet = self.service.spreadsheets()
        result = sheet.values().get(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!A2:M200").execute()
        rows = result.get('values', [])

        stats = {"total": len(rows), "new_requests": 0, "in_progress": 0, "completed": 0}
        for row in rows:
            category = row[9] if len(row) > 9 else ""
            status = row[12] if len(row) > 12 else ""

            if not category.strip() or not status.strip():
                stats["new_requests"] += 1
            elif status in ["Closed", "Resolved"]:
                stats["completed"] += 1
            else:
                stats["in_progress"] += 1
        return stats
