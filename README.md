# DANBOORU TAG AUTO-CHECKER BOT

Hệ thống bot tự động kiểm tra và cập nhật tag Danbooru được xây dựng theo mô-đun hóa cao, dễ mở rộng và an toàn.

---

## 📁 Cấu trúc thư mục

```
danbooru_tag_bot/
│
├── .env                  # Cấu hình tài khoản, API key và cờ an toàn DRY_RUN
├── .env.example          # File mẫu cấu hình
├── requirements.txt      # Thư viện phụ thuộc (requests, python-dotenv)
│
├── main.py               # File tổng thực thi toàn bộ quy trình của bot
├── danbooru_api.py       # Module giao tiếp API Danbooru (xác thực, rate limit, dry-run)
├── checkfile_parser.py   # Module phân tích cú pháp checkfile và lọc scope
│
├── systems/              # THƯ MỤC CÁC HỆ THỐNG XỬ LÝ (Dễ fix / thêm hệ thống mới)
│   ├── __init__.py       # Registry quản lý các hệ thống (2tag, 3tag, ...)
│   ├── base_system.py    # Lớp cơ sở BaseTagSystem
│   ├── two_tag_system.py # Hệ thống luật 2 tag (A -> B -D)
│   └── three_tag_system.py # Hệ thống luật 3 tag (? A B C -D)
│
└── data/                 # THƯ MỤC DATABASE & QUY TẮC
    ├── checkfile.txt     # Phạm vi quét post (pool, post, user, tag, action...)
    ├── 2tag/             # Chứa các file luật cho hệ thống 2 tag
    │   └── rules.txt     # Các dòng quy tắc: A -> B -D
    └── 3tag/             # Chứa các file luật cho hệ thống 3 tag
        └── rules.txt     # Các dòng quy tắc: ? A B C -D
```

---

## ⚙️ Cài đặt & Cấu hình

1. **Cài đặt thư viện**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Cấu hình file `.env`**:
   Mở file `.env` và điền thông tin tài khoản:
   ```env
   DANBOORU_URL=https://danbooru.donmai.us
   DANBOORU_USERNAME=tên_user_danbooru
   DANBOORU_API_KEY=api_key_của_bạn
   DRY_RUN=True
   REQUEST_DELAY=1.0
   ```
   > ⚠️ **Lưu ý quan trọng**: Mặc định `DRY_RUN=True` sẽ chỉ quét và hiển thị ra màn hình các tag dự kiến thêm, **hoàn toàn không ghi đè lên Danbooru**. Khi bạn đã kiểm tra kỹ các quy tắc, đổi thành `DRY_RUN=False` để bot cập nhật thật.

---

## 📝 Hướng dẫn viết luật

### 1. Hệ thống 2 Tag (`data/2tag/rules.txt`)
Cú pháp:
```
A -> B -D -E
```
* **Logic**: Nếu post có tag `A` nhưng **chưa có** `B` $\rightarrow$ Thêm `B`.
* Nếu post đã có `B` $\rightarrow$ Kệ nó (không làm gì).
* Nếu post có chứa tag loại trừ `-D` $\rightarrow$ Bỏ qua, không thêm.

**Ví dụ**:
```txt
# Có bikini nhưng chưa có swimwear thì thêm swimwear (trừ khi có school_swimsuit)
bikini -> swimwear -school_swimsuit
cat_ears -> animal_ears
```

---

### 2. Hệ thống 3 Tag (`data/3tag/rules.txt`)
Cú pháp:
```
? A B C -D -E
```
* **Logic tam giác tương hỗ**:
  * Có `A` và `B` (thiếu `C`) $\rightarrow$ Thêm `C`.
  * Có `A` và `C` (thiếu `B`) $\rightarrow$ Thêm `B`.
  * Có `B` và `C` (thiếu `A`) $\rightarrow$ Thêm `A`.
  * Đã có đủ cả 3 tag $\rightarrow$ Không cần thêm gì.
* Nếu post có chứa bất kỳ tag loại trừ nào (`-D`, `-E`...) $\rightarrow$ Bỏ qua, không thêm.

**Ví dụ**:
```txt
# Tam giác twintails, ruy băng tóc và twin_ribbons
? twintails hair_ribbon twin_ribbons -single_ribbon

# Bộ 3 ma cà rồng
? vampire fangs pointy_ears -elf
```

---

### 3. Cấu hình phạm vi quét (`data/checkfile.txt`)
File này quyết định bot sẽ quét các bài viết nào và áp dụng hệ thống nào.

| Token | Ý nghĩa |
| :--- | :--- |
| `post:<id>` | Quét trực tiếp bài viết có ID cụ thể |
| `pool:<id>` | Quét các bài viết trong pool có ID cụ thể |
| `pool:all` | Quét tất cả bài viết thuộc bất kỳ pool nào (`has:pools`) |
| `tag:<tên>` | Quét các bài viết có tag này |
| `user:<tên>` | Quét các bài viết do user này upload |
| `ALL` | Quét toàn bộ bài viết mới |
| `action:<hệ_thống>` | Chỉ áp dụng hệ thống đó (`action:2tag`, `action:3tag`, hoặc `action:all`) |
| Dấu `-` | Loại trừ (ví dụ `-user:tên`, `-tag:tên`, `-pool:id`) |

**Ví dụ dòng lệnh trong `checkfile.txt`**:
```txt
# Quét tất cả mọi người trừ uploader spammer, chạy tất cả hệ thống
ALL -user:spammer action:all

# Quét post của user artist có tag miku, chỉ chạy hệ thống 2 tag
user:artist tag:hatsune_miku action:2tag

# Quét tất cả các bài thuộc pool, chỉ áp dụng hệ thống 3 tag
pool:all action:3tag

# Quét kiểm tra 1 post cụ thể
post:8000000 action:all
```

---

## 🚀 Chạy bot

```bash
python main.py
```
Bot sẽ nạp toàn bộ luật từ các thư mục, đọc các dòng trong `checkfile.txt`, truy vấn Danbooru và hiển thị kết quả kiểm tra từng bài viết!
