from __future__ import annotations

import re
from typing import Optional, Tuple

from .menu import MenuMapping, find_sku_by_text


KOR_NUM_MAP = {
    "한": 1, "하나": 1, "1": 1,
    "두": 2, "둘": 2, "2": 2,
    "세": 3, "셋": 3, "3": 3,
    "네": 4, "넷": 4, "4": 4,
    "다섯": 5, "5": 5,
    "여섯": 6, "6": 6,
    "일곱": 7, "7": 7,
    "여덟": 8, "8": 8,
    "아홉": 9, "9": 9,
    "열": 10, "10": 10,
    "열한": 11, "열하나": 11, "11": 11,
    "열두": 12, "열둘": 12, "12": 12,
    "열세": 13, "열셋": 13, "13": 13,
    "열네": 14, "열넷": 14, "14": 14,
    "열다섯": 15, "15": 15,
    "열여섯": 16, "16": 16,
    "열일곱": 17, "17": 17,
    "열여덟": 18, "18": 18,
    "열아홉": 19, "19": 19,
    "스무": 20, "스물": 20, "20": 20,
}


def parse_quantity(text: str) -> Optional[int]:
    t = text.strip()
    # 1) 숫자 + 단위
    m = re.search(r"(\d{1,3})\s*(잔|개|병|세트|컵)", t)
    if m:
        return int(m.group(1))
    # 2) 한글수 + 단위
    for tok, val in sorted(KOR_NUM_MAP.items(), key=lambda x: -len(x[0])):
        if re.search(fr"{tok}\s*(잔|개|병|세트|컵)", t):
            return val
    # 3) 단독 숫자 토큰
    m = re.search(r"\b(\d{1,3})\b", t)
    if m:
        return int(m.group(1))
    return None


def detect_temp(text: str) -> Optional[str]:
    t = text
    if any(x in t for x in ["아이스", "차가운", "아아"]):
        return "ICE"
    if any(x in t for x in ["뜨거운", "핫", "뜨아"]):
        return "HOT"
    return None


def detect_size(text: str) -> Optional[str]:
    t = text
    if any(x in t for x in ["라지", "벤티"]):
        return "L"
    if any(x in t for x in ["톨", "레귤러", "미디움"]):
        return "M"
    return None


def detect_sku(text: str, menu_mapping: Optional[MenuMapping] = None) -> Optional[str]:
    t = text
    if menu_mapping is not None:
        return find_sku_by_text(t, menu_mapping)
    # fallback 간단 규칙
    if "아메리카노" in t or "아아" in t or "뜨아" in t:
        return "AMERICANO"
    if "바닐라 라떼" in t or "바닐라라떼" in t:
        return "VANILLA_LATTE"
    if "라떼" in t:
        return "LATTE"
    return None


def split_order_segments(text: str) -> list[str]:
    # 쉼표/접속사 기준 분할: ",", "그리고", "랑", "와", "및"
    parts = re.split(r"[\s,]*(?:그리고|랑|와|및|,)[\s,]*", text)
    parts = [p.strip() for p in parts if p and p.strip()]
    return parts


def parse_order_items(text: str, menu_mapping: Optional[MenuMapping]) -> list[dict]:
    items: list[dict] = []
    for seg in split_order_segments(text):
        sku = detect_sku(seg, menu_mapping)
        if not sku:
            continue
        qty = parse_quantity(seg) or 1
        temp = detect_temp(seg)
        size = detect_size(seg)
        item = {"sku": sku, "quantity": qty}
        opts = {k: v for k, v in {"temp": temp, "size": size}.items() if v is not None}
        if opts:
            item["options"] = opts
        items.append(item)
    return items


