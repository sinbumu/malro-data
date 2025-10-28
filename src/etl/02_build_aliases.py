from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Dict

import pandas as pd

from src.utils.io import Paths, load_yaml, write_json


def extract_alias_candidates(df: pd.DataFrame) -> Dict[str, dict]:
    # 간단한 휴리스틱: 상위 빈도 축약어 매핑 예시(도메인별 강화 가능)
    text_col = df["발화문"].astype(str).fillna("")
    tokens = []
    for t in text_col:
        tokens.extend(t.replace("/", " ").split())
    freq = Counter(tokens)
    aliases: Dict[str, dict] = {}
    # 대표 축약 예시 고정 룰(초안)
    rules = {
        "아아": {"sku": "AMERICANO", "temp": "ICE"},
        "뜨아": {"sku": "AMERICANO", "temp": "HOT"},
        "톨": {"size": "M"},
        "라지": {"size": "L"},
    }
    for k, v in rules.items():
        if freq.get(k, 0) > 0:
            aliases[k] = v
    return aliases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    args = parser.parse_args()

    paths = Paths(root=Path(__file__).resolve().parents[2])
    interim = paths.data_interim / f"{args.domain}_orders.csv"
    if not interim.exists():
        raise FileNotFoundError(f"missing interim file: {interim}")
    df = pd.read_csv(interim)

    cfg_patterns = load_yaml(paths.configs / "patterns.yml")
    _ = cfg_patterns  # reserved for future advanced rules

    aliases = extract_alias_candidates(df)

    out_dir = paths.outputs / args.domain
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "aliases.json", aliases)
    print(f"[Aliases] saved {len(aliases)} aliases -> {out_dir / 'aliases.json'}")


if __name__ == "__main__":
    main()
