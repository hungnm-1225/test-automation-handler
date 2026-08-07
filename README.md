# 🤖 PTV Support Ticket Automation Agent

Hệ thống tự động hóa tiếp nhận Feedback từ Google Forms/Sheet, phân tích nội dung đính kèm trong Google Doc bằng Gemini AI, duyệt qua Telegram Bot và cập nhật ngược lại Google Sheet/Google Doc.

## 🛠️ Công Nghệ Sử Dụng
- **Ngôn ngữ:** Python 3.10+
- **Google APIs:** Sheets API v4, Docs API v1, Drive API v3 (Service Account)
- **AI Engine:** Google Generative AI (Model Switcher & 429 Fallback)
- **Tương tác:** Telegram Bot API (`python-telegram-bot`)
- **Hosting & Keep-Alive:** Render Web Service + Flask + UptimeRobot

---

## ⚙️ Hướng Dẫn Cấu Hình & Triển Khai

### 1. Cấu hình Google Cloud Console
1. Bật **Google Sheets API**, **Google Docs API**, **Google Drive API** trên Google Cloud Console.
2. Tạo **Service Account** và tải file key `credentials.json` đặt vào thư mục gốc của dự án.
3. **Quan trọng:** Lấy địa chỉ email của Service Account (`...@...gserviceaccount.com`) và:
   - Share quyền **Editor** vào file Google Sheet tổng hợp.
   - Hướng dẫn người dùng share file Google Doc với quyền **Commenter** hoặc **Editor**.

### 2. Triển khai lên Render.com
1. Tạo một Repository mới trên GitHub và Push toàn bộ code lên (nhớ thêm `credentials.json` và `.env` vào `.gitignore`).
2. Trên Render.com, tạo một **Web Service** mới và kết nối với GitHub Repo.
3. Cấu hình Build:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. Vào mục **Environment Variables** trên Render và khai báo các biến môi trường từ tệp `.env.example`.
5. Tạo tệp `credentials.json` trực tiếp bằng tính năng **Secret Files** trên Render.

### 3. Giữ cho App sống 24/7 với UptimeRobot
1. Lấy URL trang web mà Render cấp cho ứng dụng (Ví dụ: `https://ptv-support-agent.onrender.com`).
2. Truy cập [UptimeRobot.com](https://uptimerobot.com/), tạo 1 Monitor mới:
   - **Monitor Type:** HTTP(s)
   - **URL:** Paste URL Render của anh vào.
   - **Interval:** 5 phút/lần.
3. Việc này giữ cho Flask Webserver luôn có Request, giúp Bot không bị trôi vào trạng thái Sleep trên Render.
