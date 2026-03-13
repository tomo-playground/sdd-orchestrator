"""Korean text preprocessing for TTS.

Converts numbers, dates, units, and special patterns to spoken Korean
to improve Qwen3-TTS pronunciation accuracy.
"""

from __future__ import annotations

import re

# --- 한글 숫자 매핑 ---
_DIGITS_KO = {
    "0": "영", "1": "일", "2": "이", "3": "삼", "4": "사",
    "5": "오", "6": "육", "7": "칠", "8": "팔", "9": "구",
}
_UNITS = ["", "만", "억", "조"]
_SUB_UNITS = ["", "십", "백", "천"]
_DIGITS_NATIVE = {
    1: "한", 2: "두", 3: "세", 4: "네", 5: "다섯",
    6: "여섯", 7: "일곱", 8: "여덟", 9: "아홉", 10: "열",
    20: "스물", 30: "서른", 40: "마흔", 50: "쉰",
}
_COUNTER_WORDS = {"개", "명", "번", "잔", "살", "마리", "장", "권", "대", "벌", "켤레", "그루"}


def _num_to_sino(n: int) -> str:
    """Convert integer to Sino-Korean reading (일이삼...)."""
    if n == 0:
        return "영"
    if n < 0:
        return "마이너스 " + _num_to_sino(-n)

    result = []
    s = str(n)
    length = len(s)

    for i, ch in enumerate(s):
        d = int(ch)
        pos = length - i - 1  # position from right
        big_unit = pos // 4
        sub_pos = pos % 4

        # Guard: _UNITS only covers up to 조 (10^16). Fall back to digit-by-digit.
        if big_unit >= len(_UNITS):
            return "".join(_DIGITS_KO[c] for c in s)

        if d == 0:
            # Add big unit marker at 4-digit group boundary if group has non-zero digits
            if sub_pos == 0 and big_unit > 0:
                group_start = max(0, i - 3)
                if any(int(s[j]) != 0 for j in range(group_start, i)):
                    result.append(_UNITS[big_unit])
            continue

        if d == 1 and sub_pos > 0:
            result.append(_SUB_UNITS[sub_pos])
        else:
            result.append(_DIGITS_KO[ch] + _SUB_UNITS[sub_pos])

        if sub_pos == 0 and big_unit > 0:
            result.append(_UNITS[big_unit])

    return "".join(result)


def _num_to_native(n: int) -> str:
    """Convert integer (1-99) to native Korean reading (하나둘셋...)."""
    if n <= 0 or n >= 100:
        return _num_to_sino(n)
    if n in _DIGITS_NATIVE:
        return _DIGITS_NATIVE[n]
    tens = (n // 10) * 10
    ones = n % 10
    parts = []
    if tens > 0 and tens in _DIGITS_NATIVE:
        parts.append(_DIGITS_NATIVE[tens])
    if ones > 0 and ones in _DIGITS_NATIVE:
        parts.append(_DIGITS_NATIVE[ones])
    return "".join(parts) if parts else _num_to_sino(n)


def _convert_year(m: re.Match) -> str:
    """2026년 → 이천이십육년."""
    return _num_to_sino(int(m.group(1))) + "년"


def _convert_month_day(m: re.Match) -> str:
    """3월, 13일."""
    num = int(m.group(1))
    suffix = m.group(2)
    return _num_to_sino(num) + suffix


def _convert_counter(m: re.Match) -> str:
    """5개 → 다섯 개, 3명 → 세 명."""
    num = int(m.group(1))
    counter = m.group(2)
    if num < 100:
        return _num_to_native(num) + " " + counter
    return _num_to_sino(num) + " " + counter


def _convert_temperature(m: re.Match) -> str:
    """영하 5도 → 영하 오도, 30도 → 삼십도."""
    prefix = m.group(1) or ""
    num = int(m.group(2))
    return prefix + _num_to_sino(num) + "도"


def _convert_time(m: re.Match) -> str:
    """3시 30분 → 세 시 삼십 분."""
    hour = int(m.group(1))
    minute = m.group(2)
    result = _num_to_native(hour) + " 시"
    if minute:
        result += " " + _num_to_sino(int(minute)) + " 분"
    return result


def _convert_percent(m: re.Match) -> str:
    """50% → 오십 퍼센트."""
    return _num_to_sino(int(m.group(1))) + " 퍼센트"


def _convert_duration(m: re.Match) -> str:
    """3시간 → 삼시간, 5분간 → 오분간."""
    num = int(m.group(1))
    suffix = m.group(2)
    return _num_to_sino(num) + suffix


def _convert_plain_number(m: re.Match) -> str:
    """Standalone numbers → Sino-Korean."""
    return _num_to_sino(int(m.group(0)))


_COUNTER_PATTERN = re.compile(r"(\d+)\s*(" + "|".join(_COUNTER_WORDS) + ")")


def preprocess_korean(text: str) -> str:
    """Convert numbers and patterns in Korean text to spoken form."""
    # Year (4-digit + 년)
    text = re.sub(r"(\d{4})년", _convert_year, text)

    # Month/Day (월, 일)
    text = re.sub(r"(\d{1,2})(월|일)", _convert_month_day, text)

    # Temperature (영하/영상 + 숫자 + 도)
    text = re.sub(r"(영하\s*|영상\s*)?(\d+)도", _convert_temperature, text)

    # Time (시, 분) — negative lookahead to avoid matching "시간", "시즌", "시작" etc.
    text = re.sub(r"(\d{1,2})시(?!간|즌|작|리|험|합|설|청)\s*(?:(\d{1,2})분)?", _convert_time, text)

    # Percent
    text = re.sub(r"(\d+)%", _convert_percent, text)

    # Counter words (native Korean numerals)
    text = _COUNTER_PATTERN.sub(_convert_counter, text)

    # Duration (시간, 분간, 초간)
    text = re.sub(r"(\d+)(시간|분간|초간)", _convert_duration, text)

    # Remaining standalone numbers (use lookaround for Korean context)
    text = re.sub(r"(?<![가-힣])(\d+)(?![가-힣\d])", _convert_plain_number, text)

    return text
