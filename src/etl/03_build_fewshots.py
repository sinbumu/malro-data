from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.utils.io import Paths, write_jsonl, load_yaml
from src.utils.menu import load_menu_mapping, has_menu_phrase
from src.utils.parse import detect_sku, detect_size, detect_temp, parse_quantity, parse_order_items


def to_order_or_ask(text: str, menu_mapping) -> Dict:
    t = text
    items = parse_order_items(t, menu_mapping)
    if not items:
        missing = ["sku"]
        return {
            "label": "ASK",
            "missing_slots": missing,
            "question": "메뉴와 (ICE/HOT), 사이즈(S/M/L)를 알려주세요.",
        }
    return {"label": "ORDER_DRAFT", "target": {"order": {"items": items}}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--k", type=int, default=50)
    parser.add_argument("--only_order_draft", action="store_true", help="ASK 샘플 제외")
    parser.add_argument("--max_ask_ratio", type=float, default=0.4, help="ASK 최대 비율")
    args = parser.parse_args()

    paths = Paths(root=Path(__file__).resolve().parents[2])
    interim = paths.data_interim / f"{args.domain}_orders.csv"
    if not interim.exists():
        raise FileNotFoundError(f"missing interim file: {interim}")
    df = pd.read_csv(interim)
    menu_mapping = load_menu_mapping(paths.configs / f"menu.{args.domain}.yml")
    patterns = load_yaml(paths.configs / "patterns.yml")

    import re
    order_regexes = [re.compile(p) for p in (patterns.get("intents", {}).get("order", {}).get("include_regex", []) or [])]

    def is_order_text(text: str) -> bool:
        t = str(text)
        return any(r.search(t) for r in order_regexes)

    rows: List[dict] = []
    for _, r in df.sample(n=min(args.k, len(df)), random_state=42).iterrows():
        text = str(r.get("발화문", ""))
        # 메뉴 언급이 없거나 주문 동사 미포함이면 스킵
        if not has_menu_phrase(text, menu_mapping) or not is_order_text(text):
            continue
        res = to_order_or_ask(text, menu_mapping)
        if res["label"] == "ORDER_DRAFT":
            rows.append({"input": text, "label": res["label"], "target": res["target"]})
        else:
            if args.only_order_draft:
                continue
            rows.append({
                "input": text,
                "label": "ASK",
                "missing_slots": res["missing_slots"],
                "question": res["question"],
            })

    # ASK 비율 제한
    if not args.only_order_draft and rows:
        drafts = [r for r in rows if r["label"] == "ORDER_DRAFT"]
        asks = [r for r in rows if r["label"] == "ASK"]
        max_ask = int(len(drafts) * args.max_ask_ratio)
        asks = asks[:max_ask]
        rows = drafts + asks

    out_dir = paths.outputs / args.domain
    write_jsonl(out_dir / "few_shots.jsonl", rows)
    print(f"[FewShots] saved {len(rows)} lines -> {out_dir / 'few_shots.jsonl'}")


if __name__ == "__main__":
    main()
