import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class GoogleSheetModule:
    def __init__(self, spreadsheet_id: str, creds_path: str = 'credentials.json'):
        self.spreadsheet_id = spreadsheet_id
        credentials = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        self.service = build('sheets', '4', credentials=credentials)

    def get_unprocessed_rows(self, sheet_name: str = 'Form_Responses'):
        sheet = self.service.spreadsheets()
        result = sheet.values().get(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!A2:Q100").execute()
        rows = result.get('values', [])
        
        unprocessed = []
        for index, row in enumerate(rows, start=2):
            category = row[10] if len(row) > 10 else ""
            if not category.strip():
                unprocessed.append({
                    "row_number": index,
                    "timestamp": row[0] if len(row) > 0 else "",
                    "country": row[1] if len(row) > 1 else "",
                    "submitter": row[2] if len(row) > 2 else "",
                    "subject": row[3] if len(row) > 3 else "",
                    "doc_link": row[5] if len(row) > 5 else "",
                    "remarks": row[6] if len(row) > 6 else "",
                    "fb_id": row[8] if len(row) > 8 else f"FB-{index:03d}"
                })
        return unprocessed

    def update_feedback_row(self, row_number: int, category: str, assigned_person: str, status: str = "To Implement", sheet_name: str = 'Form_Responses'):
        sheet = self.service.spreadsheets().values()
        sheet.update(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!K{row_number}", valueInputOption="USER_ENTERED", body={'values': [[category]]}).execute()
        sheet.update(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!L{row_number}", valueInputOption="USER_ENTERED", body={'values': [[assigned_person]]}).execute()
        sheet.update(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!P{row_number}", valueInputOption="USER_ENTERED", body={'values': [[status]]}).execute()
        print(f"✅ Đã cập nhật dòng #{row_number} trên Google Sheet!")

    def get_dashboard_stats(self, sheet_name: str = 'Form_Responses') -> dict:
        sheet = self.service.spreadsheets()
        result = sheet.values().get(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!A2:P200").execute()
        rows = result.get('values', [])

        stats = {"total": len(rows), "new_requests": 0, "in_progress": 0, "completed": 0}
        for row in rows:
            category = row[10] if len(row) > 10 else ""
            status = row[15] if len(row) > 15 else ""

            if not category.strip() or not status.strip():
                stats["new_requests"] += 1
            elif status in ["Closed", "Resolved"]:
                stats["completed"] += 1
            else:
                stats["in_progress"] += 1
        return stats
