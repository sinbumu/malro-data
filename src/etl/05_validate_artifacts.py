from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from src.utils.io import Paths, file_sha256, write_json
from src.utils.validation import (
    load_json,
    load_schema_store,
    validate_json,
    validate_jsonl,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    args = parser.parse_args()

    paths = Paths(root=Path(__file__).resolve().parents[2])
    out_dir = paths.outputs / args.domain
    aliases_p = out_dir / "aliases.json"
    few_p = out_dir / "few_shots.jsonl"
    eval_p = out_dir / "evalset.jsonl"
    menu_p = out_dir / "menu.json"

    store = load_schema_store(paths.configs)
    slots_schema = load_json(paths.configs / "slots.schema.json")
    aliases_schema = load_json(paths.configs / "aliases.schema.json")
    few_schema = load_json(paths.configs / "few_shots.schema.json")
    eval_schema = load_json(paths.configs / "evalset.schema.json")
    manifest_schema = load_json(paths.configs / "artifact_manifest.schema.json")

    # Validate aliases.json
    aliases_obj = load_json(aliases_p)
    ok, err = validate_json(aliases_obj, aliases_schema, store)
    if not ok:
        raise SystemExit(f"aliases.json invalid: {err}")

    # Validate few_shots.jsonl
    ok_cnt, fail_cnt, messages = validate_jsonl(few_p, few_schema, store)
    if fail_cnt > 0:
        raise SystemExit(f"few_shots.jsonl invalid lines={fail_cnt}: {messages[:3]}")

    # Validate evalset.jsonl
    ok_cnt, fail_cnt, messages = validate_jsonl(eval_p, eval_schema, store)
    if fail_cnt > 0:
        raise SystemExit(f"evalset.jsonl invalid lines={fail_cnt}: {messages[:3]}")

    # Preflight: menu option allowance & enum normalization
    if not menu_p.exists():
        raise SystemExit("menu.json not found. Run export menu step first.")
    menu_obj = load_json(menu_p)
    sku_to_conf = {it.get("sku"): it for it in menu_obj.get("items", []) if isinstance(it, dict)}

    def check_items_in_lines(jsonl_path):
        problems = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for ln, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception as e:
                    problems.append((ln, f"json parse error: {e}"))
                    continue
                data = obj.get("target") or obj.get("gold") or {}
                order = (data or {}).get("order") or {}
                for item in (order.get("items") or []):
                    sku = item.get("sku")
                    conf = sku_to_conf.get(sku)
                    if not conf:
                        problems.append((ln, f"unknown sku: {sku}"))
                        continue
                    allowed = set(conf.get("allow_options") or [])
                    if conf.get("sizes_enabled"):
                        allowed.add("size")
                    temps = set(conf.get("temps") or [])
                    opts = (item.get("options") or {}) if isinstance(item.get("options"), dict) else {}
                    # key allow check
                    for k in opts.keys():
                        if k not in {"size", "temp", "shot", "syrup", "ice"}:
                            problems.append((ln, f"unsupported option key: {k}"))
                        elif k not in allowed and k != "temp":
                            problems.append((ln, f"option not allowed for {sku}: {k}"))
                    # enum/value check
                    if "size" in opts and opts["size"] not in {"S", "M", "L"}:
                        problems.append((ln, f"invalid size: {opts['size']}"))
                    if "temp" in opts and opts["temp"] not in {"ICE", "HOT"}:
                        problems.append((ln, f"invalid temp: {opts['temp']}"))
                    if "temp" in opts and temps and opts["temp"] not in temps:
                        problems.append((ln, f"temp not supported for {sku}: {opts['temp']}"))
                    if "ice" in opts and opts["ice"] not in {"less", "normal", "more"}:
                        problems.append((ln, f"invalid ice: {opts['ice']}"))
                    if "shot" in opts and (not isinstance(opts["shot"], int) or opts["shot"] < 0):
                        problems.append((ln, f"invalid shot: {opts['shot']}"))
        return problems

    problems_few = check_items_in_lines(few_p)
    problems_eval = check_items_in_lines(eval_p)
    problems = [("few_shots", ln, msg) for ln, msg in problems_few] + [("evalset", ln, msg) for ln, msg in problems_eval]
    if problems:
        preview = ", ".join([f"{src}:{ln} {msg}" for src, ln, msg in problems[:5]])
        raise SystemExit(f"preflight failed: {len(problems)} issues. e.g. {preview}")

    # Alias conflicts (non-fatal warnings): same term mapping in configs
    try:
        cfg_aliases_path = paths.configs / f"aliases.{args.domain}.yml"
        if cfg_aliases_path.exists():
            import yaml
            with open(cfg_aliases_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            entries = cfg.get("aliases", [])
            seen = {}
            conflicts = []
            if isinstance(entries, list):
                for e in entries:
                    if not isinstance(e, dict):
                        continue
                    term = e.get("term")
                    sku = (e.get("apply") or {}).get("sku")
                    if not term:
                        continue
                    prev = seen.get(term)
                    if prev and sku and prev != sku:
                        conflicts.append((term, prev, sku))
                    if sku:
                        seen[term] = sku
            if conflicts:
                print(f"[Validate][warn] alias conflicts detected: {len(conflicts)} (e.g. {conflicts[:3]})")
    except Exception as _:
        pass

    # Manifest
    # source hash: 합쳐서 계산(간단히 aliases만 기준으로 예시)
    source_hash = file_sha256(aliases_p)
    manifest = {
        "domain": args.domain,
        "version": "0.1.0",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "counts": {
            "aliases": len(aliases_obj),
            "few_shots": sum(1 for _ in open(few_p, "r", encoding="utf-8")),
            "evalset": sum(1 for _ in open(eval_p, "r", encoding="utf-8")),
        },
        "source_hash": source_hash,
        "patterns_version": "2025-10-20",
    }
    ok, err = validate_json(manifest, manifest_schema, store)
    if not ok:
        raise SystemExit(f"manifest invalid: {err}")
    write_json(out_dir / "artifact_manifest.json", manifest)
    print(f"[Validate] artifacts valid. manifest -> {out_dir / 'artifact_manifest.json'}")


if __name__ == "__main__":
    main()
