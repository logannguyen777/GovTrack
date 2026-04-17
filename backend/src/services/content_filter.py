"""
backend/src/services/content_filter.py
Simple keyword + heuristic content filter for citizen-facing chatbot.
No ML model required — keyword denylist + length/repetition heuristics.
"""

from __future__ import annotations

import re
import unicodedata


def _normalize(text: str) -> str:
    """Strip diacritics, lowercase — for denylist matching."""
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


# Vietnamese toxic/off-topic keywords (normalized, no diacritics)
_DENYLIST_RAW: list[str] = [
    # Toxic / hate
    "dit",
    "lon",
    "cac",
    "du ma",
    "con cho",
    "chet di",
    "thu dam",
    "hiep dam",
    "giet",
    "bom",
    # Off-topic / spam
    "casino",
    "co bac",
    "choi bai",
    "ma tuy",
    "sung",
    "vu khi",
    "hack",
    "crack",
    "jailbreak",
    "ignore previous",
    "forget instructions",
    # Political sensitivity
    "lat do",
    "bieu tinh",
    "chong chinh phu",
    "chong dang",
    # PII phishing attempts
    "cho toi mat khau",
    "so cccd",
    "so the tin dung",
    "tai khoan ngan hang",
]

_DENYLIST = [_normalize(w) for w in _DENYLIST_RAW]

# Hard limits
_MAX_LENGTH = 2000
_MAX_REPETITION_RATIO = 0.6  # if >60% chars are same char → spam


class ContentFilter:
    """
    Stateless content filter. Call check() before passing user input to LLM.
    Returns (allowed: bool, reason: str | None).
    """

    def check(self, text: str) -> tuple[bool, str | None]:
        """Return (True, None) if allowed. (False, reason) if blocked."""
        if not text or not text.strip():
            return False, "Nội dung không được để trống."

        # Length guard
        if len(text) > _MAX_LENGTH:
            return False, "Nội dung quá dài. Vui lòng rút gọn xuống dưới 2000 ký tự."

        # Repetition heuristic (spam / keyboard-mash detection)
        stripped = text.replace(" ", "")
        if stripped:
            most_common_char_count = max(stripped.count(c) for c in set(stripped))
            ratio = most_common_char_count / len(stripped)
            if ratio > _MAX_REPETITION_RATIO and len(stripped) > 20:
                return False, "Nội dung không hợp lệ. Vui lòng nhập câu hỏi rõ ràng."

        # Keyword denylist
        normalized = _normalize(text)
        for keyword in _DENYLIST:
            if keyword in normalized:
                return False, "Nội dung không phù hợp. Hệ thống chỉ hỗ trợ thủ tục hành chính."

        # Excessive special chars heuristic (obfuscation attempts)
        _safe_pattern = r"[^a-zA-Z0-9\s\u00C0-\u024F\u1E00-\u1EFF.,!?;:\"'()\-]"
        special_count = len(re.findall(_safe_pattern, text))
        if len(text) > 10 and special_count / len(text) > 0.3:
            return False, "Nội dung chứa quá nhiều ký tự đặc biệt. Vui lòng nhập lại."

        return True, None
