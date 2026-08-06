def get_unprocessed_rows(self, sheet_name: str = 'Form_Responses'):
        sheet = self.service.spreadsheets()
        result = sheet.values().get(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!A2:N100").execute()
        rows = result.get('values', [])
        
        unprocessed = []
        for index, row in enumerate(rows, start=2):
            # Cột J tương ứng với index 9 trong mảng
            category = row[9] if len(row) > 9 else ""
            if not category.strip(): # Nếu Cột J trống -> Cần xử lý
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

    def update_feedback_row(self, row_number: int, category: str, assigned_person: str, targetted_date: str = "", status: str = "To Implement", sheet_name: str = 'Form_Responses'):
        """Ghi dữ liệu chuẩn vào từ Cột J đến Cột M"""
        sheet = self.service.spreadsheets().values()
        
        # Cột J: CATEGORY (Column 10 / J)
        sheet.update(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!J{row_number}", valueInputOption="USER_ENTERED", body={'values': [[category]]}).execute()
        # Cột K: Assigned (Column 11 / K)
        sheet.update(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!K{row_number}", valueInputOption="USER_ENTERED", body={'values': [[assigned_person]]}).execute()
        # Cột L: Targetted Date (Column 12 / L)
        if targetted_date:
            sheet.update(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!L{row_number}", valueInputOption="USER_ENTERED", body={'values': [[targetted_date]]}).execute()
        # Cột M: STATUS (Column 13 / M)
        sheet.update(spreadsheetId=self.spreadsheet_id, range=f"'{sheet_name}'!M{row_number}", valueInputOption="USER_ENTERED", body={'values': [[status]]}).execute()
        
        print(f"✅ Đã điền tự động Cột J->M cho dòng #{row_number} trên Sheet!")
