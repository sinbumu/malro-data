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
    data = load_yaml(menu_yaml_path) or {}
    sku_to_phrases: Dict[str, List[str]] = {}
    phrase_to_sku: Dict[str, str] = {}

    # 1) 신형 스키마: items: [ { sku, display, alt: [] } ]
    items = data.get("items")
    if isinstance(items, list) and items:
        for it in items:
            if not isinstance(it, dict):
                continue
            sku = it.get("sku")
            if not sku:
                continue
            phrases: List[str] = []
            disp = it.get("display")
            if isinstance(disp, str) and disp:
                phrases.append(disp)
            alt = it.get("alt") or []
            if isinstance(alt, list):
                phrases.extend([a for a in alt if isinstance(a, str)])
            # 고유화/정리
            norm_phrases = sorted(set(p.strip() for p in phrases if p and isinstance(p, str)))
            sku_to_phrases[sku] = norm_phrases
            for ph in norm_phrases:
                phrase_to_sku[ph] = sku
        return MenuMapping(phrase_to_sku=phrase_to_sku, sku_to_phrases=sku_to_phrases)

    # 2) 구형 스키마: sku: { SKU: { display, synonyms: [] } }
    for sku, meta in (data.get("sku", {}) or {}).items():
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
    raw_aliases = data.get("aliases", {})
    mapping: Dict[str, dict] = {}
    # 신형: aliases: [ { term: str, apply: { sku?, options? }, meta? } ]
    if isinstance(raw_aliases, list):
        for entry in raw_aliases:
            if not isinstance(entry, dict):
                continue
            term = entry.get("term")
            apply = entry.get("apply") or {}
            if isinstance(term, str) and isinstance(apply, dict) and term:
                mapping[term] = apply
        return mapping
    # 구형: aliases: { phrase: { sku?, options? } }
    if isinstance(raw_aliases, dict):
        for k, v in raw_aliases.items():
            if isinstance(k, str) and isinstance(v, dict):
                mapping[k] = v
    return mapping


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


