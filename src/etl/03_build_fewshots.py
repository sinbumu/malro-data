from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.utils.io import Paths, write_jsonl


def to_order_draft(text: str) -> Dict:
    # 매우 단순한 휴리스틱: 아메리카노/라떼 키워드, 수량 숫자, 온도/사이즈 한글 힌트
    t = text
    sku = None
    if "아메리카노" in t:
        sku = "AMERICANO"
    elif "라떼" in t:
        sku = "VANILLA_LATTE" if "바닐라" in t else "LATTE"
    qty = 1
    for tok in t.split():
        if tok.isdigit():
            qty = int(tok)
            break
    temp = "ICE" if any(x in t for x in ["아이스", "차가운", "아아"]) else None
    if temp is None and any(x in t for x in ["뜨거운", "핫", "뜨아"]):
        temp = "HOT"
    size = "L" if any(x in t for x in ["라지", "벤티"]) else ("M" if "톨" in t else None)
    item = {"sku": sku or "AMERICANO", "quantity": qty}
    opts = {k: v for k, v in {"temp": temp, "size": size}.items() if v is not None}
    if opts:
        item["options"] = opts
    return {"order": {"items": [item]}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--k", type=int, default=50)
    args = parser.parse_args()

    paths = Paths(root=Path(__file__).resolve().parents[2])
    interim = paths.data_interim / f"{args.domain}_orders.csv"
    if not interim.exists():
        raise FileNotFoundError(f"missing interim file: {interim}")
    df = pd.read_csv(interim)

    rows: List[dict] = []
    for _, r in df.sample(n=min(args.k, len(df)), random_state=42).iterrows():
        text = str(r.get("발화문", ""))
        # 간단히 두 가지 라벨을 혼합 생성
        draft = to_order_draft(text)
        rows.append({"input": text, "label": "ORDER_DRAFT", "target": draft})
        rows.append({
            "input": text,
            "label": "ASK",
            "missing_slots": ["size", "temp"],
            "question": "온도(ICE/HOT)와 사이즈(S/M/L)를 알려주세요."
        })

    out_dir = paths.outputs / args.domain
    write_jsonl(out_dir / "few_shots.jsonl", rows)
    print(f"[FewShots] saved {len(rows)} lines -> {out_dir / 'few_shots.jsonl'}")


if __name__ == "__main__":
    main()
