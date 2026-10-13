import os
from typing import Set, List
from .base_system import BaseTagSystem

class ThreeTagRule:
    def __init__(self, tag_a: str, tag_b: str, tag_c: str, negatives: Set[str]):
        self.tags: Set[str] = {tag_a, tag_b, tag_c}
        self.negatives: Set[str] = negatives

    def evaluate(self, post_tags: Set[str]) -> str | None:
        """
        Logic 3-tag (? A B C -D):
        - Nếu post có bất kỳ tag nào trong negatives (D, ...) -> Bỏ qua.
        - Kiểm tra sự xuất hiện của {A, B, C}:
          + Nếu có 2 trong 3 tag và thiếu 1 tag -> Thêm tag còn thiếu.
          + Nếu đã có cả 3 tag -> Không cần thêm.
          + Nếu chỉ có 1 hoặc 0 tag -> Không làm gì.
        """
        # Nếu bài viết có chứa bất kỳ tag loại trừ nào thì không thêm
        if any(neg in post_tags for neg in self.negatives):
            return None

        present_tags = self.tags.intersection(post_tags)
        
        # Nếu có đúng 2 trong 3 tag, tìm tag thứ 3 còn thiếu
        if len(present_tags) == 2:
            missing_tags = self.tags - present_tags
            if len(missing_tags) == 1:
                return next(iter(missing_tags))

        return None

class ThreeTagSystem(BaseTagSystem):
    """
    Hệ thống 3 tag:
    - Đọc TẤT CẢ các file .txt trong thư mục data/3tag/ (ví dụ rules.txt, characters.txt...)
    - Định dạng: `? A B C -D` hoặc `A B C -D -E`
    - Tự động suy luận quan hệ tam giác: nếu có 2 tag thì bổ sung tag thứ 3.
    """
    def __init__(self):
        super().__init__(name="3tag")
        self.rules: List[ThreeTagRule] = []

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
        # Hỗ trợ cú pháp bắt đầu bằng ? hoặc không:
        # Ví dụ: ? tag_a tag_b tag_c -tag_d
        tokens = line.split()
        if tokens and tokens[0] == "?":
            tokens = tokens[1:]

        positive_tags = []
        negatives = set()

        for token in tokens:
            token = token.strip()
            if not token:
                continue
            if token.startswith("-"):
                negatives.add(token[1:].strip())
            else:
                positive_tags.append(token)

        # Hệ thống 3 tag yêu cầu chính xác 3 tag dương
        if len(positive_tags) == 3:
            self.rules.append(
                ThreeTagRule(
                    tag_a=positive_tags[0],
                    tag_b=positive_tags[1],
                    tag_c=positive_tags[2],
                    negatives=negatives
                )
            )

    def evaluate(self, post_tags: Set[str]) -> Set[str]:
        tags_to_add = set()
        for rule in self.rules:
            missing_tag = rule.evaluate(post_tags)
            if missing_tag:
                tags_to_add.add(missing_tag)
        return tags_to_add

    def get_rule_count(self) -> int:
        return len(self.rules)
