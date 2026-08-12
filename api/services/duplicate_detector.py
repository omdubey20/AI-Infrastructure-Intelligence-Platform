"""
Multi-Signal Duplicate Detection Engine
Detects duplicate projects across different servers using:
- Exact name / domain match (across servers)
- Git remote URL match (across servers)
- High fuzzy name similarity (>0.85) (across servers)
"""
import json
import logging
from difflib import SequenceMatcher
from typing import List, Tuple

logger = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """Normalize project name for comparison."""
    if not name:
        return ""
    base = name.lower()
    for tld in [".co.uk", ".com", ".uk", ".org", ".net", ".io", ".local"]:
        base = base.replace(tld, "")
    return base.replace("-", "").replace("_", "").replace(".", "").replace(" ", "").strip()


def _similarity(a: str, b: str) -> float:
    """Return 0.0 to 1.0 fuzzy similarity ratio."""
    norm_a = _normalize_name(a)
    norm_b = _normalize_name(b)
    if not norm_a or not norm_b:
        return 0.0
    return SequenceMatcher(None, norm_a, norm_b).ratio()


def detect_duplicates(discoveries: list) -> List[dict]:
    """
    Run multi-signal duplicate detection across all discoveries.
    Returns list of dicts with duplicate metadata.
    Updates each discovery's duplicate flags in-place (caller must commit).
    """
    n = len(discoveries)
    duplicate_groups = {}  # id -> group_id
    signal_map = {}        # id -> list of signals

    for i in range(n):
        a = discoveries[i]
        if getattr(a, "user_override", None) == "keep":
            continue

        for j in range(i + 1, n):
            b = discoveries[j]
            if getattr(b, "user_override", None) == "keep":
                continue

            # Duplicates exist ONLY across different servers
            if a.server_id == b.server_id:
                continue

            signals = []
            confidence = 0

            norm_a = _normalize_name(a.project_name)
            norm_b = _normalize_name(b.project_name)

            # Signal 1: Exact domain / normalized name match across servers
            if norm_a and norm_b and norm_a == norm_b:
                signals.append("exact_name_match")
                confidence += 90

            # Signal 2: Domain match across servers
            elif a.domain and b.domain and a.domain.lower() == b.domain.lower():
                signals.append("domain_match")
                confidence += 90

            # Signal 3: Git remote match across servers
            if a.git_remote and b.git_remote:
                def norm_git(url):
                    return url.lower().replace(".git", "").replace("https://", "").replace("http://", "").replace("git@", "").replace(":", "/")
                if norm_git(a.git_remote) == norm_git(b.git_remote):
                    signals.append("git_remote_match")
                    confidence += 95

            # Signal 4: High fuzzy name similarity > 0.85
            if not signals and _similarity(a.project_name, b.project_name) > 0.85:
                signals.append("fuzzy_name_match")
                confidence += 75

            # Requires minimum 60% confidence
            if confidence >= 60 and signals:
                confidence = min(confidence, 98)

                a_live = bool(a.dns_points_here and a.web_config_active)
                b_live = bool(b.dns_points_here and b.web_config_active)

                if a_live and not b_live:
                    live_id, dup_id = a.id, b.id
                elif b_live and not a_live:
                    live_id, dup_id = b.id, a.id
                elif (a.size_mb or 0) >= (b.size_mb or 0):
                    live_id, dup_id = a.id, b.id
                else:
                    live_id, dup_id = b.id, a.id

                group_id = duplicate_groups.get(live_id, live_id)
                duplicate_groups[live_id] = group_id
                duplicate_groups[dup_id] = group_id

                signal_map[dup_id] = {
                    "signals": signals,
                    "confidence": confidence,
                    "duplicate_of_id": live_id,
                }

    results = []
    for disc in discoveries:
        if getattr(disc, "user_override", None) == "keep":
            disc.is_duplicate = False
            disc.duplicate_confidence = 0
            disc.duplicate_of_id = None
        elif disc.id in signal_map:
            sm = signal_map[disc.id]
            disc.is_duplicate = True
            disc.duplicate_confidence = sm["confidence"]
            disc.duplicate_of_id = sm["duplicate_of_id"]
            disc.duplicate_signals = json.dumps(sm["signals"])
            disc.recommendation = "delete"
            if disc.env_type not in ("live", "staging"):
                disc.env_type = "duplicate"
        else:
            if disc.id not in duplicate_groups:
                disc.is_duplicate = False
                disc.duplicate_confidence = 0
                disc.duplicate_of_id = None

        results.append({
            "id": disc.id,
            "project_name": disc.project_name,
            "server_id": disc.server_id,
            "is_duplicate": disc.is_duplicate,
            "duplicate_confidence": disc.duplicate_confidence,
            "duplicate_of_id": disc.duplicate_of_id,
            "duplicate_signals": signal_map.get(disc.id, {}).get("signals", []),
        })

    logger.info(f"Duplicate detection: {len(signal_map)} duplicates found in {n} projects")
    return results


def get_duplicate_pairs(discoveries: list) -> List[Tuple]:
    """Return list of (original, duplicate) discovery pairs."""
    id_map = {d.id: d for d in discoveries}
    pairs = []
    seen = set()
    for disc in discoveries:
        if disc.is_duplicate and disc.duplicate_of_id:
            pair_key = tuple(sorted([disc.id, disc.duplicate_of_id]))
            if pair_key not in seen and disc.duplicate_of_id in id_map:
                pairs.append((id_map[disc.duplicate_of_id], disc))
                seen.add(pair_key)
    return pairs
