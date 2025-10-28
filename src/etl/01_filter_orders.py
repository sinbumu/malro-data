from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from src.utils.io import Paths


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


def filter_orderlike(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df[(df["발화자"].fillna("") == "c") & (df["QA여부"].fillna("") == "q")]
    pattern = re.compile(
        r"주문|추가|빼|변경|포장|테이크아웃|사이즈|샷|시럽|뜨거운|차가운|아이스|핫|수량|개|잔|세트|메뉴|옵션"
    )
    mask = df["발화문"].fillna("").str.contains(pattern)
    return df[mask]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    args = parser.parse_args()

    paths = Paths(root=Path(__file__).resolve().parents[2])
    df = load_domain_csvs(paths, args.domain)
    filtered = filter_orderlike(df)

    out_path = paths.data_interim / f"{args.domain}_orders.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    filtered.to_csv(out_path, index=False)
    print(f"[Filter] saved {len(filtered)} rows -> {out_path}")


if __name__ == "__main__":
    main()
