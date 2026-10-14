import re
from typing import Set, Optional, Union

class ImplicationRule:
    """
    Dạng 1: A B C -> D <E I K>
    - Post có ĐỦ tất cả tag nguồn bên trái (A, B, C)
    - Post KHÔNG chứa bất kỳ tag nào trong <...> (E, I, K)
    - Post CHƯA có D
    -> Thêm D
    """
    def __init__(self, sources: Set[str], target: str, exclusions: Set[str], raw_text: str = ""):
        self.sources = sources
        self.target = target
        self.exclusions = exclusions
        self.raw_text = raw_text

    def evaluate(self, post_tags: Set[str]) -> Optional[str]:
        # 1. Nếu dính tag loại trừ trong <...> -> HỦY
        if any(ex in post_tags for ex in self.exclusions):
            return None

        # 2. Phải có ĐỦ tất cả tag nguồn
        if not self.sources.issubset(post_tags):
            return None

        # 3. Nếu chưa có target -> Thêm target
        if self.target not in post_tags:
            return self.target

        return None

    def __repr__(self):
        ex_str = f" <{' '.join(sorted(self.exclusions))}>" if self.exclusions else ""
        return f"<ImplicationRule {' '.join(sorted(self.sources))} -> {self.target}{ex_str}>"


class AnchorCandidateRule:
    """
    Dạng 2: ?A ?B C D E <H I K>
    - Tag bắt đầu bằng '?' (vd: ?A, ?B): Tag BẮT BUỘC phải có (và KHÔNG bao giờ được tự động thêm)
    - Tag không có '?': Tập tag ứng viên suy luận (C, D, E)
    - Tag trong <...>: Tag loại trừ (H, I, K)

    Quy tắc suy luận:
    1. Post có bất kỳ tag loại trừ nào -> HỦY
    2. Post thiếu bất kỳ tag bắt buộc (?) nào -> HỦY
    3. Trong tập tag ứng viên:
       Nếu post đã có (tổng số ứng viên - 1) tag, tức là THIẾU ĐÚNG 1 TAG:
       -> Bổ sung tag còn thiếu đó!
       Ví dụ:
       - ?A B C D : Có A, B, C -> thêm D; Có A, C, D -> thêm B; Có B, C, D (thiếu A) -> không thêm
       - ?A B C   : Có A, B -> thêm C; Có A, C -> thêm B; Có B, C -> không thêm
       - ?A B     : Có A -> thêm B; Có B -> không làm gì A
    """
    def __init__(self, required: Set[str], candidates: Set[str], exclusions: Set[str], raw_text: str = ""):
        self.required = required
        self.candidates = candidates
        self.exclusions = exclusions
        self.raw_text = raw_text

    def evaluate(self, post_tags: Set[str]) -> Optional[str]:
        # 1. Nếu dính tag loại trừ -> HỦY
        if any(ex in post_tags for ex in self.exclusions):
            return None

        # 2. Nếu thiếu bất kỳ tag bắt buộc (?) nào -> HỦY
        if not self.required.issubset(post_tags):
            return None

        # 3. Xét tập tag ứng viên
        present = self.candidates.intersection(post_tags)
        missing = self.candidates - present

        # Nếu thiếu đúng 1 tag trong tập ứng viên -> Bổ sung tag đó
        if len(missing) == 1:
            return next(iter(missing))

        return None

    def __repr__(self):
        req_str = " ".join(f"?{t}" for t in sorted(self.required))
        cand_str = " ".join(sorted(self.candidates))
        ex_str = f" <{' '.join(sorted(self.exclusions))}>" if self.exclusions else ""
        return f"<AnchorCandidateRule {req_str} {cand_str}{ex_str}>"


RuleType = Union[ImplicationRule, AnchorCandidateRule]

def parse_rule_line(line: str) -> Optional[RuleType]:
    """
    Phân tích dòng quy tắc theo cú pháp mới:
    1. A B C -> D <E I K>
    2. ?A ?B C D E <H I K> hoặc ?A B C D hoặc ?A B C hoặc ?A B
    """
    raw_line = line.strip()
    if not raw_line or raw_line.startswith("#"):
        return None

    line = raw_line

    # 1. Tách phần loại trừ trong dấu ngoặc nhọn <...>
    exclusions = set()
    match = re.search(r'<([^>]+)>', line)
    if match:
        exclusion_content = match.group(1).strip()
        for tok in exclusion_content.split():
            clean_tok = tok.strip().lstrip("-")
            if clean_tok:
                exclusions.add(clean_tok)
        line = re.sub(r'<[^>]+>', '', line).strip()

    # Hỗ trợ thêm cú pháp cũ có dấu trừ (-tag) nếu người dùng viết sót
    clean_tokens = []
    for tok in line.split():
        if tok.startswith("-") and len(tok) > 1:
            exclusions.add(tok[1:])
        else:
            clean_tokens.append(tok)

    line = " ".join(clean_tokens).strip()
    if not line:
        return None

    # 2. Dạng mũi tên: A B C -> D
    if "->" in line:
        parts = line.split("->", 1)
        sources = set(parts[0].split())
        targets = parts[1].split()
        if not sources or not targets:
            return None
        target = targets[0].strip()
        # Nếu có thêm token phía sau target, coi như exclusions
        for extra in targets[1:]:
            exclusions.add(extra.strip().lstrip("-"))
        return ImplicationRule(sources=sources, target=target, exclusions=exclusions, raw_text=raw_line)

    # 3. Dạng neo bắt buộc (?) và ứng viên suy luận: ?A B C D
    tokens = line.split()
    required = set()
    candidates = set()

    for tok in tokens:
        if tok.startswith("?"):
            tag_name = tok[1:].strip()
            if tag_name:
                required.add(tag_name)
        else:
            candidates.add(tok.strip())

    if not candidates:
        return None

    return AnchorCandidateRule(required=required, candidates=candidates, exclusions=exclusions, raw_text=raw_line)
