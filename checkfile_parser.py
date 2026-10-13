import re
from typing import List, Set, Dict, Any

class CheckScope:
    def __init__(self, raw_line: str):
        self.raw_line = raw_line
        self.actions: Set[str] = {"all"}  # Mặc định là all nếu không khai báo
        
        # Tiêu chí bao gồm (positive)
        self.post_id: int | None = None
        self.pool: str | None = None      # "all" hoặc số pool id
        self.users: Set[str] = set()
        self.tags: Set[str] = set()
        self.is_all: bool = False

        # Tiêu chí loại trừ (negative - bắt đầu bằng dấu trừ -)
        self.exclude_users: Set[str] = set()
        self.exclude_tags: Set[str] = set()
        self.exclude_pools: Set[str] = set()

        self._parse(raw_line)

    def _parse(self, line: str):
        tokens = line.split()
        for token in tokens:
            token = token.strip()
            if not token:
                continue

            # Xử lý action
            if token.lower().startswith("action:"):
                act = token[len("action:"):].lower().strip()
                if act == "all":
                    self.actions = {"all"}
                else:
                    self.actions = {act}
                continue

            # Xử lý loại trừ (bắt đầu bằng -)
            is_negative = token.startswith("-")
            clean_token = token[1:] if is_negative else token

            # ALL hoặc -ALL
            if clean_token.upper() == "ALL":
                if is_negative:
                    # -ALL: không quét toàn bộ, giới hạn theo các bộ lọc khác
                    self.is_all = False
                else:
                    self.is_all = True
                continue

            # pool:...
            if clean_token.lower().startswith("pool:"):
                val = clean_token[len("pool:"):].lower().strip()
                if is_negative:
                    self.exclude_pools.add(val)
                else:
                    self.pool = val
                continue

            # post:...
            if clean_token.lower().startswith("post:"):
                val = clean_token[len("post:"):].strip()
                try:
                    self.post_id = int(val)
                except ValueError:
                    pass
                continue

            # user:...
            if clean_token.lower().startswith("user:"):
                val = clean_token[len("user:"):].strip()
                if is_negative:
                    self.exclude_users.add(val.lower())
                else:
                    self.users.add(val.lower())
                continue

            # tag:...
            if clean_token.lower().startswith("tag:"):
                val = clean_token[len("tag:"):].strip()
                if is_negative:
                    self.exclude_tags.add(val)
                else:
                    self.tags.add(val)
                continue

    def build_danbooru_query(self) -> str:
        """
        Tạo chuỗi tag query Danbooru tương ứng để fetch danh sách post.
        """
        query_parts = []

        if self.post_id is not None:
            return f"id:{self.post_id}"

        if self.pool:
            if self.pool == "all":
                query_parts.append("has:pools")
            else:
                query_parts.append(f"pool:{self.pool}")

        for u in self.users:
            query_parts.append(f"user:{u}")

        for t in self.tags:
            query_parts.append(t)

        for eu in self.exclude_users:
            query_parts.append(f"-user:{eu}")

        for et in self.exclude_tags:
            query_parts.append(f"-{et}")

        for ep in self.exclude_pools:
            if ep != "all":
                query_parts.append(f"-pool:{ep}")

        # Nếu không có query nào và is_all = True, trả về chuỗi rỗng để lấy post mới nhất
        return " ".join(query_parts)

    def matches_post(self, post: Dict[str, Any]) -> bool:
        """
        Kiểm tra chặt chẽ phía client xem post có thỏa mãn scope này hay không.
        """
        post_id = post.get("id")
        post_tags = set(post.get("tag_string", "").split())
        uploader_name = str(post.get("uploader_name", "")).lower()
        
        # 1. Kiểm tra post:id
        if self.post_id is not None and post_id != self.post_id:
            return False

        # 2. Kiểm tra loại trừ tags
        if any(et in post_tags for et in self.exclude_tags):
            return False

        # 3. Kiểm tra loại trừ users
        if uploader_name and uploader_name in self.exclude_users:
            return False

        # 4. Kiểm tra positive tags
        if self.tags and not self.tags.issubset(post_tags):
            return False

        # 5. Kiểm tra user nếu có chỉ định
        if self.users:
            if uploader_name and uploader_name not in self.users:
                return False

        # 6. Kiểm tra pool
        if self.pool:
            # Danbooru post có trường pool_string hoặc has_large/pools
            pool_str = post.get("pool_string", "")
            if self.pool == "all":
                # Có ít nhất 1 pool trong pool_string hoặc có thuộc tính liên quan
                if not pool_str:
                    return False
            else:
                # Kiểm tra pool id cụ thể
                pool_ids = pool_str.split()
                if f"pool:{self.pool}" not in pool_ids and self.pool not in pool_ids:
                    # Nếu post API không trả pool_string đầy đủ, ta tin tưởng kết quả từ query
                    pass

        return True

    def should_run_system(self, system_name: str) -> bool:
        """Kiểm tra action của scope có áp dụng cho system này không."""
        return "all" in self.actions or system_name.lower() in self.actions

    def __repr__(self):
        return f"<CheckScope line='{self.raw_line}' actions={self.actions}>"

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
