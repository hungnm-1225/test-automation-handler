def send_approval_card(self, row_data: dict, ai_analysis: dict):
        # Lấy chính xác tên Model Gemini 3.x đã vừa xử lý thành công
        model_name = ai_analysis.get('used_model', os.getenv('GEMINI_MODEL', 'gemini-3.6-flash'))
        warning_text = f"\n⚠️ **CẢNH BÁO:** {ai_analysis.get('doc_warning')}" if ai_analysis.get('doc_warning') != "None" else ""
        
        message_text = f"""
📥 **[FEEDBACK MỚI - #{row_data.get('fb_id')}]**

👤 **Người gửi:** {row_data.get('submitter')} ({row_data.get('country')})
📌 **Tiêu đề:** {row_data.get('subject')}
📝 **Ghi chú:** {row_data.get('remarks') or 'Không có'}
📄 **Google Doc:** [Mở Document]({row_data.get('doc_link')}){warning_text}

---
🧠 **AI TÓM TẮT DỮ LIỆU ({model_name}):**
• {ai_analysis.get('summary')}

🎯 **AI ĐỀ XUẤT:**
• **Category:** `{ai_analysis.get('category')}`
• **Phân công:** {ai_analysis.get('suggested_assignee_name')} (`{ai_analysis.get('suggested_assignee_email')}`)

👇 **ANH HÙNG NGUYỄN MẠNH BẤM DUYỆT BÊN DƯỚI:**
        """
        # ... (Phần bên dưới giữ nguyên) ...
