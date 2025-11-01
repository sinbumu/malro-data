from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

from src.utils.io import Paths, write_json
from src.utils.menu import load_aliases_map


def _normalize_alias_apply(apply: dict) -> dict:
    out: Dict[str, object] = {}
    # sku
    sku = apply.get("sku")
    if isinstance(sku, str):
        out["sku"] = sku
    # options
    opts = apply.get("options") or {}
    if isinstance(opts, dict):
        # 화이트리스트만 허용 (slots.schema.json 호환)
        allowed = {"size", "temp", "shot", "syrup", "ice"}
        norm: Dict[str, object] = {}
        for k, v in opts.items():
            if k not in allowed:
                continue
            if k == "shot":
                # "+1" -> 1
                if isinstance(v, str):
                    import re
                    m = re.search(r"[-+]?\d+", v)
                    if m:
                        try:
                            norm[k] = max(0, int(m.group(0)))
                        except ValueError:
                            pass
                elif isinstance(v, int):
                    norm[k] = max(0, v)
            elif k == "size":
                norm[k] = "L" if v == "XL" else v
            elif k == "ice":
                if isinstance(v, str):
                    up = v.upper()
                    mp = {"NONE": "less", "LESS": "less", "REGULAR": "normal", "MORE": "more",
                          "less": "less", "normal": "normal", "more": "more"}
                    if up in mp or v in mp:
                        norm[k] = mp.get(up, mp.get(v))
            else:
                norm[k] = v
        out.update(norm)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    args = parser.parse_args()

    paths = Paths(root=Path(__file__).resolve().parents[2])
    aliases_map = load_aliases_map(paths.configs / f"aliases.{args.domain}.yml")

    out_obj: Dict[str, dict] = {}
    for term, apply in aliases_map.items():
        normalized = _normalize_alias_apply(apply)
        if not normalized:
            continue
        out_obj[term] = normalized

    out_dir = paths.outputs / args.domain
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "aliases.json", out_obj)
    print(f"[Aliases] saved {len(out_obj)} aliases -> {out_dir / 'aliases.json'}")


if __name__ == "__main__":
    main()
