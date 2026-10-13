import re
from typing import List, Set, Dict, Any

class CheckScope:
    """
    Đại diện cho một phạm vi quét bài viết trong checkfile.txt.
    Tất cả các token (ngoại trừ action:...) đều tuân theo chuẩn cú pháp tag của Danbooru cheatsheet:
    - id:123456
    - pool:123 hoặc pool:any / has:pools
    - user:artist_name
    - rating:g / rating:s / rating:q / rating:e
    - tag_name hoặc -tag_name (loại trừ)
    - ALL (quét bài mới tổng thể)
    - action:2tag / action:3tag / action:all (chỉ định hệ thống bot áp dụng)
    """
    def __init__(self, raw_line: str):
        self.raw_line = raw_line
        self.actions: Set[str] = {"all"}  # Mặc định là all
        self.danbooru_tags: List[str] = []
        self.is_all: bool = False

        self._parse(raw_line)

    def _parse(self, line: str):
        tokens = line.split()
        for token in tokens:
            token = token.strip()
            if not token:
                continue

            # Chỉ định action của bot (ví dụ: action:2tag, action:3tag, action:all)
            if token.lower().startswith("action:"):
                act = token[len("action:"):].lower().strip()
                if act == "all":
                    self.actions = {"all"}
                else:
                    self.actions = {act}
                continue

            # Cờ ALL (quét tổng thể bài viết)
            if token.upper() == "ALL":
                self.is_all = True
                continue

            # Tất cả các token còn lại đều là tag Danbooru hợp lệ (id:..., pool:..., user:..., tag...)
            self.danbooru_tags.append(token)

    def build_danbooru_query(self) -> str:
        """
        Tạo chuỗi query gửi lên Danbooru API (?tags=...).
        """
        return " ".join(self.danbooru_tags)

    def matches_post(self, post: Dict[str, Any]) -> bool:
        """
        Kiểm tra an toàn bổ sung ở phía client (đặc biệt các tag loại trừ có dấu trừ -).
        """
        post_tags = set(post.get("tag_string", "").split())
        uploader_name = str(post.get("uploader_name", "")).lower()

        for tag in self.danbooru_tags:
            # Kiểm tra tag loại trừ (bắt đầu bằng -)
            if tag.startswith("-"):
                neg = tag[1:]
                if neg.lower().startswith("user:"):
                    target_u = neg[len("user:"):].lower()
                    if uploader_name and uploader_name == target_u:
                        return False
                else:
                    # Nếu post dính tag loại trừ
                    if neg in post_tags:
                        return False

        return True

    def should_run_system(self, system_name: str) -> bool:
        """Kiểm tra action có áp dụng cho system này không."""
        return "all" in self.actions or system_name.lower() in self.actions

    def __repr__(self):
        return f"<CheckScope line='{self.raw_line}' query='{self.build_danbooru_query()}' actions={self.actions}>"

def parse_checkfile(filepath: str) -> List[CheckScope]:
    """Đọc file checkfile.txt và trả về danh sách các CheckScope hợp lệ."""
    scopes = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            scopes.append(CheckScope(line))
    return scopes
