from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from rapidfuzz import fuzz, process

from .io import load_yaml


@dataclass
class MenuMapping:
    phrase_to_sku: Dict[str, str]
    sku_to_phrases: Dict[str, List[str]]


def load_menu_mapping(menu_yaml_path: Path) -> MenuMapping:
    data = load_yaml(menu_yaml_path)
    sku_to_phrases: Dict[str, List[str]] = {}
    phrase_to_sku: Dict[str, str] = {}
    for sku, meta in data.get("sku", {}).items():
        phrases = list({meta.get("display", sku)})
        phrases.extend(meta.get("synonyms", []) or [])
        norm_phrases = sorted(set(p.strip() for p in phrases if p and isinstance(p, str)))
        sku_to_phrases[sku] = norm_phrases
        for ph in norm_phrases:
            phrase_to_sku[ph] = sku
    return MenuMapping(phrase_to_sku=phrase_to_sku, sku_to_phrases=sku_to_phrases)


def load_aliases_map(aliases_yaml_path: Path) -> Dict[str, dict]:
    if not aliases_yaml_path.exists():
        return {}
    data = load_yaml(aliases_yaml_path) or {}
    return {k: v for k, v in (data.get("aliases", {}) or {}).items() if isinstance(v, dict)}


def load_combined_mapping(menu_yaml_path: Path, aliases_yaml_path: Optional[Path] = None) -> MenuMapping:
    mapping = load_menu_mapping(menu_yaml_path)
    if aliases_yaml_path is None or not aliases_yaml_path.exists():
        return mapping
    aliases = load_aliases_map(aliases_yaml_path)
    # alias에 sku가 명시된 경우 phrase_to_sku에 추가
    for phrase, cfg in aliases.items():
        sku = cfg.get("sku")
        if isinstance(phrase, str) and sku:
            mapping.phrase_to_sku[phrase] = sku
            mapping.sku_to_phrases.setdefault(sku, []).append(phrase)
    return mapping


def find_sku_by_text(text: str, mapping: MenuMapping, threshold: int = 88) -> str | None:
    # 1) substring match 우선
    for ph, sku in mapping.phrase_to_sku.items():
        if ph and ph in text:
            return sku
    # 2) fuzzy match (partial ratio)
    all_phrases = list(mapping.phrase_to_sku.keys())
    if not all_phrases:
        return None
    cand = process.extractOne(text, all_phrases, scorer=fuzz.partial_ratio)
    if cand and cand[1] >= threshold:
        return mapping.phrase_to_sku[cand[0]]
    return None


def has_menu_phrase(text: str, mapping: MenuMapping) -> bool:
    for ph in mapping.phrase_to_sku.keys():
        if ph and ph in text:
            return True
    return False


