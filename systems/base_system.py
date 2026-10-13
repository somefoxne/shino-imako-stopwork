from abc import ABC, abstractmethod
from typing import Set, List, Dict, Any

class BaseTagSystem(ABC):
    """
    Lớp cơ sở cho các hệ thống kiểm tra và đề xuất cập nhật tag.
    Mọi hệ thống luật mới (2-tag, 3-tag, n-tag...) chỉ cần kế thừa lớp này.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def load_rules(self, data_dir_or_file: str) -> None:
        """Đọc và nạp các luật từ file hoặc thư mục dữ liệu."""
        pass

    @abstractmethod
    def evaluate(self, post_tags: Set[str]) -> Set[str]:
        """
        Kiểm tra danh sách tag hiện tại của post dựa trên các luật đã nạp.
        Trả về tập hợp các tag cần THÊM vào post.
        """
        pass

    @abstractmethod
    def get_rule_count(self) -> int:
        """Trả về số lượng quy tắc hiện đang nạp."""
        pass
