from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd

from src.utils.io import Paths, write_jsonl
from src.utils.menu import load_combined_mapping, load_aliases_map
from src.utils.parse import parse_order_items


def to_gold(text: str, menu_mapping) -> dict | None:
    items = parse_order_items(text, menu_mapping)
    if not items:
        return None
    return {"order": {"items": items}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--n", type=int, default=300)
    args = parser.parse_args()

    paths = Paths(root=Path(__file__).resolve().parents[2])
    interim = paths.data_interim / f"{args.domain}_orders.csv"
    if not interim.exists():
        raise FileNotFoundError(f"missing interim file: {interim}")
    df = pd.read_csv(interim)
    aliases_map = load_aliases_map(paths.configs / f"aliases.{args.domain}.yml")
    menu_mapping = load_combined_mapping(paths.configs / f"menu.{args.domain}.yml", paths.configs / f"aliases.{args.domain}.yml")

    sample = df.sample(n=min(args.n * 3, len(df)), random_state=123)
    rows: List[dict] = []
    for _, r in sample.iterrows():
        text = str(r.get("발화문", ""))
        gold = to_gold(text, menu_mapping)
        if gold is None:
            continue
        # 암시 옵션 반영 재파싱
        items = parse_order_items(text, menu_mapping, aliases_map)
        rows.append({"input": text, "gold": {"order": {"items": items}}})

    out_dir = paths.outputs / args.domain
    # 상한 n 유지
    rows = rows[: args.n]
    write_jsonl(out_dir / "evalset.jsonl", rows)
    print(f"[EvalSet] saved {len(rows)} lines -> {out_dir / 'evalset.jsonl'}")


if __name__ == "__main__":
    main()
