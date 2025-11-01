from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.utils.io import Paths, write_jsonl, load_yaml
from src.utils.menu import load_combined_mapping, has_menu_phrase, load_aliases_map
from src.utils.validation import load_json
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
    aliases_map = load_aliases_map(paths.configs / f"aliases.{args.domain}.yml")
    menu_mapping = load_combined_mapping(paths.configs / f"menu.{args.domain}.yml", paths.configs / f"aliases.{args.domain}.yml")
    # menu constraints from exported JSON
    menu_json = load_json(paths.outputs / args.domain / "menu.json")
    sku_conf = {it.get("sku"): it for it in (menu_json.get("items") or []) if isinstance(it, dict)}
    patterns = load_yaml(paths.configs / "patterns.yml") or {}

    import re
    # 새로운 구조: filters.order_gate_regex 또는 filters.order_keywords 사용
    filters = patterns.get("filters", {}) or {}
    gate_pat = filters.get("order_gate_regex")
    order_keywords = filters.get("order_keywords") or []
    if gate_pat:
        order_regexes = [re.compile(gate_pat)]
    else:
        if order_keywords:
            safe = [re.escape(k) for k in order_keywords if isinstance(k, str)]
            order_regexes = [re.compile("(?:" + "|".join(safe) + ")")]
        else:
            order_regexes = []

    def is_order_text(text: str) -> bool:
        if not order_regexes:
            return True
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
            # 멀티 아이템 파싱 시 aliases 암시 옵션 반영을 위해 재파싱
            from src.utils.parse import parse_order_items
            items = parse_order_items(text, menu_mapping, aliases_map)
            # filter options by sku constraints & schema-allowed keys
            filtered_items = []
            for it in items:
                sku = it.get("sku")
                conf = sku_conf.get(sku, {})
                allowed_schema = {"size", "temp", "shot", "syrup", "ice"}
                allow_options = set(conf.get("allow_options") or [])
                if conf.get("sizes_enabled"):
                    allow_options.add("size")
                temps = set(conf.get("temps") or [])
                opts = it.get("options") or {}
                if isinstance(opts, dict):
                    new_opts = {}
                    for k, v in opts.items():
                        if k not in allowed_schema:
                            continue
                        if k != "temp" and k not in allow_options:
                            continue
                        if k == "temp" and temps and v not in temps:
                            continue
                        new_opts[k] = v
                    if new_opts:
                        it["options"] = new_opts
                    elif "options" in it:
                        del it["options"]
                filtered_items.append(it)
            items = filtered_items
            if not items:
                continue
            rows.append({"input": text, "label": "ORDER_DRAFT", "target": {"order": {"items": items}}})
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
