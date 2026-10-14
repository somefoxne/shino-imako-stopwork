import os
import sys
import asyncio
from dotenv import load_dotenv

# Đảm bảo stdout / stderr hỗ trợ UTF-8 mượt mà trên Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from danbooru_api import DanbooruClient
from systems import get_all_systems
from checkfile_parser import parse_checkfile
from discord_notifier import DiscordNotifier
from history_manager import HistoryManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHECKFILE_PATH = os.path.join(DATA_DIR, "checkfile.txt")
HISTORY_DB_PATH = os.path.join(DATA_DIR, "history.db")

async def run_scan_cycle(client, history_mgr, notifier, dry_run, env_readd_policy, min_edits_before_readd):
    """Thực thi một chu kỳ kiểm tra và cập nhật tag."""
    # Nạp các hệ thống luật từ registry và nạp database tương ứng (đọc lại để cập nhật nếu có file mới)
    systems = get_all_systems()
    print("\n[*] Đang nạp các hệ thống luật:")
    for sys_name, sys_instance in systems.items():
        sys_data_dir = os.path.join(DATA_DIR, sys_name)
        if os.path.exists(sys_data_dir):
            sys_instance.load_rules(sys_data_dir)
            files_str = ", ".join(sys_instance.loaded_files) if sys_instance.loaded_files else "Không có file nào"
            print(f"  + [{sys_name.upper()}] Đã nạp {sys_instance.get_rule_count()} quy tắc từ {len(sys_instance.loaded_files)} file: [{files_str}]")
        else:
            print(f"  + [{sys_name.upper()}] Thư mục {sys_data_dir} chưa tồn tại!")

    # Đọc file phạm vi (checkfile.txt)
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

    # Duyệt qua từng scope và xử lý
    for idx, scope in enumerate(scopes, 1):
        print(f"--- Scope #{idx}: {scope.raw_line} ---")
        print(f"  > Hành động áp dụng : {list(scope.actions)}")
        print(f"  > Tùy chọn thông báo: {list(scope.notis) if scope.notis else 'Mặc định'}")
        scope_policy = scope.readd_policy or env_readd_policy
        print(f"  > Chính sách readd  : {scope_policy}")

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

            candidate_tags = set()

            # Chạy qua các hệ thống được phép trong scope này
            for sys_name, sys_instance in systems.items():
                if scope.should_run_system(sys_name):
                    additions = sys_instance.evaluate(post_tags)
                    if additions:
                        candidate_tags.update(additions)

            if not candidate_tags:
                continue

            # Kiểm tra chính sách Re-add / Lịch sử chỉnh sửa để chống chiến tranh tag
            current_version = post.get("version")
            if current_version is None:
                current_version = client.get_post_latest_version(post_id)

            tags_to_add = set()
            for tag in candidate_tags:
                allowed, reason = history_mgr.check_tag_permission(
                    post_id=post_id,
                    tag=tag,
                    current_version=current_version,
                    policy=scope_policy,
                    min_edits=min_edits_before_readd
                )
                if allowed:
                    tags_to_add.add(tag)
                else:
                    print(f"  [CHẶN RE-ADD] Post #{post_id} -> {reason}")

            if not tags_to_add:
                continue

            # Xử lý Noti:ask (Hỏi duyệt)
            should_proceed = True
            if scope.should_ask():
                should_proceed = await notifier.ask_approval(post, tags_to_add, dry_run=dry_run)

            if not should_proceed:
                print(f"  [SKIPPED] Post #{post_id} -> Đã bỏ qua theo phản hồi Noti:ask")
                continue

            # Thực hiện cập nhật tag
            is_success = client.update_post_tags(
                post_id=post_id,
                old_tag_string=old_tag_string,
                tags_to_add=tags_to_add
            )

            if is_success:
                total_updated += 1
                history_mgr.record_edits(post_id, tags_to_add, current_version=current_version + 1)

                # Xử lý Noti:discord (Gửi log thông báo nếu có cờ Noti:discord)
                if scope.should_notify_discord():
                    await notifier.send_notification(
                        post=post,
                        tags_to_add=tags_to_add,
                        success=True,
                        dry_run=dry_run
                    )

    print("\n" + "=" * 65)
    print(" KẾT QUẢ TỔNG KẾT CHU KỲ")
    print("=" * 65)
    print(f"Tổng số post đã kiểm tra : {total_inspected}")
    print(f"Tổng số post {'dự kiến cập nhật' if dry_run else 'đã cập nhật thành công'} : {total_updated}")
    if dry_run:
        print("[*] Lưu ý: Đang ở chế độ DRY_RUN. Hãy đổi DRY_RUN=False trong .env để cập nhật thật.")
    print("=" * 65)


