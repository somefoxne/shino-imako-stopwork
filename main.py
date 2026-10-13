import os
import sys
from dotenv import load_dotenv

# Đảm bảo stdout / stderr hỗ trợ UTF-8 mượt mà trên Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from danbooru_api import DanbooruClient
from systems import get_all_systems
from checkfile_parser import parse_checkfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHECKFILE_PATH = os.path.join(DATA_DIR, "checkfile.txt")

def main():
    # 1. Nạp biến môi trường từ .env
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)

    base_url = os.getenv("DANBOORU_URL", "https://danbooru.donmai.us")
    username = os.getenv("DANBOORU_USERNAME", "")
    api_key = os.getenv("DANBOORU_API_KEY", "")
    dry_run_str = os.getenv("DRY_RUN", "True").strip().lower()
    dry_run = dry_run_str in ("true", "1", "yes")
    
    try:
        request_delay = float(os.getenv("REQUEST_DELAY", "1.0"))
    except ValueError:
        request_delay = 1.0

    edit_reason = os.getenv("EDIT_REASON", "[Bot] Auto-updating tags based on rules")

    print("=" * 65)
    print(" DANBOORU TAG AUTO-CHECKER BOT")
    print("=" * 65)
    print(f"[*] API Base URL     : {base_url}")
    print(f"[*] Tài khoản        : {username if username else '(Chưa cấu hình, chỉ đọc)'}")
    print(f"[*] Chế độ DRY_RUN   : {'BẬT (Chỉ mô phỏng, KHÔNG ghi lên Danbooru)' if dry_run else 'TẮT (SẼ CẬP NHẬT TRỰC TIẾP LÊN DANBOORU!)'}")
    print(f"[*] Độ trễ request   : {request_delay}s")
    print(f"[*] Edit Reason      : {edit_reason}")
    print("=" * 65)

    # 2. Khởi tạo Danbooru API client
    client = DanbooruClient(
        base_url=base_url,
        username=username,
        api_key=api_key,
        request_delay=request_delay,
        dry_run=dry_run,
        edit_reason=edit_reason
    )

    # 3. Nạp các hệ thống luật từ registry và nạp database tương ứng
    systems = get_all_systems()
    print("\n[*] Đang nạp các hệ thống luật:")
    for sys_name, sys_instance in systems.items():
        sys_data_dir = os.path.join(DATA_DIR, sys_name)
        if os.path.exists(sys_data_dir):
            sys_instance.load_rules(sys_data_dir)
            print(f"  + [{sys_name.upper()}] Đã nạp {sys_instance.get_rule_count()} quy tắc từ {sys_name}/")
        else:
            print(f"  + [{sys_name.upper()}] Thư mục {sys_data_dir} chưa tồn tại!")

    # 4. Đọc file phạm vi (checkfile.txt)
    if not os.path.exists(CHECKFILE_PATH):
        print(f"\n[!] Không tìm thấy file {CHECKFILE_PATH}. Vui lòng tạo file này để chạy bot.")
        return

    scopes = parse_checkfile(CHECKFILE_PATH)
    if not scopes:
        print("\n[!] Không có dòng scope hợp lệ nào trong checkfile.txt. Vui lòng kiểm tra lại.")
        return

    print(f"\n[*] Đã tìm thấy {len(scopes)} phạm vi quét trong checkfile.txt\n")

    total_inspected = 0
    total_updated = 0

    # 5. Duyệt qua từng scope và xử lý
    for idx, scope in enumerate(scopes, 1):
        print(f"--- Scope #{idx}: {scope.raw_line} ---")
        print(f"  > Hành động áp dụng: {list(scope.actions)}")
        
        posts = []
        if scope.post_id is not None:
            print(f"  > Đang lấy trực tiếp Post #{scope.post_id}...")
            single_post = client.get_post(scope.post_id)
            if single_post:
                posts.append(single_post)
        else:
            danbooru_query = scope.build_danbooru_query()
            print(f"  > Đang truy vấn Danbooru với query: '{danbooru_query}'...")
            posts = client.get_posts(tags=danbooru_query, limit=50)

        print(f"  > Nhận về {len(posts)} bài viết.")

        # Kiểm tra và áp dụng quy tắc cho từng post
        for post in posts:
            total_inspected += 1
            post_id = post.get("id")
            old_tag_string = post.get("tag_string", "")
            post_tags = set(old_tag_string.split())

            # Kiểm tra xem post có khớp chặt chẽ với điều kiện scope không
            if not scope.matches_post(post):
                continue

            tags_to_add = set()

            # Chạy qua các hệ thống được phép trong scope này
            for sys_name, sys_instance in systems.items():
                if scope.should_run_system(sys_name):
                    additions = sys_instance.evaluate(post_tags)
                    if additions:
                        tags_to_add.update(additions)

            # Nếu có tag mới cần bổ sung
            if tags_to_add:
                is_success = client.update_post_tags(
                    post_id=post_id,
                    old_tag_string=old_tag_string,
                    tags_to_add=tags_to_add
                )
                if is_success:
                    total_updated += 1

    print("\n" + "=" * 65)
    print(" KẾT QUẢ TỔNG KẾT")
    print("=" * 65)
    print(f"Tổng số post đã kiểm tra : {total_inspected}")
    print(f"Tổng số post {'dự kiến cập nhật' if dry_run else 'đã cập nhật thành công'} : {total_updated}")
    if dry_run:
        print("[*] Lưu ý: Đang ở chế độ DRY_RUN. Hãy đổi DRY_RUN=False trong .env để cập nhật thật.")
    print("=" * 65)

if __name__ == "__main__":
    main()
