import sqlite3
import os
import time
from typing import Set, Tuple, Optional

class HistoryManager:
    """
    Quản lý lịch sử thêm tag của Bot bằng SQLite database.
    Mục đích:
    - Tránh 'edit war' (chiến tranh tag) khi tag bot thêm bị người dùng khác xóa.
    - Cung cấp chính sách:
        + 'never': Đã từng thêm nhưng bị xóa -> KHÔNG bao giờ add lại.
        + 'after_edits': Đã từng bị xóa -> Chỉ add lại khi đã có ít nhất N lượt sửa từ người khác.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_edit_history (
                    post_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    version_at_edit INTEGER DEFAULT 0,
                    edited_at REAL NOT NULL,
                    PRIMARY KEY (post_id, tag)
                )
            """)
            conn.commit()

    def record_edits(self, post_id: int, tags: Set[str], current_version: int = 0):
        """Ghi nhận các tag vừa được bot thêm vào bài viết."""
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for tag in tags:
                cursor.execute("""
                    INSERT INTO bot_edit_history (post_id, tag, version_at_edit, edited_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(post_id, tag) DO UPDATE SET
                        version_at_edit = excluded.version_at_edit,
                        edited_at = excluded.edited_at
                """, (post_id, tag, current_version, now))
            conn.commit()

    def check_tag_permission(
        self,
        post_id: int,
        tag: str,
        current_version: int,
        policy: str = "never",
        min_edits: int = 5
    ) -> Tuple[bool, str]:
        """
        Kiểm tra xem tag này có được phép thêm vào post_id hay không.
        Trả về: (cho_phép: bool, lý_do: str)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT version_at_edit, edited_at 
                FROM bot_edit_history 
                WHERE post_id = ? AND tag = ?
            """, (post_id, tag))
            row = cursor.fetchone()

        # 1. Bot chưa từng thêm tag này cho post này -> Hoàn toàn hợp lệ
        if not row:
            return True, "Tag mới chưa từng được bot thêm"

        # 2. Tag này ĐÃ TỪNG được bot thêm, nhưng hiện tại post lại bị thiếu (nghĩa là đã bị người khác xóa đi)
        last_version, _ = row
        policy_clean = policy.strip().lower()

        # Chính sách NEVER: Không bao giờ add lại nếu bị xóa
        if policy_clean == "never":
            return False, f"Tag '{tag}' đã từng được bot thêm nhưng bị người khác xóa. Bỏ qua theo chính sách không add lại (never)."

        # Chính sách AFTER_EDITS: Chỉ add lại sau N lượt chỉnh sửa từ người khác
        if policy_clean in ("after_edits", "edits") or policy_clean.isdigit():
            threshold = int(policy_clean) if policy_clean.isdigit() else min_edits
            
            # Tính số lượt chỉnh sửa kể từ lần bot sửa trước
            diff_edits = current_version - last_version
            if diff_edits < threshold:
                return False, f"Tag '{tag}' đã bị xóa. Mới có {diff_edits}/{threshold} lượt chỉnh sửa sau đó, chưa đủ điều kiện add lại."
            else:
                return True, f"Tag '{tag}' đã trải qua {diff_edits} >= {threshold} lượt chỉnh sửa của người khác. Cho phép add lại."

        return True, "Hợp lệ"
