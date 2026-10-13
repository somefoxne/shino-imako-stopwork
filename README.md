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

### 3. Cấu hình phạm vi quét & Thông báo (`data/checkfile.txt`)
File này quyết định bot sẽ quét các bài viết nào, áp dụng hệ thống nào, có cần hỏi duyệt hay gửi log Discord không, và giới hạn sửa lại khi bị xóa tag. **Hỗ trợ trực tiếp mọi cú pháp tag từ [Danbooru Cheatsheet](https://danbooru.donmai.us/wiki_pages/help:cheatsheet)**!

| Cú pháp | Ý nghĩa |
| :--- | :--- |
| `id:<số>` | Quét trực tiếp bài viết có ID cụ thể (ví dụ: `id:8000000`) |
| `pool:<id>` | Quét các bài viết trong pool có ID cụ thể |
| `pool:any` hoặc `has:pools` | Quét tất cả bài viết thuộc bất kỳ pool nào |
| `user:<tên>` | Quét các bài viết do user này upload |
| `<tag_name>` | Quét bài viết có chứa tag này (ví dụ: `hatsune_miku`, `touhou`) |
| `rating:g/s/q/e` | Quét bài viết theo rating kiểm duyệt |
| `ALL` | Quét toàn bộ bài viết mới |
| `-<tag_name>` / `-user:<tên>` | Dấu `-` loại trừ bài viết theo chuẩn Danbooru |
| `action:<hệ_thống>` | Chỉ định bot chạy hệ thống nào (`action:2tag`, `action:3tag`, hoặc `action:all`) |
| `Noti:discord` | **CHỈ GỬI LOG**: Gửi thông báo kết quả cập nhật vào Discord (không hỏi duyệt). |
| `Noti:ask` | **CHỈ HỎI DUYỆT**: Gửi embed có nút bấm **[✅ Đồng ý]** / **[❌ Bỏ qua]** vào Discord. Chỉ khi được bấm Đồng ý bot mới thêm tag. |
| `readd:never` | Nếu tag từng được bot thêm mà bị người khác xóa $\rightarrow$ **Không bao giờ add lại**. |
| `readd:<N>` | Nếu tag bị xóa $\rightarrow$ Chỉ add lại nếu đã có ít nhất `<N>` lượt chỉnh sửa của người khác sau đó (ví dụ: `readd:5`). |

**Ví dụ dòng cấu hình trong `checkfile.txt`**:
```txt
# Quét tất cả các bài thuộc pool, loại trừ spammer, hỏi duyệt qua Discord trước khi thêm và cho phép add lại sau 5 lượt sửa:
pool:any -user:spammer action:all Noti:ask Noti:discord readd:5

# Quét post của artist có tag miku, chạy hệ thống 2 tag, chỉ gửi log discord, không add lại nếu bị xóa:
user:artist hatsune_miku action:2tag Noti:discord readd:never

# Quét kiểm tra 1 post cụ thể theo ID:
id:8000000 action:all
```

---

## 🚀 Chạy bot

```bash
python main.py
```
Bot sẽ nạp toàn bộ luật từ các thư mục, đọc các dòng trong `checkfile.txt`, truy vấn Danbooru và hiển thị kết quả kiểm tra từng bài viết!
