import gspread
from google.oauth2.service_account import Credentials

class GoogleSheetManager:
    def __init__(self, credentials_path: str, spreadsheet_title_or_key: str, sheet_name: str = "Form_Responses"):
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = self.client.open_by_key(spreadsheet_title_or_key) if len(spreadsheet_title_or_key) > 30 else self.client.open(spreadsheet_title_or_key)
        self.sheet = self.spreadsheet.worksheet(sheet_name)
        self._refresh_header_map()

    def _refresh_header_map(self):
        """Tự động ánh xạ Tên cột -> Chỉ số cột (1-indexed) để tránh lỗi lệch cột"""
        headers = self.sheet.row_values(1)
        self.col_map = {str(header).strip(): idx + 1 for idx, header in enumerate(headers)}

    def get_unprocessed_rows(self):
        """Lấy danh sách các dòng chưa được gán hoặc chưa có Status/Category"""
        records = self.sheet.get_all_records()
        unprocessed = []
        
        for idx, row in enumerate(records, start=2):  # Row 1 là Header
            category = str(row.get("CATEGORY", "")).strip()
            assigned = row.get("Assigned", False)
            status = str(row.get("STATUS", "")).strip()

            # Nếu chưa tick Assigned hoặc thiếu Category/Status thì đưa vào hàng chờ
            if not assigned or not category or not status:
                row_data = dict(row)
                row_data["_row_number"] = idx
                unprocessed.append(row_data)
                
        return unprocessed

    def update_row_data(self, row_number: int, category: str, assigned: bool, status: str):
        """Cập nhật kết quả vào Google Sheet"""
        self._refresh_header_map()
        
        if "CATEGORY" in self.col_map:
            self.sheet.update_cell(row_number, self.col_map["CATEGORY"], category)
        if "Assigned" in self.col_map:
            # Ghi TRUE/FALSE chuẩn checkbox Google Sheet
            self.sheet.update_cell(row_number, self.col_map["Assigned"], "TRUE" if assigned else "FALSE")
        if "STATUS" in self.col_map:
            self.sheet.update_cell(row_number, self.col_map["STATUS"], status)
