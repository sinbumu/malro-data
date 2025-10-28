from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Tuple

from jsonschema import Draft202012Validator, RefResolver


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_schema_store(configs_dir: Path) -> Dict[str, dict]:
    """Load all *.schema.json under configs to a store keyed by $id."""
    store: Dict[str, dict] = {}
    for schema_path in configs_dir.glob("*.schema.json"):
        schema = load_json(schema_path)
        schema_id = schema.get("$id")
        if schema_id:
            store[schema_id] = schema
    return store


def validate_json(obj: dict, schema: dict, store: Dict[str, dict]) -> Tuple[bool, str]:
    resolver = RefResolver.from_schema(schema, store=store)
    validator = Draft202012Validator(schema, resolver=resolver)
    errors = sorted(validator.iter_errors(obj), key=lambda e: e.path)
    if errors:
        msg = "; ".join([f"{list(e.path)}: {e.message}" for e in errors])
        return False, msg
    return True, ""


def validate_jsonl(path: Path, schema: dict, store: Dict[str, dict]) -> Tuple[int, int, list]:
    ok, fail = 0, 0
    messages = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            valid, err = validate_json(obj, schema, store)
            if valid:
                ok += 1
            else:
                fail += 1
                messages.append(f"line {i}: {err}")
    return ok, fail, messages


