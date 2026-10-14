import os
from typing import Set, List
from .base_system import BaseTagSystem
from .rule_models import parse_rule_line, RuleType

class ThreeTagSystem(BaseTagSystem):
    """
    Hệ thống 3 tag & N-tag:
    - Đọc TẤT CẢ các file .txt trong data/3tag/
    - Hỗ trợ cú pháp mới:
        1. Dạng mũi tên: `A B C -> D <E>`
           (Có đủ A B C thì thêm D, trừ khi có tag trong <E>)
        2. Dạng neo bắt buộc & suy luận tương hỗ: `?A B C D <E>` hoặc `?A B C` hoặc `?A ?B C D E <H I K>`
           (?A là bắt buộc phải có và không thêm. Thiếu đúng 1 tag trong tập ứng viên thì bù tag đó).
    """
    def __init__(self):
        super().__init__(name="3tag")
        self.rules: List[RuleType] = []

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
                for line in f:
                    rule = parse_rule_line(line)
                    if rule:
                        self.rules.append(rule)

    def evaluate(self, post_tags: Set[str]) -> Set[str]:
        tags_to_add = set()
        for rule in self.rules:
            result = rule.evaluate(post_tags)
            if result:
                tags_to_add.add(result)
        return tags_to_add

    def get_rule_count(self) -> int:
        return len(self.rules)
