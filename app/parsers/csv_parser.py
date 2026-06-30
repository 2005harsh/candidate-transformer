"""CSV parser for candidate exports using csv.DictReader."""

from __future__ import annotations

import csv
import io
import re
from typing import Any, Dict, Iterable, List, Optional

from ..services.normalizer import Normalizer

import requests

from .base import BaseParser


_SPLIT_RE = re.compile(r"[,;\n\r•]+")


def _ensure_list(v: Optional[Any]) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if x]
    if isinstance(v, str):
        parts = [p.strip() for p in _SPLIT_RE.split(v) if p and p.strip()]
        return parts
    return [str(v)]


def _first_field(row: Dict[str, Any], candidates: Iterable[str]) -> Optional[Any]:
    for c in candidates:
        if c in row and row[c] not in (None, ""):
            return row[c]
    return None


class CSVParser(BaseParser):
    """Parser for CSV candidate exports. Extracts one or more candidate fields."""

    COMMON_NAME = ["name", "full_name", "full name", "candidate", "displayname", "display name"]
    COMMON_EMAIL = ["email", "emails", "email_address", "e-mail"]
    COMMON_PHONE = ["phone", "phone_number", "phone number", "phones", "mobile"]
    COMMON_SKILLS = ["skills", "skillset", "technologies", "tech"]
    COMMON_TITLE = ["title", "headline", "position", "role"]
    COMMON_LOCATION = ["location", "city", "region", "country", "address"]
    COMMON_LINKS = ["linkedin", "github", "profiles", "links", "url", "urls"]

    def get_source_name(self) -> str:
        return self.source_path_str

    def parse(self) -> List[Dict[str, Any]]:
        if not self.validate_source():
            raise ValueError(f"Source not valid or reachable: {self.source_path_str}")

        text_stream = None
        if self.source_path and self.source_path.exists():
            f = open(self.source_path_str, "r", encoding="utf-8", errors="ignore")
            text_stream = f
        else:
            resp = requests.get(self.source_path_str, timeout=15)
            resp.raise_for_status()
            text_stream = io.StringIO(resp.text)

        try:
            reader = csv.DictReader(text_stream)
            candidates: List[Dict[str, Any]] = []
            for row in reader:
                if row is None:
                    continue

                norm_row = {k.strip().lower(): v for k, v in row.items() if k is not None}
                candidate = self._normalize_row(norm_row, row)
                if candidate:
                    candidates.append(candidate)

            return candidates
        finally:
            if self.source_type == "file":
                f.close()

    def parse_one(self) -> Dict[str, Any]:
        """Return the first candidate from the CSV for backward compatibility."""
        candidates = self.parse()
        if candidates:
            return candidates[0]
        return {"raw": None}

    def get_all_candidates(self) -> List[Dict[str, Any]]:
        """Return all candidates parsed from the CSV."""
        return self.parse()

    def _normalize_row(self, norm_row: Dict[str, Any], raw_row: Dict[str, Any]) -> Dict[str, Any]:
        name = _first_field(norm_row, self.COMMON_NAME) or None
        emails = _ensure_list(_first_field(norm_row, self.COMMON_EMAIL))
        phones = _ensure_list(_first_field(norm_row, self.COMMON_PHONE))
        title = _first_field(norm_row, self.COMMON_TITLE) or None
        skills = _ensure_list(_first_field(norm_row, self.COMMON_SKILLS))
        location_value = _first_field(norm_row, self.COMMON_LOCATION) or None
        location = self._parse_location(location_value)

        links = []
        for k in norm_row:
            if any(key in k for key in self.COMMON_LINKS):
                val = norm_row.get(k)
                if val:
                    links.extend(_ensure_list(val))

        skill_objects = []
        for skill in skills:
            skill_objects.append({"name": skill, "confidence": 1.0})

        return {
            "candidate_id": norm_row.get("id") or norm_row.get("candidate_id"),
            "full_name": name,
            "emails": emails,
            "phones": phones,
            "headline": title,
            "skills": skill_objects,
            "location": location,
            "links": links,
            "current_company": _first_field(norm_row, ["company", "current_company", "current company", "employer"]) or None,
            "raw": raw_row,
        }

    def _parse_location(self, location_value: Optional[Any]) -> Optional[Dict[str, Any]]:
        if not location_value:
            return None

        if isinstance(location_value, dict):
            return location_value

        text = str(location_value).strip()
        if not text:
            return None

        parts = [part.strip() for part in text.split(",") if part and part.strip()]
        if len(parts) == 0:
            return None

        location: Dict[str, Any] = {"raw": text}
        if len(parts) == 1:
            location["city"] = parts[0]
        elif len(parts) == 2:
            location["city"] = parts[0]
            location["region"] = parts[1]
        else:
            location["city"] = parts[0]
            location["region"] = parts[1]
            location["country"] = parts[-1]

        return location