async def main():
    # 1. Nạp biến môi trường từ .env
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)

    # Chế độ TEST_MODE (Testbooru)
    test_mode_str = os.getenv("TEST_MODE", "False").strip().lower()
    test_mode = test_mode_str in ("true", "1", "yes")

    if test_mode:
        base_url = os.getenv("TESTBOORU_URL", "https://testbooru.donmai.us").rstrip("/")
        username = os.getenv("TESTBOORU_USERNAME", "") or os.getenv("DANBOORU_USERNAME", "")
        api_key = os.getenv("TESTBOORU_API_KEY", "") or os.getenv("DANBOORU_API_KEY", "")
    else:
        base_url = os.getenv("DANBOORU_URL", "https://danbooru.donmai.us").rstrip("/")
        username = os.getenv("DANBOORU_USERNAME", "")
        api_key = os.getenv("DANBOORU_API_KEY", "")

    dry_run_str = os.getenv("DRY_RUN", "True").strip().lower()
    dry_run = dry_run_str in ("true", "1", "yes")

    # Nếu đang ở chế độ TEST_MODE trên Testbooru -> Tự động tắt DRY_RUN (tiến hành cập nhật thật lên Testbooru)
    if test_mode:
        dry_run = False
    
    try:
        request_delay = float(os.getenv("REQUEST_DELAY", "1.0"))
    except ValueError:
        request_delay = 1.0

    edit_reason = os.getenv("EDIT_REASON", "[Bot] Auto tag update based on rules")

    # Cấu hình Discord
    discord_token = os.getenv("DISCORD_BOT_TOKEN", "")
    discord_channel_id_str = os.getenv("DISCORD_CHANNEL_ID", "")
    discord_channel_id = int(discord_channel_id_str) if discord_channel_id_str.isdigit() else None
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL", "")

    # Cấu hình kiểm soát sửa lại (Anti edit-war / Re-add policy)
    env_readd_policy = os.getenv("RE_ADD_POLICY", "never").strip().lower()
    try:
        min_edits_before_readd = int(os.getenv("MIN_EDITS_BEFORE_READD", "5"))
    except ValueError:
        min_edits_before_readd = 5

    # Cấu hình vòng lặp 24/7 (cho VPS / Vibe Host)
    run_loop_str = os.getenv("RUN_LOOP", "True").strip().lower()
    run_loop = run_loop_str in ("true", "1", "yes")
    try:
        loop_interval = int(os.getenv("LOOP_INTERVAL_SECONDS", "300"))
    except ValueError:
        loop_interval = 300

    print("=" * 65)
    print(" DANBOORU TAG AUTO-CHECKER BOT")
    print("=" * 65)
    if test_mode:
        print("[!] >> CHẾ ĐỘ TESTBOORU ĐANG BẬT (https://testbooru.donmai.us) <<")
    print(f"[*] API Base URL       : {base_url}")
    print(f"[*] Tài khoản          : {username if username else '(Chưa cấu hình, chỉ đọc)'}")
    if test_mode:
        print("[*] Chế độ DRY_RUN     : TẮT (Tự động cập nhật thật trên Testbooru để kiểm tra)")
    else:
        print(f"[*] Chế độ DRY_RUN     : {'BẬT (Chỉ mô phỏng, KHÔNG ghi lên Danbooru)' if dry_run else 'TẮT (SẼ CẬP NHẬT TRỰC TIẾP LÊN DANBOORU!)'}")
    print(f"[*] Chế độ chạy liên tục: {'BẬT (24/7, lặp lại mỗi ' + str(loop_interval) + 's)' if run_loop else 'TẮT (Chạy 1 lần)'}")
    print(f"[*] Độ trễ request     : {request_delay}s")
    print(f"[*] Edit Reason        : {edit_reason}")
    print(f"[*] Chính sách re-add  : {env_readd_policy} (tối thiểu {min_edits_before_readd} lần sửa)")
    print(f"[*] Discord Channel    : {discord_channel_id if discord_channel_id else '(Chưa cấu hình)'}")
    print("=" * 65)

    # Khởi tạo client, history manager và discord notifier
    client = DanbooruClient(
        base_url=base_url,
        username=username,
        api_key=api_key,
        request_delay=request_delay,
        dry_run=dry_run,
        edit_reason=edit_reason
    )

    history_mgr = HistoryManager(HISTORY_DB_PATH)

    notifier = DiscordNotifier(
        bot_token=discord_token,
        channel_id=discord_channel_id,
        webhook_url=discord_webhook,
        base_url=base_url
    )

    if discord_token and discord_channel_id:
        print("[*] Đang kết nối Discord bot...")
        await notifier.start()

    try:
        cycle_num = 1
        while True:
            if run_loop:
                print(f"\n>>> BẮT ĐẦU CHU KỲ QUÉT #{cycle_num} <<<")

            await run_scan_cycle(
                client=client,
                history_mgr=history_mgr,
                notifier=notifier,
                dry_run=dry_run,
                env_readd_policy=env_readd_policy,
                min_edits_before_readd=min_edits_before_readd
            )

            # Nếu không bật chạy liên tục (chạy 1 lần) -> thoát vòng lặp
            if not run_loop:
                break

            print(f"\n[*] Đang nghỉ {loop_interval} giây ({loop_interval // 60} phút) trước khi bắt đầu chu kỳ tiếp theo...")
            await asyncio.sleep(loop_interval)
            cycle_num += 1

    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\n[*] Nhận tín hiệu dừng, đang tắt bot an toàn...")
    finally:
        await notifier.close()

if __name__ == "__main__":
    asyncio.run(main())
