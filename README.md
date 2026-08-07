# 🤖 PTV Support Ticket Automation Agent - System Specification & Architecture Blueprint

Dự án tự động hóa việc tiếp nhận Feedback từ Google Forms/Sheet, phân tích nội dung đính kèm trong Google Doc bằng Gemini AI, xin phệ duyệt qua Telegram Bot tương tác, và tự động gán dữ liệu ngược lại Google Sheet & Google Doc.

---

## 📐 1. CẤU TRÚC THƯ MỤC HỆ THỐNG (DIRECTORY TREE)

```text
ptv-support-agent/
│
├── 📁 brain/
│   └── knowledge_base.json         # Cấu hình danh mục, trạng thái & danh sách nhân sự
│
├── 📁 modules/
│   ├── __init__.py
│   ├── google_sheet.py             # Đọc/Ghi dữ liệu Google Sheet v4
│   ├── google_doc.py               # Đọc nội dung & Comment/Tag qua Google Drive API v3
│   ├── ai_engine.py                # Gọi AI Gemini với cơ chế Auto-Fallback (429 Quota)
│   └── telegram_handler.py         # Bot Telegram bất đồng bộ & nút bấm Callback
│
├── .env                            # Chứa biến môi trường bảo mật (Local)
├── .env.example                    # Mẫu cấu hình môi trường
├── requirements.txt                # Khai báo các thư viện Python chuẩn phiên bản
├── README.md                       # Tài liệu đặc tả hệ thống (Tệp này)
└── main.py                         # Điều phối trung tâm, Flask Keep-Alive & Telegram JobQueue
```

---

## 🛠️ 2. DANH SÁCH THƯ VIỆN & PHIÊN BẢN (REQUIREMENTS.TXT)

Hệ thống bắt buộc chạy trên **Python 3.10 - 3.11** (tránh tương thích lỗi `__slots__` trên Python 3.14).

```text
google-api-python-client==2.118.0
google-auth==2.28.1
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.0
google-generativeai>=0.8.3
python-telegram-bot[job-queue]>=21.7
python-dotenv==1.0.1
Flask==3.0.2
requests==2.31.0
gunicorn==21.2.0
```

---

## 📊 3. DỮ LIỆU BẢNG BỂU GOOGLE SHEET (SCHEMA & COLUMN MAPPING)

File Google Sheet theo dõi có cấu trúc cột cố định:

| Cột Index | Tên Cột trong Sheet | Loại Dữ Liệu | Vai Trò & Quy Tắc Cập Nhật |
|---|---|---|---|
| **A (0)** | Timestamp | Text | Thời gian gửi form |
| **C (2)** | COUNTRY | Text | Quốc gia gửi (Viet Nam, Malaysia, Philippines, ...) |
| **D (3)** | SUBMITTER NAME | Text | Tên người gửi feedback |
| **E (4)** | SUBJECT | Text | Tiêu đề bài toán |
| **G (6)** | REPORT GoogleDoc | URL | Đường dẫn tới file Google Doc chi tiết |
| **H (7)** | REMARKS | Text | Ghi chú thêm của người dùng |
| **I (8)** | FB ID | Text | Mã định danh ticket (VD: `FB-001`, `FB-002`) |
| **J (9)** | Aging (Days) | Number | Số ngày xử lý (Auto formula) |
| **K (10)** | **CATEGORY** | Dropdown | AI đề xuất & Cập nhật: `Hardware`, `Software`, `Content`, `Account`, `Operations`, `other` |
| **L (11)** | **Assigned** | Checkbox | AI/Admin cập nhật: **TRUE** (Đã tick) / **FALSE** (Chưa tick) |
| **M (12)** | Targetted Date | Date | Ngày mục tiêu hoàn thành |
| **N (13)** | **STATUS** | Dropdown | AI đề xuất & Cập nhật: `Critical`, `Non-Critical`, `To Implement`, `Backlog`, `Resolved`, `Closed` |
| **P (15)** | Resolved Date | Date | Ngày hoàn tất |

> **Điều kiện nhận biết dòng chưa xử lý:** Cột **Assigned (L)** mang giá trị `FALSE` (chưa tick) HOẶC Cột **CATEGORY (K)** / **STATUS (N)** bị bỏ trống.

---

## 🔄 4. LUỒNG XỬ LÝ HỆ THỐNG (END-TO-END WORKFLOW)

