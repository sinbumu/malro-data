from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from src.utils.io import Paths, load_yaml


def load_domain_csvs(paths: Paths, domain: str) -> pd.DataFrame:
    glob = list((paths.data_raw).glob(f"{domain}_*.csv"))
    if not glob:
        raise FileNotFoundError(f"no raw CSVs for domain={domain} under {paths.data_raw}")
    dtype = {
        "IDX": "Int64",
        "발화자": "string",
        "발화문": "string",
        "카테고리": "string",
        "QA번호": "Int64",
        "QA여부": "string",
        "감성": "string",
        "인텐트": "string",
        "개체명": "string",
        "상담번호": "Int64",
        "상담내순번": "Int64",
    }
    frames = [pd.read_csv(p, dtype=dtype) for p in glob]
    df = pd.concat(frames, ignore_index=True)
    return df


def filter_orderlike(df: pd.DataFrame, patterns: dict) -> pd.DataFrame:
    df = df.copy()
    filters = (patterns.get("filters") or {}) if isinstance(patterns, dict) else {}
    speaker = str(filters.get("require_speaker", "c"))
    qa = str(filters.get("require_qa", "q"))
    cats = filters.get("category_whitelist") or []
    order_keywords = filters.get("order_keywords") or []
    gate_regex = filters.get("order_gate_regex")

    df = df[(df["발화자"].fillna("") == speaker) & (df["QA여부"].fillna("") == qa)]
    if cats:
        df = df[df["카테고리"].isin(cats)]

    if gate_regex:
        pat = re.compile(gate_regex)
        mask = df["발화문"].fillna("").str.contains(pat)
    elif order_keywords:
        safe = [re.escape(k) for k in order_keywords if isinstance(k, str)]
        pat = re.compile("(?:" + "|".join(safe) + ")") if safe else None
        mask = df["발화문"].fillna("").str.contains(pat) if pat else pd.Series(False, index=df.index)
    else:
        # fallback: 모두 통과
        mask = pd.Series(True, index=df.index)
    return df[mask]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    args = parser.parse_args()

    paths = Paths(root=Path(__file__).resolve().parents[2])
    df = load_domain_csvs(paths, args.domain)
    patterns = load_yaml(paths.configs / "patterns.yml") or {}
    filtered = filter_orderlike(df, patterns)

    out_path = paths.data_interim / f"{args.domain}_orders.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    filtered.to_csv(out_path, index=False)
    print(f"[Filter] saved {len(filtered)} rows -> {out_path}")


if __name__ == "__main__":
    main()
