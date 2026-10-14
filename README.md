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
    ├── checkfile.txt     # Phạm vi quét post (pool, post, user, tag, action, Noti, readd...)
    ├── history.db        # Database SQLite tự động lưu lịch sử sửa bài để chống edit-war
    ├── 2tag/             # Chứa TẤT CẢ các file .txt của hệ thống 2 tag (rules.txt, extra.txt...)
    └── 3tag/             # Chứa TẤT CẢ các file .txt của hệ thống 3 tag (rules.txt, chars.txt...)
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
   # Tài khoản Danbooru chính thức
   DANBOORU_URL=https://danbooru.donmai.us
   DANBOORU_USERNAME=tên_user_danbooru
   DANBOORU_API_KEY=api_key_của_bạn

   # Chế độ TESTBOORU: Đổi sang True để test bot an toàn trên https://testbooru.donmai.us
   TEST_MODE=False
   TESTBOORU_URL=https://testbooru.donmai.us
   TESTBOORU_USERNAME=
   TESTBOORU_API_KEY=

   # An toàn: DRY_RUN=True chỉ quét mô phỏng, KHÔNG ghi đè lên server
   DRY_RUN=True
   REQUEST_DELAY=1.0

   # Chính sách re-add khi tag bị người khác xóa: "never" hoặc "after_edits"
   RE_ADD_POLICY=never
   MIN_EDITS_BEFORE_READD=5
   ```

---

## 📝 Hướng dẫn viết luật

> 💡 **Lưu ý quan trọng về thư mục luật**: Trong thư mục `data/2tag/` và `data/3tag/`, bạn có thể tạo **bao nhiêu file `.txt` tùy ý** (ví dụ: `rules.txt`, `general.txt`, `character.txt`, `asdashjdash.txt`...). Bot sẽ tự động quét và nạp toàn bộ các file `.txt` có trong thư mục!

### 1. Hệ thống 2 Tag (`data/2tag/*.txt`)
Cú pháp mới:
```
?A B <E>       hoặc       A -> B <E>
```
* **Logic**:
  * `?A`: Tag **bắt buộc** phải có (và bot không bao giờ tự ý thêm tag `A`).
  * `B`: Tag cần thêm nếu post đã có `A` nhưng chưa có `B`.
  * Nếu post có `B` nhưng chưa có `A` $\rightarrow$ **Không hoạt động** (không thêm `A`).
  * `<E>`: Tag loại trừ. Nếu post dính tag trong `<...>` $\rightarrow$ Không thêm.

**Ví dụ**:
```txt
# Có bikini thì thêm swimwear, trừ khi có school_swimsuit
?bikini swimwear <school_swimsuit>

# Có cat_ears thì thêm animal_ears
?cat_ears animal_ears
```

---

### 2. Hệ thống 3 Tag & N-Tag (`data/3tag/*.txt`)
Hỗ trợ 2 dạng công thức mạnh mẽ:

#### Dạng 1: Mũi tên suy luận (`A B C -> D <E>`)
* **Logic**: Khi bài viết có **đủ tất cả các tag bên trái** (`A`, `B`, `C`) $\rightarrow$ Thêm tag **`D`** (trừ khi có tag `E` trong `<E>`).
* **Ví dụ**:
  ```txt
  school_uniform sailor_collar pleated_skirt -> student <cosplay>
  ```

#### Dạng 2: Neo bắt buộc & Suy luận tương hỗ (`?A B C D <E>`)
* **Quy ước**:
  * Các tag có dấu `?` (ví dụ: `?A`, `?B`) là tag **bắt buộc phải có** (và bot không bao giờ tự thêm các tag này).
  * Các tag không có dấu `?` là **tập ứng viên suy luận**. Khi bài viết đã có đủ $(N - 1)$ tag trong tập ứng viên $\rightarrow$ tự động bù **tag thứ $N$ còn thiếu**!
  * Tag trong `<...>` là **tag loại trừ**.
* **Các trường hợp cụ thể**:
  * `?A B C <E>`:
    * Có `A` và `B` $\rightarrow$ Thêm `C`.
    * Có `A` và `C` $\rightarrow$ Thêm `B`.
    * Có `B` và `C` (thiếu `A`) $\rightarrow$ **Không hoạt động**.
  * `?A B C D <E>`:
    * Bắt buộc có `A`. Nếu có 2 trong 3 tag `{B, C, D}` $\rightarrow$ tự động bù tag thứ 3 còn thiếu.
    * Có `B, C, D` (thiếu `A`) $\rightarrow$ **Không hoạt động**.
  * Dạng mở rộng nhiều neo: `?A ?B C D E F G <H I K>`:
    * Bắt buộc có cả `A` và `B`. Nếu có 4 trong 5 tag `{C, D, E, F, G}` $\rightarrow$ tự động bù tag còn thiếu.

**Ví dụ**:
```txt
# Bắt buộc twintails: có hair_ribbon thì bù twin_ribbons; có twin_ribbons thì bù hair_ribbon
?twintails hair_ribbon twin_ribbons <single_ribbon>

# Bộ 4 tag ma cà rồng:
?vampire fangs pointy_ears cape <elf>
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