```text
[Google Form] ➔ [Google Sheet]
                     │
         (Quét định kỳ mỗi 5 phút)
                     │
                     ▼
         [Kiểm tra dòng chưa gán] ➔ [Đọc Google Doc đính kèm]
                     │
                     ▼
          [AI Gemini Engine] ➔ Phân tích & Tóm tắt dựa trên knowledge_base.json
                     │
                     ▼
       [Gửi Notification sang Telegram Admin] ➔ [Hiện Nút ✅ Đồng ý / ❌ Bỏ qua]
                     │
             (Admin ấn nút ✅)
                     │
                     ▼
 [Thực thi 1]: Tick Checkbox (Col L) & Điền Category (Col K), Status (Col N) vào Sheet
 [Thực thi 2]: Chèn Comment & Tag Email người phụ trách vào Google Doc via Drive API
```

---

## ⚠️ 5. CÁC QUY TẮC KỸ THUẬT QUAN TRỌNG (CRITICAL EDGE CASES)

### 1. Google API Naming Spec (`spreadsheetId`)
* Khi gọi Google API Client Python SDK, tham số truyền id bảng tính **bắt buộc là `spreadsheetId` (camelCase có chữ I viết hoa)**. Nếu dùng `spreadsheet_id` sẽ bị `TypeError: Got an unexpected keyword argument`.

### 2. Xử lý linh hoạt tên Tab trong Google Sheet
* Không hardcode tên tab là `"Feedbacks"`. Hệ thống tự động quét danh sách Tab trong Spreadsheet, nếu không tìm thấy tab chỉ định sẽ tự chuyển sang tab đầu tiên (VD: `'Form Responses'`).
* Luôn bọc tên Tab trong dấu nháy đơn khi chỉ định Range (Ví dụ: `'Form Responses'!K6:L6`) để tránh lỗi parse range do chứa khoảng trắng.

### 3. Tự động chuyển đổi Model Gemini (Quota 429 Fallback)
Khi một Model gặp lỗi quá tải Quota (`429 Too Many Requests`), AI Engine lập tức lặp chuyển sang Model tiếp theo trong danh sách ưu tiên:
```python
GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-pro-latest",
    "gemini-flash-latest",
    "gemini-flash-lite-latest"
]
```

### 4. Quản lý Credentials trên Môi Trường Cloud (Render.com)
* KHÔNG push file `credentials.json` lên Git.
* Đọc JSON cấu hình Service Account trực tiếp từ biến môi trường `GOOGLE_CREDENTIALS_JSON` thông qua hàm `Credentials.from_service_account_info(json.loads(...))`.

### 5. Giữ App Sống 24/7 trên Render Free Tier
* Render Free Web Service sẽ "ngủ" sau 15 phút nếu không có traffic.
* `main.py` khởi chạy một Flask App nhẹ ở Thread riêng mở cổng `PORT=8080`.
* Sử dụng dịch vụ **UptimeRobot** thực hiện `HEAD/GET Request` mỗi 5 phút tới URL Render để giữ cho ứng dụng và Telegram Polling luôn hoạt động.

### 6. Xử lý Quyền File Google Doc
* Để chèn Comment & Tag `@email`, Service Account phải được cấp quyền **Commenter** hoặc **Editor** trên file Doc đó.
* Sử dụng **Google Drive API v3 (`comments().create`)** thay vì Google Docs API v1 (Docs API không hỗ trợ API tag comment).
* Bẫy lỗi `HttpError 403 Permission Denied` nếu file ở chế độ restricted/viewer và báo ngược lại Telegram mà không làm sập ứng dụng.

---

## 🔑 6. DANH SÁCH BIẾN MÔI TRƯỜNG (.ENV)

```env
SPREADSHEET_ID=1utinYZ0_GQpUDzWIZMJVBLsdETF...
GEMINI_API_KEY=AIzaSy...
TELEGRAM_BOT_TOKEN=8983168799:AAFP2CwL...
TELEGRAM_CHAT_ID=123456789
CHECK_INTERVAL_MINUTES=5
PORT=8080
PYTHON_VERSION=3.11.9
GOOGLE_CREDENTIALS_JSON={"type": "service_account", "project_id": "...", ...}
```

---

## 🚀 7. HƯỚNG DẪN LỆNH KHỞI CHẠY (START COMMANDS)

* **Build Command:** `pip install -r requirements.txt`
* **Start Command:** `python main.py`
