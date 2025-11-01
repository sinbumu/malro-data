from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from src.utils.io import Paths, load_yaml, write_json


def compile_menu(menu_yaml: dict) -> Dict[str, Any]:
    # 메뉴 YAML을 런타임 친화 JSON으로 변환 (불필요한 정책/주석 제거)
    result: Dict[str, Any] = {"version": menu_yaml.get("version", "0.1.0"), "items": []}
    items = menu_yaml.get("items") or []
    for it in items:
        if not isinstance(it, dict):
            continue
        out: Dict[str, Any] = {
            "sku": it.get("sku"),
            "display": it.get("display"),
        }
        # sizes/temps
        if isinstance(it.get("temps"), list):
            out["temps"] = it["temps"]
        if isinstance(it.get("base_price"), dict):
            out["base_price"] = it["base_price"]
        if it.get("sizes_enabled") is not None:
            out["sizes_enabled"] = bool(it.get("sizes_enabled"))
        # allow_options 제한은 참고용으로 포함
        if isinstance(it.get("allow_options"), list):
            out["allow_options"] = it["allow_options"]
        result["items"].append(out)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    args = parser.parse_args()

    paths = Paths(root=Path(__file__).resolve().parents[2])
    menu_yaml = load_yaml(paths.configs / f"menu.{args.domain}.yml")
    compiled = compile_menu(menu_yaml)
    out_dir = paths.outputs / args.domain
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "menu.json", compiled)
    print(f"[Menu] exported -> {out_dir / 'menu.json'}")


if __name__ == "__main__":
    main()


