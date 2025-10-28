from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd

from src.utils.io import Paths, write_jsonl


def to_gold(text: str) -> dict:
    # 간단한 정답 생성 휴리스틱 (스키마 적합성만 보장)
    return {"order": {"items": [{"sku": "AMERICANO", "quantity": 1}]}}


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

    sample = df.sample(n=min(args.n, len(df)), random_state=123)
    rows: List[dict] = []
    for _, r in sample.iterrows():
        text = str(r.get("발화문", ""))
        rows.append({"input": text, "gold": to_gold(text)})

    out_dir = paths.outputs / args.domain
    write_jsonl(out_dir / "evalset.jsonl", rows)
    print(f"[EvalSet] saved {len(rows)} lines -> {out_dir / 'evalset.jsonl'}")


if __name__ == "__main__":
    main()
