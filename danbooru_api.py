import time
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any, Set, Optional

class DanbooruClient:
    def __init__(
        self,
        base_url: str = "https://danbooru.donmai.us",
        username: str = "",
        api_key: str = "",
        request_delay: float = 1.0,
        dry_run: bool = True,
        edit_reason: str = "[Bot] Auto-updating tags"
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.api_key = api_key
        self.request_delay = request_delay
        self.dry_run = dry_run
        self.edit_reason = edit_reason

        self.session = requests.Session()
        # Định dạng User-Agent chuẩn được Danbooru yêu cầu
        user_agent_name = username if username and username != "your_username_here" else "DanbooruTagBot"
        self.session.headers.update({
            "User-Agent": f"DanbooruTagBot/1.0 (by {user_agent_name} on danbooru)"
        })

        # Chỉ bật Basic Auth khi đã điền thông tin thật (không phải giá trị placeholder)
        if (
            username 
            and api_key 
            and username != "your_username_here" 
            and api_key != "your_api_key_here"
        ):
            self.session.auth = HTTPBasicAuth(username, api_key)
        else:
            self.session.auth = None

    def get_posts(self, tags: str = "", limit: int = 20, page: int = 1) -> List[Dict[str, Any]]:
        """
        Tìm kiếm danh sách bài viết từ Danbooru theo tags.
        """
        url = f"{self.base_url}/posts.json"
        params = {
            "limit": limit,
            "page": page
        }
        if tags.strip():
            params["tags"] = tags.strip()

        try:
            res = self.session.get(url, params=params, timeout=15)
            res.raise_for_status()
            data = res.json()
            if isinstance(data, list):
                return data
            return []
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                print(f"[!] Lỗi 403 Forbidden từ Danbooru: Danbooru yêu cầu tài khoản và API Key hợp lệ trong file .env để truy vấn API.")
            else:
                print(f"[!] Lỗi HTTP khi lấy danh sách post (tags='{tags}'): {e}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"[!] Lỗi kết nối khi lấy danh sách post (tags='{tags}'): {e}")
            return []

    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin chi tiết một bài viết theo ID.
        """
        url = f"{self.base_url}/posts/{post_id}.json"
        try:
            res = self.session.get(url, timeout=15)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                print(f"[!] Lỗi 403 Forbidden từ Danbooru: Vui lòng điền DANBOORU_USERNAME và DANBOORU_API_KEY trong file .env để truy vấn bài viết #{post_id}.")
            else:
                print(f"[!] Lỗi HTTP khi lấy bài viết #{post_id}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[!] Lỗi kết nối khi lấy bài viết #{post_id}: {e}")
            return None

    def get_post_latest_version(self, post_id: int) -> int:
        """
        Lấy số thứ tự phiên bản mới nhất (version number) của bài viết từ Danbooru.
        """
        url = f"{self.base_url}/post_versions.json"
        params = {
            "search[post_id]": post_id,
            "limit": 1
        }
        try:
            res = self.session.get(url, params=params, timeout=15)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("version", 1)
        except Exception:
            pass
        return 1

    def update_post_tags(
        self,
        post_id: int,
        old_tag_string: str,
        tags_to_add: Set[str]
    ) -> bool:
        """
        Cập nhật thêm tag mới vào post.
        Nếu DRY_RUN=True: Chỉ mô phỏng và log kết quả ra console.
        """
        if not tags_to_add:
            return False

        current_tags = set(old_tag_string.split())
        new_tags = current_tags.union(tags_to_add)

        # Nếu không có tag nào thực sự mới
        if new_tags == current_tags:
            return False

        new_tag_string = " ".join(sorted(new_tags))
        added_list = sorted(list(tags_to_add))

        if self.dry_run:
            print(f"  [DRY-RUN] Post #{post_id} -> Dự kiến THÊM tags: {added_list}")
            return True

        # Thực thi gửi yêu cầu PATCH lên Danbooru
        url = f"{self.base_url}/posts/{post_id}.json"
        payload = {
            "post[tag_string]": new_tag_string,
            "post[old_tag_string]": old_tag_string,
            "post[edit_reason]": self.edit_reason
        }

        try:
            res = self.session.patch(url, data=payload, timeout=20)
            if res.status_code == 200:
                print(f"  [SUCCESS] Post #{post_id} -> Đã thêm tags: {added_list}")
                time.sleep(self.request_delay)
                return True
            else:
                print(f"  [ERROR] Post #{post_id} -> Mã lỗi {res.status_code}: {res.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"  [ERROR] Lỗi kết nối khi cập nhật Post #{post_id}: {e}")
            return False
