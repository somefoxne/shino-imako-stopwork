from typing import Dict, Type
from .base_system import BaseTagSystem
from .two_tag_system import TwoTagSystem
from .three_tag_system import ThreeTagSystem

# Đăng ký các hệ thống vào registry để dễ mở rộng và fix lỗi
SYSTEM_REGISTRY: Dict[str, Type[BaseTagSystem]] = {
    "2tag": TwoTagSystem,
    "3tag": ThreeTagSystem,
}

def get_system(name: str) -> BaseTagSystem | None:
    cls = SYSTEM_REGISTRY.get(name.lower())
    if cls:
        return cls()
    return None

def get_all_systems() -> Dict[str, BaseTagSystem]:
    return {name: cls() for name, cls in SYSTEM_REGISTRY.items()}
