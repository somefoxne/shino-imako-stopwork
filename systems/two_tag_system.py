import os
from typing import Set, List
from .base_system import BaseTagSystem

class TwoTagRule:
    def __init__(self, source: str, target: str, negatives: Set[str]):
        self.source = source          # Tag A
        self.target = target          # Tag B
        self.negatives = negatives    # Danh sách các tag loại trừ (-D, -E...)

    def evaluate(self, post_tags: Set[str]) -> str | None:
        """
        Nếu post có tag loại trừ -> bỏ qua.
        Nếu post có A và CHƯA có B -> trả về tag B để thêm vào.
        Nếu post đã có B hoặc không có A -> trả về None (kệ nó).
        """
        # Nếu bài viết có bất kỳ tag loại trừ nào thì không áp dụng
        if any(neg in post_tags for neg in self.negatives):
            return None

        # Có A và thiếu B
        if self.source in post_tags and self.target not in post_tags:
            return self.target

        return None

class TwoTagSystem(BaseTagSystem):
    """
    Hệ thống 2 tag (A -> B -D):
    - Đọc TẤT CẢ các file .txt trong thư mục data/2tag/ (ví dụ rules.txt, custom.txt, list.txt...)
    - Logic: Nếu post có A nhưng thiếu B, và không chứa D -> thêm B.
    """
    def __init__(self):
        super().__init__(name="2tag")
        self.rules: List[TwoTagRule] = []

    def load_rules(self, data_dir_or_file: str) -> None:
        self.rules.clear()
        self.loaded_files.clear()
        files_to_read = []

        if os.path.isdir(data_dir_or_file):
            for root, _, files in os.walk(data_dir_or_file):
                for fname in sorted(files):
                    if fname.lower().endswith(".txt"):
                        files_to_read.append(os.path.join(root, fname))
        elif os.path.isfile(data_dir_or_file):
            files_to_read.append(data_dir_or_file)

        for filepath in files_to_read:
            self.loaded_files.append(os.path.basename(filepath))
            with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    self._parse_rule_line(line, filepath, line_num)

    def _parse_rule_line(self, line: str, filepath: str, line_num: int) -> None:
        # Cú pháp: A -> B -D -E...
        if "->" not in line:
            return

        parts = line.split("->")
        source = parts[0].strip()
        right_side = parts[1].strip().split()

        if not right_side:
            return

        target = right_side[0].strip()
        negatives = set()
        for item in right_side[1:]:
            item = item.strip()
            if item.startswith("-"):
                negatives.add(item[1:].strip())
            else:
                negatives.add(item)

        if source and target:
            self.rules.append(TwoTagRule(source=source, target=target, negatives=negatives))

    def evaluate(self, post_tags: Set[str]) -> Set[str]:
        tags_to_add = set()
        for rule in self.rules:
            result = rule.evaluate(post_tags)
            if result:
                tags_to_add.add(result)
        return tags_to_add

    def get_rule_count(self) -> int:
        return len(self.rules)
