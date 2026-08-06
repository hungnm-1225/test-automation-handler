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
        if self._cached_sheet_name:
            return self._cached_sheet_name
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            if sheets:
                self._cached_sheet_name = sheets[0]['properties']['title']
                return self._cached_sheet_name
        except Exception as e:
            print(f"⚠️ Lỗi lấy tên tab: {e}")
        return 'Form Responses'

    def get_unprocessed_rows(self, sheet_name: str = None):
        sheet_name = sheet_name or self.get_first_sheet_name()
        sheet = self.service.spreadsheets()
        
        result = sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{sheet_name}'!A2:Q100"
        ).execute()
        rows = result.get('values', [])
        
        unprocessed = []
        for index, row in enumerate(rows, start=2):
            # Lấy đúng vị trí cột trên Sheet của anh:
            # J=Index 9 (CATEGORY), N=Index 13 (STATUS)
            category = row[9].strip() if len(row) > 9 else ""
            status = row[13].strip() if len(row) > 13 else ""
            
            # ĐIỀU KIỆN MỚI: Nếu CATEGORY trống HOẶC STATUS trống -> Xem là Feedback mới!
            if not category or not status:
                unprocessed.append({
                    "row_number": index,
                    "timestamp": row[0] if len(row) > 0 else "",
                    "country": row[1] if len(row) > 1 else "",
                    "submitter": row[2] if len(row) > 2 else "",
                    "email": row[3] if len(row) > 3 else "",
                    "subject": row[4] if len(row) > 4 else "",      # Cột E: SUBJECT
                    "doc_link": row[5] if len(row) > 5 else "",     # Cột F: REPORT GoogleDoc
                    "remarks": row[6] if len(row) > 6 else "",      # Cột G: REMARKS
                    "fb_id": row[7] if len(row) > 7 else f"FB-{index:03d}" # Cột H: FB ID
                })
        return unprocessed

    def update_feedback_row(self, row_number: int, category: str, assigned_person: str, status: str = "To Implement", sheet_name: str = None):
        sheet_name = sheet_name or self.get_first_sheet_name()
        
        range_category = f"'{sheet_name}'!J{row_number}" # Cột J
        range_assigned = f"'{sheet_name}'!K{row_number}" # Cột K
        range_status = f"'{sheet_name}'!N{row_number}"   # Cột N

        sheet = self.service.spreadsheets().values()
        sheet.update(spreadsheetId=self.spreadsheet_id, range=range_category, valueInputOption="USER_ENTERED", body={'values': [[category]]}).execute()
        sheet.update(spreadsheetId=self.spreadsheet_id, range=range_assigned, valueInputOption="USER_ENTERED", body={'values': [[assigned_person]]}).execute()
        sheet.update(spreadsheetId=self.spreadsheet_id, range=range_status, valueInputOption="USER_ENTERED", body={'values': [[status]]}).execute()
        print(f"✅ Đã cập nhật dòng {row_number} trên Google Sheet!")

    def get_dashboard_stats(self, sheet_name: str = None) -> dict:
        sheet_name = sheet_name or self.get_first_sheet_name()
        result = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!A2:Q200").execute()
        rows = result.get('values', [])
        stats = {"total": len(rows), "new_requests": 0, "in_progress": 0, "completed": 0}

        for row in rows:
            category = row[9].strip() if len(row) > 9 else ""
            status = row[13].strip() if len(row) > 13 else ""
            if not category or not status: stats["new_requests"] += 1
            elif status in ["Closed", "Resolved"]: stats["completed"] += 1
            else: stats["in_progress"] += 1
        return stats
