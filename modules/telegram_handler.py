if action == "approve":
            await query.edit_message_text(f"⏳ Đang thực thi gán dữ liệu vào Sheet & Doc cho `{fb_id}`...")
            
            try:
                row_idx = task['row_index']
                ai_res = task['ai_res']
                doc_url = task['doc_url']
                target_sheet = task.get('sheet_name', 'Form Responses')

                # 1. Cập nhật Google Sheet với đúng Tab Name
                self.sheet_mgr.update_feedback_row(
                    sheet_name=target_sheet,
                    row_index=row_idx,
                    category=ai_res['category'],
                    status=ai_res['status']
                )

                # 2. Tag người dùng vào Google Doc
                doc_msg = "Không có URL Doc."
                if doc_url:
                    comment_text = f"Hi {ai_res['assigned_name']}, tác vụ feedback này đã được gán cho bạn. Nội dung: {ai_res['summary']}"
                    success, msg = self.doc_mgr.add_comment_and_tag(
                        doc_url=doc_url,
                        comment_text=comment_text,
                        tag_email=ai_res['assigned_email']
                    )
                    doc_msg = msg

                await query.edit_message_text(
                    f"✅ **ĐÃ XỬ LÝ THÀNH CÔNG [{fb_id}]**\n\n"
                    f"• Cập nhật Sheet: Thành công\n"
                    f"• Comment Google Doc: {doc_msg}"
                )
            except Exception as e:
                logger.error(f"Lỗi thực thi: {e}")
                await query.edit_message_text(f"❌ **XỬ LÝ THẤT BẠI [{fb_id}]**: {str(e)}")

            del self.pending_tasks[fb_id]
