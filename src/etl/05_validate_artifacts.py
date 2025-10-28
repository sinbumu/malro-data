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
